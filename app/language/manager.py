from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.language.models import Language
from app.language.resource_access import LanguageResourceAccess
from app.language.schemas import LanguageCreate, LanguageUpdate


class LanguageManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.languages = LanguageResourceAccess(session)

    def create_language(self, data: LanguageCreate) -> Language:
        return self._write(
            lambda: self.languages.create(data.model_dump()),
            conflict_message="The language conflicts with existing database data",
        )

    def get_language(self, language_id: int) -> Language:
        language = self.languages.get(language_id)
        if language is None:
            raise ResourceNotFoundError("Language", language_id)
        return language

    def list_languages(self, *, offset: int = 0, limit: int = 100) -> list[Language]:
        return self.languages.list(offset=offset, limit=limit)

    def update_language(self, language_id: int, data: LanguageUpdate) -> Language:
        language = self.get_language(language_id)
        return self._write(
            lambda: self.languages.update(language, data.model_dump(exclude_unset=True)),
            conflict_message="The language update conflicts with existing database data",
        )

    def delete_language(self, language_id: int) -> None:
        language = self.get_language(language_id)
        self._write(
            lambda: self.languages.delete(language),
            conflict_message="The language cannot be deleted while it is referenced by other data",
        )
