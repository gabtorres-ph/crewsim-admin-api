from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.accounts.models import Account
from app.accounts.schemas import AccountSnapshot
from app.common.resource_access import CRUDResourceAccess

ACCOUNT_BATCH_SIZE = 500
# Arbitrary fixed key identifying the Telcovision account refresh advisory lock.
REFRESH_LOCK_KEY = 7_204_001
SNAPSHOT_FIELDS = ("name", "balance", "reseller_id", "package_only", "steering_list_id")


class AccountResourceAccess(CRUDResourceAccess[Account]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Account)

    def try_acquire_refresh_lock(self) -> bool:
        """Take the refresh lock until the transaction ends; False if another holds it."""
        return bool(self.session.scalar(select(func.pg_try_advisory_xact_lock(REFRESH_LOCK_KEY))))

    def upsert_snapshot(self, accounts: list[AccountSnapshot]) -> tuple[int, int, int]:
        """Insert or update accounts by ID without committing.

        Returns (created, updated, unchanged) counts.
        """
        created = updated = unchanged = 0
        for start in range(0, len(accounts), ACCOUNT_BATCH_SIZE):
            batch = accounts[start : start + ACCOUNT_BATCH_SIZE]
            existing = {
                account.id: account
                for account in self.session.scalars(
                    select(Account).where(Account.id.in_([item.id for item in batch]))
                )
            }
            for snapshot in batch:
                values = {field: getattr(snapshot, field) for field in SNAPSHOT_FIELDS}
                current = existing.get(snapshot.id)
                if current is None:
                    self.session.add(Account(id=snapshot.id, **values))
                    created += 1
                elif any(getattr(current, field) != value for field, value in values.items()):
                    for field, value in values.items():
                        setattr(current, field, value)
                    updated += 1
                else:
                    unchanged += 1
        self.session.flush()
        return created, updated, unchanged

    def list_missing_ids(self, present_ids: set[int]) -> list[int]:
        current_ids = self.session.scalars(select(Account.id).order_by(Account.id))
        return [account_id for account_id in current_ids if account_id not in present_ids]

    def delete_ids(self, account_ids: list[int]) -> int:
        """Delete accounts by ID without committing; returns rows deleted."""
        deleted = 0
        for start in range(0, len(account_ids), ACCOUNT_BATCH_SIZE):
            batch = account_ids[start : start + ACCOUNT_BATCH_SIZE]
            result = self.session.execute(delete(Account).where(Account.id.in_(batch)))
            deleted += result.rowcount
        return deleted
