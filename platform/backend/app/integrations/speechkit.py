"""Short OggOpus transcription via official SpeechKit STT v1.

https://aistudio.yandex.ru/ru/docs/speechkit/stt/request
"""

from __future__ import annotations

import os

import httpx

from .messaging import IntegrationError, request_json


class SpeechKit:
    API = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        folder_id: str | None = None,
        iam_token: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.client = client
        self.folder_id = folder_id or os.getenv("YANDEX_CLOUD_FOLDER_ID")
        self.iam_token = iam_token or os.getenv("YANDEX_CLOUD_IAM_TOKEN")
        self.api_key = api_key or os.getenv("YANDEX_SPEECHKIT_API_KEY") or os.getenv("YANDEX_CLOUD_API_KEY")

    async def transcribe_ogg(self, audio: bytes, *, language: str = "ru-RU") -> str:
        if not (self.iam_token or self.api_key) or (self.iam_token and not self.folder_id):
            raise IntegrationError("speechkit", "configuration")
        if not audio or len(audio) > 1024 * 1024:
            raise ValueError("SpeechKit synchronous OggOpus audio must be 1-1048576 bytes and <=30s")
        authorization = f"Bearer {self.iam_token}" if self.iam_token else f"Api-Key {self.api_key}"
        params = {"topic": "general", "lang": language, "format": "oggopus"}
        if self.folder_id:
            params["folderId"] = self.folder_id
        result = await request_json(
            self.client, "speechkit", "recognize", "POST", self.API,
            params=params,
            headers={"Authorization": authorization, "Content-Type": "application/octet-stream"},
            content=audio, timeout=35,
        )
        if result.get("error_code") is not None or not isinstance(result.get("result"), str):
            raise IntegrationError("speechkit", "recognize")
        return result["result"]
