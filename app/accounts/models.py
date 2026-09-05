from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    esims: Mapped[list["ESIM"]] = relationship(back_populates="account", passive_deletes=True)