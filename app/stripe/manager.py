from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.common.resource_access import CRUDResourceAccess
from app.stripe.models import StripeNotification
from app.stripe.schemas import StripeNotificationCreate, StripeNotificationUpdate


class StripeManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.notifications = CRUDResourceAccess(session, StripeNotification)

    def create_notification(self, data: StripeNotificationCreate) -> StripeNotification:
        return self._write(
            lambda: self.notifications.create(data.model_dump()),
            conflict_message="The stripe notification conflicts with existing database data",
        )

    def get_notification(self, notification_id: int) -> StripeNotification:
        notification = self.notifications.get(notification_id)
        if notification is None:
            raise ResourceNotFoundError("Stripe notification", notification_id)
        return notification

    def list_notifications(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[StripeNotification]:
        return self.notifications.list(offset=offset, limit=limit)

    def update_notification(
        self, notification_id: int, data: StripeNotificationUpdate
    ) -> StripeNotification:
        notification = self.get_notification(notification_id)
        return self._write(
            lambda: self.notifications.update(
                notification, data.model_dump(exclude_unset=True)
            ),
            conflict_message="The stripe notification update conflicts with existing database data",
        )

    def delete_notification(self, notification_id: int) -> None:
        notification = self.get_notification(notification_id)
        self._write(
            lambda: self.notifications.delete(notification),
            conflict_message=(
                "The stripe notification cannot be deleted while it is referenced by other data"
            ),
        )
