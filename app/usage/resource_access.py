from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.usage.models import Usage


class UsageResourceAccess(CRUDResourceAccess[Usage]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Usage)
