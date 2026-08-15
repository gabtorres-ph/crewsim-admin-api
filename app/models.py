from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(255), nullable=False)


class ESIM(Base):
    __tablename__ = "esims"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    userid: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    imsi: Mapped[str] = mapped_column(String(255), nullable=False)
