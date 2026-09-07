from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.packages.manager import PackageManager
from app.packages.schemas import PackageCreate, PackageRead, PackageUpdate

router = APIRouter(prefix="/packages", tags=["packages"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=PackageRead, status_code=status.HTTP_201_CREATED)
def create_package(data: PackageCreate, db: DatabaseSession) -> PackageRead:
    return PackageManager(db).create_package(data)


@router.get("", response_model=list[PackageRead])
def list_packages(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[PackageRead]:
    return PackageManager(db).list_packages(offset=offset, limit=limit)


@router.get("/{package_id}", response_model=PackageRead)
def get_package(package_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> PackageRead:
    return PackageManager(db).get_package(package_id)


@router.patch("/{package_id}", response_model=PackageRead)
def update_package(
    package_id: Annotated[int, Path(gt=0)], data: PackageUpdate, db: DatabaseSession
) -> PackageRead:
    return PackageManager(db).update_package(package_id, data)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(package_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> Response:
    PackageManager(db).delete_package(package_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
