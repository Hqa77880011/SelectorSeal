import copy
import random
import unittest

from selectorseal import core


class SelectorSealTests(unittest.TestCase):
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
