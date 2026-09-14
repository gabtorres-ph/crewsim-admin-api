from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Country(Base):
    __tablename__ = "countries"
    __table_args__ = (
        UniqueConstraint("cc2", name="uq_countries_cc2"),
        UniqueConstraint("cc3", name="uq_countries_cc3"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cc2: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    cc3: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    continent: Mapped[str | None] = mapped_column(String(2), nullable=True)
    flag_emoji: Mapped[str | None] = mapped_column(String(16), nullable=True)
    flag_url1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    flag_url2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_square: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_rectangle: Mapped[str | None] = mapped_column(String(255), nullable=True)
