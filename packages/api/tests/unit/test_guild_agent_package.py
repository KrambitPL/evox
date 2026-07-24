from pathlib import Path


def test_guild_agent_is_runtime_scoped_and_has_no_package_managed_sdk_dependency() -> None:
    root = Path(__file__).parents[4] / "integrations" / "guild" / "issue-resolver-release-inspector"
    agent = (root / "agent.ts").read_text()
    package = (root / "package.json").read_text()

    assert 'from "@guildai/agents-sdk"' in agent
    assert '"use agent"' in agent
    assert "@guildai/agents-sdk" not in package
    assert "zod" not in package


def test_guild_publish_script_requires_matching_approved_release_identity() -> None:
    script = (
        Path(__file__).parents[4]
        / "integrations"
        / "guild"
        / "publish-approved-release.sh"
    ).read_text()

    assert '"$EVOX_RELEASE_ID" != "$EVOX_APPROVED_RELEASE_ID"' in script
    assert "guild agent save -A --wait --publish" in script
    assert "guild auth status" in script
