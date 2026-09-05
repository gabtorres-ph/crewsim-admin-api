from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.esims.models import ESIM
    from app.models import Favorite


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(255), nullable=False)
    firstname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lastname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    airline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referralcode: Mapped[str | None] = mapped_column(String(8), nullable=True)
    referredby: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    stripeid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logtoid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    createdate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    newsletter: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    smsnotification: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rateus: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    esims: Mapped[list["ESIM"]] = relationship(back_populates="user", passive_deletes=True)
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", passive_deletes=True)
