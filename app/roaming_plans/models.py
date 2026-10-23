from app.database import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

class RoamingPlans(Base):
    __tablename__ = "roaming_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roaming_plan_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
