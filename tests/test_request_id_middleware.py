from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.request_id import RequestIDMiddleware


def test_request_id_is_added_to_response():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") is not None
    assert response.json() == {"status": "ok"}

def test_each_request_gets_a_unique_request_id():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    client = TestClient(app)
    first_response = client.get("/test")
    second_response = client.get("/test")

    first_id = first_response.headers.get("X-Request-ID")
    second_id = second_response.headers.get("X-Request-ID")
    assert first_id != second_id