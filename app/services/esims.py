from sqlalchemy.orm import Session

from app.exceptions import ResourceNotFoundError
from app.models import ESIM
from app.repositories.esims import ESIMRepository
from app.repositories.users import UserRepository
from app.schemas.esims import ESIMCreate, ESIMUpdate
from app.services.base import TransactionalService


class ESIMService(TransactionalService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.esims = ESIMRepository(session)
        self.users = UserRepository(session)

    def create_esim(self, data: ESIMCreate) -> ESIM:
        self._require_user(data.user_id)
        values = {"userid": data.user_id, "imsi": data.imsi}
        return self._write(
            lambda: self.esims.create(values),
            conflict_message="The eSIM conflicts with existing database data",
        )

    def get_esim(self, esim_id: int) -> ESIM:
        esim = self.esims.get(esim_id)
        if esim is None:
            raise ResourceNotFoundError("eSIM", esim_id)
        return esim

    def list_esims(
        self, *, user_id: int | None = None, offset: int = 0, limit: int = 100
    ) -> list[ESIM]:
        if user_id is None:
            return self.esims.list(offset=offset, limit=limit)
        self._require_user(user_id)
        return self.esims.list_for_user(user_id, offset=offset, limit=limit)

    def update_esim(self, esim_id: int, data: ESIMUpdate) -> ESIM:
        esim = self.get_esim(esim_id)
        values = data.model_dump(exclude_unset=True)
        if "user_id" in values:
            self._require_user(values["user_id"])
            values["userid"] = values.pop("user_id")
        return self._write(
            lambda: self.esims.update(esim, values),
            conflict_message="The eSIM update conflicts with existing database data",
        )

    def delete_esim(self, esim_id: int) -> None:
        esim = self.get_esim(esim_id)
        self._write(
            lambda: self.esims.delete(esim),
            conflict_message="The eSIM cannot be deleted because it is referenced by other data",
        )

    def _require_user(self, user_id: int) -> None:
        if self.users.get(user_id) is None:
            raise ResourceNotFoundError("User", user_id)
