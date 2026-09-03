from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.esims import ESIMCreate, ESIMRead, ESIMUpdate
from app.services.esims import ESIMService

router = APIRouter(prefix="/esims", tags=["esims"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ESIMRead, status_code=status.HTTP_201_CREATED)
def create_esim(data: ESIMCreate, db: DatabaseSession) -> ESIMRead:
    return ESIMService(db).create_esim(data)


@router.get("", response_model=list[ESIMRead])
def list_esims(
    db: DatabaseSession,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ESIMRead]:
    return ESIMService(db).list_esims(user_id=user_id, offset=offset, limit=limit)


@router.get("/{esim_id}", response_model=ESIMRead)
def get_esim(esim_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> ESIMRead:
    return ESIMService(db).get_esim(esim_id)


@router.patch("/{esim_id}", response_model=ESIMRead)
def update_esim(
    esim_id: Annotated[int, Path(gt=0)], data: ESIMUpdate, db: DatabaseSession
) -> ESIMRead:
    return ESIMService(db).update_esim(esim_id, data)


@router.delete("/{esim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_esim(esim_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    ESIMService(db).delete_esim(esim_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
