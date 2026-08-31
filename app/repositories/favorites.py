from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Favorite
from app.repositories.base import CRUDRepository


class FavoriteRepository(CRUDRepository[Favorite]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Favorite)

    def list_for_user(
        self, user_id: int, *, offset: int = 0, limit: int = 100
    ) -> list[Favorite]:
        statement = (
            select(Favorite)
            .where(Favorite.userid == user_id)
            .order_by(Favorite.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))
