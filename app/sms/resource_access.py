from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.sms.models import Sms


class SmsResourceAccess(CRUDResourceAccess[Sms]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Sms)
