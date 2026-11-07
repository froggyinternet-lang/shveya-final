"""Telegram Bot API: https://core.telegram.org/bots/api"""

from __future__ import annotations

import hmac
import os
from typing import Any, Mapping, Sequence

import httpx

from .messaging import IncomingMessage, IntegrationError, MediaRef, Position, request_json


class TelegramBot:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        token: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self.client = client
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.webhook_secret = webhook_secret or os.getenv("TELEGRAM_WEBHOOK_SECRET")

    def verify_webhook(self, headers: Mapping[str, str]) -> bool:
        supplied = next(
            (value for key, value in headers.items() if key.lower() == "x-telegram-bot-api-secret-token"),
            "",
        )
        return bool(self.webhook_secret and hmac.compare_digest(supplied, self.webhook_secret))

    def parse_update(self, update: Mapping[str, Any]) -> IncomingMessage | None:
        message = update.get("message") or update.get("edited_message")
        callback = update.get("callback_query")
        if callback:
            message = callback.get("message")
        if not isinstance(message, dict):
            return None
        sender = callback.get("from") if isinstance(callback, dict) else message.get("from")
        chat = message.get("chat") or {}
        if not isinstance(sender, dict) or not isinstance(chat, dict):
            return None
        media: list[MediaRef] = []
        photos = message.get("photo") or []
        if photos and isinstance(photos[-1], dict) and photos[-1].get("file_id"):
            media.append(MediaRef("photo", str(photos[-1]["file_id"])))
        for field, kind in (("voice", "voice"), ("document", "document"), ("video", "video")):
            attachment = message.get(field)
            if isinstance(attachment, dict) and attachment.get("file_id"):
                media.append(MediaRef(kind, str(attachment["file_id"]), attachment.get("mime_type")))
        location = message.get("location")
        position = (
            Position(float(location["latitude"]), float(location["longitude"]))
            if isinstance(location, dict) and "latitude" in location and "longitude" in location
            else None
        )
        return IncomingMessage(
            channel="telegram",
            event_id=str(update.get("update_id", callback.get("id") if isinstance(callback, dict) else "")),
            sender_id=str(sender.get("id", "")),
            chat_id=str(chat.get("id", "")),
            text=str(message.get("text") or message.get("caption") or ""),
            media=tuple(media),
            position=position,
            callback_data=str(callback.get("data")) if isinstance(callback, dict) and callback.get("data") is not None else None,
            raw=update,
        )

    def _url(self, method: str) -> str:
        if not self.token:
            raise IntegrationError("telegram", "configuration")
        return f"https://api.telegram.org/bot{self.token}/{method}"

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        buttons: Sequence[Sequence[tuple[str, str]]] | None = None,
        request_location: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if buttons:
            body["reply_markup"] = {
                "inline_keyboard": [
                    [{"text": label, "callback_data": data} for label, data in row]
                    for row in buttons
                ]
            }
        elif request_location:
            body["reply_markup"] = {
                "keyboard": [[{"text": "Отправить геопозицию", "request_location": True}]],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
        result = await request_json(self.client, "telegram", "sendMessage", "POST", self._url("sendMessage"), json=body, timeout=10)
        if result.get("ok") is not True:
            raise IntegrationError("telegram", "sendMessage")
        return result

    async def send_photo(
        self,
        chat_id: str | int,
        photo: str | bytes,
        *,
        caption: str = "",
    ) -> dict[str, Any]:
        if isinstance(photo, bytes):
            kwargs: dict[str, Any] = {"data": {"chat_id": str(chat_id), "caption": caption}, "files": {"photo": ("photo.jpg", photo, "image/jpeg")}}
        else:
            kwargs = {"json": {"chat_id": chat_id, "photo": photo, "caption": caption}}
        result = await request_json(self.client, "telegram", "sendPhoto", "POST", self._url("sendPhoto"), timeout=20, **kwargs)
        if result.get("ok") is not True:
            raise IntegrationError("telegram", "sendPhoto")
        return result

    async def download_file(self, file_id: str) -> bytes:
        info = await request_json(
            self.client, "telegram", "getFile", "POST", self._url("getFile"), json={"file_id": file_id}, timeout=10
        )
        path = info.get("result", {}).get("file_path") if info.get("ok") else None
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
            raise IntegrationError("telegram", "getFile")
        try:
            response = await self.client.get(f"https://api.telegram.org/file/bot{self.token}/{path}", timeout=20)
        except httpx.RequestError:
            raise IntegrationError("telegram", "downloadFile") from None
        if not response.is_success or len(response.content) > 20 * 1024 * 1024:
            raise IntegrationError("telegram", "downloadFile", response.status_code)
        return response.content

    async def answer_callback(self, callback_query_id: str, text: str = "") -> dict[str, Any]:
        result = await request_json(
            self.client, "telegram", "answerCallbackQuery", "POST", self._url("answerCallbackQuery"),
            json={"callback_query_id": callback_query_id, "text": text}, timeout=10,
        )
        if result.get("ok") is not True:
            raise IntegrationError("telegram", "answerCallbackQuery")
        return result
