import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.accounts.manager import AccountManager
from app.config import Settings, get_settings
from app.database import get_db
from app.esims.manager import ESIMManager
from app.esims.schemas import ESIMCreate, ESIMRead, ESIMRefreshResult, ESIMUpdate
from app.integrations.telcovision.client import TelcovisionError, TelcovisionNotConfiguredError
from app.integrations.telcovision.subscribers import refresh_telcovision_subscribers

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/esims", tags=["esims"])
account_router = APIRouter(prefix="/accounts", tags=["accounts"])
user_router = APIRouter(prefix="/users", tags=["users"])
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.post("", response_model=ESIMRead, status_code=status.HTTP_201_CREATED)
def create_esim(data: ESIMCreate, db: DatabaseSession) -> ESIMRead:
    return ESIMManager(db).create_esim(data)


@router.get("", response_model=list[ESIMRead])
def list_esims(
    db: DatabaseSession,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ESIMRead]:
    return ESIMManager(db).list_esims(user_id=user_id, offset=offset, limit=limit)


@router.post("/refresh", response_model=list[ESIMRefreshResult])
def refresh_esims(
    request: Request,
    db: DatabaseSession,
    settings: AppSettings,
    account_id: Annotated[int, Query(gt=0)],
) -> list[ESIMRefreshResult]:
    try:
        return refresh_telcovision_subscribers(
            db,
            settings,
            account_id=account_id,
            request_id=request.state.request_id,
            outbound_exchanges=request.state.outbound_exchanges,
        )
    except TelcovisionNotConfiguredError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "eSIM refresh is not configured"
        ) from None
    except TelcovisionError as error:
        logger.warning(
            "Telcovision eSIM refresh failed account_id=%s category=%s provider_code=%s",
            account_id,
            error.category,
            error.provider_code,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            {
                "message": "Telcovision eSIM refresh failed",
                "category": error.category,
                "provider_code": error.provider_code,
            },
        ) from None


@router.get("/{esim_id}", response_model=ESIMRead)
def get_esim(esim_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> ESIMRead:
    return ESIMManager(db).get_esim(esim_id)


@router.patch("/{esim_id}", response_model=ESIMRead)
def update_esim(
    esim_id: Annotated[int, Path(gt=0)], data: ESIMUpdate, db: DatabaseSession
) -> ESIMRead:
    return ESIMManager(db).update_esim(esim_id, data)


@router.delete("/{esim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_esim(esim_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    ESIMManager(db).delete_esim(esim_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@account_router.get("/{account_id}/esims", response_model=list[ESIMRead])
def list_account_esims(
    account_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ESIMRead]:
    AccountManager(db).get_account(account_id)
    return ESIMManager(db).list_esims(account_id=account_id, offset=offset, limit=limit)


@user_router.get("/{user_id}/esims", response_model=list[ESIMRead])
def list_user_esims(
    user_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ESIMRead]:
    return ESIMManager(db).list_esims(user_id=user_id, offset=offset, limit=limit)
