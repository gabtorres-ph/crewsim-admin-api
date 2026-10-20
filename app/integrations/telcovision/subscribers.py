import logging
from functools import partial

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings
from app.esims.manager import ESIMManager
from app.esims.schemas import ESIMMoveResult, ESIMRefreshResult, ESIMSingleSnapshot, ESIMSnapshot
from app.integrations.redis.outbound_logging import OutboundExchange
from app.integrations.telcovision.client import TelcovisionError, open_telcovision_client
from app.integrations.telcovision.schemas import (
    TelcovisionListedSubscriber,
    TelcovisionSingleSubscriberResponse,
    TelcovisionSubscriberMoveResponse,
    TelcovisionSubscribersResponse,
)

logger = logging.getLogger(__name__)


class TelcovisionSubscriberMoveError(TelcovisionError):
    def __init__(
        self,
        error: TelcovisionError,
        *,
        moved_imsis: list[str],
        failed_imsi: str,
        not_attempted_imsis: list[str],
    ) -> None:
        super().__init__(error.category, error.provider_code)
        self.moved_imsis = moved_imsis
        self.failed_imsi = failed_imsi
        self.not_attempted_imsis = not_attempted_imsis


def parse_subscriber_move(payload: dict[str, object]) -> int:
    """Return the provider's moved count, accepting only a singleton IMSI move."""
    try:
        moved_count = TelcovisionSubscriberMoveResponse.model_validate(payload).moved_count
    except ValidationError:
        raise TelcovisionError("invalid_response") from None
    if moved_count != 1:
        raise TelcovisionError("unexpected_moved_count")
    return moved_count


def _subscriber_snapshot(subscriber: TelcovisionListedSubscriber, *, imsi: str) -> ESIMSnapshot:
    latest_status = max(subscriber.status, key=lambda status: status.id, default=None)
    return ESIMSnapshot(
        imsi=imsi,
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
        subscriber_status=latest_status.status if latest_status is not None else None,
    )


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
            # TODO reject subscribers whose account_id differs from the requested account
            # (e.g. TelcovisionError("account_mismatch")); otherwise they are stored under
            # another account and the IMSI upsert can reassign an existing eSIM's accountid
            for item in subscriber.imsi_list:
                snapshots.append(_subscriber_snapshot(subscriber, imsi=str(item.imsi)))
    except ValidationError:
        # Validation messages echo provider values, so only a category is propagated.
        raise TelcovisionError("invalid_response") from None

    if len({snapshot.imsi for snapshot in snapshots}) != len(snapshots):
        raise TelcovisionError("duplicate_imsi")
    return snapshots


def parse_single_subscriber(payload: dict[str, object], *, imsi: str) -> ESIMSingleSnapshot:
    """Map only supplied getSingleSubscriber fields for the requested IMSI."""
    try:
        response = TelcovisionSingleSubscriberResponse.model_validate(payload)
        subscriber = response.get_single_subscriber
        if "imsi_list" in subscriber.model_fields_set:
            matching_imsis = [
                item for item in subscriber.imsi_list or [] if str(item.imsi) == imsi
            ]
            if len(matching_imsis) != 1:
                raise TelcovisionError("invalid_response")

        values: dict[str, object] = {"imsi": imsi}
        field_mappings = {
            "account_id": "account_id",
            "balance": "balance",
            "use_account_for_charging": "use_account_for_charging",
            "allowed_data": "allow_data",
            "mobile_plan_id": "mobileplanid",
            "activation_date": "activationdate",
            "last_usage_date": "lastusagedate",
        }
        for source, target in field_mappings.items():
            if source in subscriber.model_fields_set:
                values[target] = getattr(subscriber, source)

        if subscriber.status:
            latest_status = max(subscriber.status, key=lambda status: status.id)
            values["subscriber_status"] = latest_status.status

        network_info = subscriber.network_info
        if network_info is not None:
            field_mappings = {
                "time": "lastnetworkdate",
                "last_mcc": "lastmcc",
                "last_mnc": "lastmnc",
                "last_cell_id": "lastcellid",
                "last_lac": "lastlac",
                "last_imei": "imei",
                "model": "imei_device",
                "last_rat": "lastrat",
            }
            for source, target in field_mappings.items():
                if source not in network_info.model_fields_set:
                    continue
                value = getattr(network_info, source)
                if source in {"last_mcc", "last_mnc"} and value is not None:
                    value = str(value)
                values[target] = value
        return ESIMSingleSnapshot.model_validate(values)
    except ValidationError:
        # Validation messages echo provider values, so only a category is propagated.
        raise TelcovisionError("invalid_response") from None


def refresh_telcovision_subscriber(
    session: Session,
    settings: Settings,
    *,
    imsi: str,
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> ESIMRefreshResult:
    """Fetch one live Telcovision subscriber and update its existing eSIM."""
    with open_telcovision_client(
        settings, request_id=request_id, outbound_exchanges=outbound_exchanges
    ) as client:
        logger.info(
            "Telcovision subscriber refresh started request_id=%s imsi=%s",
            request_id,
            imsi,
        )

        def load_snapshot() -> ESIMSingleSnapshot:
            payload = client.get_single_subscriber(
                imsi,
                validate=lambda body: parse_single_subscriber(body, imsi=imsi),
            )
            snapshot = parse_single_subscriber(payload, imsi=imsi)
            logger.info(
                "Telcovision subscriber snapshot parsed request_id=%s account_id=%s imsi=%s",
                request_id,
                snapshot.account_id,
                snapshot.imsi,
            )
            return snapshot

        return ESIMManager(session).refresh_esim(imsi, load_snapshot)


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


def move_subscriber_range_to_account(
    session: Session,
    settings: Settings,
    *,
    source_account_id: int,
    destination_account_id: int,
    imsis: list[str],
    request_id: str,
    outbound_exchanges: list[OutboundExchange],
) -> list[ESIMMoveResult]:
    """Move selected IMSIs in Telcovision, then mirror each confirmed move locally."""
    manager = ESIMManager(session)
    manager.validate_account_move(source_account_id, destination_account_id, imsis)
    results: list[ESIMMoveResult] = []

    with open_telcovision_client(
        settings, request_id=request_id, outbound_exchanges=outbound_exchanges
    ) as client:
        logger.info(
            "Telcovision subscriber transfer started request_id=%s source_account_id=%s "
            "destination_account_id=%s esims=%d",
            request_id,
            source_account_id,
            destination_account_id,
            len(imsis),
        )
        for index, imsi in enumerate(imsis):
            move_subscriber = partial(
                client.move_subscriber_range_to_account,
                imsi,
                imsi,
                source_account_id,
                destination_account_id,
                validate=parse_subscriber_move,
            )

            try:
                results.extend(
                    manager.move_esims_to_account(
                        source_account_id,
                        destination_account_id,
                        [imsi],
                        move_subscriber,
                    )
                )
            except TelcovisionError as error:
                raise TelcovisionSubscriberMoveError(
                    error,
                    moved_imsis=[result.imsi for result in results],
                    failed_imsi=imsi,
                    not_attempted_imsis=imsis[index + 1 :],
                ) from None
            except Exception:
                logger.error(
                    "Telcovision subscriber transfer local update failed request_id=%s "
                    "imsi=%s moved_imsis=%s",
                    request_id,
                    imsi,
                    [result.imsi for result in results],
                )
                raise

            logger.info(
                "Telcovision subscriber transfer completed request_id=%s imsi=%s",
                request_id,
                imsi,
            )

    return results
