import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.esims.manager import ESIMManager
from app.esims.schemas import ESIMRefreshResult, ESIMSnapshot
from app.integrations.redis.outbound_logging import OutboundExchange
from app.integrations.telcovision.client import TelcovisionError, open_telcovision_client
from app.integrations.telcovision.schemas import TelcovisionSubscribersResponse

logger = logging.getLogger(__name__)


def parse_subscriber_snapshot(payload: dict[str, object]) -> list[ESIMSnapshot]:
    """Flatten a complete listSubscriber response; reject invalid or duplicate IMSIs."""
    try:
        response = TelcovisionSubscribersResponse.model_validate(payload)
        subscriber_list = response.list_subscriber
        # TODO implement listSubscriber pagination; until then any account with more than one
        # page of subscribers always fails with incomplete_response (502)
        if subscriber_list.has_more or subscriber_list.nb_found != len(
            subscriber_list.subscriber_list
        ):
            raise TelcovisionError("incomplete_response")

        snapshots: list[ESIMSnapshot] = []
        for subscriber in subscriber_list.subscriber_list:
            latest_status = max(subscriber.status, key=lambda status: status.id, default=None)
            # TODO reject subscribers whose account_id differs from the requested account
            # (e.g. TelcovisionError("account_mismatch")); otherwise they are stored under
            # another account and the IMSI upsert can reassign an existing eSIM's accountid
            for item in subscriber.imsi_list:
                snapshots.append(
                    ESIMSnapshot(
                        imsi=str(item.imsi),
                        account_id=subscriber.account_id,
                        isesim=subscriber.sim.esim,
                        balance=subscriber.balance,
                        use_account_for_charging=subscriber.use_account_for_charging,
                        smdpserver=subscriber.sim.smdp_server,
                        activationcode=subscriber.sim.activation_code,
                        allow_data=subscriber.allowed_data,
                        mobileplanid=subscriber.mobile_plan_id,
                        activationdate=subscriber.activation_date,
                        lastusagedate=subscriber.last_usage_date,
                        subscriber_status=(
                            latest_status.status if latest_status is not None else None
                        ),
                    )
                )
    except ValidationError:
        # Validation messages echo provider values, so only a category is propagated.
        raise TelcovisionError("invalid_response") from None

    if len({snapshot.imsi for snapshot in snapshots}) != len(snapshots):
        raise TelcovisionError("duplicate_imsi")
    return snapshots


def refresh_telcovision_subscribers(
    session: Session,
    settings: Settings,
    *,
    account_id: int,
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> list[ESIMRefreshResult]:
    """Fetch a live Telcovision subscriber snapshot and insert or update eSIMs by IMSI."""
    with open_telcovision_client(
        settings, request_id=request_id, outbound_exchanges=outbound_exchanges
    ) as client:
        logger.info(
            "Telcovision subscribers refresh started request_id=%s account_id=%s",
            request_id,
            account_id,
        )

        def load_snapshot() -> list[ESIMSnapshot]:
            snapshots = parse_subscriber_snapshot(
                client.list_subscribers(account_id, validate=parse_subscriber_snapshot)
            )
            logger.info(
                "Telcovision subscribers snapshot parsed request_id=%s account_id=%s esims=%d",
                request_id,
                account_id,
                len(snapshots),
            )
            return snapshots

        return ESIMManager(session).refresh_esims(account_id, load_snapshot)
