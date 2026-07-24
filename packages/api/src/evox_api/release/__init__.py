"""Fail-closed promotion receipts and reversible active-version transitions."""

from .gate import ActiveVersion, activate_version, decide_promotion, rollback_active_version

__all__ = ["ActiveVersion", "activate_version", "decide_promotion", "rollback_active_version"]
