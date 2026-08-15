from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.base import CRUDRepository


class UserRepository(CRUDRepository[User]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))
