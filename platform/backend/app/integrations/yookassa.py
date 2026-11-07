"""YooKassa HTTP Basic API and 54-FZ receipt payload pass-through.

https://yookassa.ru/developers/payment-acceptance/receipts/54fz/yoomoney/payments
https://yookassa.ru/developers/using-api/webhooks
"""

from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

import httpx

from .messaging import IntegrationError, request_json


_ID = re.compile(r"^[A-Za-z0-9-]{10,64}$")


class YooKassa:
    API = "https://api.yookassa.ru/v3"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        shop_id: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self.client = client
        self.shop_id = shop_id or os.getenv("YOOKASSA_SHOP_ID")
        self.secret_key = secret_key or os.getenv("YOOKASSA_SECRET_KEY")

    def _auth(self) -> httpx.BasicAuth:
        if not self.shop_id or not self.secret_key:
            raise IntegrationError("yookassa", "configuration")
        return httpx.BasicAuth(self.shop_id, self.secret_key)

    @staticmethod
    def _key(value: str) -> str:
        if not value or len(value) > 64:
            raise ValueError("Idempotence-Key must contain 1-64 characters")
        return value

    @staticmethod
    def _id(value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("invalid provider object id")
        return value

    async def _request(self, method: str, path: str, *, body: Mapping[str, Any] | None = None, key: str | None = None) -> dict[str, Any]:
        headers = {"Idempotence-Key": self._key(key)} if key is not None else {}
        return await request_json(
            self.client, "yookassa", path, method, self.API + path,
            auth=self._auth(), headers=headers, json=dict(body) if body is not None else None, timeout=15,
        )

    @staticmethod
    def _validate_receipt(payment: Mapping[str, Any]) -> None:
        receipt = payment.get("receipt")
        if not isinstance(receipt, dict):
            raise ValueError("receipt is required for the payment-and-receipt scenario")
        customer = receipt.get("customer") or {}
        items = receipt.get("items") or []
        if not isinstance(customer, dict) or not customer.get("email") or not isinstance(items, list) or not 1 <= len(items) <= 80:
            raise ValueError("receipt requires customer.email and 1-80 items")
        try:
            total = Decimal("0")
            for item in items:
                for field in ("description", "quantity", "amount", "vat_code", "payment_mode", "payment_subject"):
                    if field not in item:
                        raise ValueError(f"receipt item requires {field}")
                quantity = Decimal(str(item["quantity"]))
                value = item["amount"]["value"]
                if isinstance(value, float):
                    raise ValueError("money must be a decimal string")
                line = Decimal(str(value))
                if quantity <= 0 or line <= 0:
                    raise ValueError("receipt quantities and prices must be positive")
                total += quantity * line
            amount_value = payment["amount"]["value"]
            if isinstance(amount_value, float) or total != Decimal(str(amount_value)):
                raise ValueError("receipt sum must equal payment amount")
        except (InvalidOperation, KeyError, TypeError) as exc:
            raise ValueError("invalid receipt amount or item") from exc

    async def create_payment(self, payload: Mapping[str, Any], *, idempotence_key: str) -> dict[str, Any]:
        self._validate_receipt(payload)
        if not isinstance(payload.get("confirmation"), dict):
            raise ValueError("confirmation is required")
        return await self._request("POST", "/payments", body=payload, key=idempotence_key)

    async def get_payment(self, payment_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/payments/{self._id(payment_id)}")

    async def capture_payment(self, payment_id: str, *, idempotence_key: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        # For a partial capture, the caller must supply the recalculated receipt.
        if payload and "amount" in payload and "receipt" not in payload:
            raise ValueError("partial capture requires updated receipt")
        return await self._request("POST", f"/payments/{self._id(payment_id)}/capture", body=payload, key=idempotence_key)

    async def create_refund(self, payload: Mapping[str, Any], *, idempotence_key: str) -> dict[str, Any]:
        if not payload.get("payment_id") or not payload.get("amount"):
            raise ValueError("payment_id and amount are required")
        self._id(str(payload["payment_id"]))
        return await self._request("POST", "/refunds", body=payload, key=idempotence_key)

    async def get_refund(self, refund_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/refunds/{self._id(refund_id)}")

    async def verify_webhook(self, notification: Mapping[str, Any]) -> bool:
        """Do not trust the notification body: read current state from YooKassa."""
        return await self.verified_webhook_object(notification) is not None

    async def verified_webhook_object(self, notification: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return the provider object only when its current ID and status match."""
        if notification.get("type") != "notification":
            return None
        event = notification.get("event")
        obj = notification.get("object")
        if not isinstance(event, str) or not isinstance(obj, dict):
            return None
        object_id = obj.get("id")
        if not isinstance(object_id, str) or not _ID.fullmatch(object_id):
            return None
        category, _, status = event.partition(".")
        if category == "payment":
            fresh = await self.get_payment(object_id)
        elif category == "refund":
            fresh = await self.get_refund(object_id)
        else:
            return None
        return fresh if fresh.get("id") == object_id and fresh.get("status") == status else None
