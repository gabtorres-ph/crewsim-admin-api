from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.roaming_plan_details.models import RoamingPlanDetails
from app.roaming_plan_details.schemas import RoamingPlanDetailSnapshot

ROAMING_PLAN_DETAIL_BATCH_SIZE = 500
REFRESH_LOCK_KEY = 7_204_003


class RoamingPlanDetailResourceAccess(CRUDResourceAccess[RoamingPlanDetails]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RoamingPlanDetails)

    def try_acquire_refresh_lock(self) -> bool:
        """Take the refresh lock until the transaction ends; False if another holds it."""
        return bool(self.session.scalar(select(func.pg_try_advisory_xact_lock(REFRESH_LOCK_KEY))))

    def upsert_snapshot(
        self, details: list[RoamingPlanDetailSnapshot]
    ) -> tuple[int, int, int]:
        """Insert or update roaming-plan details by rule ID without committing.

        Returns (created, updated, unchanged) counts.
        """
        created = updated = unchanged = 0
        for start in range(0, len(details), ROAMING_PLAN_DETAIL_BATCH_SIZE):
            batch = details[start : start + ROAMING_PLAN_DETAIL_BATCH_SIZE]
            existing = {
                detail.roaming_plan_rule_id: detail
                for detail in self.session.scalars(
                    select(RoamingPlanDetails).where(
                        RoamingPlanDetails.roaming_plan_rule_id.in_(
                            [item.roaming_plan_rule_id for item in batch]
                        )
                    )
                )
            }
            for snapshot in batch:
                values = snapshot.model_dump()
                current = existing.get(snapshot.roaming_plan_rule_id)
                if current is None:
                    self.session.add(RoamingPlanDetails(**values))
                    created += 1
                elif any(getattr(current, field) != value for field, value in values.items()):
                    for field, value in values.items():
                        setattr(current, field, value)
                    updated += 1
                else:
                    unchanged += 1
        self.session.flush()
        return created, updated, unchanged
