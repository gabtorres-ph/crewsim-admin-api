from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Usage(Base):
    __tablename__ = "usage"
    __table_args__ = (
        Index("idx_usage_date_utc", "usage_date_utc"),
        Index("idx_imsi", "imsi"),
        Index("idx_iccid", "iccid"),
        Index("idx_imsi_usage_dt", "imsi", "usage_date_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usage_date_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    mcc: Mapped[int] = mapped_column(Integer, nullable=False)
    mnc: Mapped[int] = mapped_column(Integer, nullable=False)
    total_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_type: Mapped[str] = mapped_column(String(100), nullable=False)
    dest_phone_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subs_reseller_name: Mapped[str] = mapped_column(String(100), nullable=False)
    custo_account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    subs_account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    subscriber_id: Mapped[int] = mapped_column(Integer, nullable=False)
    imsi: Mapped[str] = mapped_column(String(100), nullable=False)
    iccid: Mapped[str] = mapped_column(String(100), nullable=False)
    subs_phone_number: Mapped[str] = mapped_column(String(100), nullable=False)
    prepaid_package_ids: Mapped[str] = mapped_column(String(100), nullable=False)
    prepaid_package_qtys: Mapped[str] = mapped_column(String(100), nullable=False)
    toll_free: Mapped[str] = mapped_column(String(10), nullable=False)
    custo_account_id: Mapped[int | None] = mapped_column(
        "CUSTO_ACCOUNT_ID", Integer, nullable=True
    )
    custo_charge: Mapped[Decimal | None] = mapped_column(Numeric(20, 15), nullable=True)
    subs_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subs_charge: Mapped[Decimal | None] = mapped_column(Numeric(20, 15), nullable=True)
    apn: Mapped[str] = mapped_column(String(100), nullable=False)
    rat: Mapped[int] = mapped_column(Integer, nullable=False)
    imei: Mapped[str] = mapped_column(String(100), nullable=False)
    down_bitrate: Mapped[int] = mapped_column(BigInteger, nullable=False)
    up_bitrate: Mapped[int] = mapped_column(BigInteger, nullable=False)
    filename: Mapped[str] = mapped_column(String(100), nullable=False)
