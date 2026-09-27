from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Language(Base):
    __tablename__ = "languages"
    __table_args__ = (UniqueConstraint("iso1", name="uq_languages_iso1"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    iso1: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
