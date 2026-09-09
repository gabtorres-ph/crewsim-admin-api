from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StripeNotification(Base):
    __tablename__ = "stripenotification"
    __table_args__ = (
        Index("idx_eventid", "eventid"),
        Index("idx_invoiceid", "invoiceid"),
        Index("idx_customerid", "customerid"),
        Index("idx_userid", "userid"),
        Index("idx_createdate", "createdate"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eventid: Mapped[str] = mapped_column(String(100), nullable=False)
    invoiceid: Mapped[str] = mapped_column(String(100), nullable=False)
    customerid: Mapped[str] = mapped_column(String(100), nullable=False)
    taxrate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    taxcountry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_net: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_tax: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_gross: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(100), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    userid: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    createdate: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    imsi: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_credit: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
