from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.accounts.manager import AccountManager
from app.accounts.schemas import AccountCreate, AccountRead, AccountUpdate
from app.database import get_db
from app.schemas.esims import ESIMRead
from app.services.esims import ESIMService

router = APIRouter(prefix="/accounts", tags=["accounts"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate, db: DatabaseSession) -> AccountRead:
    return AccountManager(db).create_account(data)


@router.get("", response_model=list[AccountRead])
def list_accounts(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[AccountRead]:
    return AccountManager(db).list_accounts(offset=offset, limit=limit)


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> AccountRead:
    return AccountManager(db).get_account(account_id)


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: Annotated[int, Path(gt=0)], data: AccountUpdate, db: DatabaseSession
) -> AccountRead:
    return AccountManager(db).update_account(account_id, data)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    AccountManager(db).delete_account(account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{account_id}/esims", response_model=list[ESIMRead])
def list_account_esims(
    account_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ESIMRead]:
    AccountManager(db).get_account(account_id)
    return ESIMService(db).list_esims(account_id=account_id, offset=offset, limit=limit)
