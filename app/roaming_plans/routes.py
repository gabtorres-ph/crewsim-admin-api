import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.integrations.telcovision.client import TelcovisionError, TelcovisionNotConfiguredError
from app.integrations.telcovision.subscriber_tariff import refresh_telcovision_subscriber_tariffs
from app.integrations.telcovision.tariff_rule import refresh_telcovision_tariff_rules
from app.roaming_plan_details.manager import RoamingPlanDetailManager
from app.roaming_plan_details.schemas import (
    RoamingPlanDetailRead,
    RoamingPlanDetailRefreshResult,
)
from app.roaming_plans.manager import RoamingPlanManager
from app.roaming_plans.schemas import RoamingPlanRead, RoamingPlanRefreshResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/roaming-plans", tags=["roaming-plans"])
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.get("", response_model=list[RoamingPlanRead])
def list_roaming_plans(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[RoamingPlanRead]:
    return RoamingPlanManager(db).list_roaming_plans(offset=offset, limit=limit)


@router.get("/details", response_model=list[RoamingPlanDetailRead])
def list_roaming_plan_details(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[RoamingPlanDetailRead]:
    return RoamingPlanDetailManager(db).list_roaming_plan_details(
        offset=offset,
        limit=limit,
    )


@router.post("/refresh", response_model=RoamingPlanRefreshResult)
def refresh_roaming_plans(
    request: Request,
    db: DatabaseSession,
    settings: AppSettings,
) -> RoamingPlanRefreshResult:
    try:
        return refresh_telcovision_subscriber_tariffs(
            db,
            settings,
            request_id=request.state.request_id,
            outbound_exchanges=request.state.outbound_exchanges,
        )
    except TelcovisionNotConfiguredError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Roaming plan refresh is not configured"
        ) from None
    except TelcovisionError as error:
        logger.warning(
            "Telcovision roaming plan refresh failed category=%s provider_code=%s",
            error.category,
            error.provider_code,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            {
                "message": "Telcovision roaming plan refresh failed",
                "category": error.category,
                "provider_code": error.provider_code,
            },
        ) from None


@router.post("/details/refresh", response_model=RoamingPlanDetailRefreshResult)
def refresh_roaming_plan_details(
    request: Request,
    db: DatabaseSession,
    settings: AppSettings,
    tariff_id: int | None = Query(default=None, gt=0),
) -> RoamingPlanDetailRefreshResult:
    try:
        return refresh_telcovision_tariff_rules(
            db,
            settings,
            tariff_id=tariff_id,
            request_id=request.state.request_id,
            outbound_exchanges=request.state.outbound_exchanges,
        )
    except TelcovisionNotConfiguredError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Roaming plan detail refresh is not configured",
        ) from None
    except TelcovisionError as error:
        logger.warning(
            "Telcovision roaming plan detail refresh failed category=%s provider_code=%s",
            error.category,
            error.provider_code,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            {
                "message": "Telcovision roaming plan detail refresh failed",
                "category": error.category,
                "provider_code": error.provider_code,
            },
        ) from None
