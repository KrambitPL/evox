from evox_api.domain.errors import DomainError


class EvaluationLeakageError(DomainError):
    def __init__(self, message: str, details: dict[str, object]) -> None:
        super().__init__(code="evaluation_leakage", message=message, details=details)


class CandidateFreezeError(DomainError):
    def __init__(self, message: str, details: dict[str, object]) -> None:
        super().__init__(code="candidate_freeze_failed", message=message, details=details)
