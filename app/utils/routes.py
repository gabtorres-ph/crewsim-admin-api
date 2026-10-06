"""Administrative routes for querying Redis-backed request logs."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.common.schemas import PaginatedResponse
from app.integrations.redis.request_logging import RequestLogManager
from app.utils.schemas import RequestLogEntry, RequestLogMetricsResponse

DEFAULT_PAGE_LIMIT = 100

router = APIRouter(prefix="/utils/request-logs", tags=["request-logs"])


def _to_epoch_milliseconds(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return int(value.timestamp() * 1000)


def _validate_timestamp_range(start_ts: int | None, end_ts: int | None) -> None:
    if start_ts is not None and end_ts is not None and end_ts < start_ts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'to' must be greater than or equal to 'from'",
        )


def _require_request_logging() -> None:
    if not RequestLogManager.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Request logging is disabled",
        )


@router.get("", response_model=PaginatedResponse[RequestLogEntry])
async def list_request_logs(
    user_id: Annotated[str | None, Query()] = None,
    path: Annotated[str | None, Query()] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    include_body: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=1000)] = DEFAULT_PAGE_LIMIT,
    page_size: Annotated[int | None, Query(ge=1, le=1000)] = None,
    start: Annotated[int | None, Query(ge=0)] = None,
) -> PaginatedResponse[RequestLogEntry]:
    _require_request_logging()
    start_ts = _to_epoch_milliseconds(from_)
    end_ts = _to_epoch_milliseconds(to)
    _validate_timestamp_range(start_ts, end_ts)

    effective_limit = page_size if page_size is not None else limit
    offset = start if start is not None else (page - 1) * effective_limit
    effective_page = offset // effective_limit + 1 if start is not None else page

    if path is not None:
        total, entries = await RequestLogManager.get_requests_matching_path(
            user_id=user_id,
            path_query=path,
            start_ts=start_ts,
            end_ts=end_ts,
            start=offset,
            count=effective_limit,
            include_body=include_body,
        )
    elif start_ts is not None or end_ts is not None:
        if user_id is not None:
            total = await RequestLogManager.get_request_count_for_user_by_ts_range(
                user_id, start_ts, end_ts
            )
            entries = await RequestLogManager.get_requests_for_user_by_ts_range(
                user_id,
                start_ts,
                end_ts,
                offset,
                effective_limit,
                include_body=include_body,
            )
        else:
            total = await RequestLogManager.get_request_count_for_all_by_ts_range(
                start_ts, end_ts
            )
            entries = await RequestLogManager.get_requests_for_all_by_ts_range(
                start_ts,
                end_ts,
                offset,
                effective_limit,
                include_body=include_body,
            )
    elif user_id is not None:
        total = await RequestLogManager.get_request_count_for_user(user_id)
        entries = await RequestLogManager.get_requests_for_user(
            user_id,
            offset,
            offset + effective_limit - 1,
            include_body=include_body,
        )
    else:
        total = await RequestLogManager.get_request_count_for_all()
        entries = await RequestLogManager.get_requests_for_all(
            offset,
            offset + effective_limit - 1,
            include_body=include_body,
        )

    return PaginatedResponse[RequestLogEntry](
        items=[RequestLogEntry.model_validate(entry) for entry in entries],
        total=total,
        page=effective_page,
        limit=effective_limit,
    )


@router.get("/metrics", response_model=RequestLogMetricsResponse)
async def get_request_log_metrics(
    user_id: Annotated[str | None, Query()] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    path: Annotated[str | None, Query()] = None,
) -> RequestLogMetricsResponse:
    _require_request_logging()
    start_ts = _to_epoch_milliseconds(from_)
    end_ts = _to_epoch_milliseconds(to)
    _validate_timestamp_range(start_ts, end_ts)
    metrics = await RequestLogManager.get_request_log_metrics(
        user_id=user_id,
        path_query=path,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    return RequestLogMetricsResponse.model_validate(metrics)


@router.get("/{request_id}", response_model=RequestLogEntry)
async def get_request_log(
    request_id: Annotated[str, Path()],
    include_body: Annotated[bool, Query()] = True,
) -> RequestLogEntry:
    _require_request_logging()
    entry = await RequestLogManager.get_request_by_id(request_id, include_body=include_body)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request log not found",
        )
    return RequestLogEntry.model_validate(entry)
