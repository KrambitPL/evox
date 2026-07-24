"""Deterministic held-out evaluation and candidate comparison."""

from .comparison import compare_candidates
from .errors import CandidateFreezeError, EvaluationLeakageError
from .isolation import require_isolated_cases
from .scoring import IssueResolution, score_issue_resolution

__all__ = [
    "CandidateFreezeError",
    "EvaluationLeakageError",
    "IssueResolution",
    "compare_candidates",
    "require_isolated_cases",
    "score_issue_resolution",
]
