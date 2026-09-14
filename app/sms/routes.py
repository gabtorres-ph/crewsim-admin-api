from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.sms.manager import SmsManager
from app.sms.schemas import SmsCreate, SmsRead, SmsUpdate

router = APIRouter(prefix="/sms", tags=["sms"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=SmsRead, status_code=status.HTTP_201_CREATED)
def create_sms(data: SmsCreate, db: DatabaseSession) -> SmsRead:
    return SmsManager(db).create_sms(data)


@router.get("", response_model=list[SmsRead])
def list_sms(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[SmsRead]:
    return SmsManager(db).list_sms(offset=offset, limit=limit)


@router.get("/{sms_id}", response_model=SmsRead)
def get_sms(sms_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> SmsRead:
    return SmsManager(db).get_sms(sms_id)


@router.patch("/{sms_id}", response_model=SmsRead)
def update_sms(
    sms_id: Annotated[int, Path(gt=0)], data: SmsUpdate, db: DatabaseSession
) -> SmsRead:
    return SmsManager(db).update_sms(sms_id, data)


@router.delete("/{sms_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sms(sms_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    SmsManager(db).delete_sms(sms_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
