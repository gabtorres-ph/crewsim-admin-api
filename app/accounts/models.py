from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.esims.models import ESIM


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    reseller_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_only: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    steering_list_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    esims: Mapped[list["ESIM"]] = relationship(back_populates="account", passive_deletes=True)
