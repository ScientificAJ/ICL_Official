"""Language contract test harness for pack validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from icl.errors import CompilerError
from icl.language_pack import PackRegistry
from icl.main import compile_source, default_pack_registry


@dataclass(frozen=True)
class ContractCase:
    """Single contract fixture for cross-target compilation checks."""

    name: str
    source: str
    features: tuple[str, ...]
    required_for_stable: bool = True


@dataclass
class CaseResult:
    """Result for one case/target compilation run."""

    case: str
    target: str
    ok: bool
    error_code: str | None
    error_message: str | None


CONTRACT_CASES: list[ContractCase] = [
    ContractCase(
        name="assignment_arithmetic",
        source="x := 1 + 2;",
        features=("assignment", "arithmetic", "literal"),
    ),
    ContractCase(
        name="reference_reuse",
        source="x := 1; y := x + 2;",
        features=("assignment", "reference", "arithmetic", "literal"),
    ),
    ContractCase(
        name="function_call_return",
        source="fn add(a, b) { ret a + b; } out := add(1, 2);",
        features=(
            "function",
            "return",
            "call",
            "assignment",
            "arithmetic",
            "literal",
            "reference",
        ),
    ),
    ContractCase(
        name="if_else_comparison",
        source="x := 2; if x > 1 ? { y := x; } : { y := 0; }",
        features=("if", "comparison", "assignment", "literal", "reference"),
    ),
    ContractCase(
        name="loop_update",
        source="sum := 0; loop i in 0..3 { sum := sum + i; }",
        features=("loop", "assignment", "arithmetic", "literal", "reference"),
    ),
    ContractCase(
        name="unary_logic",
        source="ok := true && !false;",
        features=("assignment", "logic", "unary", "literal"),
    ),
    ContractCase(
        name="expression_stmt_call",
        source="print(1);",
        features=("expression_stmt", "call", "literal"),
    ),
    ContractCase(
        name="typed_annotation",
        source="v:Num := 1;",
        features=("typed_annotation", "assignment", "literal"),
    ),
    ContractCase(
        name="at_call",
        source="fn inc(n) { ret n + 1; } z := @inc(1);",
        features=("at_call", "call", "function", "return", "assignment", "arithmetic", "literal", "reference"),
    ),
]


ALL_FEATURES: tuple[str, ...] = tuple(sorted({feature for case in CONTRACT_CASES for feature in case.features}))
REQUIRED_STABLE_FEATURES: tuple[str, ...] = tuple(
    sorted({feature for case in CONTRACT_CASES if case.required_for_stable for feature in case.features})
)


def run_contract_suite(
    *,
    targets: list[str] | None = None,
    stable_only: bool = True,
    plugin_specs: list[str] | None = None,
    registry: PackRegistry | None = None,
) -> dict[str, Any]:
    """Run canonical contract cases for selected targets."""
    registry = registry or default_pack_registry()

    if targets:
        selected_targets = targets
    else:
        stability = "stable" if stable_only else None
        selected_targets = registry.targets(stability=stability)

    results: list[CaseResult] = []
    plugin_specs = plugin_specs or []

    for target in selected_targets:
        for case in CONTRACT_CASES:
            try:
                compile_source(
                    case.source,
                    target=target,
                    plugin_specs=plugin_specs,
                    optimize=False,
                    debug=False,
                    pack_registry=registry,
                )
            except CompilerError as err:
                results.append(
                    CaseResult(
                        case=case.name,
                        target=target,
                        ok=False,
                        error_code=err.code,
                        error_message=err.message,
                    )
                )
            else:
                results.append(
                    CaseResult(
                        case=case.name,
                        target=target,
                        ok=True,
                        error_code=None,
                        error_message=None,
                    )
                )

    summary: dict[str, dict[str, Any]] = {}
    feature_matrix: dict[str, Any] = {}

    target_ok_flags: list[bool] = []

    for target in selected_targets:
        manifest = registry.get(target).manifest
        target_results = [result for result in results if result.target == target]
        by_case = {result.case: result for result in target_results}

        passed = sum(1 for result in target_results if result.ok)
        total = len(target_results)

        per_feature: dict[str, Any] = {}
        contradictions: list[str] = []

        for feature in ALL_FEATURES:
            declared_supported = bool(manifest.feature_coverage.get(feature, True))
            all_feature_cases = [case for case in CONTRACT_CASES if feature in case.features]

            if declared_supported:
                # Assess support only on cases that should be legal for this target matrix.
                applicable_cases = [
                    case
                    for case in all_feature_cases
                    if all(bool(manifest.feature_coverage.get(item, True)) for item in case.features)
                ]
                applicable_results = [by_case[case.name] for case in applicable_cases]
                pass_count = sum(1 for item in applicable_results if item.ok)
                low001_count = sum(1 for item in applicable_results if item.error_code == "LOW001")
                other_fail_count = sum(
                    1 for item in applicable_results if (not item.ok and item.error_code != "LOW001")
                )

                if not applicable_results:
                    status = "unexercised"
                elif pass_count == len(applicable_results):
                    status = "supported"
                elif low001_count > 0:
                    status = "declared_supported_but_rejected"
                else:
                    status = "declared_supported_but_failed"
            else:
                # Unsupported features should fail explicitly anywhere they are exercised.
                exercised_results = [by_case[case.name] for case in all_feature_cases]
                pass_count = sum(1 for item in exercised_results if item.ok)
                low001_count = sum(1 for item in exercised_results if item.error_code == "LOW001")
                other_fail_count = sum(1 for item in exercised_results if (not item.ok and item.error_code != "LOW001"))

                if not exercised_results:
                    status = "unexercised"
                elif low001_count == len(exercised_results):
                    status = "unsupported_enforced"
                elif pass_count > 0:
                    status = "declared_unsupported_but_passed"
                else:
                    status = "declared_unsupported_but_failed_nonstruct"

            if "but" in status:
                contradictions.append(f"{feature}:{status}")

            per_feature[feature] = {
                "declared_supported": declared_supported,
                "status": status,
                "cases": [case.name for case in all_feature_cases],
                "pass_count": pass_count,
                "low001_count": low001_count,
                "other_fail_count": other_fail_count,
            }

        is_stable = manifest.stability == "stable"
        all_cases_ok = all(result.ok for result in target_results)
        stable_feature_ok = all(per_feature[feature]["status"] == "supported" for feature in REQUIRED_STABLE_FEATURES)

        if is_stable:
            target_ok = all_cases_ok and stable_feature_ok and not contradictions
        else:
            target_ok = not contradictions

        summary[target] = {
            "passed": passed,
            "total": total,
            "stability": manifest.stability,
            "all_cases_ok": all_cases_ok,
            "stable_feature_ok": stable_feature_ok,
            "target_ok": target_ok,
        }
        feature_matrix[target] = {
            "target": target,
            "stability": manifest.stability,
            "contradictions": contradictions,
            "features": per_feature,
        }
        target_ok_flags.append(target_ok)

    return {
        "ok": all(target_ok_flags),
        "stable_only": stable_only,
        "targets": selected_targets,
        "required_stable_features": list(REQUIRED_STABLE_FEATURES),
        "cases": [
            {
                "name": case.name,
                "features": list(case.features),
                "required_for_stable": case.required_for_stable,
            }
            for case in CONTRACT_CASES
        ],
        "results": [
            {
                "case": result.case,
                "target": result.target,
                "ok": result.ok,
                "error_code": result.error_code,
                "error_message": result.error_message,
            }
            for result in results
        ],
        "summary": summary,
        "feature_matrix": feature_matrix,
    }
