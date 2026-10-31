import copy
import random
import unittest

from selectorseal import core


class SelectorSealTests(unittest.TestCase):
    def test_bound_certificate_rejects_boolean_for_integer_generation(self):
        case = self.case()
        state = core.State(case["initial"])
        cert = state.approve(case["query"], "u", "export", "local", "n")
        cert["identities"][0][1] = True
        cert["objects"][0]["generation"] = True
        self.assertEqual(state.execute(cert, "selectorseal")["status"], "DENIED")

    def test_deleted_object_requires_fresh_generation(self):
        case = self.case()
        state = core.State(case["initial"])
        cert = state.approve(case["query"], "u", "export", "local", "n")
        row = copy.deepcopy(case["initial"]["objects"]["0"])
        state.apply(dict(table="objects", key="0", after=None))
        with self.assertRaisesRegex(ValueError, "generation"):
            state.apply(dict(table="objects", key="0", after=row))
        row["generation"] = 2
        state.apply(dict(table="objects", key="0", after=row))
        self.assertEqual(state.execute(cert, "selectorseal")["status"], "RECONSENT")

    def test_selector_distinguishes_missing_null_and_boolean_integer(self):
        state = {"objects": {"a": {"flag": True}, "b": {"flag": None}, "c": {}}}
        self.assertEqual(core.resolve(state, {"flag": 1}), [])
        self.assertEqual(core.resolve(state, {"flag": None}), [{"flag": None}])

    def test_receipt_replay_is_immutable_to_caller_changes(self):
        case = self.case()
        state = core.State(case["initial"])
        cert = state.approve(case["query"], "u", "export", "local", "n")
        first = state.execute(cert, "selectorseal")
        expected = copy.deepcopy(first["objects"])
        first["objects"].clear()
        replay = state.execute(cert, "selectorseal")
        self.assertEqual(replay["objects"], expected)
        replay["objects"].clear()
        self.assertEqual(state.execute(cert, "selectorseal")["objects"], expected)

    def case(self):
        case = next(core.generate(random.Random(17), 1))
        case.update(writes=[], late_writes=[])
        return case

    def test_color_change_is_semantically_irrelevant(self):
        case = self.case()
        after = {**case["initial"]["objects"]["0"], "color": 1}
        case["writes"] = [dict(table="objects", key="0", after=after)]
        result = core.run_case(case, "selectorseal")
        self.assertEqual(result["status"], "COMMITTED")
        self.assertFalse(result["recomputed"])

    def test_nonce_cannot_be_rebound_and_receipt_is_idempotent(self):
        case = self.case()
        state = core.State(case["initial"])
        cert = state.approve(case["query"], "u", "export", "local", "n")
        first = state.execute(cert, "selectorseal")
        self.assertFalse(first["replayed"])
        self.assertTrue(state.execute(cert, "selectorseal")["replayed"])
        with self.assertRaisesRegex(ValueError, "nonce|Nonce"):
            state.approve(case["query"], "u", "export", "remote", "n")

    def test_negative_domain_and_generation_changes_block_commit(self):
        for write in [
            dict(table="denies", key="ban", after=dict(principal="u", tenant="t")),
            dict(
                table="objects",
                key="0",
                after={**self.case()["initial"]["objects"]["0"], "generation": 2},
            ),
        ]:
            case = self.case()
            case["late_writes"] = [copy.deepcopy(write)]
            self.assertNotEqual(
                core.run_case(case, "selectorseal")["status"], "COMMITTED"
            )


if __name__ == "__main__":
    unittest.main()
