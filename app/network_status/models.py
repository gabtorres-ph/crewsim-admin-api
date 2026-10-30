from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NetworkStatus(Base):
    __tablename__ = "network_status"
    __table_args__ = (Index("network_status_imsi_idx", "imsi"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simid: Mapped[int] = mapped_column(Integer, nullable=False)
    imsi: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    profiletype: Mapped[str] = mapped_column(String(255), nullable=False)
    statusmodification: Mapped[str] = mapped_column(String(255), nullable=False)
