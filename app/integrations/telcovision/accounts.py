from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError

from app.accounts.schemas import AccountSnapshot
from app.integrations.telcovision.client import TelcovisionError


class _ProviderAccount(BaseModel):
    # Undocumented provider fields are ignored; the fields we store are strictly typed.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: StrictInt = Field(gt=0)
    name: str
    balance: float = Field(allow_inf_nan=False)
    package_only: StrictBool = Field(alias="packageOnly")
    steering_list_id: StrictInt | None = Field(default=None, alias="steeringListId")


class _ProviderReseller(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: StrictInt = Field(gt=0)
    account: list[_ProviderAccount]


class _ProviderAccountList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reseller: list[_ProviderReseller]


class _ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    list_reseller_account: _ProviderAccountList = Field(alias="listResellerAccount")


def parse_account_snapshot(payload: dict[str, object]) -> list[AccountSnapshot]:
    """Flatten a full listResellerAccount response; any invalid element rejects the whole snapshot."""
    try:
        response = _ProviderResponse.model_validate(payload)
        snapshots = [
            AccountSnapshot(
                id=account.id,
                reseller_id=reseller.id,
                name=account.name,
                balance=account.balance,
                package_only=account.package_only,
                steering_list_id=account.steering_list_id,
            )
            for reseller in response.list_reseller_account.reseller
            for account in reseller.account
        ]
    except ValidationError:
        # Validation messages echo provider values, so only a category is propagated.
        raise TelcovisionError("invalid_response") from None

    if len({snapshot.id for snapshot in snapshots}) != len(snapshots):
        raise TelcovisionError("duplicate_account_id")
    return snapshots
