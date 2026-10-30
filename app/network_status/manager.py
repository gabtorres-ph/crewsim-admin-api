from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.common.exceptions import InvalidOperationError, ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.network_status.models import NetworkStatus
from app.network_status.resource_access import NetworkStatusResourceAccess
from app.network_status.schemas import (
    NetworkStatusCreate,
    NetworkStatusRead,
    NetworkStatusSnapshot,
    NetworkStatusSyncResult,
    NetworkStatusUpdate,
)


class NetworkStatusManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.network_statuses = NetworkStatusResourceAccess(session)

    def create_network_status(self, data: NetworkStatusCreate) -> NetworkStatus:
        values = self._database_values(data.model_dump())
        return self._write(
            lambda: self.network_statuses.create(values),
            conflict_message="The network status conflicts with existing database data",
        )

    def get_network_status(self, network_status_id: int) -> NetworkStatus:
        network_status = self.network_statuses.get(network_status_id)
        if network_status is None:
            raise ResourceNotFoundError("Network status", network_status_id)
        return network_status

    def list_network_statuses(
        self,
        *,
        imsi: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[NetworkStatus]:
        if imsi is not None:
            return self.network_statuses.list_for_imsi(imsi, offset=offset, limit=limit)
        return self.network_statuses.list(offset=offset, limit=limit)

    def update_network_status(
        self, network_status_id: int, data: NetworkStatusUpdate
    ) -> NetworkStatus:
        network_status = self.get_network_status(network_status_id)
        values = self._database_values(data.model_dump(exclude_unset=True))
        return self._write(
            lambda: self.network_statuses.update(network_status, values),
            conflict_message="The network status update conflicts with existing database data",
        )

    def delete_network_status(self, network_status_id: int) -> None:
        network_status = self.get_network_status(network_status_id)
        self._write(
            lambda: self.network_statuses.delete(network_status),
            conflict_message=(
                "The network status cannot be deleted while it is referenced by other data"
            ),
        )

    def sync_network_status(
        self,
        imsi: str,
        sim_id: int,
        fetch_snapshot: Callable[[], list[NetworkStatusSnapshot]],
    ) -> NetworkStatusSyncResult:
        """Fetch and replace one IMSI's provider history in one transaction."""

        def operation() -> NetworkStatusSyncResult:
            snapshots = fetch_snapshot()
            if any(snapshot.imsi != imsi for snapshot in snapshots):
                raise InvalidOperationError("The network status snapshot IMSI does not match")
            if any(snapshot.sim_id != sim_id for snapshot in snapshots):
                raise InvalidOperationError("The network status snapshot SIM ID does not match")
            deleted, records = self.network_statuses.replace_for_imsi(imsi, snapshots)
            return NetworkStatusSyncResult(
                fetched=len(snapshots),
                deleted=deleted,
                created=len(records),
                records=[NetworkStatusRead.model_validate(record) for record in records],
            )

        return self._write(
            operation,
            conflict_message="The network status sync conflicts with existing database data",
        )

    @staticmethod
    def _database_values(values: dict[str, Any]) -> dict[str, Any]:
        if "sim_id" in values:
            values["simid"] = values.pop("sim_id")
        if "profile_type" in values:
            values["profiletype"] = values.pop("profile_type")
        if "status_modification" in values:
            values["statusmodification"] = values.pop("status_modification")
        return values
