from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.network_status.models import NetworkStatus
from app.network_status.schemas import NetworkStatusSnapshot


class NetworkStatusResourceAccess(CRUDResourceAccess[NetworkStatus]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, NetworkStatus)

    def list_for_imsi(self, imsi: str) -> list[NetworkStatus]:
        statement = (
            select(NetworkStatus)
            .where(NetworkStatus.imsi == imsi)
            .order_by(NetworkStatus.start.desc(), NetworkStatus.id)
        )
        return list(self.session.scalars(statement))

    def replace_for_imsi(
        self, imsi: str, snapshots: list[NetworkStatusSnapshot]
    ) -> tuple[int, list[NetworkStatus]]:
        """Replace one IMSI's provider history without committing."""
        result = self.session.execute(delete(NetworkStatus).where(NetworkStatus.imsi == imsi))
        records = [self._from_snapshot(snapshot) for snapshot in snapshots]
        self.session.add_all(records)
        self.session.flush()
        return result.rowcount, records

    @staticmethod
    def _from_snapshot(snapshot: NetworkStatusSnapshot) -> NetworkStatus:
        values = snapshot.model_dump()
        values["simid"] = values.pop("sim_id")
        values["profiletype"] = values.pop("profile_type")
        values["statusmodification"] = values.pop("status_modification")
        return NetworkStatus(**values)
