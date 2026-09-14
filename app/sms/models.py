from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Sms(Base):
    __tablename__ = "sms"
    __table_args__ = (
        Index("userid_idx", "userid"),
        Index("imsi_idx", "imsi"),
        Index("createdate_idx", "createdate"),
        Index("sentresultcode_idx", "sentresultcode"),
        Index("sentdate_idx", "sentdate"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column("userid", Integer, nullable=False)
    imsi: Mapped[str] = mapped_column(String(100), nullable=False)
    sender: Mapped[str] = mapped_column(String(100), nullable=False)
    sms_text: Mapped[str] = mapped_column("smstext", String(3000), nullable=False)
    template: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column("createdate", DateTime, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column("sentdate", DateTime, nullable=True)
    sent_result_code: Mapped[str | None] = mapped_column(
        "sentresultcode", String(50), nullable=True
    )
    sent_result_text: Mapped[str | None] = mapped_column(
        "sentresulttext", String(150), nullable=True
    )
    retry_counter: Mapped[int | None] = mapped_column("retrycounter", Integer, nullable=True)
