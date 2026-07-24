from pathlib import Path

from fastapi.testclient import TestClient

from evox_api.main import app


def test_healthz_reports_process_readiness() -> None:
    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_worker_console_entrypoint_is_packaged() -> None:
    package = Path(__file__).parents[2] / "pyproject.toml"

    assert 'evox-worker = "evox_api.jobs.worker:main"' in package.read_text()
    assert "[tool.uv]\npackage = true" in package.read_text()
