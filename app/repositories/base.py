from collections.abc import Mapping
from typing import Any, Generic, TypeVar

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db import Base

ModelT = TypeVar("ModelT", bound=Base)


class CRUDRepository(Generic[ModelT]):
    """Reusable persistence operations for a single SQLAlchemy model."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get(self, object_id: int) -> ModelT | None:
        return self.session.get(self.model, object_id)

    def list(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        primary_key = inspect(self.model).primary_key
        statement = select(self.model).order_by(*primary_key).offset(offset).limit(limit)
        return list(self.session.scalars(statement))

    def create(self, values: Mapping[str, Any]) -> ModelT:
        instance = self.model(**dict(values))
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def update(self, instance: ModelT, values: Mapping[str, Any]) -> ModelT:
        for field, value in values.items():
            setattr(instance, field, value)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()
