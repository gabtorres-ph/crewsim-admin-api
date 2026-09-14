from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.sms.models import Sms
from app.sms.resource_access import SmsResourceAccess
from app.sms.schemas import SmsCreate, SmsUpdate


class SmsManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.sms = SmsResourceAccess(session)

    def create_sms(self, data: SmsCreate) -> Sms:
        return self._write(
            lambda: self.sms.create(data.model_dump()),
            conflict_message="The SMS record conflicts with existing database data",
        )

    def get_sms(self, sms_id: int) -> Sms:
        sms = self.sms.get(sms_id)
        if sms is None:
            raise ResourceNotFoundError("SMS", sms_id)
        return sms

    def list_sms(self, *, offset: int = 0, limit: int = 100) -> list[Sms]:
        return self.sms.list(offset=offset, limit=limit)

    def update_sms(self, sms_id: int, data: SmsUpdate) -> Sms:
        sms = self.get_sms(sms_id)
        return self._write(
            lambda: self.sms.update(sms, data.model_dump(exclude_unset=True)),
            conflict_message="The SMS update conflicts with existing database data",
        )

    def delete_sms(self, sms_id: int) -> None:
        sms = self.get_sms(sms_id)
        self._write(
            lambda: self.sms.delete(sms),
            conflict_message="The SMS record cannot be deleted while it is referenced by other data",
        )
