"""Schemas shared across application domains."""

from typing import Generic, TypeVar

from pydantic import BaseModel

ItemT = TypeVar("ItemT")


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """A typed page of API results."""

    items: list[ItemT]
    total: int
    page: int
    limit: int
