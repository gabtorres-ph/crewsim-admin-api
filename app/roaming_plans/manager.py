from collections.abc import Callable

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError
from app.common.manager import TransactionalManager
from app.roaming_plans.models import RoamingPlans
from app.roaming_plans.resource_access import RoamingPlanResourceAccess
from app.roaming_plans.schemas import RoamingPlanRefreshResult, RoamingPlanSnapshot


class RoamingPlanManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.roaming_plans = RoamingPlanResourceAccess(session)

    def refresh_roaming_plans(
        self, fetch_snapshot: Callable[[], list[RoamingPlanSnapshot]]
    ) -> RoamingPlanRefreshResult:
        """Fetch and apply a roaming-plan snapshot in one transaction."""

        def operation() -> RoamingPlanRefreshResult:
            if not self.roaming_plans.try_acquire_refresh_lock():
                raise ResourceConflictError("Roaming plan refresh is already running")
            snapshot = fetch_snapshot()
            created, updated, unchanged = self.roaming_plans.upsert_snapshot(snapshot)
            return RoamingPlanRefreshResult(
                fetched=len(snapshot),
                created=created,
                updated=updated,
                unchanged=unchanged,
            )

        return self._write(
            operation,
            conflict_message="The roaming plan refresh conflicts with existing database data",
        )

    def list_roaming_plans(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[RoamingPlans]:
        return self.roaming_plans.list(offset=offset, limit=limit)
