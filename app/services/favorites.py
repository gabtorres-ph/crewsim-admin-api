from sqlalchemy.orm import Session

from app.exceptions import ResourceNotFoundError
from app.models import Favorite
from app.repositories.favorites import FavoriteRepository
from app.repositories.users import UserRepository
from app.schemas.favorites import FavoriteCreate
from app.services.base import TransactionalService


class FavoriteService(TransactionalService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.favorites = FavoriteRepository(session)
        self.users = UserRepository(session)

    def create_favorite(self, data: FavoriteCreate) -> Favorite:
        self._require_user(data.user_id)
        values = data.model_dump()
        values["userid"] = values.pop("user_id")
        return self._write(
            lambda: self.favorites.create(values),
            conflict_message="The favorite conflicts with existing database data",
        )

    def get_favorite(self, favorite_id: int) -> Favorite:
        favorite = self.favorites.get(favorite_id)
        if favorite is None:
            raise ResourceNotFoundError("Favorite", favorite_id)
        return favorite

    def list_favorites(
        self, *, user_id: int | None = None, offset: int = 0, limit: int = 100
    ) -> list[Favorite]:
        if user_id is None:
            return self.favorites.list(offset=offset, limit=limit)
        self._require_user(user_id)
        return self.favorites.list_for_user(user_id, offset=offset, limit=limit)

    def delete_favorite(self, favorite_id: int) -> None:
        favorite = self.get_favorite(favorite_id)
        self._write(
            lambda: self.favorites.delete(favorite),
            conflict_message="The favorite cannot be deleted because it is referenced by other data",
        )

    def _require_user(self, user_id: int) -> None:
        if self.users.get(user_id) is None:
            raise ResourceNotFoundError("User", user_id)
