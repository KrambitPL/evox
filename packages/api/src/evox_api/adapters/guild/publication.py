"""Governed, fail-closed publication through Guild.ai's official CLI boundary.

The Guild CLI owns authentication and packaging.  This adapter deliberately accepts a
typed remote client rather than credentials or an undocumented Guild HTTP API.
"""

import os
from dataclasses import dataclass
from typing import Literal, Protocol

from evox_api.domain.contracts import AgenticSystemSpec, ReleaseDecision
from evox_api.domain.errors import DomainError, IntegrationUnavailable
from evox_api.ports.sponsors import PublicationReceipt


class GuildPublicationError(DomainError):
    """A safe-to-surface Guild release-governance failure."""

    def __init__(self, message: str) -> None:
        super().__init__("guild_publication_rejected", message)


@dataclass(frozen=True)
class GuildSettings:
    """Non-secret identity required to bind an Evox release to one Guild agent."""

    workspace_id: str
    agent_id: str

    def __post_init__(self) -> None:
        if not self.workspace_id.strip() or not self.agent_id.strip():
            raise IntegrationUnavailable("guild")

    @classmethod
    def from_environment(cls) -> "GuildSettings":
        return cls(
            workspace_id=os.environ.get("GUILD_WORKSPACE_ID", ""),
            agent_id=os.environ.get("GUILD_AGENT_ID", ""),
        )


@dataclass(frozen=True)
class GuildReleaseState:
    """The remotely observed active Guild publication state."""

    workspace_id: str
    agent_id: str
    release_id: str
    version: str
    immutable_policy_digest: str
    rollback_release_id: str | None
    status: Literal["published"]


class GuildRemotePublicationClient(Protocol):
    """Implemented by the official CLI packaging/reconciliation boundary only."""

    async def publish(
        self, *, release_id: str, immutable_policy_digest: str
    ) -> GuildReleaseState: ...

    async def active_release(self) -> GuildReleaseState | None: ...

    async def activate(self, *, release_id: str) -> GuildReleaseState: ...


class GuildPublicationAdapter:
    """PublicationPort implementation that rejects incomplete or drifted releases."""

    def __init__(self, settings: GuildSettings, remote: GuildRemotePublicationClient) -> None:
        self._settings = settings
        self._remote = remote

    async def publish(
        self, release: ReleaseDecision, system: AgenticSystemSpec
    ) -> PublicationReceipt:
        release.validate_publication(system)
        state = await self._remote.publish(
            release_id=release.id,
            immutable_policy_digest=release.immutable_policy_digest,
        )
        self._validate_state(state, release, expected_release_id=release.id)
        return PublicationReceipt(
            release_id=state.release_id,
            active_version=state.version,
            rollback_release_id=state.rollback_release_id,
        )

    async def reconcile(
        self, release: ReleaseDecision, system: AgenticSystemSpec
    ) -> PublicationReceipt:
        """Read real remote state and reject any active-release drift."""
        release.validate_publication(system)
        state = await self._remote.active_release()
        if state is None:
            raise GuildPublicationError("Guild has no active release to reconcile.")
        self._validate_state(state, release, expected_release_id=release.id)
        return PublicationReceipt(
            release_id=state.release_id,
            active_version=state.version,
            rollback_release_id=state.rollback_release_id,
        )

    async def rollback(
        self, release: ReleaseDecision, system: AgenticSystemSpec
    ) -> PublicationReceipt:
        """Activate exactly the rollback release named by an approved receipt."""
        release.validate_publication(system)
        rollback_release_id = release.rollback_release_id
        rollback_version = release.rollback_version
        if not rollback_release_id or not rollback_version:
            raise GuildPublicationError("Approved release does not contain rollback linkage.")
        state = await self._remote.activate(release_id=rollback_release_id)
        self._validate_identity(state)
        if state.status != "published":
            raise GuildPublicationError("Guild rollback target is not published.")
        if state.release_id != rollback_release_id:
            raise GuildPublicationError("Guild activated a different rollback release ID.")
        if state.version != rollback_version:
            raise GuildPublicationError("Guild activated a different rollback version.")
        if state.immutable_policy_digest != release.immutable_policy_digest:
            raise GuildPublicationError("Guild rollback changed the immutable policy digest.")
        return PublicationReceipt(
            release_id=state.release_id,
            active_version=state.version,
            rollback_release_id=state.rollback_release_id,
            rolled_back_from_release_id=release.id,
        )

    def _validate_state(
        self, state: GuildReleaseState, release: ReleaseDecision, *, expected_release_id: str
    ) -> None:
        self._validate_identity(state)
        if state.status != "published":
            raise GuildPublicationError("Guild release is not published.")
        if state.release_id != expected_release_id:
            raise GuildPublicationError("Guild reported a different active release ID.")
        if state.version != release.promoted_version:
            raise GuildPublicationError("Guild reported a different active version.")
        if state.rollback_release_id != release.rollback_release_id:
            raise GuildPublicationError("Guild reported different rollback linkage.")
        if state.immutable_policy_digest != release.immutable_policy_digest:
            raise GuildPublicationError("Guild reported a different immutable policy digest.")

    def _validate_identity(self, state: GuildReleaseState) -> None:
        if state.workspace_id != self._settings.workspace_id:
            raise GuildPublicationError("Guild remote state belongs to a different workspace.")
        if state.agent_id != self._settings.agent_id:
            raise GuildPublicationError("Guild remote state belongs to a different agent.")
