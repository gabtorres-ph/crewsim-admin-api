from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NetworkStatus(Base):
    __tablename__ = "network_status"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    simid: Mapped[int] = mapped_column(Integer, nullable=False)
    imsi: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    profiletype: Mapped[str] = mapped_column(String(255), nullable=False)
    statusmodification: Mapped[str] = mapped_column(String(255), nullable=False)
