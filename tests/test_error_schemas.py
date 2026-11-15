from app.schemas.errors import ErrorDetail, ErrorInfo, ErrorResponse


def test_error_response_serialization():
    response = ErrorResponse(
        error = ErrorInfo(
            code = "EMAIL_ALREADY_REGISTERED",
            message = "An account with this email already exists",
            details = [],
            request_id = "test-request-123",
        )
    )
    assert response.model_dump() == {
        "error": {
            "code": "EMAIL_ALREADY_REGISTERED",
            "message" : "An account with this email already exists",
            "details" : [],
            "request_id" : "test-request-123",
        }
    }

def test_response_supports_validation_details():
    response = ErrorResponse(
        error = ErrorInfo(
            code = "VALIDATION_ERROR",
            message = "The request contains invalid fields.",
            details = [
                ErrorDetail(
                    field = "email",
                    message = "Enter a valid email address."
                )
            ],
            request_id = "test-request-456",
        )
    )
    assert response.error.details[0].field == "email"
    assert response.error.details[0].message == (
        "Enter a valid email address."
    )