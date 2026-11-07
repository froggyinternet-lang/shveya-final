"""Authenticated incoming webhooks for messaging and payments."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.domain import record
from app.domain_models import ChannelIdentity, EventLog, Garment, GarmentPhoto, MasterProfile, RepairOrder
from app.integrations import MaxBot, SpeechKit, TelegramBot, VKBot, YandexGeocoder, YooKassa, notify_assignment
from app.integrations.messaging import IncomingMessage, IntegrationError, download_provider_media

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
_MAX_BODY = 1_000_000
_VK_MEDIA_DOMAINS = ("vk.com", "userapi.com", "vkuseraudio.net")
_MAX_MEDIA_DOMAINS = ("max.ru",)


async def _json(request: Request) -> dict[str, Any]:
    content = await request.body()
    if len(content) > _MAX_BODY:
        raise HTTPException(413, "Webhook body too large")
    try:
        payload = json.loads(content)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid webhook JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(400, "Invalid webhook JSON")
    return payload


async def _media_and_transcript(
    incoming: IncomingMessage,
    client: httpx.AsyncClient,
    telegram: TelegramBot | None = None,
) -> tuple[IncomingMessage, list[tuple[bytes, str]]]:
    photos: list[tuple[bytes, str]] = []
    transcript = ""
    for ref in incoming.media:
        if ref.kind not in {"photo", "voice"}:
            continue
        try:
            if incoming.channel == "telegram" and telegram:
                content = await telegram.download_file(ref.reference)
                mime = "image/jpeg" if ref.kind == "photo" else (ref.mime_type or "audio/ogg")
            elif ref.url:
                domains = _VK_MEDIA_DOMAINS if incoming.channel == "vk" else _MAX_MEDIA_DOMAINS
                content, mime = await download_provider_media(client, ref.url, allowed_domains=domains)
            else:
                continue
            if ref.kind == "photo":
                if len(content) <= 10_000_000:
                    photos.append((content, mime))
            elif not incoming.text and not transcript and mime in {"audio/ogg", "application/ogg"}:
                if os.getenv("YANDEX_SPEECHKIT_API_KEY") or os.getenv("YANDEX_CLOUD_IAM_TOKEN"):
                    transcript = await SpeechKit(client).transcribe_ogg(content)
        except (IntegrationError, ValueError):
            # The intake draft keeps media references. It must not claim a photo
            # was transferred when its bytes could not be retrieved/validated.
            continue
    if transcript:
        incoming = replace(incoming, text=transcript)
    return incoming, photos


async def _ingest(
    incoming: IncomingMessage, session: SessionDep, client: httpx.AsyncClient,
    telegram: TelegramBot | None = None, photos: list[tuple[bytes, str]] | None = None,
) -> dict:
    from app.ingest import ingest_message

    if photos is None:
        incoming, photos = await _media_and_transcript(incoming, client, telegram)
    address_match = re.match(r"^\s*(?:/address\s+|адрес\s*:\s*)(.+)$", incoming.text, re.IGNORECASE)
    if incoming.position is None and address_match and os.getenv("YANDEX_GEOCODER_KEY"):
        try:
            location = await YandexGeocoder(client).geocode_house(address_match.group(1).strip())
        except IntegrationError:
            location = None
        if location:
            incoming = replace(incoming, position=location.position)
    return ingest_message(session, incoming, photos=photos)


async def _notify_assigned_master(result: dict, session: SessionDep, client: httpx.AsyncClient) -> bool:
    if result.get("status") != "created" or result.get("replayed") or not result.get("master_id"):
        return False
    try:
        master = session.get(MasterProfile, uuid.UUID(str(result["master_id"])))
        garment = session.get(Garment, uuid.UUID(str(result["garment_ids"][0])))
        order_id = uuid.UUID(str(result["order_id"]))
    except (ValueError, KeyError, IndexError, TypeError):
        return False
    if not master or not garment:
        return False
    identity = session.exec(select(ChannelIdentity).where(
        ChannelIdentity.user_id == master.user_id,
        ChannelIdentity.channel == "telegram",
    )).first()
    if not identity or not identity.chat_id:
        return False
    photos: list[bytes] = []
    stored = session.exec(select(GarmentPhoto).where(
        GarmentPhoto.garment_id == garment.id,
        GarmentPhoto.kind == "BEFORE_CUSTOMER",
    )).all()
    for photo in stored:
        if Path(photo.storage_key).name != photo.storage_key:
            continue
        path = Path(settings.PHOTO_DIR) / photo.storage_key
        if path.is_file() and path.stat().st_size <= 10_000_000:
            photos.append(path.read_bytes())
    if not photos:
        return False
    try:
        await notify_assignment(
            client, chat_id=identity.chat_id, order_id=order_id,
            garment_id=garment.id, garment_name=garment.name,
            problem=garment.problem, photos=photos,
        )
        return True
    except IntegrationError:
        return False


def _master_prompt(result: dict) -> str | None:
    return {
        "master_linked": "Telegram привязан к профилю швеи. Новые задания придут сюда.",
        "invalid_link": "Код привязки неверный или истёк. Получите новый код в панели.",
        "already_linked": "Этот Telegram уже привязан к профилю.",
        "accepted": "Вещь принята. Отправьте стоимость ремонта сообщением, например «Цена 600».",
        "estimated": "Оценка сохранена. После ремонта отправьте фото вещи и нажмите «Готово».",
        "after_photo_saved": "Фото результата сохранено. Нажмите «Готово» под заданием.",
        "ready": "Готовность вещи сохранена.",
        "needs_job_selection": "Выберите задание кнопкой «Принять» под сообщением с вещью.",
    }.get(result.get("status"))


async def _notify_customer_ready(result: dict, session: SessionDep, client: httpx.AsyncClient) -> bool:
    if result.get("status") != "ready":
        return False
    garment_data = result.get("garment") or {}
    try:
        order_id = uuid.UUID(str(garment_data["order_id"]))
    except (ValueError, KeyError, TypeError):
        return False
    order = session.get(RepairOrder, order_id)
    if not order or order.status != "READY":
        return False
    event_key = f"customer:ready-notice:{order_id}"
    if session.exec(select(EventLog).where(EventLog.idempotency_key == event_key)).first():
        return False
    identity = session.exec(select(ChannelIdentity).where(
        ChannelIdentity.user_id == order.customer_id,
        ChannelIdentity.channel == order.intake_channel,
    )).first()
    if not identity or not identity.chat_id:
        return False
    message = "Вещь готова. Оператор согласует с вами время обратной доставки."
    try:
        if identity.channel == "telegram":
            await TelegramBot(client).send_message(identity.chat_id, message)
        elif identity.channel == "vk":
            await VKBot(client).send_message(identity.chat_id, message, idempotency_key=event_key)
        elif identity.channel == "max":
            await MaxBot(client).send_message(identity.chat_id, message)
        else:
            return False
    except IntegrationError:
        return False
    record(session, order_id=order.id, actor_id=None,
           event_type="customer.ready_notified", key=event_key,
           payload={"channel": identity.channel})
    return True


def _prompt(result: dict) -> str | None:
    status = result.get("status")
    if status == "needs_address":
        return "Чтобы оформить ремонт, отправьте точный адрес сообщением «Адрес: Пермь, улица, дом» и геопозицию кнопкой мессенджера."
    if status == "needs_photo_transfer":
        return "Фото не удалось сохранить. Отправьте, пожалуйста, снимок вещи ещё раз."
    if status == "needs_description":
        return "Напишите или надиктуйте, что нужно отремонтировать."
    if status == "created":
        return f"Заявка {result['order_id']} зарегистрирована. После оценки сообщим цену ремонта и доставки."
    return None


async def _reply(incoming: IncomingMessage, result: dict, client: httpx.AsyncClient, telegram: TelegramBot | None = None) -> bool:
    if result.get("replayed"):
        return False
    prompt = _prompt(result)
    if not prompt:
        return False
    try:
        if incoming.channel == "telegram":
            await (telegram or TelegramBot(client)).send_message(
                incoming.chat_id, prompt, request_location=result.get("status") == "needs_address"
            )
        elif incoming.channel == "vk":
            keyboard = {"one_time": True, "buttons": [[{"action": {"type": "location"}}]]} if result.get("status") == "needs_address" else None
            await VKBot(client).send_message(incoming.chat_id, prompt, idempotency_key=f"intake:{incoming.event_id}", keyboard=keyboard)
        elif incoming.channel == "max":
            await MaxBot(client).send_message(incoming.chat_id, prompt, request_location=result.get("status") == "needs_address")
        return True
    except IntegrationError:
        return False


@router.post("/telegram")
async def telegram_webhook(request: Request, session: SessionDep) -> dict:
    async with httpx.AsyncClient() as client:
        bot = TelegramBot(client)
        if not bot.verify_webhook(request.headers):
            raise HTTPException(403, "Invalid webhook secret")
        incoming = bot.parse_update(await _json(request))
        if incoming is None:
            return {"ok": True, "ignored": True}
        incoming, photos = await _media_and_transcript(incoming, client, bot)
        from app.ingest import handle_master_message

        master_result = handle_master_message(session, incoming, photos=photos)
        if master_result is not None and master_result.get("status") != "not_master":
            customer_notified = await _notify_customer_ready(master_result, session, client)
            prompt = _master_prompt(master_result)
            callback_id = (incoming.raw or {}).get("callback_query", {}).get("id")
            if callback_id:
                try:
                    await bot.answer_callback(str(callback_id), prompt or "Готово")
                except IntegrationError:
                    pass
            if prompt:
                try:
                    await bot.send_message(incoming.chat_id, prompt)
                except IntegrationError:
                    pass
            return {"ok": True, "result": master_result, "customer_notified": customer_notified}
        result = await _ingest(incoming, session, client, bot, photos)
        notified = await _notify_assigned_master(result, session, client)
        return {"ok": True, "result": result, "reply_sent": await _reply(incoming, result, client, bot), "master_notified": notified}


@router.post("/vk")
async def vk_webhook(request: Request, session: SessionDep) -> PlainTextResponse:
    async with httpx.AsyncClient() as client:
        bot = VKBot(client)
        update = await _json(request)
        if not bot.verify_webhook(update):
            raise HTTPException(403, "Invalid webhook secret")
        if update.get("type") == "confirmation":
            confirmation = os.getenv("VK_CONFIRMATION_CODE")
            if not confirmation:
                raise HTTPException(503, "VK confirmation is not configured")
            return PlainTextResponse(confirmation)
        incoming = bot.parse_update(update)
        if incoming is not None:
            result = await _ingest(incoming, session, client)
            await _notify_assigned_master(result, session, client)
            await _reply(incoming, result, client)
        return PlainTextResponse("ok")


@router.post("/max")
async def max_webhook(request: Request, session: SessionDep) -> dict:
    async with httpx.AsyncClient() as client:
        bot = MaxBot(client)
        if not bot.verify_webhook(request.headers):
            raise HTTPException(403, "Invalid webhook secret")
        incoming = bot.parse_update(await _json(request))
        if incoming is None:
            return {"ok": True, "ignored": True}
        result = await _ingest(incoming, session, client)
        notified = await _notify_assigned_master(result, session, client)
        return {"ok": True, "result": result, "reply_sent": await _reply(incoming, result, client), "master_notified": notified}


@router.post("/yookassa")
async def yookassa_webhook(request: Request, session: SessionDep) -> dict:
    from app.payments import mark_paid

    notification = await _json(request)
    async with httpx.AsyncClient() as client:
        provider = YooKassa(client)
        try:
            current = await provider.verified_webhook_object(notification)
        except IntegrationError:
            raise HTTPException(503, "Payment status verification unavailable") from None
    if current is None:
        raise HTTPException(403, "Unverified payment notification")
    if notification.get("event") != "payment.succeeded":
        return {"ok": True, "ignored": True}
    metadata = current.get("metadata") or {}
    amount = current.get("amount") or {}
    try:
        order_id = uuid.UUID(str(metadata["order_id"]))
        payment_id = str(current["id"])
        value = Decimal(str(amount["value"]))
        currency = str(amount["currency"])
    except (KeyError, TypeError, ValueError, InvalidOperation):
        raise HTTPException(422, "Verified payment is missing order or amount") from None
    mark_paid(
        session, order_id=order_id, external_payment_id=payment_id,
        amount=value, currency=currency, event_id=f"yookassa:payment.succeeded:{payment_id}",
    )
    return {"ok": True}
