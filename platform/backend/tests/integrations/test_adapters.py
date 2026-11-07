"""Offline contract tests: every HTTP call uses httpx.MockTransport."""

from __future__ import annotations

import json
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import httpx

from app.integrations import (
    MaxBot,
    PartnerDelivery,
    SpeechKit,
    TelegramBot,
    VKBot,
    YandexDelivery,
    YandexGeocoder,
    YooKassa,
    dispatch_leg,
    resume_claim,
    notify_assignment,
)
from app.integrations.messaging import IntegrationError, download_provider_media


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_telegram_secret_parse_and_send(self) -> None:
        seen: list[httpx.Request] = []

        def reply(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            bot = TelegramBot(client, token="test-token", webhook_secret="secret")
            self.assertFalse(bot.verify_webhook({}))
            self.assertFalse(bot.verify_webhook({"X-Telegram-Bot-Api-Secret-Token": "bad"}))
            self.assertTrue(bot.verify_webhook({"X-Telegram-Bot-Api-Secret-Token": "secret"}))
            incoming = bot.parse_update({"update_id": 17, "message": {
                "message_id": 2, "from": {"id": 12}, "chat": {"id": 12},
                "caption": "молнию", "photo": [{"file_id": "small"}, {"file_id": "large"}],
                "voice": {"file_id": "voice", "mime_type": "audio/ogg"},
                "location": {"latitude": 58.0, "longitude": 56.3},
            }})
            self.assertEqual(incoming.event_id, "17")
            self.assertEqual(incoming.media[0].reference, "large")
            self.assertEqual(incoming.position.longitude, 56.3)
            await bot.send_message(12, "Готово", buttons=[[('Забрать', 'pickup:1')]])
            self.assertEqual(seen[0].url.path, "/bottest-token/sendMessage")
            self.assertEqual(json.loads(seen[0].content)["reply_markup"]["inline_keyboard"][0][0]["callback_data"], "pickup:1")

    async def test_vk_secret_parse_and_send_idempotency(self) -> None:
        seen: list[httpx.Request] = []

        def reply(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"response": 123})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            bot = VKBot(client, token="vk-secret-token", group_id=7, callback_secret="cb")
            self.assertFalse(bot.verify_webhook({"secret": "cb", "group_id": 8}))
            self.assertTrue(bot.verify_webhook({"secret": "cb", "group_id": 7}))
            incoming = bot.parse_update({"type": "message_new", "group_id": 7, "object": {"message": {
                "id": 13, "from_id": 11, "peer_id": 11, "text": "Подшить",
                "attachments": [{"type": "photo", "photo": {"owner_id": 1, "id": 2}}],
                "geo": {"coordinates": {"latitude": 58.0, "longitude": 56.0}},
            }}})
            self.assertEqual(incoming.media[0].reference, "photo1_2")
            self.assertEqual(incoming.position.latitude, 58.0)
            await bot.send_message(11, "Цена", idempotency_key="order-1-quote")
            await bot.send_message(11, "Цена", idempotency_key="order-1-quote")
            self.assertEqual(seen[0].url.path, "/method/messages.send")
            self.assertIn(b"access_token=vk-secret-token", seen[0].content)
            self.assertEqual(seen[0].content, seen[1].content)

    async def test_max_secret_parse_and_send(self) -> None:
        seen: list[httpx.Request] = []

        def reply(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"message": {"body": {"mid": "new"}}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            bot = MaxBot(client, token="max-token", webhook_secret="max-secret")
            self.assertFalse(bot.verify_webhook({"X-Max-Bot-Api-Secret": "bad"}))
            self.assertTrue(bot.verify_webhook({"X-Max-Bot-Api-Secret": "max-secret"}))
            incoming = bot.parse_update({"update_type": "message_created", "message": {
                "sender": {"user_id": 5}, "recipient": {"chat_id": 9},
                "body": {"mid": "m1", "text": "Починить", "attachments": [
                    {"type": "image", "payload": {"token": "img"}},
                    {"type": "location", "payload": {"latitude": 58.0, "longitude": 56.0}},
                ]},
            }})
            self.assertEqual(incoming.event_id, "m1")
            self.assertEqual(incoming.media[0].reference, "img")
            await bot.send_message(9, "Готово", buttons=[[('Да', 'yes')]])
            self.assertEqual(seen[0].headers["Authorization"], "max-token")
            self.assertEqual(seen[0].url.params["chat_id"], "9")
            self.assertEqual(json.loads(seen[0].content)["attachments"][0]["type"], "inline_keyboard")

    async def test_delivery_live_workflow_and_price_guard(self) -> None:
        seen: list[httpx.Request] = []

        def reply(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            if request.url.path.endswith("/offers/calculate"):
                return httpx.Response(200, json={"offers": [
                    {"taxi_class": "express", "price": {"total_price": "250.00", "total_price_with_vat": "300.00", "currency": "RUB"}, "payload": "e", "offer_ttl": "2099-01-01T00:00:00Z"},
                    {"taxi_class": "courier", "price": {"total_price": "200.00", "total_price_with_vat": "350.00", "currency": "RUB"}, "payload": "c", "offer_ttl": "2099-01-01T00:00:00Z"},
                ]})
            if request.url.path.endswith("/claims/create"):
                return httpx.Response(200, json={"id": "claim-id"})
            if request.url.path.endswith("/claims/info"):
                return httpx.Response(200, json={"status": "ready_for_approval", "version": 2, "pricing": {"offer": {"price": "250.00", "price_with_vat": "300.00", "valid_until": "2099-01-01T00:00:00Z"}}})
            return httpx.Response(200, json={"id": "claim-id", "status": "accepted"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            adapter = YandexDelivery(client, token="delivery-token")
            route = {"items": [{"pickup_point": 1, "dropoff_point": 2, "weight": 1}], "route_points": [{"id": 1}, {"id": 2}]}
            offers = await adapter.calculate_offers(route)
            self.assertEqual(offers.offers[0].price, Decimal("300.00"))
            self.assertEqual(offers.offers[0].net_price, Decimal("250.00"))
            self.assertEqual(offers.offers[0].tariff, "express")
            self.assertTrue(json.loads(seen[0].content)["requirements"]["skip_door_to_door"])
            await adapter.create_claim({**route, "offer_payload": "e", "auto_accept": True}, request_id="stable-1")
            self.assertEqual(seen[1].url.params["request_id"], "stable-1")
            self.assertFalse(json.loads(seen[1].content)["auto_accept"])
            with self.assertRaises(IntegrationError):
                await adapter.accept_claim("claim-id", expected_price=Decimal("299.00"))
            self.assertFalse(any(r.url.path.endswith("/claims/accept") for r in seen))
            await adapter.accept_claim("claim-id", expected_price=Decimal("300.00"))
            self.assertEqual(json.loads(seen[-1].content)["version"], 2)
            self.assertEqual(seen[-1].headers["Authorization"], "Bearer delivery-token")

    async def test_partner_mode_never_calls_transport(self) -> None:
        partner = PartnerDelivery()
        quote = await partner.calculate_offers({"route_points": [{"id": 1}, {"id": 2}]})
        self.assertFalse(quote.live)
        self.assertEqual(quote.offers, ())
        self.assertEqual((await partner.create_claim({}, request_id="order-1"))["status"], "manual_dispatch_required")

    async def test_dispatch_helper_requotes_and_accepts_once(self) -> None:
        seen: list[httpx.Request] = []
        claim_id = "a" * 32

        def reply(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            path = request.url.path
            if path.endswith("/offers/calculate"):
                return httpx.Response(200, json={"offers": [{
                    "taxi_class": "courier", "payload": "fresh-offer", "offer_ttl": "2099-01-01T00:00:00Z",
                    "price": {"total_price": "300.00", "total_price_with_vat": "360.00", "currency": "RUB"},
                }]})
            if path.endswith("/claims/create"):
                return httpx.Response(200, json={"id": claim_id})
            if path.endswith("/claims/info"):
                return httpx.Response(200, json={"status": "ready_for_approval", "version": 1,
                                                 "pricing": {"offer": {"price": "300.00", "price_with_vat": None,
                                                                       "valid_until": "2099-01-01T00:00:00Z"}}})
            return httpx.Response(200, json={"id": claim_id, "status": "accepted"})

        offer_request = {"items": [{"pickup_point": 1, "dropoff_point": 2, "weight": 1}],
                         "route_points": [{"id": 1}, {"id": 2}]}
        claim_request = {"items": [{"pickup_point": 1, "dropoff_point": 2, "title": "Куртка",
                                    "cost_value": "1000.00", "cost_currency": "RUB"}],
                         "route_points": [
                             {"point_id": 1, "type": "source", "contact": {"phone": "+79000000000", "email": "customer@example.org"},
                              "address": {"fullname": "Пермь, Ленина, 1", "coordinates": [56.2, 58.0]}},
                             {"point_id": 2, "type": "destination", "contact": {"phone": "+79000000001"},
                              "address": {"fullname": "Пермь, Ленина, 2", "coordinates": [56.3, 58.0]}},
                         ]}
        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            adapter = YandexDelivery(client, token="token")
            result = await dispatch_leg(adapter, offer_request=offer_request, claim_request=claim_request,
                                        request_id="leg-1", max_polls=1)
            self.assertTrue(result.accepted)
            self.assertEqual(result.offer.price, Decimal("360.00"))
            self.assertEqual(result.claim_id, claim_id)
            self.assertEqual(json.loads(seen[1].content)["offer_payload"], "fresh-offer")
            before_resume = len(seen)
            progress = await resume_claim(adapter, claim_id=claim_id,
                                          expected_price=Decimal("360.00"), expected_net_price=Decimal("300.00"))
            self.assertTrue(progress.accepted)
            self.assertEqual(len(seen), before_resume + 3)
        with self.assertRaises(ValueError):
            bad = dict(claim_request)
            bad["route_points"] = [dict(claim_request["route_points"][0], contact={"phone": "+79000000000", "email": "customer@internal.shveyamozg.local"}), claim_request["route_points"][1]]
            await dispatch_leg(adapter, offer_request=offer_request, claim_request=bad, request_id="leg-2")

    async def test_speechkit_geocoder_and_yookassa(self) -> None:
        seen: list[httpx.Request] = []

        def reply(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            if request.url.host == "stt.api.cloud.yandex.net":
                return httpx.Response(200, json={"result": "заменить молнию"})
            if request.url.host == "geocode-maps.yandex.ru":
                return httpx.Response(200, json={"response": {"GeoObjectCollection": {"featureMember": [{"GeoObject": {
                    "Point": {"pos": "56.234 58.010"}, "metaDataProperty": {"GeocoderMetaData": {
                        "precision": "exact", "kind": "house", "Address": {"country_code": "RU", "formatted": "Пермь, Ленина, 1"},
                    }},
                }}]}}})
            if request.method == "GET":
                return httpx.Response(200, json={"id": "payment-123", "status": "succeeded"})
            return httpx.Response(200, json={"id": "payment-123", "status": "pending"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            speech = SpeechKit(client, folder_id="folder", iam_token="iam-token")
            self.assertEqual(await speech.transcribe_ogg(b"ogg"), "заменить молнию")
            self.assertEqual(seen[-1].url.params["format"], "oggopus")
            geocoder = YandexGeocoder(client, api_key="geo-key")
            result = await geocoder.geocode_house("Пермь, Ленина, 1")
            self.assertTrue(result.exact_house)
            self.assertEqual(result.position.longitude, 56.234)
            payment = YooKassa(client, shop_id="shop", secret_key="secret")
            payload = {
                "amount": {"value": "300.00", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": "https://example.org/return"},
                "receipt": {"customer": {"email": "test@example.org"}, "items": [{
                    "description": "Ремонт одежды", "quantity": "1", "amount": {"value": "300.00", "currency": "RUB"},
                    "vat_code": 1, "payment_mode": "full_payment", "payment_subject": "service",
                }]},
            }
            await payment.create_payment(payload, idempotence_key="pay-1")
            self.assertEqual(seen[-1].headers["Idempotence-Key"], "pay-1")
            self.assertTrue(await payment.verify_webhook({"type": "notification", "event": "payment.succeeded", "object": {"id": "payment-123"}}))
            self.assertFalse(await payment.verify_webhook({"type": "notification", "event": "payment.canceled", "object": {"id": "payment-123"}}))

    async def test_media_download_allowlist_and_api_key_speech(self) -> None:
        seen: list[httpx.Request] = []

        def reply(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            if request.url.host == "stt.api.cloud.yandex.net":
                return httpx.Response(200, json={"result": "ушить рукав"})
            return httpx.Response(200, content=b"\xff\xd8\xffimage", headers={"content-type": "image/jpeg"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
            data, mime = await download_provider_media(client, "https://sun9.userapi.com/photo.jpg", allowed_domains=("userapi.com",))
            self.assertEqual((data[:3], mime), (b"\xff\xd8\xff", "image/jpeg"))
            with self.assertRaises(IntegrationError):
                await download_provider_media(client, "http://127.0.0.1/image", allowed_domains=("userapi.com",))
            self.assertEqual(len(seen), 1)
            speech = SpeechKit(client, api_key="service-key")
            self.assertEqual(await speech.transcribe_ogg(b"ogg"), "ушить рукав")
            self.assertNotIn("folderId", seen[-1].url.params)
            self.assertEqual(seen[-1].headers["Authorization"], "Api-Key service-key")

    async def test_master_assignment_sends_photo_and_action_buttons(self) -> None:
        seen: list[httpx.Request] = []

        def reply(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 21}})

        garment_id = uuid4()
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "bot-token"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
                result = await notify_assignment(
                    client, chat_id="123", order_id=uuid4(), garment_id=garment_id,
                    garment_name="Куртка", problem="Заменить молнию", photos=[b"\xff\xd8\xffimage"],
                )
        self.assertEqual(result.photos_sent, 1)
        self.assertEqual(result.message_id, 21)
        self.assertTrue(seen[0].url.path.endswith("/sendPhoto"))
        buttons = json.loads(seen[1].content)["reply_markup"]["inline_keyboard"]
        self.assertEqual(buttons[0][0]["callback_data"], f"master:accept:{garment_id}")
        self.assertEqual(buttons[1][0]["callback_data"], f"master:ready:{garment_id}")

    async def test_yandex_unknown_create_outcome_fails_closed(self) -> None:
        test_env = {
            "SECRET_KEY": "test-only-strong-secret-key",
            "PROJECT_NAME": "test",
            "DATABASE_URL": "postgresql+psycopg://test:test@localhost:5432/test",
            "FIRST_SUPERUSER": "test@example.org",
            "FIRST_SUPERUSER_PASSWORD": "test-only-password",
        }
        with patch.dict(os.environ, test_env):
            from fastapi import HTTPException
            from app.yandex_dispatch import dispatch_yandex_leg

            leg = SimpleNamespace(mode="yandex", status="PLANNED", external_request_id="stable-key", external_claim_id=None)
            with self.assertRaises(HTTPException) as raised:
                await dispatch_yandex_leg(None, leg)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("manual_reconciliation_required", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
