from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.packages.models import Packages


class PackageResourceAccess(CRUDResourceAccess[Packages]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Packages)
