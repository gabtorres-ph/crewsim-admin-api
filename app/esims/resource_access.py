import secrets
from string import ascii_lowercase, digits

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.esims.models import ESIM
from app.esims.schemas import ESIMSnapshot

ESIM_BATCH_SIZE = 500
TOKEN_ALPHABET = ascii_lowercase + digits
TOKEN_LENGTH = 7
SNAPSHOT_FIELDS = (
    "isesim",
    "balance",
    "use_account_for_charging",
    "smdpserver",
    "activationcode",
    "allow_data",
    "mobileplanid",
    "activationdate",
    "lastusagedate",
    "subscriber_status",
)


class ESIMResourceAccess(CRUDResourceAccess[ESIM]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ESIM)

    def upsert_snapshot(self, snapshots: list[ESIMSnapshot]) -> list[ESIM]:
        """Upsert unique snapshots by IMSI without committing; return rows in input order."""
        # TODO add a lock mechanism later to prevent multiple processes doing an update
        # on the same record; concurrent refreshes inserting the same new IMSI currently
        # hit uq_esims_imsi and surface as a misleading 409 (see try_acquire_refresh_lock
        # in AccountResourceAccess for the existing pattern)
        esims: list[ESIM] = []
        for start in range(0, len(snapshots), ESIM_BATCH_SIZE):
            batch = snapshots[start : start + ESIM_BATCH_SIZE]
            existing = {
                esim.imsi: esim
                for esim in self.session.scalars(
                    select(ESIM).where(ESIM.imsi.in_([item.imsi for item in batch]))
                )
            }
            for snapshot in batch:
                values = {field: getattr(snapshot, field) for field in SNAPSHOT_FIELDS}
                values["accountid"] = snapshot.account_id
                current = existing.get(snapshot.imsi)
                if current is None:
                    # TODO tokens are not checked for uniqueness and have no DB constraint;
                    # add one if eSIMs are ever looked up by token
                    current = ESIM(
                        imsi=snapshot.imsi,
                        userid=None,
                        token="".join(secrets.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH)),
                        **values,
                    )
                    self.session.add(current)
                else:
                    # TODO tz-aware provider datetimes never equal the naive values loaded
                    # from the DB, so every row is rewritten on every refresh; normalize
                    # datetimes before comparing (see TelcovisionListedSubscriber)
                    for field, value in values.items():
                        if getattr(current, field) != value:
                            setattr(current, field, value)
                esims.append(current)
        self.session.flush()
        return esims

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
