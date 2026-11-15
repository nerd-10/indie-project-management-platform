from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health_endpoint_atill_works():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status" : "ok"}

def test_unknown_route_retunrs_standard_error():
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    assert response.headers.get("X-Request-ID") is not None