from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.accounts.models import Account
from app.database import Base
from app.users.models import User


class ESIM(Base):
    __tablename__ = "esims"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    userid: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    accountid: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    imsi: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    isesim: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    createdate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    token: Mapped[str | None] = mapped_column(String(8), nullable=True)
    networkstatus: Mapped[str | None] = mapped_column(String(255), nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    use_account_for_charging: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    smdpserver: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activationcode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imei: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imei_device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allow_data: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    user: Mapped[User | None] = relationship(back_populates="esims")
    account: Mapped[Account] = relationship(back_populates="esims")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("userid", "country", name="uq_favorites_userid_country"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    userid: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    country: Mapped[str] = mapped_column(String(255), nullable=False)
    user: Mapped[User] = relationship(back_populates="favorites")
