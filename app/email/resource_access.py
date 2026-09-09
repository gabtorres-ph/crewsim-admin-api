from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.resource_access import CRUDResourceAccess
from app.email.models import EmailWhitelist


class EmailWhitelistResourceAccess(CRUDResourceAccess[EmailWhitelist]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, EmailWhitelist)

    def get_by_email(self, email: str) -> EmailWhitelist | None:
        statement = select(EmailWhitelist).where(EmailWhitelist.email == email)
        return self.session.scalars(statement).first()
