import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.api.exception_handlers import (
    email_already_registered_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import EmailAlreadyRegisteredError
from app.middleware.request_id import RequestIDMiddleware


@pytest.fixture
def client():
    app = FastAPI()

    app.add_middleware(RequestIDMiddleware)

    app.add_exception_handler(
        EmailAlreadyRegisteredError,
        email_already_registered_handler,
    )
    app.add_exception_handler(
        HTTPException,
        http_exception_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    app.add_exception_handler(
        Exception,
        unexpected_exception_handler,
    )

    @app.get("/duplicate")
    def duplicate():
        raise EmailAlreadyRegisteredError

    @app.get("/unauthorized")
    def unauthorized():
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/validation")
    def validation(value: int):
        return {"value": value}

    @app.get("/unexpected")
    def unexpected():
        raise RuntimeError("Internal database details")

    return TestClient(app, raise_server_exceptions=False)


def test_duplicate_email_returns_409(client):
    response = client.get("/duplicate")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "EMAIL_ALREADY_REGISTERED"
    )


def test_http_exception_preserves_authentication_header(client):
    response = client.get("/unauthorized")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_validation_error_returns_standard_envelope(client):
    response = client.get("/validation?value=not-an-integer")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["field"] == "value"


def test_unexpected_error_does_not_expose_internal_details(client):
    response = client.get("/unexpected")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "Internal database details" not in response.text


def test_error_request_id_matches_response_header(client):
    response = client.get("/duplicate")

    request_id = response.headers["X-Request-ID"]

    assert response.json()["error"]["request_id"] == request_id