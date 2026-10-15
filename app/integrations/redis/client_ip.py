"""Resolve globally reachable client IP candidates from a request."""

from ipaddress import IPv4Address, IPv6Address, ip_address

from fastapi import Request
from pydantic import BaseModel, Field

_HEADERS = (
    "CF-Connecting-IPv6",
    "CF-Connecting-IP",
    "True-Client-IP",
    "Fastly-Client-IP",
    "CloudFront-Viewer-Address",
    "X-Azure-ClientIP",
    "X-Azure-SocketIP",
    "X-Envoy-External-Address",
    "Forwarded",
    "X-Forwarded-For",
    "X-Original-Forwarded-For",
    "X-Real-IP",
    "X-Client-IP",
    "Client-IP",
    "X-Cluster-Client-IP",
)
_LIST_HEADERS = {"x-forwarded-for", "x-original-forwarded-for"}
_MAX_VALUES_PER_HEADER = 16
_MAX_VALUE_LENGTH = 2048
_MAX_HEADER_CANDIDATES = 31


class ClientIpCandidate(BaseModel):
    source: str
    ip: str


class ClientIpCapture(BaseModel):
    caller_ip: str = ""
    caller_ip_source: str = ""
    candidates: list[ClientIpCandidate] = Field(default_factory=list)


def _strip_port(token: str) -> str:
    token = token.strip().strip('"')
    if token.startswith("["):
        end = token.find("]")
        return token[1:end] if end > 0 else ""
    if token.count(":") == 1:
        return token.split(":", 1)[0]
    return token


def _public_ip(token: str) -> str:
    try:
        addr = ip_address(_strip_port(token))
    except ValueError:
        return ""
    if isinstance(addr, IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    if not addr.is_global or addr.is_multicast or addr.is_reserved:
        return ""
    return str(addr)


def _tokens(name: str, value: str) -> list[str]:
    lowered = name.lower()
    if lowered == "forwarded":
        tokens = []
        for element in value.split(",")[:_MAX_VALUES_PER_HEADER]:
            for pair in element.split(";"):
                key, _, val = pair.partition("=")
                if key.strip().lower() == "for":
                    tokens.append(val)
        return tokens
    if lowered in _LIST_HEADERS:
        return value.split(",")[:_MAX_VALUES_PER_HEADER]
    return [value]


def resolve_public_client_ips(request: Request) -> ClientIpCapture:
    candidates: list[ClientIpCandidate] = []
    seen: set[tuple[str, str]] = set()

    def add(source: str, ip: str) -> None:
        if ip and (source, ip) not in seen:
            seen.add((source, ip))
            candidates.append(ClientIpCandidate(source=source, ip=ip))

    for name in _HEADERS:
        for value in request.headers.getlist(name):
            if len(value) > _MAX_VALUE_LENGTH:
                continue
            for token in _tokens(name, value):
                if len(candidates) >= _MAX_HEADER_CANDIDATES:
                    break
                add(name.lower(), _public_ip(token))

    if request.client:
        add("socket", _public_ip(request.client.host))

    first = candidates[0] if candidates else None
    return ClientIpCapture(
        caller_ip=first.ip if first else "",
        caller_ip_source=first.source if first else "",
        candidates=candidates,
    )
