"""VK community Callback API and messages.send.

Official schemas: https://github.com/VKCOM/vk-api-schema
Official SDK: https://github.com/VKCOM/vk-php-sdk
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any, Mapping

import httpx

from .messaging import IncomingMessage, IntegrationError, MediaRef, Position, request_json


class VKBot:
    API = "https://api.vk.com/method/"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        token: str | None = None,
        group_id: str | int | None = None,
        callback_secret: str | None = None,
        api_version: str = "5.199",
    ) -> None:
        self.client = client
        self.token = token or os.getenv("VK_GROUP_TOKEN")
        self.group_id = str(group_id or os.getenv("VK_GROUP_ID") or "")
        self.callback_secret = callback_secret or os.getenv("VK_CALLBACK_SECRET")
        self.api_version = api_version

    def verify_webhook(self, update: Mapping[str, Any]) -> bool:
        # VK's Callback API provides a body secret, not an HMAC signature.
        supplied = update.get("secret")
        group = update.get("group_id")
        return bool(
            self.callback_secret
            and self.group_id
            and isinstance(supplied, str)
            and hmac.compare_digest(supplied, self.callback_secret)
            and hmac.compare_digest(str(group), self.group_id)
        )

    def parse_update(self, update: Mapping[str, Any]) -> IncomingMessage | None:
        event_type = update.get("type")
        if event_type not in {"message_new", "message_reply", "message_event"}:
            return None
        obj = update.get("object")
        if not isinstance(obj, dict):
            return None
        message = obj.get("message", obj) if event_type != "message_event" else obj
        if not isinstance(message, dict):
            return None
        media: list[MediaRef] = []
        position: Position | None = None
        for attachment in message.get("attachments") or []:
            if not isinstance(attachment, dict):
                continue
            kind = attachment.get("type")
            data = attachment.get(kind)
            if not isinstance(data, dict):
                continue
            if kind == "photo":
                owner, media_id = data.get("owner_id"), data.get("id")
                if owner is not None and media_id is not None:
                    access_key = f"_{data['access_key']}" if data.get("access_key") else ""
                    sizes = [s for s in data.get("sizes", []) if isinstance(s, dict) and isinstance(s.get("url"), str)]
                    best = max(sizes, key=lambda s: int(s.get("width", 0)) * int(s.get("height", 0)), default=None)
                    media.append(MediaRef("photo", f"photo{owner}_{media_id}{access_key}", url=best["url"] if best else None))
            elif kind == "audio_message":
                url = data.get("link_ogg") or data.get("link_mp3")
                if isinstance(url, str):
                    media.append(MediaRef("voice", url, "audio/ogg" if data.get("link_ogg") else "audio/mpeg"))
            elif kind == "doc":
                url = data.get("url")
                if isinstance(url, str):
                    media.append(MediaRef("document", url))
        geo = message.get("geo")
        if isinstance(geo, dict):
            coordinates = geo.get("coordinates")
            if isinstance(coordinates, dict) and "latitude" in coordinates and "longitude" in coordinates:
                position = Position(float(coordinates["latitude"]), float(coordinates["longitude"]))
        sender_id = message.get("from_id", message.get("user_id", ""))
        chat_id = message.get("peer_id", sender_id)
        event_id = update.get("event_id") or obj.get("event_id") or message.get("id") or message.get("conversation_message_id")
        return IncomingMessage(
            channel="vk",
            event_id=f"{self.group_id}:{event_type}:{chat_id}:{event_id}",
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            text=str(message.get("text") or ""),
            media=tuple(media),
            position=position,
            callback_data=str(obj.get("payload")) if event_type == "message_event" and obj.get("payload") is not None else None,
            raw=update,
        )

    async def _call(self, method: str, params: Mapping[str, Any]) -> Any:
        if not self.token:
            raise IntegrationError("vk", "configuration")
        form: dict[str, Any] = {"access_token": self.token, "v": self.api_version, **params}
        response = await request_json(self.client, "vk", method, "POST", self.API + method, data=form, timeout=10)
        if "error" in response or "response" not in response:
            raise IntegrationError("vk", method)
        return response["response"]

    @staticmethod
    def _random_id(idempotency_key: str) -> int:
        if not idempotency_key:
            raise ValueError("idempotency_key is required for VK messages.send")
        return (int.from_bytes(hashlib.sha256(idempotency_key.encode()).digest()[:4], "big") % 2_147_483_647) + 1

    async def send_message(
        self,
        peer_id: str | int,
        text: str,
        *,
        idempotency_key: str,
        attachment: str | None = None,
        keyboard: Mapping[str, Any] | None = None,
    ) -> int:
        params: dict[str, Any] = {
            "peer_id": peer_id,
            "message": text,
            "random_id": self._random_id(idempotency_key),
        }
        if attachment:
            params["attachment"] = attachment
        if keyboard:
            params["keyboard"] = json.dumps(keyboard, ensure_ascii=False, separators=(",", ":"))
        result = await self._call("messages.send", params)
        return int(result)

    async def answer_callback(self, event_id: str, user_id: str | int, peer_id: str | int, text: str) -> Any:
        return await self._call(
            "messages.sendMessageEventAnswer",
            {
                "event_id": event_id,
                "user_id": user_id,
                "peer_id": peer_id,
                "event_data": json.dumps({"type": "show_snackbar", "text": text}, ensure_ascii=False),
            },
        )
