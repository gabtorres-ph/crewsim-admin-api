import pytest
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.currencies.manager import CurrencyManager
from app.currencies.models import Currencies
from app.currencies.resource_access import CurrencyResourceAccess
from app.currencies.schemas import CurrencyCreate, CurrencyUpdate

USD = {
    "code": "USD",
    "name": "US Dollar",
    "symbol": "$",
    "symbol_native": "$",
    "decimal_digits": 2,
    "rounding": 0,
    "iso_numeric": 840,
}
AUD = {**USD, "code": "AUD", "name": "Australian Dollar", "iso_numeric": 36}


def test_resource_access_crud_and_pagination(db_session: Session) -> None:
    access = CurrencyResourceAccess(db_session)
    first = access.create(USD)
    second = access.create(AUD)
    assert access.get(first.id) is first
    assert access.list(offset=1, limit=1) == [second]

    access.update(first, {"name": "United States Dollar"})
    assert first.name == "United States Dollar"
    access.delete(second)
    assert access.get(second.id) is None


def test_manager_commits_updates_and_deletes(db_session: Session) -> None:
    manager = CurrencyManager(db_session)
    currency = manager.create_currency(CurrencyCreate(**USD))
    with Session(db_session.get_bind()) as other_session:
        assert other_session.get(Currencies, currency.id) is not None

    updated = manager.update_currency(currency.id, CurrencyUpdate(name="US dollar"))
    assert updated.name == "US dollar"
    assert updated.iso_numeric == 840

    manager.delete_currency(currency.id)
    with pytest.raises(ResourceNotFoundError, match=f"Currency '{currency.id}' was not found"):
        manager.get_currency(currency.id)


def test_manager_rolls_back_unique_code_and_numeric_conflicts(db_session: Session) -> None:
    manager = CurrencyManager(db_session)
    first = manager.create_currency(CurrencyCreate(**USD))
    with pytest.raises(ResourceConflictError, match="currency conflicts"):
        manager.create_currency(CurrencyCreate(**{**AUD, "code": "USD"}))
    with pytest.raises(ResourceConflictError, match="currency conflicts"):
        manager.create_currency(CurrencyCreate(**{**AUD, "iso_numeric": 840}))
    assert manager.list_currencies() == [first]

    second = manager.create_currency(CurrencyCreate(**AUD))
    with pytest.raises(ResourceConflictError, match="currency update conflicts"):
        manager.update_currency(second.id, CurrencyUpdate(iso_numeric=840))
    assert manager.get_currency(second.id).iso_numeric == 36


@pytest.mark.asyncio
async def test_currency_routes_crud_and_pagination(client) -> None:
    response = await client.post("/api/currencies", json=USD)
    assert response.status_code == 201
    first = response.json()
    assert first == {"id": first["id"], **USD}

    response = await client.post("/api/currencies", json=AUD)
    assert response.status_code == 201
    second = response.json()
    assert second == {"id": second["id"], **AUD}
    assert (await client.get(f"/api/currencies/{first['id']}")).json() == first
    assert (await client.get("/api/currencies?offset=1&limit=1")).json() == [second]

    response = await client.patch(f"/api/currencies/{first['id']}", json={"name": "US dollar"})
    assert response.status_code == 200
    assert response.json() == {**first, "name": "US dollar"}

    assert (await client.delete(f"/api/currencies/{first['id']}")).status_code == 204
    assert (await client.get(f"/api/currencies/{first['id']}")).status_code == 404
    assert (await client.patch(f"/api/currencies/{first['id']}", json={})).status_code == 404
    assert (await client.delete(f"/api/currencies/{first['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_currency_routes_validate_payloads_and_parameters(client) -> None:
    invalid_creates = (
        {},
        {**USD, "code": "US"},
        {**USD, "name": "  "},
        {**USD, "symbol": ""},
        {**USD, "symbol_native": "x" * 11},
        {**USD, "decimal_digits": -1},
        {**USD, "rounding": -1},
        {**USD, "iso_numeric": 0},
        {**USD, "iso_numeric": 1000},
    )
    for payload in invalid_creates:
        assert (await client.post("/api/currencies", json=payload)).status_code == 422

    currency = (await client.post("/api/currencies", json=USD)).json()
    for field in USD:
        assert (
            await client.patch(f"/api/currencies/{currency['id']}", json={field: None})
        ).status_code == 422

    assert (await client.post("/api/currencies", json={**AUD, "code": "USD"})).status_code == 409
    assert (await client.post("/api/currencies", json={**AUD, "iso_numeric": 840})).status_code == 409
    assert (await client.get("/api/currencies/0")).status_code == 422
    assert (await client.get("/api/currencies?offset=-1")).status_code == 422
    assert (await client.get("/api/currencies?limit=0")).status_code == 422
    assert (await client.get("/api/currencies?limit=101")).status_code == 422
