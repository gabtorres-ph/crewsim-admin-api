from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.accounts.models import Account


class AccountResourceAccess(CRUDResourceAccess[Account]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Account)
