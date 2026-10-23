from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[int | None] = mapped_column(ForeignKey("currencies.id"), nullable=True)
    language: Mapped[int | None] = mapped_column(ForeignKey("languages.id"), nullable=True)
    timezone: Mapped[int | None] = mapped_column(ForeignKey("time_zone.id"), nullable=True)
    reseller_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_only: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    steering_list_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
