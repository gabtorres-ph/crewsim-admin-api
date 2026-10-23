from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.timezone.models import Timezone


class TimezoneResourceAccess(CRUDResourceAccess[Timezone]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Timezone)

    def get_by_name(self, name: str) -> Timezone | None:
        return self.session.scalar(select(Timezone).where(Timezone.name == name))
