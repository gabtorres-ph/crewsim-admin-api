from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.crew.models import Crew


class CrewResourceAccess(CRUDResourceAccess[Crew]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Crew)
