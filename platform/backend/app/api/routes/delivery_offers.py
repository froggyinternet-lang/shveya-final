"""Server-side prices for both legs of a repair order."""

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.delivery_offers import save_offers
from app.domain import order_for_user, require_role
from app.domain_models import MasterProfile
from app.integrations.delivery import YandexDelivery
from app.integrations.geocoder import YandexGeocoder
from app.integrations.messaging import IntegrationError

router = APIRouter(tags=["delivery offers"])


class OfferRequest(BaseModel):
    order_id: uuid.UUID
    mode: Literal["partner", "yandex"] = "partner"
    pickup_requested_at: datetime | None = None
    door_to_door: bool = False


async def _coordinates(client: httpx.AsyncClient, *, address: str,
                       latitude: Decimal | None, longitude: Decimal | None) -> list[float]:
    if latitude is not None and longitude is not None:
        return [float(longitude), float(latitude)]
    if not os.getenv("YANDEX_GEOCODER_KEY"):
        raise HTTPException(409, "Для расчёта Яндекс Доставки нужны координаты обоих адресов")
    result = await YandexGeocoder(client).geocode_house(address)
    if not result:
        raise HTTPException(409, "Подтвердите точный адрес дома для доставки")
    return [result.position.longitude, result.position.latitude]


def _request(origin: str, destination: str, origin_xy: list[float],
             destination_xy: list[float], door_to_door: bool,
             due: datetime | None = None) -> dict:
    requirements: dict = {
        "taxi_classes": ["express"] if due else ["courier", "express"],
        "skip_door_to_door": not door_to_door,
    }
    if due:
        requirements["due"] = due.isoformat()
    return {
        "items": [{"size": {"length": 0.4, "width": 0.3, "height": 0.1},
                   "weight": 1, "quantity": 1, "pickup_point": 1, "dropoff_point": 2}],
        "route_points": [{"id": 1, "coordinates": origin_xy, "fullname": origin},
                         {"id": 2, "coordinates": destination_xy, "fullname": destination}],
        "requirements": requirements,
    }


@router.post("/delivery/offers")
async def delivery_offers(body: OfferRequest, session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    order = order_for_user(session, body.order_id, user)
    master = session.get(MasterProfile, order.master_id) if order.master_id else None
    if not master or not master.address:
        raise HTTPException(409, "Сначала назначьте швею с адресом")
    if body.pickup_requested_at and (body.pickup_requested_at.tzinfo is None or
                                     body.pickup_requested_at < datetime.now(UTC)):
        raise HTTPException(422, "Время забора должно быть в будущем с часовым поясом")

    if body.mode == "partner":
        pickup, back = save_offers(session, order, mode="partner",
                                   pickup_price=Decimal(0), return_price=Decimal(0),
                                   pickup_requested_at=body.pickup_requested_at,
                                   door_to_door=body.door_to_door)
    else:
        if not os.getenv("YANDEX_DELIVERY_TOKEN"):
            raise HTTPException(409, "Яндекс Доставка не подключена")
        try:
            async with httpx.AsyncClient() as client:
                customer_xy = await _coordinates(client, address=order.customer_address,
                                                 latitude=order.customer_latitude,
                                                 longitude=order.customer_longitude)
                master_xy = await _coordinates(client, address=master.address,
                                               latitude=master.latitude, longitude=master.longitude)
                provider = YandexDelivery(client)
                outbound = await provider.calculate_offers(_request(
                    order.customer_address, master.address, customer_xy, master_xy,
                    body.door_to_door, body.pickup_requested_at))
                inbound = await provider.calculate_offers(_request(
                    master.address, order.customer_address, master_xy, customer_xy,
                    body.door_to_door))
        except IntegrationError:
            raise HTTPException(503, "Не удалось получить тариф Яндекс Доставки") from None
        if not outbound.offers or not inbound.offers:
            raise HTTPException(409, "На выбранный маршрут нет доступного тарифа")
        first, second = outbound.offers[0], inbound.offers[0]
        if len(first.payload) > 4096 or len(second.payload) > 4096:
            raise HTTPException(503, "Яндекс вернул слишком длинный идентификатор тарифа")
        if first.currency != "RUB" or second.currency != "RUB":
            raise HTTPException(409, "Тариф доступен в другой валюте")
        try:
            if not first.expires_at or not second.expires_at:
                raise ValueError("missing expiry")
            expiry = min(datetime.fromisoformat(x.replace("Z", "+00:00"))
                         for x in (first.expires_at, second.expires_at))
        except ValueError:
            raise HTTPException(503, "Яндекс вернул некорректный срок тарифа") from None
        expiry = min(expiry, datetime.now(UTC) + timedelta(minutes=10))
        pickup, back = save_offers(
            session, order, mode="yandex", pickup_price=first.price,
            return_price=second.price, pickup_reference=first.payload,
            return_reference=second.payload, quote_expires_at=expiry,
            provider="yandex_delivery", indicative_return=True,
            pickup_requested_at=body.pickup_requested_at,
            door_to_door=body.door_to_door)
    session.commit()
    return {
        "mode": body.mode,
        "pickup": {"amount": str(pickup.quoted_price), "reference": pickup.offer_reference,
                   "expires_at": pickup.quote_expires_at.isoformat() if pickup.quote_expires_at else None},
        "return": {"amount": str(back.quoted_price), "reference": back.offer_reference,
                   "expires_at": back.quote_expires_at.isoformat() if back.quote_expires_at else None,
                   "indicative": back.indicative},
    }
