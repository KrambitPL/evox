from __future__ import annotations

import hashlib
import json

from evox_api.domain.contracts import EvaluationCase

from .errors import EvaluationLeakageError


def require_isolated_cases(cases: tuple[EvaluationCase, ...]) -> None:
    """Reject duplicate case IDs or literal evaluation content across split boundaries."""
    split_by_id: dict[str, str] = {}
    split_by_fingerprint: dict[str, str] = {}
    for case in cases:
        _require_new_split(split_by_id, case.id, case.split.value, "case identifier")
        _require_new_split(
            split_by_fingerprint,
            evaluation_content_fingerprint(case),
            case.split.value,
            "content fingerprint",
        )


def evaluation_content_fingerprint(case: EvaluationCase) -> str:
    payload = {
        "input": case.input,
        "expected_facts": case.expected_facts,
        "expected_disposition": case.expected_disposition.value,
        "expected_citations": case.expected_citations,
        "hard_gates": case.hard_gates,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_new_split(
    split_by_value: dict[str, str], value: str, split: str, value_kind: str
) -> None:
    previous_split = split_by_value.get(value)
    if previous_split is not None and previous_split != split:
        raise EvaluationLeakageError(
            f"Evaluation {value_kind} is present in both {previous_split} and {split} splits.",
            {"value_kind": value_kind, "first_split": previous_split, "second_split": split},
        )
    split_by_value[value] = split
