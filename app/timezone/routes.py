from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.timezone.manager import TimezoneManager
from app.timezone.schemas import TimezoneCreate, TimezoneRead, TimezoneUpdate

router = APIRouter(prefix="/timezones", tags=["timezones"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=TimezoneRead, status_code=status.HTTP_201_CREATED)
def create_timezone(data: TimezoneCreate, db: DatabaseSession) -> TimezoneRead:
    return TimezoneManager(db).create_timezone(data)


@router.get("", response_model=list[TimezoneRead])
def list_timezones(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[TimezoneRead]:
    return TimezoneManager(db).list_timezones(offset=offset, limit=limit)


@router.get("/{name:path}", response_model=TimezoneRead)
def get_timezone(
    name: Annotated[str, Path(min_length=1, max_length=255)], db: DatabaseSession
) -> TimezoneRead:
    return TimezoneManager(db).get_timezone(name)


@router.patch("/{name:path}", response_model=TimezoneRead)
def update_timezone(
    name: Annotated[str, Path(min_length=1, max_length=255)],
    data: TimezoneUpdate,
    db: DatabaseSession,
) -> TimezoneRead:
    return TimezoneManager(db).update_timezone(name, data)


@router.delete("/{name:path}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timezone(
    name: Annotated[str, Path(min_length=1, max_length=255)], db: DatabaseSession
) -> Response:
    TimezoneManager(db).delete_timezone(name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
