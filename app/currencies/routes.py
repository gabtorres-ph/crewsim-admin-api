from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.currencies.manager import CurrencyManager
from app.currencies.schemas import CurrencyCreate, CurrencyRead, CurrencyUpdate
from app.database import get_db

router = APIRouter(prefix="/currencies", tags=["currencies"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=CurrencyRead, status_code=status.HTTP_201_CREATED)
def create_currency(data: CurrencyCreate, db: DatabaseSession) -> CurrencyRead:
    return CurrencyManager(db).create_currency(data)


@router.get("", response_model=list[CurrencyRead])
def list_currencies(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[CurrencyRead]:
    return CurrencyManager(db).list_currencies(offset=offset, limit=limit)


@router.get("/{currency_id}", response_model=CurrencyRead)
def get_currency(currency_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> CurrencyRead:
    return CurrencyManager(db).get_currency(currency_id)


@router.patch("/{currency_id}", response_model=CurrencyRead)
def update_currency(
    currency_id: Annotated[int, Path(gt=0)], data: CurrencyUpdate, db: DatabaseSession
) -> CurrencyRead:
    return CurrencyManager(db).update_currency(currency_id, data)


@router.delete("/{currency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_currency(currency_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    CurrencyManager(db).delete_currency(currency_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
