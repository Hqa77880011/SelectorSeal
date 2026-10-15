import copy
import json
import threading


METHODS = [
    "selectorseal",
    "full_exact",
    "whole_table",
    "query_cache",
    "no_negative_domains",
    "display_name",
    "split_check_effect",
]


def resolve(state, query):
    return [
        row
        for row in state["objects"].values()
        if all(row.get(key) == value for key, value in query.items())
    ]


def permit(state, principal, objects):
    return all(principal in row.get("members", []) for row in objects) and not any(
        deny["principal"] == principal and any(row["tenant"] == deny["tenant"] for row in objects)
        for deny in state["denies"].values()
    )


def identities(rows, display=False):
    return sorted(row["name"] if display else [row["id"], row["generation"]] for row in rows)


def affected(write, query, principal, negative=True, coarse=False):
    if coarse:
        return write["table"] in ("objects", "denies")
    images = [write.get("before"), write.get("after")]
    if write["table"] == "objects":
        return any(
            image is not None and all(image.get(k) == v for k, v in query.items())
            for image in images
        )
    if write["table"] == "denies" and negative:
        return any(
            image is not None
            and image.get("principal") == principal
            and image.get("tenant") == query.get("tenant")
            for image in images
        )
    return False


class State:
    def __init__(self, value):
        self.value = copy.deepcopy(value)
        self.revision = 0
        self.journal = []
        self.receipts = {}
        self.approvals = {}
        self.lock = threading.RLock()

    def apply(self, write):
        with self.lock:
            table = self.value[write["table"]]
            before = copy.deepcopy(table.get(write["key"]))
            after = copy.deepcopy(write.get("after"))
            if after is None:
                table.pop(write["key"], None)
            else:
                table[write["key"]] = after
            self.revision += 1
            self.journal.append(
                {**write, "before": before, "after": after, "revision": self.revision}
            )

    def approve(self, query, principal, action, destination, nonce):
        with self.lock:
            rows = resolve(self.value, query)
            if not rows or not permit(self.value, principal, rows):
                raise ValueError("Approval requires a nonempty authorized snapshot")
            certificate = {
                "query": copy.deepcopy(query),
                "principal": principal,
                "action": action,
                "destination": destination,
                "nonce": nonce,
                "revision": self.revision,
                "identities": identities(rows),
                "names": identities(rows, True),
                "objects": copy.deepcopy(rows),
            }
            self.approvals[nonce] = copy.deepcopy(certificate)
            return certificate

    def execute(self, certificate, method, late_writes=()):
        with self.lock:
            nonce = certificate["nonce"]
            if nonce not in self.approvals or certificate != self.approvals[nonce]:
                return {"status": "DENIED", "recomputed": False, "objects": [], "replayed": False}
            if nonce in self.receipts:
                return {**self.receipts[nonce], "replayed": True}
            query = certificate["query"]
            principal = certificate["principal"]
            selected = certificate["objects"]
            writes = [w for w in self.journal if w["revision"] > certificate["revision"]]
            recompute = method == "full_exact" or any(
                affected(
                    w,
                    query,
                    principal,
                    negative=method != "no_negative_domains",
                    coarse=method == "whole_table",
                )
                for w in writes
            )
            if method == "query_cache":
                recompute = False
            for write in late_writes:
                self.apply(write)
            if late_writes and method != "split_check_effect":
                recompute |= any(
                    affected(w, query, principal)
                    for w in self.journal
                    if w["revision"] > certificate["revision"]
                )
            status = "COMMITTED"
            if recompute:
                selected = resolve(self.value, query)
                current_ids = identities(selected, method == "display_name")
                approved_ids = (
                    certificate["names"] if method == "display_name" else certificate["identities"]
                )
                if not all(item in approved_ids for item in current_ids):
                    status = "RECONSENT"
                elif current_ids != approved_ids:
                    status = "RETRY"
                elif not permit(self.value, principal, selected):
                    status = "DENIED"
            result = {
                "status": status,
                "recomputed": recompute,
                "objects": identities(selected) if status == "COMMITTED" else [],
                "replayed": False,
            }
            if status == "COMMITTED":
                self.receipts[nonce] = result
            return result


def generate(rng, count):
    for index in range(count):
        objects = {
            str(i): {
                "id": str(i),
                "generation": 1,
                "name": f"doc-{i}",
                "tenant": "t",
                "tag": "approved" if i < 2 else "other",
                "members": ["u"],
                "color": 0,
            }
            for i in range(4)
        }
        initial = {"objects": objects, "denies": {}}
        attack = rng.choice(["none", "deny", "expand", "shrink", "irrelevant", "generation"])
        if attack == "deny":
            write = {"table": "denies", "key": "ban", "after": {"principal": "u", "tenant": "t"}}
        else:
            key = "2" if attack == "expand" else "0"
            after = copy.deepcopy(objects[key])
            if attack == "expand":
                after["tag"] = "approved"
            elif attack == "shrink":
                after["tag"] = "other"
            elif attack == "generation":
                after["generation"] = 2
            else:
                after["color"] = 1
            write = {"table": "objects", "key": key, "after": after}
        late = rng.random() < 0.3
        yield {
            "id": str(index),
            "family": attack,
            "initial": initial,
            "query": {"tenant": "t", "tag": "approved"},
            "principal": "u",
            "writes": [] if late or attack == "none" else [write],
            "late_writes": [write] if late and attack != "none" else [],
        }


def run_case(case, method):
    state = State(case["initial"])
    certificate = state.approve(case["query"], case["principal"], "export", "local", case["id"])
    for write in case["writes"]:
        state.apply(write)
    result = state.execute(certificate, method, case["late_writes"])
    result["certificate_bytes"] = len(json.dumps(certificate).encode())
    result["final_state"] = state.value
    return result


def score(case, result):
    rows = resolve(result["final_state"], case["query"])
    initial = resolve(case["initial"], case["query"])
    oracle = identities(rows) == identities(initial) and permit(
        result["final_state"], case["principal"], rows
    )
    committed = result["status"] == "COMMITTED"
    scope_bad = committed and not all(item in identities(initial) for item in result["objects"])
    policy_bad = committed and not permit(result["final_state"], case["principal"], rows)
    return {
        "uar": int(committed and not oracle),
        "object_scope_violation": int(scope_bad),
        "policy_violation": int(policy_bad),
        "task_success": int(committed and oracle),
        "false_denial": int(not committed) if oracle else None,
        "reauthorization": int(result["recomputed"]),
        "retry": int(result["status"] == "RETRY"),
        "reconsent": int(result["status"] == "RECONSENT"),
        "false_reuse": int(not oracle) if not result["recomputed"] else None,
        "false_invalidation": int(result["recomputed"] and oracle),
        "certificate_bytes": result["certificate_bytes"],
        "legal_effects": len(result["objects"]) if oracle and committed else 0,
    }
