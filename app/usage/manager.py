from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.usage.models import Usage
from app.usage.resource_access import UsageResourceAccess
from app.usage.schemas import UsageCreate, UsageUpdate


class UsageManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.usage = UsageResourceAccess(session)

    def create_usage(self, data: UsageCreate) -> Usage:
        return self._write(
            lambda: self.usage.create(data.model_dump()),
            conflict_message="The usage record conflicts with existing database data",
        )

    def get_usage(self, usage_id: int) -> Usage:
        usage = self.usage.get(usage_id)
        if usage is None:
            raise ResourceNotFoundError("Usage", usage_id)
        return usage

    def list_usage(self, *, offset: int = 0, limit: int = 100) -> list[Usage]:
        return self.usage.list(offset=offset, limit=limit)

    def update_usage(self, usage_id: int, data: UsageUpdate) -> Usage:
        usage = self.get_usage(usage_id)
        return self._write(
            lambda: self.usage.update(usage, data.model_dump(exclude_unset=True)),
            conflict_message="The usage update conflicts with existing database data",
        )

    def delete_usage(self, usage_id: int) -> None:
        usage = self.get_usage(usage_id)
        self._write(
            lambda: self.usage.delete(usage),
            conflict_message="The usage record cannot be deleted while it is referenced by other data",
        )
