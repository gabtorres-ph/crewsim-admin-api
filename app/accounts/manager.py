from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.models import Account
from app.accounts.manager import AccountResourceAccess
from app.accounts.schemas import AccountCreate, AccountUpdate


class AccountManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.accounts = AccountResourceAccess(session)

    def create_account(self, data: AccountCreate) -> Account:
        return self._write(
            lambda: self.accounts.create(data.model_dump()),
            conflict_message="The account conflicts with existing database data",
        )

    def get_account(self, account_id: int) -> Account:
        account = self.accounts.get(account_id)
        if account is None:
            raise ResourceNotFoundError("Account", account_id)
        return account

    def list_accounts(self, *, offset: int = 0, limit: int = 100) -> list[Account]:
        return self.accounts.list(offset=offset, limit=limit)

    def update_account(self, account_id: int, data: AccountUpdate) -> Account:
        account = self.get_account(account_id)
        return self._write(
            lambda: self.accounts.update(account, data.model_dump(exclude_unset=True)),
            conflict_message="The account update conflicts with existing database data",
        )

    def delete_account(self, account_id: int) -> None:
        account = self.get_account(account_id)
        self._write(
            lambda: self.accounts.delete(account),
            conflict_message="The account cannot be deleted while it is referenced by other data",
        )

