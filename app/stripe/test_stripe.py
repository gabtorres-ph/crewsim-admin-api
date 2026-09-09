from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.common.exceptions import ResourceConflictError, ResourceNotFoundError
from app.stripe.manager import StripeManager
from app.stripe.models import StripeNotification
from app.stripe.resource_access import StripeNotificationResourceAccess
from app.stripe.schemas import StripeNotificationCreate, StripeNotificationUpdate


def stripe_notification_values(**overrides):
    values = {
        "eventid": "evt_123",
        "invoiceid": "in_123",
        "customerid": "cus_123",
        "taxrate": Decimal("12.50"),
        "taxcountry": "PH",
        "amount_net": Decimal("100.00"),
        "amount_tax": Decimal("12.50"),
        "amount_gross": Decimal("112.50"),
        "currency": "php",
        "sku": "crew-data-1gb",
        "userid": 1001,
        "state": "paid",
        "createdate": datetime.fromisoformat("2026-09-07T08:30:00"),
        "imsi": "515020000000001",
        "amount_credit": Decimal("100.00"),
    }
    values.update(overrides)
    return values


def stripe_notification_json(**overrides):
    values = stripe_notification_values(**overrides)
    values["createdate"] = values["createdate"].isoformat()
    for field in (
        "taxrate",
        "amount_net",
        "amount_tax",
        "amount_gross",
        "amount_credit",
    ):
        if values[field] is not None:
            values[field] = str(values[field])
    return values


def test_stripe_notification_resource_access_crud_and_pagination(
    db_session: Session,
) -> None:
    notifications = StripeNotificationResourceAccess(db_session)
    first = notifications.create(stripe_notification_values())
    second = notifications.create(stripe_notification_values(eventid="evt_456"))
    third = notifications.create(stripe_notification_values(eventid="evt_789"))

    assert notifications.get(first.id) is first
    assert notifications.list(offset=1, limit=1) == [second]
    assert notifications.list(offset=2, limit=10) == [third]

    notifications.update(first, {"state": "credited", "amount_credit": Decimal("112.50")})
    assert first.state == "credited"
    assert first.amount_credit == Decimal("112.50")

    notifications.delete(third)
    assert notifications.get(third.id) is None


def test_stripe_manager_crud_nullable_update_and_commits(db_session: Session) -> None:
    manager = StripeManager(db_session)
    notification = manager.create_notification(
        StripeNotificationCreate(**stripe_notification_values())
    )

    with Session(db_session.get_bind()) as other_session:
        assert other_session.get(StripeNotification, notification.id) is not None

    updated = manager.update_notification(
        notification.id,
        StripeNotificationUpdate(
            taxrate=None,
            taxcountry=None,
            state=None,
            imsi=None,
            amount_credit=None,
        ),
    )
    assert updated.eventid == "evt_123"
    assert updated.taxrate is None
    assert updated.taxcountry is None
    assert updated.state is None
    assert updated.imsi is None
    assert updated.amount_credit is None

    manager.delete_notification(notification.id)
    with pytest.raises(
        ResourceNotFoundError,
        match=f"Stripe notification '{notification.id}' was not found",
    ):
        manager.get_notification(notification.id)


def test_stripe_manager_rolls_back_database_conflicts(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = StripeManager(db_session)

    def create_invalid_notification(values) -> StripeNotification:
        notification = StripeNotification()
        db_session.add(notification)
        db_session.flush()
        return notification

    monkeypatch.setattr(manager.notifications, "create", create_invalid_notification)

    with pytest.raises(ResourceConflictError, match="stripe notification conflicts"):
        manager.create_notification(StripeNotificationCreate(**stripe_notification_values()))

    assert manager.list_notifications() == []


def test_stripe_notification_schemas_validate_payloads() -> None:
    with pytest.raises(ValidationError):
        StripeNotificationCreate(**stripe_notification_values(eventid="  "))

    with pytest.raises(ValidationError):
        StripeNotificationCreate(**stripe_notification_values(eventid="x" * 101))

    with pytest.raises(ValidationError):
        StripeNotificationCreate(
            **stripe_notification_values(amount_net=Decimal("123456789.12"))
        )

    with pytest.raises(ValidationError):
        StripeNotificationUpdate(eventid=None)

    nullable_update = StripeNotificationUpdate(
        taxrate=None,
        taxcountry=None,
        state=None,
        imsi=None,
        amount_credit=None,
    )
    assert nullable_update.model_dump(exclude_unset=True) == {
        "taxrate": None,
        "taxcountry": None,
        "state": None,
        "imsi": None,
        "amount_credit": None,
    }


def test_stripe_notification_model_preserves_database_indexes() -> None:
    table = StripeNotification.__table__

    assert {index.name for index in table.indexes} == {
        "idx_eventid",
        "idx_invoiceid",
        "idx_customerid",
        "idx_userid",
        "idx_createdate",
    }
