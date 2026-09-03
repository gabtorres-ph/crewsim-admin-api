from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError

ResultT = TypeVar("ResultT")


class TransactionalManager:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _write(self, operation: Callable[[], ResultT], *, conflict_message: str) -> ResultT:
        try:
            result = operation()
            self.session.commit()
            return result
        except IntegrityError as error:
            self.session.rollback()
            raise ResourceConflictError(conflict_message) from error
        except Exception:
            self.session.rollback()
            raise
