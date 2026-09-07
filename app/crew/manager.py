from typing import Any

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.crew.models import Crew
from app.crew.resource_access import CrewResourceAccess
from app.crew.schemas import CrewCreate, CrewUpdate


class CrewManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.crew = CrewResourceAccess(session)

    def create_crew(self, data: CrewCreate) -> Crew:
        values = self._database_values(data.model_dump())
        return self._write(
            lambda: self.crew.create(values),
            conflict_message="The crew record conflicts with existing database data",
        )

    def get_crew(self, crew_id: int) -> Crew:
        crew = self.crew.get(crew_id)
        if crew is None:
            raise ResourceNotFoundError("Crew", crew_id)
        return crew

    def list_crew(self, *, offset: int = 0, limit: int = 100) -> list[Crew]:
        return self.crew.list(offset=offset, limit=limit)

    def update_crew(self, crew_id: int, data: CrewUpdate) -> Crew:
        crew = self.get_crew(crew_id)
        values = self._database_values(data.model_dump(exclude_unset=True))
        return self._write(
            lambda: self.crew.update(crew, values),
            conflict_message="The crew update conflicts with existing database data",
        )

    def delete_crew(self, crew_id: int) -> None:
        crew = self.get_crew(crew_id)
        self._write(
            lambda: self.crew.delete(crew),
            conflict_message="The crew record cannot be deleted while it is referenced by other data",
        )

    @staticmethod
    def _database_values(values: dict[str, Any]) -> dict[str, Any]:
        if "user_id" in values:
            values["userid"] = values.pop("user_id")
        return values
