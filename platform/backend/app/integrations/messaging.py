"""Common inbound shape and deliberately redacted transport errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx


@dataclass(frozen=True)
class Position:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class MediaRef:
    kind: str
    reference: str
    mime_type: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class IncomingMessage:
    channel: str
    event_id: str
    sender_id: str
    chat_id: str
    text: str
    media: tuple[MediaRef, ...] = ()
    position: Position | None = None
    callback_data: str | None = None
    raw: Mapping[str, Any] | None = None


class IntegrationError(RuntimeError):
    """Safe to surface without exposing tokens, request bodies or provider URLs."""

    def __init__(self, provider: str, operation: str, status_code: int | None = None):
        self.provider = provider
        self.operation = operation
        self.status_code = status_code
        super().__init__(f"{provider} {operation} failed (HTTP {status_code or 'network'})")


def checked_json(response: httpx.Response, provider: str, operation: str) -> dict[str, Any]:
    if not response.is_success:
        raise IntegrationError(provider, operation, response.status_code)
    try:
        payload = response.json()
    except ValueError as exc:
        raise IntegrationError(provider, operation, response.status_code) from exc
    if not isinstance(payload, dict):
        raise IntegrationError(provider, operation, response.status_code)
    return payload


async def request_json(
    client: httpx.AsyncClient,
    provider: str,
    operation: str,
    method: str,
    url: str,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        # httpx's original exception contains the full URL, including Telegram's
        # token-bearing path. Do not chain it into a user-visible traceback.
        raise IntegrationError(provider, operation) from None
    return checked_json(response, provider, operation)


async def download_provider_media(
    client: httpx.AsyncClient,
    url: str,
    *,
    allowed_domains: tuple[str, ...],
    max_bytes: int = 10_000_000,
) -> tuple[bytes, str]:
    """Fetch a provider-supplied media URL without following redirects or SSRF.

    A private/internal IP, alternate scheme or unrelated host is never requested.
    The caller must still inspect and sanitize the actual image content.
    """
    parts = urlsplit(url)
    hostname = (parts.hostname or "").lower()
    try:
        port = parts.port
    except ValueError:
        raise IntegrationError("messaging", "untrusted_media_url") from None
    if parts.scheme != "https" or port not in (None, 443) or not any(
        hostname == domain or hostname.endswith("." + domain) for domain in allowed_domains
    ):
        raise IntegrationError("messaging", "untrusted_media_url")
    try:
        response = await client.get(url, follow_redirects=False, timeout=20)
    except httpx.RequestError:
        raise IntegrationError("messaging", "download_media") from None
    if not response.is_success or len(response.content) > max_bytes:
        raise IntegrationError("messaging", "download_media", response.status_code)
    mime = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0].lower()
    return response.content, mime
