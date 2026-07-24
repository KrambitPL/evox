import asyncio
from dataclasses import dataclass

import pytest

from evox_api.adapters.guild.publication import (
    GuildPublicationAdapter,
    GuildPublicationError,
    GuildReleaseState,
    GuildSettings,
)
from evox_api.domain.contracts import (
    AgenticSystemSpec,
    ReleaseDecision,
    ReleaseDisposition,
    SystemNode,
)
from evox_api.domain.errors import IntegrationUnavailable


def _system() -> AgenticSystemSpec:
    return AgenticSystemSpec(
        id="system_issue_resolver_v2",
        mission_id="mission_issue_resolver",
        version=2,
        nodes=(SystemNode(id="resolve", kind="resolver"),),
        edges=(),
        models={"resolve": "pioneer-resolver"},
        prompts={"resolve": "Resolve with official evidence."},
        capability_bindings={"resolve": frozenset()},
        mutable_fields=frozenset(),
        immutable_policy_digest="a" * 64,
    )


def _release() -> ReleaseDecision:
    return ReleaseDecision(
        id="release_002",
        candidate_id="candidate_002",
        disposition=ReleaseDisposition.PROMOTE,
        reasons=("Frozen evaluation passed.",),
        evidence_refs=("s3://evox-evidence/release_002.json",),
        approved_system_id="system_issue_resolver_v2",
        promoted_version="2.0.0",
        rollback_version="1.0.0",
        rollback_release_id="release_001",
        immutable_policy_digest="a" * 64,
    )


@dataclass
class _RemoteGuild:
    state: GuildReleaseState
    published: list[tuple[str, str]]

    async def publish(self, *, release_id: str, immutable_policy_digest: str) -> GuildReleaseState:
        self.published.append((release_id, immutable_policy_digest))
        return self.state

    async def active_release(self) -> GuildReleaseState | None:
        return self.state

    async def activate(self, *, release_id: str) -> GuildReleaseState:
        assert release_id == "release_001"
        return GuildReleaseState(
            workspace_id="workspace_evox",
            agent_id="agent_issue_resolver",
            release_id="release_001",
            version="1.0.0",
            immutable_policy_digest="a" * 64,
            rollback_release_id=None,
            status="published",
        )


def _remote(*, release_id: str = "release_002", version: str = "2.0.0") -> _RemoteGuild:
    return _RemoteGuild(
        state=GuildReleaseState(
            workspace_id="workspace_evox",
            agent_id="agent_issue_resolver",
            release_id=release_id,
            version=version,
            immutable_policy_digest="a" * 64,
            rollback_release_id="release_001",
            status="published",
        ),
        published=[],
    )


def _adapter(remote: _RemoteGuild) -> GuildPublicationAdapter:
    return GuildPublicationAdapter(
        GuildSettings(workspace_id="workspace_evox", agent_id="agent_issue_resolver"), remote
    )


def test_settings_fail_closed_without_an_explicit_workspace_and_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GUILD_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("GUILD_AGENT_ID", raising=False)

    with pytest.raises(IntegrationUnavailable):
        GuildSettings.from_environment()


def test_publication_accepts_only_the_approved_immutable_release() -> None:
    remote = _remote()

    receipt = asyncio.run(_adapter(remote).publish(_release(), _system()))

    assert receipt.release_id == "release_002"
    assert receipt.active_version == "2.0.0"
    assert receipt.rollback_release_id == "release_001"
    assert remote.published == [("release_002", "a" * 64)]


def test_publication_fails_closed_when_guild_reports_a_different_release() -> None:
    remote = _remote(release_id="release_003")

    with pytest.raises(GuildPublicationError, match="release ID"):
        asyncio.run(_adapter(remote).publish(_release(), _system()))


def test_reconciliation_detects_remote_active_version_drift() -> None:
    remote = _remote(version="2.0.1")

    with pytest.raises(GuildPublicationError, match="version"):
        asyncio.run(_adapter(remote).reconcile(_release(), _system()))


def test_rollback_uses_the_release_receipt_linkage_and_reconciles_the_result() -> None:
    receipt = asyncio.run(_adapter(_remote()).rollback(_release(), _system()))

    assert receipt.release_id == "release_001"
    assert receipt.active_version == "1.0.0"
    assert receipt.rolled_back_from_release_id == "release_002"
