from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.favorites.manager import FavoriteManager
from app.favorites.schemas import FavoriteCreate, FavoriteRead

router = APIRouter(prefix="/favorites", tags=["favorites"])
user_router = APIRouter(prefix="/users", tags=["users"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def create_favorite(data: FavoriteCreate, db: DatabaseSession) -> FavoriteRead:
    return FavoriteManager(db).create_favorite(data)


@router.get("", response_model=list[FavoriteRead])
def list_favorites(
    db: DatabaseSession,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[FavoriteRead]:
    return FavoriteManager(db).list_favorites(user_id=user_id, offset=offset, limit=limit)


@router.get("/{favorite_id}", response_model=FavoriteRead)
def get_favorite(favorite_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> FavoriteRead:
    return FavoriteManager(db).get_favorite(favorite_id)


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(favorite_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    FavoriteManager(db).delete_favorite(favorite_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_router.get("/{user_id}/favorites", response_model=list[FavoriteRead])
def list_user_favorites(
    user_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[FavoriteRead]:
    return FavoriteManager(db).list_favorites(user_id=user_id, offset=offset, limit=limit)
