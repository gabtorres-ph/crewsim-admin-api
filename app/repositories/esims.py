from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.models import ESIM


class ESIMRepository(CRUDResourceAccess[ESIM]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ESIM)

    def get_by_imsi(self, imsi: str) -> ESIM | None:
        return self.session.scalar(select(ESIM).where(ESIM.imsi == imsi))

    def list_for_user(self, user_id: int, *, offset: int = 0, limit: int = 100) -> list[ESIM]:
        statement = (
            select(ESIM).where(ESIM.userid == user_id).order_by(ESIM.id).offset(offset).limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_for_account(self, account_id: int, *, offset: int = 0, limit: int = 100) -> list[ESIM]:
        statement = (
            select(ESIM)
            .where(ESIM.accountid == account_id)
            .order_by(ESIM.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))
