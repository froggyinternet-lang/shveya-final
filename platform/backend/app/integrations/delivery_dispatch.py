"""No-DB orchestration for a real Yandex Delivery leg.

The caller owns a persisted, stable request_id and stores the returned claim_id
before retrying. The customer's locked total is never changed here.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .delivery import DeliveryOffer, YandexDelivery
from .messaging import IntegrationError


@dataclass(frozen=True)
class DispatchResult:
    claim_id: str
    status: str
    accepted: bool
    offer: DeliveryOffer
    assessed_gross: Decimal | None


@dataclass(frozen=True)
class ClaimProgress:
    claim_id: str
    status: str
    accepted: bool
    assessed_gross: Decimal | None


def _validate_claim_request(request: Mapping[str, Any]) -> None:
    points = request.get("route_points")
    items = request.get("items")
    if not isinstance(points, list) or len(points) < 2 or not isinstance(items, list) or not items:
        raise ValueError("Yandex claim requires route_points and items")
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("invalid route point")
        contact = point.get("contact") or {}
        address = point.get("address") or {}
        if not contact.get("phone") or not address.get("fullname") or not address.get("coordinates"):
            raise ValueError("Yandex claim needs a phone and precise address at every point")
        if point.get("type") in {"source", "return"}:
            email = str(contact.get("email") or "")
            if "@" not in email or email.endswith("@internal.shveyamozg.local"):
                raise ValueError("Yandex source/return needs a real contact email")
    for item in items:
        if not isinstance(item, dict) or not item.get("title") or item.get("cost_value") is None or item.get("cost_currency") != "RUB":
            raise ValueError("Yandex item needs title, declared value and RUB currency")


def _assessed_gross(info: Mapping[str, Any]) -> Decimal | None:
    pricing = info.get("pricing") or {}
    offer = pricing.get("offer") or {}
    value = offer.get("price_with_vat")
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise IntegrationError("yandex_delivery", "invalid_assessed_gross_price") from None


async def dispatch_leg(
    provider: YandexDelivery,
    *,
    offer_request: Mapping[str, Any],
    claim_request: Mapping[str, Any],
    request_id: str,
    max_polls: int = 3,
    poll_interval: float = 0.5,
) -> DispatchResult:
    """Re-quote, create idempotent claim, evaluate, then accept the same price.

    A pending assessment is returned for later resume, with claim_id. A changed
    price or expired offer is rejected by accept_claim; no courier is called.
    """
    _validate_claim_request(claim_request)
    if not 1 <= max_polls <= 10 or poll_interval < 0:
        raise ValueError("invalid poll settings")
    result = await provider.calculate_offers(offer_request)
    if not result.offers:
        raise IntegrationError("yandex_delivery", "no_live_offer")
    offer = result.offers[0]
    if offer.currency != "RUB":
        raise IntegrationError("yandex_delivery", "unsupported_currency")
    body = dict(claim_request)
    body["offer_payload"] = offer.payload
    body["auto_accept"] = False
    body["client_requirements"] = {**dict(body.get("client_requirements") or {}), "taxi_class": offer.tariff}
    offer_requirements = offer_request.get("requirements") or {}
    if "skip_door_to_door" in offer_requirements:
        body["skip_door_to_door"] = offer_requirements["skip_door_to_door"]
    if "due" in offer_requirements:
        body["due"] = offer_requirements["due"]
    created = await provider.create_claim(body, request_id=request_id)
    claim_id = created.get("id")
    if not isinstance(claim_id, str) or not claim_id:
        raise IntegrationError("yandex_delivery", "missing_claim_id")
    info: dict[str, Any] = {}
    for attempt in range(max_polls):
        info = await provider.claim_info(claim_id)
        if info.get("status") not in {"new", "estimating"}:
            break
        if attempt + 1 < max_polls:
            await asyncio.sleep(poll_interval)
    status = str(info.get("status") or "unknown")
    assessed = _assessed_gross(info)
    if status in {"new", "estimating"}:
        return DispatchResult(claim_id, "assessment_pending", False, offer, assessed)
    if status != "ready_for_approval":
        return DispatchResult(claim_id, status, False, offer, assessed)
    await provider.accept_claim(claim_id, expected_price=offer.price, expected_net_price=offer.net_price)
    return DispatchResult(claim_id, "accepted", True, offer, assessed)


async def final_cost(provider: YandexDelivery, claim_id: str, *, locked_delivery_price: Decimal) -> tuple[Decimal | None, Decimal | None]:
    """Return gross actual cost and overrun vs the customer-locked leg price."""
    info = await provider.claim_info(claim_id)
    pricing = info.get("pricing") or {}
    value = pricing.get("final_price")
    if value is None:
        return None, None
    try:
        actual = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise IntegrationError("yandex_delivery", "invalid_final_price") from None
    return actual, actual - locked_delivery_price


async def resume_claim(
    provider: YandexDelivery,
    *,
    claim_id: str,
    expected_price: Decimal,
    expected_net_price: Decimal,
) -> ClaimProgress:
    """Resume an existing claim without another create call or courier booking."""
    info = await provider.claim_info(claim_id)
    status = str(info.get("status") or "unknown")
    assessed = _assessed_gross(info)
    if status == "ready_for_approval":
        await provider.accept_claim(
            claim_id, expected_price=expected_price,
            expected_net_price=expected_net_price,
        )
        return ClaimProgress(claim_id, "accepted", True, assessed)
    accepted_states = {
        "accepted", "performer_lookup", "performer_draft", "performer_found",
        "pickup_arrived", "ready_for_pickup_confirmation", "pickuped",
        "delivery_arrived", "ready_for_delivery_confirmation", "delivered", "delivered_finish",
    }
    return ClaimProgress(claim_id, status, status in accepted_states, assessed)
