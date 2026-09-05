from typing import Any

from sqlalchemy.orm import Session

from app.accounts.resource_access import AccountResourceAccess
from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.models import ESIM
from app.repositories.esims import ESIMRepository
from app.schemas.esims import ESIMCreate, ESIMUpdate
from app.users.resource_access import UserResourceAccess


class ESIMService(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.esims = ESIMRepository(session)
        self.users = UserResourceAccess(session)
        self.accounts = AccountResourceAccess(session)

    def create_esim(self, data: ESIMCreate) -> ESIM:
        values = data.model_dump()
        self._validate_references(values)
        values = self._database_values(values)
        return self._write(
            lambda: self.esims.create(values),
            conflict_message="The eSIM conflicts with existing database data",
        )

    def get_esim(self, esim_id: int) -> ESIM:
        esim = self.esims.get(esim_id)
        if esim is None:
            raise ResourceNotFoundError("eSIM", esim_id)
        return esim

    def list_esims(
        self,
        *,
        user_id: int | None = None,
        account_id: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ESIM]:
        if user_id is not None:
            self._require_user(user_id)
        if account_id is not None:
            self._require_account(account_id)
        if user_id is not None:
            return self.esims.list_for_user(user_id, offset=offset, limit=limit)
        if account_id is not None:
            return self.esims.list_for_account(account_id, offset=offset, limit=limit)
        return self.esims.list(offset=offset, limit=limit)

    def update_esim(self, esim_id: int, data: ESIMUpdate) -> ESIM:
        esim = self.get_esim(esim_id)
        values = data.model_dump(exclude_unset=True)
        self._validate_references(values)
        values = self._database_values(values)
        return self._write(
            lambda: self.esims.update(esim, values),
            conflict_message="The eSIM update conflicts with existing database data",
        )

    def delete_esim(self, esim_id: int) -> None:
        esim = self.get_esim(esim_id)
        self._write(
            lambda: self.esims.delete(esim),
            conflict_message="The eSIM cannot be deleted because it is referenced by other data",
        )

    def _require_user(self, user_id: int) -> None:
        if self.users.get(user_id) is None:
            raise ResourceNotFoundError("User", user_id)

    def _require_account(self, account_id: int) -> None:
        if self.accounts.get(account_id) is None:
            raise ResourceNotFoundError("Account", account_id)

    def _validate_references(self, values: dict[str, Any]) -> None:
        if values.get("user_id") is not None:
            self._require_user(values["user_id"])
        if "account_id" in values:
            self._require_account(values["account_id"])

    @staticmethod
    def _database_values(values: dict[str, Any]) -> dict[str, Any]:
        if "user_id" in values:
            values["userid"] = values.pop("user_id")
        if "account_id" in values:
            values["accountid"] = values.pop("account_id")
        return values
