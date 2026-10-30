from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.network_status.manager import NetworkStatusManager
from app.network_status.schemas import NetworkStatusRead

router = APIRouter(prefix="/network-status", tags=["network-status"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/{imsi}", response_model=list[NetworkStatusRead])
def list_network_statuses_for_imsi(
    imsi: Annotated[str, Path(pattern=r"^[0-9]{5,15}$")],
    db: DatabaseSession,
) -> list[NetworkStatusRead]:
    return NetworkStatusManager(db).list_network_statuses_for_imsi(imsi)
