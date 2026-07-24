from __future__ import annotations

import os

from band.client.rest import AsyncRestClient

from evox_api.adapters.actian import ActianOutcomeMemorySettings
from evox_api.adapters.band import EscalationConfig
from evox_api.adapters.guild import GuildSettings
from evox_api.adapters.pioneer import PioneerModelGateway, PioneerSettings
from evox_api.adapters.senso import SensoAdapter, SensoSettings


async def integration_health() -> dict[str, list[dict[str, str]]]:
    services = [
        await _pioneer_health(),
        await _senso_health(),
        await _actian_health(),
        await _band_health(),
        _guild_health(),
        _replay_health(),
    ]
    return {"services": services}


async def _pioneer_health() -> dict[str, str]:
    gateway: PioneerModelGateway | None = None
    try:
        gateway = PioneerModelGateway(PioneerSettings.from_environment())
        health = await gateway.health_check()
        if not health.healthy:
            return _service("Pioneer", "unavailable", "Live model discovery failed.")
        return _service("Pioneer", "healthy", f"{len(health.models)} live models available.")
    except Exception:
        return _service("Pioneer", "unavailable", "Not configured or live check failed.")
    finally:
        if gateway is not None:
            await gateway.aclose()


async def _senso_health() -> dict[str, str]:
    adapter: SensoAdapter | None = None
    try:
        adapter = SensoAdapter(SensoSettings.from_environment())
        await adapter.health_check()
        return _service("Senso", "healthy", "Authenticated organization API is reachable.")
    except Exception:
        return _service("Senso", "unavailable", "Not configured or live check failed.")
    finally:
        if adapter is not None:
            await adapter.aclose()


async def _actian_health() -> dict[str, str]:
    try:
        client = ActianOutcomeMemorySettings.from_environment().client()
        await client.connect()
        await client.health_check()
        return _service("Actian", "healthy", "VectorAI health check passed.")
    except Exception:
        return _service("Actian", "unavailable", "Not configured or live check failed.")


async def _band_health() -> dict[str, str]:
    try:
        config = EscalationConfig.from_environment()
        client = AsyncRestClient(base_url=config.rest_url, api_key=config.api_key)
        await client.agent_api_identity.get_agent_me()
        return _service("Band", "healthy", "Agent identity authenticated.")
    except Exception:
        return _service("Band", "unavailable", "Agent credential is unavailable or invalid.")


def _guild_health() -> dict[str, str]:
    try:
        GuildSettings.from_environment()
    except Exception:
        return _service("Guild.ai", "unavailable", "Workspace or agent identity is absent.")
    return _service("Guild.ai", "degraded", "Configured; publication is verified per release.")


def _replay_health() -> dict[str, str]:
    if not os.environ.get("REPLAY_API_KEY"):
        return _service("Replay.io", "unavailable", "Recording key is absent.")
    return _service("Replay.io", "degraded", "Configured; recording is verified in browser QA.")


def _service(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}
