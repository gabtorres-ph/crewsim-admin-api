import pytest
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.packages.manager import PackageManager
from app.packages.models import Packages
from app.packages.resource_access import PackageResourceAccess
from app.packages.schemas import PackageCreate, PackageUpdate


def test_package_resource_access_crud_and_pagination(db_session: Session) -> None:
    packages = PackageResourceAccess(db_session)
    first = packages.create({"sku": "pkg-1", "name": "First"})
    second = packages.create({"sku": "pkg-2", "name": "Second"})
    third = packages.create({"sku": "pkg-3", "name": "Third"})

    assert packages.get(first.id) is first
    assert packages.list(offset=1, limit=1) == [second]
    assert packages.list(offset=2, limit=10) == [third]

    packages.update(first, {"price": 12.5, "points": 10})
    assert first.price == 12.5
    assert first.points == 10

    packages.delete(third)
    assert packages.get(third.id) is None


def test_package_manager_crud_nullable_update_and_commits(db_session: Session) -> None:
    manager = PackageManager(db_session)
    package = manager.create_package(
        PackageCreate(
            sku="pkg-1",
            name="Starter",
            price=12.5,
            points=10,
            sparkid=20,
            reward=3,
        )
    )

    with Session(db_session.get_bind()) as other_session:
        assert other_session.get(Packages, package.id) is not None

    updated = manager.update_package(
        package.id,
        PackageUpdate(name=None, price=None, points=None, sparkid=None, reward=None),
    )
    assert updated.sku == "pkg-1"
    assert updated.name is None
    assert updated.price is None
    assert updated.points is None
    assert updated.sparkid is None
    assert updated.reward is None

    manager.delete_package(package.id)
    with pytest.raises(ResourceNotFoundError, match=f"Package '{package.id}' was not found"):
        manager.get_package(package.id)


def test_package_manager_rolls_back_database_conflicts(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = PackageManager(db_session)

    def create_invalid_package(values) -> Packages:
        package = Packages(sku=None)
        db_session.add(package)
        db_session.flush()
        return package

    monkeypatch.setattr(manager.packages, "create", create_invalid_package)

    with pytest.raises(ResourceConflictError, match="package conflicts"):
        manager.create_package(PackageCreate(sku="pkg-1"))

    assert manager.list_packages() == []


@pytest.mark.asyncio
async def test_package_crud_pagination_and_response_shape(client) -> None:
    first_response = await client.post(
        "/api/packages",
        json={
            "sku": "pkg-1",
            "name": "Starter",
            "price": 12.5,
            "points": 10,
            "sparkid": 20,
            "reward": 3,
        },
    )
    assert first_response.status_code == 201
    first = first_response.json()
    assert first == {
        "id": first["id"],
        "sku": "pkg-1",
        "name": "Starter",
        "price": 12.5,
        "points": 10,
        "sparkid": 20,
        "reward": 3,
    }

    second_response = await client.post("/api/packages", json={"sku": "pkg-2"})
    assert second_response.status_code == 201
    second = second_response.json()
    assert second == {
        "id": second["id"],
        "sku": "pkg-2",
        "name": None,
        "price": None,
        "points": None,
        "sparkid": None,
        "reward": None,
    }

    assert (await client.get(f"/api/packages/{first['id']}")).json() == first
    assert (await client.get("/api/packages?offset=1&limit=1")).json() == [second]

    update_response = await client.patch(
        f"/api/packages/{first['id']}",
        json={"name": None, "price": None, "points": 25},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] is None
    assert updated["price"] is None
    assert updated["points"] == 25
    assert updated["sku"] == "pkg-1"

    assert (await client.delete(f"/api/packages/{first['id']}")).status_code == 204
    assert (await client.get(f"/api/packages/{first['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_package_routes_validate_payloads_and_parameters(client) -> None:
    assert (await client.post("/api/packages", json={})).status_code == 422
    assert (await client.post("/api/packages", json={"sku": "  "})).status_code == 422

    package = (await client.post("/api/packages", json={"sku": "pkg-1"})).json()
    assert (
        await client.patch(f"/api/packages/{package['id']}", json={"sku": None})
    ).status_code == 422

    assert (await client.get("/api/packages/0")).status_code == 422
    assert (await client.get("/api/packages?offset=-1")).status_code == 422
    assert (await client.get("/api/packages?limit=0")).status_code == 422
    assert (await client.get("/api/packages?limit=101")).status_code == 422
