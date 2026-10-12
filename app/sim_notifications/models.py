from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SimNotificationType(StrEnum):
    LOCATION = "location"
    ES2 = "ES2"
    PACKAGE = "package"


class SimNotification(Base):
    __tablename__ = "sim_notification"
    __table_args__ = (
        Index("idx_sim_notification_typ", "typ"),
        Index("idx_sim_notification_imsi", "imsi"),
        Index("idx_sim_notification_createdate", "createdate"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    typ: Mapped[str] = mapped_column(String(20), nullable=False)
    imsi: Mapped[str] = mapped_column(String(15), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    createdate: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
