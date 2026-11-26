from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.exception_handlers import (
    email_already_registered_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.tasks import router as tasks_router
from app.core.exceptions import EmailAlreadyRegisteredError
from app.middleware.request_id import RequestIDMiddleware

app = FastAPI(
    title="Indie Project Management Platform",
    description="A lightweight project management API for indie game developers.",
    version="0.1.0",
)

app.add_middleware(RequestIDMiddleware)

app.add_exception_handler(
    EmailAlreadyRegisteredError,
    email_already_registered_handler,
)
app.add_exception_handler(
    StarletteHTTPException,
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

app.include_router(
    auth_router,
    prefix="/api/v1",
)
app.include_router(
    projects_router,
    prefix="/api/v1",
)
app.include_router(
    tasks_router,
    prefix="/api/v1",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
