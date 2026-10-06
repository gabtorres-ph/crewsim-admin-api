from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from app.common.cors import add_cors_middleware
from app.common.exceptions import (
    InvalidOperationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.config import get_settings
from app.integrations.redis.request_logging import RequestLogManager
from app.integrations.redis.request_logging_middleware import handle_request_logging
from app.routes import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    RequestLogManager.init(
        settings.redis_host,
        settings.redis_port,
        username=settings.redis_username,
        password=settings.redis_password,
    )
    try:
        await RequestLogManager.start_cleanup_task()
        yield
    finally:
        await RequestLogManager.close()


app = FastAPI(title=settings.app_name, debug=settings.app_debug, lifespan=lifespan)
add_cors_middleware(app, settings.allowed_cors_origins)

app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def request_logging_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    return await handle_request_logging(request, call_next)


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(
    request: Request, error: ResourceNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)})


@app.exception_handler(ResourceConflictError)
async def resource_conflict_handler(request: Request, error: ResourceConflictError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)})


@app.exception_handler(InvalidOperationError)
async def invalid_operation_handler(request: Request, error: InvalidOperationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(error)},
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to core-crewsim"}
