from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.models import User
from app.repositories.users import UserRepository
from app.schemas.users import UserCreate, UserUpdate


class UserService(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.users = UserRepository(session)

    def create_user(self, data: UserCreate) -> User:
        if data.referredby is not None:
            self._require_user(data.referredby)
        return self._write(
            lambda: self.users.create(data.model_dump()),
            conflict_message="The user conflicts with existing database data",
        )

    def get_user(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise ResourceNotFoundError("User", user_id)
        return user

    def list_users(self, *, offset: int = 0, limit: int = 100) -> list[User]:
        return self.users.list(offset=offset, limit=limit)

    def update_user(self, user_id: int, data: UserUpdate) -> User:
        user = self.get_user(user_id)
        values = data.model_dump(exclude_unset=True)
        if "referredby" in values:
            self._require_user(values["referredby"])
        return self._write(
            lambda: self.users.update(user, values),
            conflict_message="The user update conflicts with existing database data",
        )

    def delete_user(self, user_id: int) -> None:
        user = self.get_user(user_id)
        self._write(
            lambda: self.users.delete(user),
            conflict_message="The user cannot be deleted while it is referenced by other data",
        )

    def _require_user(self, user_id: int) -> None:
        if self.users.get(user_id) is None:
            raise ResourceNotFoundError("User", user_id)
