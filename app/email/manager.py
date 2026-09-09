from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.email.models import EmailWhitelist
from app.email.resource_access import EmailWhitelistResourceAccess
from app.email.schemas import EmailWhitelistCreate, EmailWhitelistUpdate


class EmailWhitelistManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.email_whitelist = EmailWhitelistResourceAccess(session)

    def create_email_whitelist(self, data: EmailWhitelistCreate) -> EmailWhitelist:
        return self._write(
            lambda: self.email_whitelist.create(data.model_dump()),
            conflict_message="The email whitelist entry conflicts with existing database data",
        )

    def get_email_whitelist(self, email_whitelist_id: int) -> EmailWhitelist:
        email_whitelist = self.email_whitelist.get(email_whitelist_id)
        if email_whitelist is None:
            raise ResourceNotFoundError("EmailWhitelist", email_whitelist_id)
        return email_whitelist

    def list_email_whitelist(self, *, offset: int = 0, limit: int = 100) -> list[EmailWhitelist]:
        return self.email_whitelist.list(offset=offset, limit=limit)

    def update_email_whitelist(
        self, email_whitelist_id: int, data: EmailWhitelistUpdate
    ) -> EmailWhitelist:
        email_whitelist = self.get_email_whitelist(email_whitelist_id)
        return self._write(
            lambda: self.email_whitelist.update(
                email_whitelist, data.model_dump(exclude_unset=True)
            ),
            conflict_message="The email whitelist entry update conflicts with existing database data",
        )

    def delete_email_whitelist(self, email_whitelist_id: int) -> None:
        email_whitelist = self.get_email_whitelist(email_whitelist_id)
        self._write(
            lambda: self.email_whitelist.delete(email_whitelist),
            conflict_message=(
                "The email whitelist entry cannot be deleted while it is referenced by other data"
            ),
        )
