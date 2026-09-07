from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Crew(Base):
    __tablename__ = "crewid"
    __table_args__ = (
        Index("IDX_file1_hash", "file1_hash"),
        Index("IDX_file2_hash", "file2_hash"),
        Index("IDX_unique_id", "unique_id"),
        Index("IDX_userid", "userid"),
        Index("idx_crewid_dhash", "dhash"),
        Index("idx_crewid_phash", "phash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unique_id: Mapped[str] = mapped_column(String(50), nullable=False)
    file1: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    firstname: Mapped[str | None] = mapped_column(String(150), nullable=True)
    lastname: Mapped[str | None] = mapped_column(String(150), nullable=True)
    airline: Mapped[str | None] = mapped_column(String(150), nullable=True)
    iscrewid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    createdate: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    userid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file1_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file2_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dhash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    phash: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dhash_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phash_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
