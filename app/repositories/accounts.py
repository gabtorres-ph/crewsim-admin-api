from sqlalchemy.orm import Session

from app.models import Account
from app.repositories.base import CRUDRepository


class AccountRepository(CRUDRepository[Account]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Account)
