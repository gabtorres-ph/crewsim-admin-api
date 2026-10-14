import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.accounts.manager import AccountManager
from app.accounts.schemas import AccountCreate, AccountRead, AccountRefreshResult, AccountUpdate
from app.config import Settings, get_settings
from app.database import get_db
from app.integrations.telcovision.accounts import (
    TelcovisionNotConfiguredError,
    refresh_telcovision_accounts,
)
from app.integrations.telcovision.client import TelcovisionError

router = APIRouter(prefix="/accounts", tags=["accounts"])
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def require_refresh_key(
    settings: AppSettings,
    provided_key: Annotated[str | None, Header(alias="X-Accounts-Refresh-Key")] = None,
) -> None:
    expected = settings.accounts_refresh_key.get_secret_value()
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Account refresh is not configured"
        )
    if provided_key is None or not secrets.compare_digest(provided_key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh key")


# The refresh key check is temporarily disabled. To re-enable it, add
# dependencies=[Depends(require_refresh_key)] to this route.
@router.post("/refresh", response_model=AccountRefreshResult)
def refresh_accounts(db: DatabaseSession, settings: AppSettings) -> AccountRefreshResult:
    try:
        return refresh_telcovision_accounts(db, settings)
    except TelcovisionNotConfiguredError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Account refresh is not configured"
        ) from None
    except TelcovisionError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Telcovision account refresh failed"
        ) from None


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
