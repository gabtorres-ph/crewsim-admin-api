from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.language.manager import LanguageManager
from app.language.schemas import LanguageCreate, LanguageRead, LanguageUpdate

router = APIRouter(prefix="/languages", tags=["languages"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=LanguageRead, status_code=status.HTTP_201_CREATED)
def create_language(data: LanguageCreate, db: DatabaseSession) -> LanguageRead:
    return LanguageManager(db).create_language(data)


@router.get("", response_model=list[LanguageRead])
def list_languages(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[LanguageRead]:
    return LanguageManager(db).list_languages(offset=offset, limit=limit)


@router.get("/{language_id}", response_model=LanguageRead)
def get_language(language_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> LanguageRead:
    return LanguageManager(db).get_language(language_id)


@router.patch("/{language_id}", response_model=LanguageRead)
def update_language(
    language_id: Annotated[int, Path(gt=0)], data: LanguageUpdate, db: DatabaseSession
) -> LanguageRead:
    return LanguageManager(db).update_language(language_id, data)


@router.delete("/{language_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_language(language_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    LanguageManager(db).delete_language(language_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
