"""Response schemas for request-log administration endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RequestLogEntry(BaseModel):
    """A decoded request-log record and its optional captured bodies."""

    request_id: str
    ts: int
    timestamp: str | None = None
    caller_ip: str
    user_id: str
    method: str
    path: str
    status: int
    duration_ms: int
    req_body_key: str
    req_body_len: int
    req_body_truncated: bool
    req_body_gzip: bool = False
    content_type: str | None = None
    resp_body_key: str | None = None
    resp_body_len: int | None = None
    resp_body_truncated: bool | None = None
    resp_body_gzip: bool | None = None
    resp_content_type: str | None = None
    body: Any | None = None
    response_body: Any | None = None

    model_config = ConfigDict(extra="allow")


class RequestLogEndpointMetrics(BaseModel):
    """Aggregated request metrics for one method and path."""

    method: str
    path: str
    count: int
    avg_duration_ms: float


class RequestLogGroupMetrics(BaseModel):
    """Aggregated request metrics for one endpoint group."""

    group: str
    count: int
    avg_duration_ms: float


class RequestLogMetricsResponse(BaseModel):
    """Aggregate request-log metrics returned by the utilities API."""

    total_calls: int
    average_response_time_ms: float
    status_codes: dict[str, int] = Field(default_factory=dict)
    endpoints: list[RequestLogEndpointMetrics] = Field(default_factory=list)
    endpoint_groups: list[RequestLogGroupMetrics] = Field(default_factory=list)
