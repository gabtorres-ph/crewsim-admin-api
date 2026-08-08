import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="function")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
