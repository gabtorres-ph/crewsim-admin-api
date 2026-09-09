from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.stripe.models import StripeNotification


class StripeNotificationResourceAccess(CRUDResourceAccess[StripeNotification]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, StripeNotification)
