from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.currencies.models import Currencies


class CurrencyResourceAccess(CRUDResourceAccess[Currencies]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Currencies)
