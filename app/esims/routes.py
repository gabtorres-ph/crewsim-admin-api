import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.accounts.manager import AccountManager
from app.config import Settings, get_settings
from app.database import get_db
from app.esims.manager import ESIMManager
from app.esims.schemas import (
    ESIMCreate,
    ESIMMoveRequest,
    ESIMMoveResult,
    ESIMRead,
    ESIMRefreshResult,
    ESIMUpdate,
)
from app.integrations.telcovision.client import TelcovisionError, TelcovisionNotConfiguredError
from app.integrations.telcovision.subscribers import (
    TelcovisionSubscriberMoveError,
    move_subscriber_range_to_account,
    refresh_telcovision_subscriber,
    refresh_telcovision_subscribers,
)

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


@router.post("/move-to-account", response_model=list[ESIMMoveResult])
def move_esims_to_account(
    data: ESIMMoveRequest,
    request: Request,
    db: DatabaseSession,
    settings: AppSettings,
) -> list[ESIMMoveResult]:
    try:
        return move_subscriber_range_to_account(
            db,
            settings,
            source_account_id=data.source_account_id,
            destination_account_id=data.destination_account_id,
            imsis=data.imsis,
            request_id=request.state.request_id,
            outbound_exchanges=request.state.outbound_exchanges,
        )
    except TelcovisionNotConfiguredError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "eSIM transfer is not configured"
        ) from None
    except TelcovisionSubscriberMoveError as error:
        logger.warning(
            "Telcovision eSIM transfer failed source_account_id=%s destination_account_id=%s "
            "failed_imsi=%s category=%s provider_code=%s",
            data.source_account_id,
            data.destination_account_id,
            error.failed_imsi,
            error.category,
            error.provider_code,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            {
                "message": "Telcovision eSIM transfer failed",
                "category": error.category,
                "provider_code": error.provider_code,
                "moved_imsis": error.moved_imsis,
                "failed_imsi": error.failed_imsi,
                "not_attempted_imsis": error.not_attempted_imsis,
            },
        ) from None
    except TelcovisionError as error:
        logger.warning(
            "Telcovision eSIM transfer failed source_account_id=%s destination_account_id=%s "
            "category=%s provider_code=%s",
            data.source_account_id,
            data.destination_account_id,
            error.category,
            error.provider_code,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            {
                "message": "Telcovision eSIM transfer failed",
                "category": error.category,
                "provider_code": error.provider_code,
            },
        ) from None


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


@router.post("/refresh/{account_id}", response_model=list[ESIMRefreshResult])
def refresh_esims_by_account(
    account_id: Annotated[int, Path(gt=0)],
    request: Request,
    db: DatabaseSession,
    settings: AppSettings,
) -> list[ESIMRefreshResult]:
    return refresh_esims(request=request, db=db, settings=settings, account_id=account_id)


@router.post(
    "/{imsi}/refresh",
    response_model=ESIMRefreshResult,
    status_code=status.HTTP_200_OK,
)
def refresh_esim_by_imsi(
    imsi: Annotated[str, Path(pattern=r"^[0-9]{5,15}$")],
    request: Request,
    db: DatabaseSession,
    settings: AppSettings,
) -> ESIMRefreshResult:
    try:
        return refresh_telcovision_subscriber(
            db,
            settings,
            imsi=imsi,
            request_id=request.state.request_id,
            outbound_exchanges=request.state.outbound_exchanges,
        )
    except TelcovisionNotConfiguredError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "eSIM refresh is not configured"
        ) from None
    except TelcovisionError as error:
        logger.warning(
            "Telcovision eSIM refresh failed imsi=%s category=%s provider_code=%s",
            imsi,
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

