class PersistenceConfigurationError(RuntimeError):
    """Raised when an explicitly required AWS integration is not configured."""


class ConcurrencyConflict(RuntimeError):
    """Raised when DynamoDB rejects an optimistic conditional write."""
