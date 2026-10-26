from collections.abc import Callable

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError
from app.common.manager import TransactionalManager
from app.roaming_plan_details.models import RoamingPlanDetails
from app.roaming_plan_details.resource_access import RoamingPlanDetailResourceAccess
from app.roaming_plan_details.schemas import (
    RoamingPlanDetailRefreshResult,
    RoamingPlanDetailSnapshot,
)


class RoamingPlanDetailManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.roaming_plan_details = RoamingPlanDetailResourceAccess(session)

    def refresh_roaming_plan_details(
        self, fetch_snapshot: Callable[[], list[RoamingPlanDetailSnapshot]]
    ) -> RoamingPlanDetailRefreshResult:
        """Fetch and apply a roaming-plan-detail snapshot in one transaction."""

        def operation() -> RoamingPlanDetailRefreshResult:
            if not self.roaming_plan_details.try_acquire_refresh_lock():
                raise ResourceConflictError("Roaming plan detail refresh is already running")
            snapshot = fetch_snapshot()
            created, updated, unchanged = self.roaming_plan_details.upsert_snapshot(snapshot)
            return RoamingPlanDetailRefreshResult(
                fetched=len(snapshot),
                created=created,
                updated=updated,
                unchanged=unchanged,
            )

        return self._write(
            operation,
            conflict_message=(
                "The roaming plan detail refresh conflicts with existing database data"
            ),
        )

    def list_roaming_plan_details(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[RoamingPlanDetails]:
        return self.roaming_plan_details.list(offset=offset, limit=limit)
