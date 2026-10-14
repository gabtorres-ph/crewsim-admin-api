from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.esims.models import ESIM

DELINK_BATCH_SIZE = 500


class ESIMResourceAccess(CRUDResourceAccess[ESIM]):
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

    def delink_accounts(self, account_ids: list[int]) -> int:
        """Detach eSIMs from the given accounts without committing; returns rows changed."""
        delinked = 0
        for start in range(0, len(account_ids), DELINK_BATCH_SIZE):
            batch = account_ids[start : start + DELINK_BATCH_SIZE]
            result = self.session.execute(
                update(ESIM)
                .where(ESIM.accountid.in_(batch))
                .values(accountid=None, use_account_for_charging=False)
            )
            delinked += result.rowcount
        return delinked
