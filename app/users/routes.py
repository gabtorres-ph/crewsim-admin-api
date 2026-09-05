from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.favorites import FavoriteRead
from app.services.favorites import FavoriteService
from app.users.manager import UserManager
from app.users.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: DatabaseSession) -> UserRead:
    return UserManager(db).create_user(data)


@router.get("", response_model=list[UserRead])
def list_users(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[UserRead]:
    return UserManager(db).list_users(offset=offset, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> UserRead:
    return UserManager(db).get_user(user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: Annotated[int, Path(gt=0)], data: UserUpdate, db: DatabaseSession
) -> UserRead:
    return UserManager(db).update_user(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    UserManager(db).delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{user_id}/favorites", response_model=list[FavoriteRead])
def list_user_favorites(
    user_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[FavoriteRead]:
    return FavoriteService(db).list_favorites(user_id=user_id, offset=offset, limit=limit)
