import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import EmailAlreadyRegisteredError
from app.schemas.errors import ErrorDetail, ErrorInfo, ErrorResponse

logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def email_already_registered_handler(
    request: Request,
    exc: EmailAlreadyRegisteredError,
) -> JSONResponse:
    error = ErrorResponse(
        error=ErrorInfo(
            code="EMAIL_ALREADY_REGISTERED",
            message="An account with this email already exists.",
            request_id=get_request_id(request),
        )
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error.model_dump(),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    error = ErrorResponse(
        error=ErrorInfo(
            code="HTTP_ERROR",
            message=str(exc.detail),
            request_id=get_request_id(request),
        )
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"][1:]) or None,
            message=error["msg"],
        )
        for error in exc.errors()
    ]

    error = ErrorResponse(
        error=ErrorInfo(
            code="VALIDATION_ERROR",
            message="The request contains invalid fields.",
            details=details,
            request_id=get_request_id(request),
        )
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error.model_dump(),
    )


async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = get_request_id(request)

    logger.error(
        "Unhandled application exception. Request ID: %s",
        request_id,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    error = ErrorResponse(
        error=ErrorInfo(
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred.",
            request_id=request_id,
        )
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error.model_dump(),
    )
