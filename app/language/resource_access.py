from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.language.models import Language


class LanguageResourceAccess(CRUDResourceAccess[Language]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Language)
