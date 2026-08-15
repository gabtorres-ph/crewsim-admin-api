from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.exceptions import InvalidOperationError, ResourceConflictError, ResourceNotFoundError
from app.routers import api_router

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(
    request: Request, error: ResourceNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)})


@app.exception_handler(ResourceConflictError)
async def resource_conflict_handler(
    request: Request, error: ResourceConflictError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)})


@app.exception_handler(InvalidOperationError)
async def invalid_operation_handler(
    request: Request, error: InvalidOperationError
) -> JSONResponse:
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
