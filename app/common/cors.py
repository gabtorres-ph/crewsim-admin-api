from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_CORS_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_CORS_HEADERS = [
    "Content-Type",
    "CF-Access-Client-Id",
    "CF-Access-Client-Secret",
]


def add_cors_middleware(application: FastAPI, origins: list[str]) -> None:
    """Configure browser access for the explicitly allowed frontend origins."""
    if not origins:
        return

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=ALLOWED_CORS_METHODS,
        allow_headers=ALLOWED_CORS_HEADERS,
    )
