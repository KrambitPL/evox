import json
from asyncio import run
from pathlib import Path

import pytest

from evox_api.domain.errors import DomainError
from evox_api.main import create_app

EXPECTED_PATHS = {
    "/v1/missions",
    "/v1/missions/{id}",
    "/v1/missions/{id}/forge",
    "/v1/systems/{id}/runs",
    "/v1/systems/{id}/evaluations",
    "/v1/systems/{id}/evolutions",
    "/v1/jobs/{id}",
    "/v1/candidates/{id}",
    "/v1/candidates/{id}/promote",
    "/v1/releases/{id}/rollback",
    "/v1/runs/{id}/feedback",
    "/v1/integrations/health",
}


def test_openapi_surface_matches_the_frozen_contract_fixture() -> None:
    app = create_app()
    fixture_path = Path(__file__).parents[2] / "fixtures" / "openapi.json"
    document = app.openapi()
    public_surface = {
        "openapi": document["openapi"],
        "info": document["info"],
        "paths": {path: sorted(operations) for path, operations in document["paths"].items()},
    }

    assert set(document["paths"]) == EXPECTED_PATHS
    assert json.loads(fixture_path.read_text()) == public_surface


def test_unconfigured_integration_health_fails_closed_with_a_structured_error() -> None:
    health_route = next(
        route for route in create_app().routes if route.path == "/v1/integrations/health"
    )

    with pytest.raises(DomainError) as error:
        run(health_route.endpoint())

    assert error.value.payload().model_dump() == {
        "code": "integration_unavailable",
        "message": "Integration health checks are not configured.",
        "details": {"integration": "health"},
    }
