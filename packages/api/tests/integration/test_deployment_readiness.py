from fastapi.testclient import TestClient

from evox_api.main import app


def test_healthz_reports_process_readiness() -> None:
    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
