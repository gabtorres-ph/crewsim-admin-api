from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundError
from app.common.manager import TransactionalManager
from app.currencies.models import Currencies
from app.currencies.resource_access import CurrencyResourceAccess
from app.currencies.schemas import CurrencyCreate, CurrencyUpdate


class CurrencyManager(TransactionalManager):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.currencies = CurrencyResourceAccess(session)

    def create_currency(self, data: CurrencyCreate) -> Currencies:
        return self._write(
            lambda: self.currencies.create(data.model_dump()),
            conflict_message="The currency conflicts with existing database data",
        )

    def get_currency(self, currency_id: int) -> Currencies:
        currency = self.currencies.get(currency_id)
        if currency is None:
            raise ResourceNotFoundError("Currency", currency_id)
        return currency

    def list_currencies(self, *, offset: int = 0, limit: int = 100) -> list[Currencies]:
        return self.currencies.list(offset=offset, limit=limit)

    def update_currency(self, currency_id: int, data: CurrencyUpdate) -> Currencies:
        currency = self.get_currency(currency_id)
        return self._write(
            lambda: self.currencies.update(currency, data.model_dump(exclude_unset=True)),
            conflict_message="The currency update conflicts with existing database data",
        )

    def delete_currency(self, currency_id: int) -> None:
        currency = self.get_currency(currency_id)
        self._write(
            lambda: self.currencies.delete(currency),
            conflict_message="The currency cannot be deleted while it is referenced by other data",
        )
