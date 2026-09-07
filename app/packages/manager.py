from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.packages.models import Packages
from app.packages.resource_access import PackageResourceAccess
from app.packages.schemas import PackageCreate, PackageUpdate


class PackageManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.packages = PackageResourceAccess(session)

    def create_package(self, data: PackageCreate) -> Packages:
        return self._write(
            lambda: self.packages.create(data.model_dump()),
            conflict_message="The package conflicts with existing database data",
        )

    def get_package(self, package_id: int) -> Packages:
        package = self.packages.get(package_id)
        if package is None:
            raise ResourceNotFoundError("Package", package_id)
        return package

    def list_packages(self, *, offset: int = 0, limit: int = 100) -> list[Packages]:
        return self.packages.list(offset=offset, limit=limit)

    def update_package(self, package_id: int, data: PackageUpdate) -> Packages:
        package = self.get_package(package_id)
        return self._write(
            lambda: self.packages.update(package, data.model_dump(exclude_unset=True)),
            conflict_message="The package update conflicts with existing database data",
        )

    def delete_package(self, package_id: int) -> None:
        package = self.get_package(package_id)
        self._write(
            lambda: self.packages.delete(package),
            conflict_message="The package cannot be deleted while it is referenced by other data",
        )
