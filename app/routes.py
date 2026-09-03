from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.accounts import AccountCreate, AccountRead, AccountUpdate
from app.schemas.esims import ESIMCreate, ESIMRead, ESIMUpdate
from app.schemas.favorites import FavoriteCreate, FavoriteRead, FavoriteService
from app.schemas.users import UserCreate, UserRead, UserUpdate
from app.services.accounts import AccountService
from app.services.esims import ESIMService
from app.services.users import UserService

router = APIRouter(prefix="/accounts", tags=["accounts"])
router = APIRouter(prefix="/esims", tags=["esims"])
router = APIRouter(prefix="/users", tags=["users"])
router = APIRouter(prefix="/favorites", tags=["favorites"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate, db: DatabaseSession) -> AccountRead:
    return AccountService(db).create_account(data)


@router.get("", response_model=list[AccountRead])
def list_accounts(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[AccountRead]:
    return AccountService(db).list_accounts(offset=offset, limit=limit)


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> AccountRead:
    return AccountService(db).get_account(account_id)


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: Annotated[int, Path(gt=0)], data: AccountUpdate, db: DatabaseSession
) -> AccountRead:
    return AccountService(db).update_account(account_id, data)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    AccountService(db).delete_account(account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{account_id}/esims", response_model=list[ESIMRead])
def list_account_esims(
    account_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ESIMRead]:
    AccountService(db).get_account(account_id)
    return ESIMService(db).list_esims(account_id=account_id, offset=offset, limit=limit)


@router.post("", response_model=ESIMRead, status_code=status.HTTP_201_CREATED)
def create_esim(data: ESIMCreate, db: DatabaseSession) -> ESIMRead:
    return ESIMService(db).create_esim(data)


@router.get("", response_model=list[ESIMRead])
def list_esims(
    db: DatabaseSession,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ESIMRead]:
    return ESIMService(db).list_esims(user_id=user_id, offset=offset, limit=limit)


@router.get("/{esim_id}", response_model=ESIMRead)
def get_esim(esim_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> ESIMRead:
    return ESIMService(db).get_esim(esim_id)


@router.patch("/{esim_id}", response_model=ESIMRead)
def update_esim(
    esim_id: Annotated[int, Path(gt=0)], data: ESIMUpdate, db: DatabaseSession
) -> ESIMRead:
    return ESIMService(db).update_esim(esim_id, data)


@router.delete("/{esim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_esim(esim_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    ESIMService(db).delete_esim(esim_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, db: DatabaseSession) -> UserRead:
    return UserService(db).create_user(data)


@router.get("", response_model=list[UserRead])
def list_users(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[UserRead]:
    return UserService(db).list_users(offset=offset, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> UserRead:
    return UserService(db).get_user(user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: Annotated[int, Path(gt=0)], data: UserUpdate, db: DatabaseSession
) -> UserRead:
    return UserService(db).update_user(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    UserService(db).delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{user_id}/esims", response_model=list[ESIMRead])
def list_user_esims(
    user_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ESIMRead]:
    return ESIMService(db).list_esims(user_id=user_id, offset=offset, limit=limit)


@router.get("/{user_id}/favorites", response_model=list[FavoriteRead])
def list_user_favorites(
    user_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[FavoriteRead]:
    return FavoriteService(db).list_favorites(user_id=user_id, offset=offset, limit=limit)


@router.post("", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def create_favorite(data: FavoriteCreate, db: DatabaseSession) -> FavoriteRead:
    return FavoriteService(db).create_favorite(data)


@router.get("", response_model=list[FavoriteRead])
def list_favorites(
    db: DatabaseSession,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[FavoriteRead]:
    return FavoriteService(db).list_favorites(user_id=user_id, offset=offset, limit=limit)


@router.get("/{favorite_id}", response_model=FavoriteRead)
def get_favorite(favorite_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> FavoriteRead:
    return FavoriteService(db).get_favorite(favorite_id)


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(favorite_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    FavoriteService(db).delete_favorite(favorite_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
