from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.sim_notifications.models import SimNotification, SimNotificationType
from app.sim_notifications.resource_access import SimNotificationResourceAccess
from app.sim_notifications.schemas import SimNotificationCreate


class SimNotificationManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.notifications = SimNotificationResourceAccess(session)

    def create_notification(self, data: SimNotificationCreate) -> SimNotification:
        # An omitted createdate falls back to the database's current timestamp.
        return self._write(
            lambda: self.notifications.create(data.model_dump(exclude_none=True)),
            conflict_message="The SIM notification conflicts with existing database data",
        )

    def get_notification(self, notification_id: int) -> SimNotification:
        notification = self.notifications.get(notification_id)
        if notification is None:
            raise ResourceNotFoundError("SIM notification", notification_id)
        return notification

    def list_notifications(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        typ: SimNotificationType | None = None,
        imsi: str | None = None,
    ) -> list[SimNotification]:
        return self.notifications.list(offset=offset, limit=limit, typ=typ, imsi=imsi)

    def delete_notification(self, notification_id: int) -> None:
        notification = self.get_notification(notification_id)
        self._write(
            lambda: self.notifications.delete(notification),
            conflict_message=(
                "The SIM notification cannot be deleted while it is referenced by other data"
            ),
        )
