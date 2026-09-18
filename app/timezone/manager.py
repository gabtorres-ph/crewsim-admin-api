from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.timezone.models import Timezone
from app.timezone.resource_access import TimezoneResourceAccess
from app.timezone.schemas import TimezoneCreate, TimezoneUpdate


class TimezoneManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.timezones = TimezoneResourceAccess(session)

    def create_timezone(self, data: TimezoneCreate) -> Timezone:
        return self._write(
            lambda: self.timezones.create(data.model_dump()),
            conflict_message="The timezone conflicts with existing database data",
        )

    def get_timezone(self, name: str) -> Timezone:
        timezone = self.timezones.get(name)
        if timezone is None:
            raise ResourceNotFoundError("Timezone", name)
        return timezone

    def list_timezones(self, *, offset: int = 0, limit: int = 100) -> list[Timezone]:
        return self.timezones.list(offset=offset, limit=limit)

    def update_timezone(self, name: str, data: TimezoneUpdate) -> Timezone:
        timezone = self.get_timezone(name)
        return self._write(
            lambda: self.timezones.update(timezone, data.model_dump(exclude_unset=True)),
            conflict_message="The timezone update conflicts with existing database data",
        )

    def delete_timezone(self, name: str) -> None:
        timezone = self.get_timezone(name)
        self._write(
            lambda: self.timezones.delete(timezone),
            conflict_message="The timezone cannot be deleted while it is referenced by other data",
        )
