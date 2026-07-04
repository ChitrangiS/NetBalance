# tests/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """
    Verify the API starts and responds correctly.
    This is the smoke test — if this fails, nothing else matters.
    """
    response = client.get("/health")
    
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}"
    )
    assert response.json() == {"status": "ok"}, (
        f"Unexpected body: {response.json()}"
    )