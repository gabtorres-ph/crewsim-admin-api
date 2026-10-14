import pytest
from sqlalchemy.orm import Session

from app.accounts.manager import AccountManager
from app.accounts.resource_access import AccountResourceAccess
from app.accounts.schemas import AccountCreate, AccountUpdate
from app.common.exceptions import ResourceConflictError, ResourceNotFoundError


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


def test_account_manager_reads_and_rejects_direct_writes(db_session: Session) -> None:
    accounts = AccountManager(db_session)
    account = AccountResourceAccess(db_session).create({"name": "Test account", "balance": 12.5})

    assert accounts.get_account(account.id) is account
    assert accounts.list_accounts() == [account]

    with pytest.raises(ResourceConflictError, match="Accounts are managed by Telcovision"):
        accounts.create_account(AccountCreate(name="Another account", balance=0))
    with pytest.raises(ResourceConflictError, match="Accounts are managed by Telcovision"):
        accounts.update_account(account.id, AccountUpdate(balance=20))
    with pytest.raises(ResourceConflictError, match="Accounts are managed by Telcovision"):
        accounts.delete_account(account.id)

    assert accounts.get_account(account.id) is account
    assert account.balance == 12.5
    with pytest.raises(ResourceNotFoundError, match="Account '999' was not found"):
        accounts.get_account(999)


@pytest.mark.asyncio
async def test_account_routes_read_and_reject_direct_writes(client, db_session: Session) -> None:
    seeded = AccountResourceAccess(db_session).create({"name": "Test account", "balance": 12.5})
    create_response = await client.post(
        "/api/accounts", json={"name": "Another account", "balance": 0}
    )
    assert create_response.status_code == 409
    assert create_response.json() == {"detail": "Accounts are managed by Telcovision"}
    account_id = seeded.id
    account = {
        "id": account_id,
        "name": "Test account",
        "balance": 12.5,
        "reseller_id": None,
        "package_only": None,
        "steering_list_id": None,
    }

    assert (await client.get(f"/api/accounts/{account_id}")).json() == account
    assert (await client.get("/api/accounts")).json() == [account]

    update_response = await client.patch(f"/api/accounts/{account_id}", json={"balance": 20})
    assert update_response.status_code == 409
    assert update_response.json() == {"detail": "Accounts are managed by Telcovision"}

    esim_response = await client.post(
        "/api/esims", json={"account_id": account_id, "imsi": "001010000000001"}
    )
    assert esim_response.status_code == 201
    esim = esim_response.json()

    assert (await client.delete(f"/api/accounts/{account_id}")).status_code == 409
    assert (await client.delete(f"/api/esims/{esim['id']}")).status_code == 204
    assert (await client.delete(f"/api/accounts/{account_id}")).status_code == 409
    assert (await client.get(f"/api/accounts/{account_id}")).json() == account
