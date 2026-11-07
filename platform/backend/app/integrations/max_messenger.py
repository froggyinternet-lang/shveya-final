"""MAX Bot API: https://dev.max.ru/docs-api/"""

from __future__ import annotations

import hmac
import os
from typing import Any, Mapping, Sequence

import httpx

from .messaging import IncomingMessage, IntegrationError, MediaRef, Position, request_json


class MaxBot:
    API = "https://platform-api2.max.ru"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        token: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self.client = client
        self.token = token or os.getenv("MAX_BOT_TOKEN")
        self.webhook_secret = webhook_secret or os.getenv("MAX_WEBHOOK_SECRET")

    def verify_webhook(self, headers: Mapping[str, str]) -> bool:
        supplied = next((v for k, v in headers.items() if k.lower() == "x-max-bot-api-secret"), "")
        return bool(self.webhook_secret and hmac.compare_digest(supplied, self.webhook_secret))

    def parse_update(self, update: Mapping[str, Any]) -> IncomingMessage | None:
        event_type = update.get("update_type")
        if event_type not in {"message_created", "message_edited", "message_callback"}:
            return None
        message = update.get("message")
        if not isinstance(message, dict):
            return None
        body = message.get("body") or {}
        sender = message.get("sender") or {}
        recipient = message.get("recipient") or {}
        callback = update.get("callback") or {}
        if not isinstance(body, dict) or not isinstance(sender, dict) or not isinstance(recipient, dict):
            return None
        if event_type == "message_callback" and isinstance(callback, dict):
            sender = callback.get("user") or sender
        media: list[MediaRef] = []
        position: Position | None = None
        for item in body.get("attachments") or []:
            if not isinstance(item, dict):
                continue
            kind = item.get("type")
            payload = item.get("payload") or {}
            if not isinstance(payload, dict):
                continue
            if kind == "location" and "latitude" in payload and "longitude" in payload:
                position = Position(float(payload["latitude"]), float(payload["longitude"]))
            elif kind in {"image", "audio", "file", "video"}:
                reference = payload.get("token") or payload.get("url")
                if reference:
                    media.append(MediaRef("photo" if kind == "image" else "voice" if kind == "audio" else kind, str(reference), url=payload.get("url")))
        event_id = (
            callback.get("callback_id") if event_type == "message_callback" and isinstance(callback, dict)
            else body.get("mid")
        )
        return IncomingMessage(
            channel="max",
            event_id=str(event_id or ""),
            sender_id=str(sender.get("user_id", "")),
            chat_id=str(recipient.get("chat_id", "")),
            text=str(body.get("text") or ""),
            media=tuple(media),
            position=position,
            callback_data=str(callback.get("payload")) if event_type == "message_callback" and isinstance(callback, dict) and callback.get("payload") is not None else None,
            raw=update,
        )

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise IntegrationError("max", "configuration")
        # MAX requires the raw token in Authorization, not Bearer and not a query param.
        return {"Authorization": self.token}

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        buttons: Sequence[Sequence[tuple[str, str]]] | None = None,
        attachments: Sequence[Mapping[str, Any]] | None = None,
        request_location: bool = False,
    ) -> dict[str, Any]:
        if len(text) > 4000:
            raise ValueError("MAX text limit is 4000 characters")
        body: dict[str, Any] = {"text": text}
        payloads = list(attachments or [])
        if buttons:
            payloads.append({
                "type": "inline_keyboard",
                "payload": {"buttons": [[{"type": "callback", "text": label, "payload": data} for label, data in row] for row in buttons]},
            })
        elif request_location:
            payloads.append({"type": "inline_keyboard", "payload": {"buttons": [[{"type": "request_geo_location", "text": "Отправить геопозицию"}]]}})
        if payloads:
            body["attachments"] = payloads
        result = await request_json(
            self.client, "max", "messages", "POST", self.API + "/messages",
            params={"chat_id": chat_id}, headers=self._headers(), json=body, timeout=10,
        )
        if "message" not in result:
            raise IntegrationError("max", "messages")
        return result

    async def subscribe(self, webhook_url: str, update_types: Sequence[str] = ("message_created", "message_callback")) -> dict[str, Any]:
        if not self.webhook_secret:
            raise IntegrationError("max", "configuration")
        if not webhook_url.startswith("https://"):
            raise ValueError("MAX webhook must use HTTPS")
        result = await request_json(
            self.client, "max", "subscriptions", "POST", self.API + "/subscriptions",
            headers=self._headers(), json={"url": webhook_url, "update_types": list(update_types), "secret": self.webhook_secret}, timeout=10,
        )
        if result.get("success") is not True:
            raise IntegrationError("max", "subscriptions")
        return result
