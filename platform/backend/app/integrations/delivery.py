"""Yandex Delivery B2B v2 and the initial manual partner workflow.

https://yandex.ru/support/delivery-profile/ru/api/express/overview
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

import httpx

from .messaging import IntegrationError, request_json


@dataclass(frozen=True)
class DeliveryOffer:
    tariff: str
    price: Decimal  # gross cost to the platform, including VAT
    net_price: Decimal
    currency: str
    payload: str
    expires_at: str | None
    pickup_interval: Mapping[str, str] | None
    delivery_interval: Mapping[str, str] | None


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    live: bool
    offers: tuple[DeliveryOffer, ...]
    status: str


class YandexDelivery:
    API = "https://b2b.taxi.yandex.net/b2b/cargo/integration/v2"

    def __init__(self, client: httpx.AsyncClient, *, token: str | None = None) -> None:
        self.client = client
        self.token = token or os.getenv("YANDEX_DELIVERY_TOKEN")

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise IntegrationError("yandex_delivery", "configuration")
        return {"Authorization": f"Bearer {self.token}", "Accept-Language": "ru"}

    async def _post(self, operation: str, *, body: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return await request_json(
            self.client, "yandex_delivery", operation, "POST", self.API + operation,
            headers=self._headers(), json=dict(body or {}), params=dict(params or {}), timeout=15,
        )

    async def calculate_offers(self, request: Mapping[str, Any]) -> DeliveryResult:
        """Pass the documented items, route_points and requirements shape.

        Coordinates must be [longitude, latitude]. For pickup at the building use
        requirements.skip_door_to_door=true; false requests door-to-door service.
        """
        if not request.get("items") or not request.get("route_points"):
            raise ValueError("items and route_points with explicit addresses are required")
        body = dict(request)
        requirements = dict(body.get("requirements") or {})
        requirements.setdefault("skip_door_to_door", True)
        body["requirements"] = requirements
        payload = await self._post("/offers/calculate", body=body)
        offers: list[DeliveryOffer] = []
        for raw in payload.get("offers") or []:
            if not isinstance(raw, dict):
                continue
            price = raw.get("price") or {}
            if not isinstance(price, dict):
                continue
            try:
                amount = Decimal(str(price["total_price_with_vat"]))
                net_amount = Decimal(str(price["total_price"]))
                token = str(raw["payload"])
            except (KeyError, InvalidOperation, TypeError):
                # An offer without gross cost cannot safely be locked into a
                # fixed customer total; do not silently use the net price.
                continue
            offers.append(DeliveryOffer(
                tariff=str(raw.get("taxi_class") or ""),
                price=amount,
                net_price=net_amount,
                currency=str(price.get("currency") or "RUB"),
                payload=token,
                expires_at=raw.get("offer_ttl"),
                pickup_interval=raw.get("pickup_interval"),
                delivery_interval=raw.get("delivery_interval"),
            ))
        offers.sort(key=lambda item: item.price)
        return DeliveryResult("yandex_delivery", True, tuple(offers), "quoted" if offers else "unavailable")

    async def create_claim(self, request: Mapping[str, Any], *, request_id: str) -> dict[str, Any]:
        """Create only; never auto-accept. Reuse request_id after timeout/5xx."""
        if not request_id or len(request_id) > 128:
            raise ValueError("request_id must contain 1-128 characters")
        if not request.get("items") or not request.get("route_points") or not request.get("offer_payload"):
            raise ValueError("items, route_points and selected offer_payload are required")
        body = dict(request)
        body["auto_accept"] = False
        return await self._post("/claims/create", body=body, params={"request_id": request_id})

    async def claim_info(self, claim_id: str) -> dict[str, Any]:
        if not claim_id:
            raise ValueError("claim_id is required")
        return await self._post("/claims/info", params={"claim_id": claim_id})

    async def accept_claim(
        self,
        claim_id: str,
        *,
        expected_price: Decimal,
        expected_net_price: Decimal | None = None,
    ) -> dict[str, Any]:
        """Recheck assessed price and expiry immediately before real dispatch."""
        info = await self.claim_info(claim_id)
        if info.get("status") != "ready_for_approval":
            raise IntegrationError("yandex_delivery", "claim_not_ready")
        offer = (info.get("pricing") or {}).get("offer") or {}
        try:
            gross_value = offer.get("price_with_vat")
            if gross_value is not None:
                actual = Decimal(str(gross_value))
                approved = expected_price
            elif expected_net_price is not None:
                actual = Decimal(str(offer["price"]))
                approved = expected_net_price
            else:
                raise IntegrationError("yandex_delivery", "missing_assessed_gross_price")
        except (KeyError, InvalidOperation, TypeError) as exc:
            raise IntegrationError("yandex_delivery", "missing_assessed_price") from exc
        if actual != approved:
            raise IntegrationError("yandex_delivery", "price_changed")
        expiry = offer.get("valid_until")
        if isinstance(expiry, str):
            try:
                valid_until = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            except ValueError as exc:
                raise IntegrationError("yandex_delivery", "invalid_offer_expiry") from exc
            if valid_until.tzinfo is None or valid_until <= datetime.now(timezone.utc):
                raise IntegrationError("yandex_delivery", "offer_expired")
        version = info.get("version")
        if not isinstance(version, int):
            raise IntegrationError("yandex_delivery", "missing_claim_version")
        return await self._post("/claims/accept", params={"claim_id": claim_id}, body={"version": version})


class PartnerDelivery:
    """No-network adapter for the companion carrying the first 30-50 orders.

    All partner state/price must be supplied and persisted by the application.
    These methods never simulate a live Yandex quote or dispatch.
    """

    async def calculate_offers(self, request: Mapping[str, Any]) -> DeliveryResult:
        if not request.get("route_points"):
            raise ValueError("route_points with explicit addresses are required")
        return DeliveryResult("partner", False, (), "manual_quote_required")

    async def create_claim(self, request: Mapping[str, Any], *, request_id: str) -> dict[str, Any]:
        if not request_id:
            raise ValueError("request_id is required")
        return {"provider": "partner", "live": False, "status": "manual_dispatch_required", "request_id": request_id}

    async def claim_info(self, claim_id: str) -> dict[str, Any]:
        return {"provider": "partner", "live": False, "status": "manual_tracking_required", "reference": claim_id}

    async def accept_claim(self, claim_id: str, *, expected_price: Decimal, expected_net_price: Decimal | None = None) -> dict[str, Any]:
        return {"provider": "partner", "live": False, "status": "manual_dispatch_required", "reference": claim_id}
