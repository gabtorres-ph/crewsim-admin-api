from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.roaming_plans.models import RoamingPlans
from app.roaming_plans.schemas import RoamingPlanSnapshot

ROAMING_PLAN_BATCH_SIZE = 500
REFRESH_LOCK_KEY = 7_204_002


class RoamingPlanResourceAccess(CRUDResourceAccess[RoamingPlans]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RoamingPlans)

    def try_acquire_refresh_lock(self) -> bool:
        """Take the refresh lock until the transaction ends; False if another holds it."""
        return bool(self.session.scalar(select(func.pg_try_advisory_xact_lock(REFRESH_LOCK_KEY))))

    def upsert_snapshot(self, plans: list[RoamingPlanSnapshot]) -> tuple[int, int, int]:
        """Insert or update roaming plans by ID without committing.

        Returns (created, updated, unchanged) counts.
        """
        created = updated = unchanged = 0
        for start in range(0, len(plans), ROAMING_PLAN_BATCH_SIZE):
            batch = plans[start : start + ROAMING_PLAN_BATCH_SIZE]
            existing = {
                plan.id: plan
                for plan in self.session.scalars(
                    select(RoamingPlans).where(RoamingPlans.id.in_([item.id for item in batch]))
                )
            }
            for snapshot in batch:
                current = existing.get(snapshot.id)
                if current is None:
                    self.session.add(
                        RoamingPlans(id=snapshot.id, roaming_plan_name=snapshot.roaming_plan_name)
                    )
                    created += 1
                elif current.roaming_plan_name != snapshot.roaming_plan_name:
                    current.roaming_plan_name = snapshot.roaming_plan_name
                    updated += 1
                else:
                    unchanged += 1
        self.session.flush()
        return created, updated, unchanged
