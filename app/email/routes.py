from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.email.manager import EmailWhitelistManager
from app.email.schemas import EmailWhitelistCreate, EmailWhitelistRead, EmailWhitelistUpdate

router = APIRouter(prefix="/email-whitelist", tags=["email-whitelist"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=EmailWhitelistRead, status_code=status.HTTP_201_CREATED)
def create_email_whitelist(
    data: EmailWhitelistCreate, db: DatabaseSession
) -> EmailWhitelistRead:
    return EmailWhitelistManager(db).create_email_whitelist(data)


@router.get("", response_model=list[EmailWhitelistRead])
def list_email_whitelist(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[EmailWhitelistRead]:
    return EmailWhitelistManager(db).list_email_whitelist(offset=offset, limit=limit)


@router.get("/{email_whitelist_id}", response_model=EmailWhitelistRead)
def get_email_whitelist(
    email_whitelist_id: Annotated[int, Path(gt=0)], db: DatabaseSession
) -> EmailWhitelistRead:
    return EmailWhitelistManager(db).get_email_whitelist(email_whitelist_id)


@router.patch("/{email_whitelist_id}", response_model=EmailWhitelistRead)
def update_email_whitelist(
    email_whitelist_id: Annotated[int, Path(gt=0)],
    data: EmailWhitelistUpdate,
    db: DatabaseSession,
) -> EmailWhitelistRead:
    return EmailWhitelistManager(db).update_email_whitelist(email_whitelist_id, data)


@router.delete("/{email_whitelist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_whitelist(
    email_whitelist_id: Annotated[int, Path(gt=0)], db: DatabaseSession
) -> Response:
    EmailWhitelistManager(db).delete_email_whitelist(email_whitelist_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
