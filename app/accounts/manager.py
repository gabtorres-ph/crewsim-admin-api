from collections.abc import Callable

from sqlalchemy.orm import Session

from app.accounts.models import Account
from app.accounts.resource_access import AccountResourceAccess
from app.accounts.schemas import (
    AccountCreate,
    AccountRefreshResult,
    AccountSnapshot,
    AccountUpdate,
)
from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.common.manager import TransactionalManager

TELCOVISION_MANAGED_MESSAGE = "Accounts are managed by Telcovision"


class AccountManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.accounts = AccountResourceAccess(session)

    def refresh_accounts(
        self, fetch_snapshot: Callable[[], list[AccountSnapshot]]
    ) -> AccountRefreshResult:
        """Make accounts match the fetched snapshot in one transaction."""

        def operation() -> AccountRefreshResult:
            if not self.accounts.try_acquire_refresh_lock():
                raise ResourceConflictError("Account refresh is already running")
            snapshot = fetch_snapshot()
            created, updated, unchanged = self.accounts.upsert_snapshot(snapshot)
            missing_ids = self.accounts.list_missing_ids({item.id for item in snapshot})
            deleted = self.accounts.delete_ids(missing_ids)
            return AccountRefreshResult(
                fetched=len(snapshot),
                created=created,
                updated=updated,
                unchanged=unchanged,
                deleted=deleted,
            )

        return self._write(
            operation, conflict_message="The account refresh conflicts with existing database data"
        )

    def create_account(self, data: AccountCreate) -> Account:
        raise ResourceConflictError(TELCOVISION_MANAGED_MESSAGE)

    def get_account(self, account_id: int) -> Account:
        account = self.accounts.get(account_id)
        if account is None:
            raise ResourceNotFoundError("Account", account_id)
        return account

    def list_accounts(self, *, offset: int = 0, limit: int = 100) -> list[Account]:
        return self.accounts.list(offset=offset, limit=limit)

    def update_account(self, account_id: int, data: AccountUpdate) -> Account:
        raise ResourceConflictError(TELCOVISION_MANAGED_MESSAGE)

    def delete_account(self, account_id: int) -> None:
        raise ResourceConflictError(TELCOVISION_MANAGED_MESSAGE)
