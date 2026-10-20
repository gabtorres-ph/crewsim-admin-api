from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.accounts.resource_access import AccountResourceAccess
from app.common.exceptions import InvalidOperationError, ResourceConflictError, ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.esims.models import ESIM
from app.esims.resource_access import ESIMResourceAccess
from app.esims.schemas import (
    ESIMCreate,
    ESIMMoveResult,
    ESIMRefreshResult,
    ESIMSingleSnapshot,
    ESIMSnapshot,
    ESIMUpdate,
)
from app.users.resource_access import UserResourceAccess


class ESIMManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.esims = ESIMResourceAccess(session)
        self.users = UserResourceAccess(session)
        self.accounts = AccountResourceAccess(session)

    def refresh_esims(
        self, account_id: int, fetch_snapshot: Callable[[], list[ESIMSnapshot]]
    ) -> list[ESIMRefreshResult]:
        """Refresh eSIMs for an existing account in one transaction."""

        def operation() -> list[ESIMRefreshResult]:
            self._require_account(account_id)
            snapshots = fetch_snapshot()
            # TODO duplicates are already rejected by parse_subscriber_snapshot (502); decide
            # whether to keep this check for other callers and align the error it returns
            if len({snapshot.imsi for snapshot in snapshots}) != len(snapshots):
                raise InvalidOperationError("The eSIM refresh snapshot contains duplicate IMSIs")
            esims = self.esims.upsert_snapshot(snapshots)
            return [ESIMRefreshResult.model_validate(esim) for esim in esims]

        return self._write(
            operation, conflict_message="The eSIM refresh conflicts with existing database data"
        )

    def refresh_esim(
        self, imsi: str, fetch_snapshot: Callable[[], ESIMSingleSnapshot]
    ) -> ESIMRefreshResult:
        """Refresh an existing eSIM by IMSI in one transaction."""

        def operation() -> ESIMRefreshResult:
            esim = self.esims.get_by_imsi(imsi)
            if esim is None:
                raise ResourceNotFoundError("eSIM with IMSI", imsi)
            snapshot = fetch_snapshot()
            if snapshot.imsi != imsi:
                raise InvalidOperationError("The eSIM refresh snapshot IMSI does not match")
            if snapshot.account_id is not None and "account_id" in snapshot.model_fields_set:
                self._require_account(snapshot.account_id)
            esim = self.esims.update_single_snapshot(esim, snapshot)
            return ESIMRefreshResult.model_validate(esim)

        return self._write(
            operation, conflict_message="The eSIM refresh conflicts with existing database data"
        )

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

    def validate_account_move(
        self, source_account_id: int, destination_account_id: int, imsis: list[str]
    ) -> None:
        source_account = self.accounts.get(source_account_id)
        if source_account is None:
            raise ResourceNotFoundError("Account", source_account_id)
        destination_account = self.accounts.get(destination_account_id)
        if destination_account is None:
            raise ResourceNotFoundError("Account", destination_account_id)
        if source_account_id == destination_account_id:
            raise InvalidOperationError("Source and destination accounts must differ")
        if (
            source_account.reseller_id is not None
            and destination_account.reseller_id is not None
            and source_account.reseller_id != destination_account.reseller_id
        ):
            raise InvalidOperationError("Subscribers can only move between accounts of the same reseller")
        self._require_esims_in_account(source_account_id, imsis)

    def move_esims_to_account(
        self,
        src_account: int,
        dst_account: int,
        imsi_list: list[str],
        move_subscribers: Callable[[], None],
    ) -> list[ESIMMoveResult]:
        def operation() -> list[ESIMMoveResult]:
            self._require_esims_in_account(src_account, imsi_list, for_update=True)
            move_subscribers()
            esims = self.esims.move_esims_to_account(src_account, dst_account, imsi_list)
            if len(esims) != len(imsi_list):
                raise ResourceConflictError("The eSIM account assignment changed during the transfer")
            return [ESIMMoveResult(imsi=esim.imsi, account_id=dst_account) for esim in esims]

        return self._write(
            operation, conflict_message="The eSIM transfer conflicts with existing database data"
        )

    def _require_user(self, user_id: int) -> None:
        if self.users.get(user_id) is None:
            raise ResourceNotFoundError("User", user_id)

    def _require_account(self, account_id: int) -> None:
        if self.accounts.get(account_id) is None:
            raise ResourceNotFoundError("Account", account_id)

    def _require_esims_in_account(
        self, account_id: int, imsis: list[str], *, for_update: bool = False
    ) -> None:
        esims = self.esims.get_by_imsis(imsis, for_update=for_update)
        esims_by_imsi = {esim.imsi: esim for esim in esims}
        for imsi in imsis:
            esim = esims_by_imsi.get(imsi)
            if esim is None:
                raise ResourceNotFoundError("eSIM with IMSI", imsi)
            if esim.accountid != account_id:
                raise ResourceConflictError(
                    f"eSIM with IMSI '{imsi}' does not belong to account '{account_id}'"
                )

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
