"""Telegram job notification for a linked master; no persistence here."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import httpx

from .telegram import TelegramBot


@dataclass(frozen=True)
class AssignmentNotification:
    garment_id: UUID
    photos_sent: int
    message_id: int | None


async def notify_assignment(
    client: httpx.AsyncClient,
    *,
    chat_id: str | int,
    order_id: UUID,
    garment_id: UUID,
    garment_name: str,
    problem: str,
    photos: Sequence[bytes] = (),
) -> AssignmentNotification:
    """Send the inspected intake photos and the master action buttons.

    `chat_id` must come from an authenticated one-time master binding, never
    from an untrusted order request. The caller handles failures/retry state.
    """
    bot = TelegramBot(client)
    count = 0
    for content in photos:
        if not content:
            continue
        await bot.send_photo(chat_id, content)
        count += 1
    message = (
        f"Новая вещь по заявке {order_id}\n"
        f"{garment_name[:200]}\n"
        f"Что сделать: {problem[:2000]}\n\n"
        "Нажмите «Принять», затем отправьте цену сообщением. "
        "После ремонта отправьте фото результата и нажмите «Готово»."
    )
    result = await bot.send_message(
        chat_id,
        message,
        buttons=[
            [("Принять", f"master:accept:{garment_id}")],
            [("Готово", f"master:ready:{garment_id}")],
        ],
    )
    message_id = result.get("result", {}).get("message_id")
    return AssignmentNotification(garment_id, count, message_id if isinstance(message_id, int) else None)
