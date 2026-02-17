from __future__ import annotations

from dataclasses import dataclass
import unittest

from icl.contract_tests import run_contract_suite
from icl.errors import ExpansionError
from icl.ir import IRModule, IRStmt
from icl.lowering import Lowerer


class ContractMatrixTests(unittest.TestCase):
    def test_stable_contract_suite_ok(self) -> None:
        report = run_contract_suite(stable_only=True)
        self.assertTrue(report["ok"])
        for target, summary in report["summary"].items():
            self.assertEqual(summary["stability"], "stable")
            self.assertTrue(summary["target_ok"], msg=f"stable target failed: {target}")
            self.assertTrue(summary["all_cases_ok"], msg=f"stable target has failing cases: {target}")

    def test_experimental_matrix_enforces_unsupported_features(self) -> None:
        report = run_contract_suite(stable_only=False, targets=["typescript"])
        self.assertTrue(report["ok"])

        matrix = report["feature_matrix"]["typescript"]["features"]
        self.assertEqual(matrix["typed_annotation"]["status"], "unsupported_enforced")
        self.assertEqual(matrix["logic"]["status"], "unsupported_enforced")
        self.assertEqual(matrix["at_call"]["status"], "unsupported_enforced")


class StructuredLoweringErrorsTests(unittest.TestCase):
    def test_unknown_ir_statement_raises_structured_error(self) -> None:
        @dataclass
        class UnsupportedStmt(IRStmt):
            pass

        module = IRModule(
            ir_id="mod0",
            span=None,
            schema_version="2.0",
            statements=[UnsupportedStmt(ir_id="stmt0", span=None)],
            inferred_types={},
        )

        with self.assertRaises(ExpansionError) as ctx:
            Lowerer().lower(module, target="python", feature_coverage={})

        self.assertEqual(ctx.exception.code, "LOW002")


if __name__ == "__main__":
    unittest.main()
