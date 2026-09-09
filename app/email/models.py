from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailWhitelist(Base):
    __tablename__ = "email_whitelist"
    __table_args__ = (
        UniqueConstraint("email", name="UNIQ_EMAILWHITELIST_EMAIL"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    createdate: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), nullable=False)
