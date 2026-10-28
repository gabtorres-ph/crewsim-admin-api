from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RoamingPlanDetails(Base):
    __tablename__ = "roaming_plan_details"

    roaming_plan_rule_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )
    roaming_plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    network_id: Mapped[int] = mapped_column(Integer, nullable=False)
    continent: Mapped[str] = mapped_column(String(100), nullable=False)
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    country_iso2: Mapped[str] = mapped_column(String(2), nullable=False)
    operator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mcc_mncs: Mapped[list[dict[str, str]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    tadigs: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
