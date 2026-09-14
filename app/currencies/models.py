from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Currencies(Base):
    __tablename__ = "currencies"
    __table_args__ = (UniqueConstraint("iso_numeric"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    symbol_native: Mapped[str] = mapped_column(String(10), nullable=False)
    decimal_digits: Mapped[int] = mapped_column(Integer, nullable=False)
    rounding: Mapped[int] = mapped_column(Integer, nullable=False)
    iso_numeric: Mapped[int] = mapped_column(Integer, nullable=False)
