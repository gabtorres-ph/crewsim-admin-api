import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.cors import ALLOWED_CORS_HEADERS, ALLOWED_CORS_METHODS, add_cors_middleware


ALLOWED_ORIGIN = "https://bss.crewsim.dev"


def create_cors_app() -> FastAPI:
    cors_app = FastAPI()
    add_cors_middleware(cors_app, [ALLOWED_ORIGIN])
    return cors_app


@pytest.mark.asyncio
async def test_cors_preflight_allows_frontend_service_token_request() -> None:
    transport = ASGITransport(app=create_cors_app())
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/api/users",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": (
                    "Content-Type, CF-Access-Client-Id, CF-Access-Client-Secret"
                ),
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert set(response.headers["access-control-allow-methods"].split(", ")) == set(
        ALLOWED_CORS_METHODS
    )
    allowed_headers = {
        header.strip().lower()
        for header in response.headers["access-control-allow-headers"].split(",")
    }
    assert {header.lower() for header in ALLOWED_CORS_HEADERS} <= allowed_headers


@pytest.mark.asyncio
async def test_cors_preflight_rejects_unconfigured_origin() -> None:
    transport = ASGITransport(app=create_cors_app())
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/api/users",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
