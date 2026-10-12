from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.sim_notifications.models import SimNotification


class SimNotificationResourceAccess(CRUDResourceAccess[SimNotification]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, SimNotification)

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        typ: str | None = None,
        imsi: str | None = None,
    ) -> list[SimNotification]:
        statement = select(SimNotification)
        if typ is not None:
            statement = statement.where(SimNotification.typ == typ)
        if imsi is not None:
            statement = statement.where(SimNotification.imsi == imsi)
        statement = statement.order_by(SimNotification.id.desc()).offset(offset).limit(limit)
        return list(self.session.scalars(statement))
