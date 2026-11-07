"""Live Yandex claim with stable request ID; customer PriceLock never changes."""

import re
import uuid
from decimal import Decimal

import httpx
from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.routes.delivery_offers import _coordinates, _request
from app.domain import record
from app.domain_models import DeliveryLeg, Garment, MasterProfile, RepairOrder
from app.integrations.delivery import YandexDelivery
from app.integrations.delivery_dispatch import dispatch_leg, resume_claim
from app.integrations.messaging import IntegrationError
from app.models import User


def _real_email(value: str | None) -> bool:
    return bool(value and "@" in value and not value.endswith("@internal.shveyamozg.local"))


async def dispatch_yandex_leg(session: Session, leg: DeliveryLeg) -> dict:
    """Create/resume one leg only after the application has checked payment/consent."""
    if leg.mode != "yandex" or leg.status not in {"OFFERED", "PLANNED", "PROVIDER_PENDING"}:
        raise HTTPException(409, "Yandex leg is not ready for dispatch")
    if leg.external_request_id and not leg.external_claim_id:
        # The previous claims/create may have succeeded although its response
        # timed out. A fresh offer would change offer_payload under the same
        # idempotency key. Reconcile the original request in Yandex first.
        raise HTTPException(409, "manual_reconciliation_required: check Yandex claim for the saved request_id")
    order = session.get(RepairOrder, leg.order_id)
    master = session.get(MasterProfile, order.master_id) if order else None
    customer = session.get(User, order.customer_id) if order else None
    master_user = session.get(User, master.user_id) if master else None
    if not order or not master or not customer or not master_user:
        raise HTTPException(409, "Delivery contacts are incomplete")
    if not (_real_email(customer.receipt_email) and _real_email(master.contact_email)
            and customer.phone and re.fullmatch(r"\+7\d{10}", customer.phone)
            and master.phone and re.fullmatch(r"\+7\d{10}", master.phone)):
        raise HTTPException(409, "needs_contact: real email and +7 phone required for customer and master")
    garments = session.exec(select(Garment).where(Garment.order_id == order.id)).all()
    if not garments or any(g.declared_value is None for g in garments):
        raise HTTPException(409, "needs_declared_value: each garment must have a declared value")
    request_id = leg.external_request_id or str(uuid.uuid5(uuid.NAMESPACE_URL, f"shveya-leg:{leg.id}"))
    leg.external_request_id = request_id
    session.add(leg)
    session.commit()
    try:
        async with httpx.AsyncClient() as client:
            if leg.external_claim_id:
                if leg.expected_gross is None or leg.expected_net is None:
                    raise HTTPException(409, "Claim price snapshot missing")
                progress = await resume_claim(YandexDelivery(client),
                                              claim_id=leg.external_claim_id,
                                              expected_price=leg.expected_gross,
                                              expected_net_price=leg.expected_net)
                status = progress.status
                accepted = progress.accepted
            else:
                customer_xy = await _coordinates(client, address=order.customer_address,
                                                 latitude=order.customer_latitude,
                                                 longitude=order.customer_longitude)
                master_xy = await _coordinates(client, address=master.address or "",
                                               latitude=master.latitude,
                                               longitude=master.longitude)
                if leg.sequence == 1:
                    origin, destination = (customer, order.customer_address, customer_xy), (master_user, master.address, master_xy)
                else:
                    origin, destination = (master_user, master.address, master_xy), (customer, order.customer_address, customer_xy)
                handoff = leg.handoff_mode == "door"
                offer_request = _request(str(origin[1]), str(destination[1]), origin[2], destination[2],
                                         handoff, leg.requested_at)
                source_email = customer.receipt_email if origin[0] == customer else master.contact_email
                target_email = customer.receipt_email if destination[0] == customer else master.contact_email
                source_phone = customer.phone if origin[0] == customer else master.phone
                target_phone = customer.phone if destination[0] == customer else master.phone
                claim_request = {
                    "route_points": [
                        {"type": "source", "point_id": 1, "visit_order": 1,
                         "contact": {"name": origin[0].full_name or "Отправитель",
                                     "phone": source_phone, "email": source_email},
                         "address": {"fullname": origin[1], "coordinates": origin[2]}},
                        {"type": "destination", "point_id": 2, "visit_order": 2,
                         "contact": {"name": destination[0].full_name or "Получатель",
                                     "phone": target_phone, "email": target_email},
                         "address": {"fullname": destination[1], "coordinates": destination[2]}},
                    ],
                    "items": [{"title": "Вещи клиента",
                               "cost_value": str(sum((g.declared_value for g in garments if g.declared_value is not None), Decimal("0"))),
                               "cost_currency": "RUB", "quantity": 1,
                               "size": {"length": 0.4, "width": 0.3, "height": 0.1},
                               "weight": 1,
                               "pickup_point": 1, "dropoff_point": 2}],
                }
                result = await dispatch_leg(YandexDelivery(client), offer_request=offer_request,
                                            claim_request=claim_request, request_id=request_id)
                leg.external_claim_id = result.claim_id
                leg.expected_gross = result.offer.price
                leg.expected_net = result.offer.net_price
                # An offer is an estimate. Actual cost is populated only from
                # pricing.final_price after delivery.
                status = result.status
                accepted = result.accepted
    except IntegrationError as exc:
        raise HTTPException(503, f"Yandex dispatch unavailable: {exc}") from exc
    leg.provider_status = status
    leg.status = "BOOKED" if accepted else ("PROVIDER_PENDING" if status == "assessment_pending" else "PROVIDER_FAILED")
    record(session, order_id=order.id, actor_id=None,
           event_type="delivery.yandex_dispatch", key=f"yandex:dispatch:{leg.id}:{status}",
           payload={"leg_id": str(leg.id), "claim_id": leg.external_claim_id,
                    "status": status, "accepted": accepted,
                    "actual_cost": str(leg.actual_cost) if leg.actual_cost is not None else None})
    return {"leg_id": str(leg.id), "claim_id": leg.external_claim_id,
            "status": leg.status, "provider_status": status,
            "actual_cost": str(leg.actual_cost) if leg.actual_cost is not None else None,
            "variance": str(leg.variance) if leg.variance is not None else None}
