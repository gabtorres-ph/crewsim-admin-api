"""Regression tests for the vertical domain architecture."""

import ast
import importlib
from pathlib import Path

from fastapi import APIRouter

from app.database import Base

APP_ROOT = Path(__file__).parent
DOMAIN_MODEL_MODULES = (
    "app.accounts.models",
    "app.users.models",
    "app.esims.models",
    "app.favorites.models",
)
REMOVED_IMPORT_SUFFIXES = (
    "db",
    "models",
    "routers",
    "schemas",
    "services",
    "repositories",
)
REMOVED_IMPORT_PREFIXES = tuple(f"app.{suffix}" for suffix in REMOVED_IMPORT_SUFFIXES)
EXPECTED_TABLES = {"accounts", "users", "esims", "favorites"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)

    return imports


def test_application_does_not_import_removed_modules() -> None:
    legacy_imports: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        for module in _imports(path):
            if any(
                module == prefix or module.startswith(f"{prefix}.")
                for prefix in REMOVED_IMPORT_PREFIXES
            ):
                legacy_imports.append(f"{path.relative_to(APP_ROOT.parent)}: {module}")

    assert legacy_imports == []


def test_router_and_domain_models_are_registered() -> None:
    for module in DOMAIN_MODEL_MODULES:
        importlib.import_module(module)

    routes = importlib.import_module("app.routes")

    assert isinstance(routes.api_router, APIRouter)
    assert set(Base.metadata.tables) == EXPECTED_TABLES
