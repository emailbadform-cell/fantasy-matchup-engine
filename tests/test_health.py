from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_status():
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "foundation_ready"
    assert "original" in data["projection_models"]
    assert "cb_challenger" in data["projection_models"]
    assert "full_cb_challenger" in data["projection_models"]
