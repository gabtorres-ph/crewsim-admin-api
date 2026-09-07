from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.usage.manager import UsageManager
from app.usage.schemas import UsageCreate, UsageRead, UsageUpdate

router = APIRouter(prefix="/usage", tags=["usage"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=UsageRead, status_code=status.HTTP_201_CREATED)
def create_usage(data: UsageCreate, db: DatabaseSession) -> UsageRead:
    return UsageManager(db).create_usage(data)


@router.get("", response_model=list[UsageRead])
def list_usage(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[UsageRead]:
    return UsageManager(db).list_usage(offset=offset, limit=limit)


@router.get("/{usage_id}", response_model=UsageRead)
def get_usage(usage_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> UsageRead:
    return UsageManager(db).get_usage(usage_id)


@router.patch("/{usage_id}", response_model=UsageRead)
def update_usage(
    usage_id: Annotated[int, Path(gt=0)], data: UsageUpdate, db: DatabaseSession
) -> UsageRead:
    return UsageManager(db).update_usage(usage_id, data)


@router.delete("/{usage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_usage(usage_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    UsageManager(db).delete_usage(usage_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
