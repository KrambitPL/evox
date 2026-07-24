from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DomainErrorPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class DomainError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def payload(self) -> DomainErrorPayload:
        return DomainErrorPayload(code=self.code, message=self.message, details=self.details)


class IntegrationUnavailable(DomainError):
    def __init__(self, integration: str) -> None:
        super().__init__(
            code="integration_unavailable",
            message=f"{integration.capitalize()} integration is not configured.",
            details={"integration": integration},
        )


class ImmutablePolicyViolation(DomainError):
    def __init__(
        self,
        expected_digest: str,
        received_digest: str,
        unauthorized_capabilities: frozenset[str] = frozenset(),
    ) -> None:
        if unauthorized_capabilities:
            super().__init__(
                code="immutable_policy_violation",
                message="System capability bindings include unauthorized_capabilities.",
                details={
                    "expected_digest": expected_digest,
                    "received_digest": received_digest,
                    "unauthorized_capabilities": sorted(unauthorized_capabilities),
                },
            )
            return
        super().__init__(
            code="immutable_policy_violation",
            message="immutable_policy_digest does not match the mission policy.",
            details={"expected_digest": expected_digest, "received_digest": received_digest},
        )
