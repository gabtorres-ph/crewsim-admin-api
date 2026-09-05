import pytest
from sqlalchemy.orm import Session

from app.accounts.manager import AccountManager
from app.accounts.resource_access import AccountResourceAccess
from app.accounts.schemas import AccountCreate, AccountUpdate
from app.common.exceptions import ResourceNotFoundError


def test_account_resource_access_crud(db_session: Session) -> None:
    accounts = AccountResourceAccess(db_session)
    first = accounts.create({"name": "First", "balance": 10})
    second = accounts.create({"name": "Second", "balance": 20})

    assert accounts.get(first.id) is first
    assert accounts.list(offset=1, limit=1) == [second]

    accounts.update(first, {"balance": 15})
    assert first.balance == 15

    accounts.delete(second)
    assert accounts.get(second.id) is None


def test_account_manager_crud(db_session: Session) -> None:
    accounts = AccountManager(db_session)
    account = accounts.create_account(AccountCreate(name="Test account", balance=12.5))

    assert accounts.get_account(account.id) is account
    assert accounts.list_accounts() == [account]

    updated = accounts.update_account(account.id, AccountUpdate(balance=20))
    assert updated.balance == 20

    accounts.delete_account(account.id)
    with pytest.raises(ResourceNotFoundError, match=f"Account '{account.id}' was not found"):
        accounts.get_account(account.id)


@pytest.mark.asyncio
async def test_account_crud_and_reference_conflict(client) -> None:
    create_response = await client.post(
        "/api/accounts", json={"name": "Test account", "balance": 12.5}
    )
    assert create_response.status_code == 201
    account = create_response.json()
    account_id = account["id"]

    assert (await client.get(f"/api/accounts/{account_id}")).json() == account
    assert (await client.get("/api/accounts")).json() == [account]

    update_response = await client.patch(f"/api/accounts/{account_id}", json={"balance": 20})
    assert update_response.status_code == 200
    assert update_response.json()["balance"] == 20

    esim_response = await client.post(
        "/api/esims", json={"account_id": account_id, "imsi": "001010000000001"}
    )
    assert esim_response.status_code == 201
    esim = esim_response.json()

    assert (await client.delete(f"/api/accounts/{account_id}")).status_code == 409
    assert (await client.delete(f"/api/esims/{esim['id']}")).status_code == 204
    assert (await client.delete(f"/api/accounts/{account_id}")).status_code == 204
    assert (await client.get(f"/api/accounts/{account_id}")).status_code == 404
