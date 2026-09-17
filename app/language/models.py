from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Language(Base):
    __tablename__ = "languages"
    __table_args__ = (
        UniqueConstraint("iso1", name="uq_languages_iso1"),
        UniqueConstraint("iso2b", name="uq_languages_iso2b"),
        UniqueConstraint("iso2t", name="uq_languages_iso2t"),
        UniqueConstraint("iso3", name="uq_languages_iso3"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    iso1: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    iso2b: Mapped[str | None] = mapped_column(String(3), nullable=True)
    iso2t: Mapped[str | None] = mapped_column(String(3), nullable=True)
    iso3: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
