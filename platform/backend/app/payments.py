"""Payment state after an independently verified YooKassa callback."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from pydantic import EmailStr

from fastapi import HTTPException
from sqlmodel import Session, select

from app.domain import money, record, replay
from app.domain_models import Payment, PriceLock
from app.domain_models import RepairOrder
from app.integrations.messaging import IntegrationError
from app.integrations.yookassa import YooKassa
from app.core.config import settings
from app.models import User


async def initiate_payment(
    session: Session,
    *,
    order: RepairOrder,
    user: User,
    receipt_email: EmailStr,
) -> dict:
    """Create exactly one YooKassa payment for locked repair + two delivery legs."""
    if order.customer_id != user.id:
        raise HTTPException(404, "Order not found")
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY or not settings.YOOKASSA_VAT_CODE:
        raise HTTPException(409, "Payment provider or receipt VAT is not configured")
    if not settings.YOOKASSA_RETURN_URL:
        raise HTTPException(409, "Payment return URL is not configured")
    payment = session.exec(select(Payment).where(Payment.order_id == order.id).with_for_update()).first()
    lock = session.exec(select(PriceLock).where(PriceLock.order_id == order.id)).first()
    if not payment or not lock:
        raise HTTPException(409, "Confirm the full quote before payment")
    if payment.status == "PAID":
        return {"payment_id": str(payment.id), "status": "PAID", "confirmation_url": None}
    if payment.external_payment_id and payment.confirmation_url:
        return {"payment_id": str(payment.id), "status": payment.status,
                "confirmation_url": payment.confirmation_url}
    if payment.status != "PENDING":
        raise HTTPException(409, "Payment cannot be initiated in this state")
    email = str(receipt_email)
    if email.endswith("@internal.shveyamozg.local"):
        raise HTTPException(422, "A real receipt email is required")
    lines = []
    for description, amount in (
        ("Ремонт одежды", lock.repair_price),
        ("Доставка до швеи", lock.pickup_delivery_price),
        ("Обратная доставка", lock.return_delivery_price),
    ):
        if amount == 0:
            continue
        lines.append({"description": description, "quantity": "1.00",
                      "amount": {"value": str(amount), "currency": "RUB"},
                      "vat_code": settings.YOOKASSA_VAT_CODE,
                      "payment_mode": "full_payment", "payment_subject": "service"})
    payload = {
        "amount": {"value": str(lock.customer_total), "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": settings.YOOKASSA_RETURN_URL},
        "description": f"Ремонт одежды, заказ {order.id}",
        "metadata": {"order_id": str(order.id)},
        "receipt": {"customer": {"email": email}, "items": lines},
    }
    stable_key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"shveya-payment:{payment.id}"))
    try:
        async with httpx.AsyncClient() as client:
            response = await YooKassa(client).create_payment(payload, idempotence_key=stable_key)
    except (IntegrationError, ValueError) as exc:
        raise HTTPException(502, "Payment provider rejected the request") from exc
    provider_id = response.get("id")
    confirmation = response.get("confirmation") or {}
    url = confirmation.get("confirmation_url") if isinstance(confirmation, dict) else None
    if not isinstance(provider_id, str) or not isinstance(url, str) or not url.startswith("https://"):
        raise HTTPException(502, "Payment provider did not return a valid confirmation URL")
    user.receipt_email = receipt_email
    payment.external_payment_id = provider_id
    payment.confirmation_url = url
    record(session, order_id=order.id, actor_id=user.id,
           event_type="payment.initiated", key=f"payment:init:{order.id}",
           payload={"payment_id": str(payment.id), "external_payment_id": provider_id})
    return {"payment_id": str(payment.id), "status": "PENDING", "confirmation_url": url}


def mark_paid(
    session: Session,
    *,
    order_id: uuid.UUID,
    external_payment_id: str,
    amount: Decimal,
    currency: str,
    event_id: str,
) -> Payment:
    """Caller must verify notification with YooKassa before invoking this function."""
    if not event_id or not external_payment_id or len(event_id) > 140:
        raise HTTPException(422, "Payment identifiers are required")
    key = f"yookassa:{event_id}"
    prior = replay(session, key, "payment.paid")
    payment = session.exec(select(Payment).where(Payment.order_id == order_id)).first()
    lock = session.exec(select(PriceLock).where(PriceLock.order_id == order_id)).first()
    if not payment or not lock:
        raise HTTPException(404, "Payment not found")
    if currency != "RUB" or money(amount) != lock.customer_total or payment.amount != lock.customer_total:
        raise HTTPException(409, "Paid amount differs from locked customer total")
    if prior:
        if payment.status != "PAID" or payment.external_payment_id != external_payment_id:
            raise HTTPException(409, "Payment event conflicts with current state")
        return payment
    if payment.status != "PENDING":
        raise HTTPException(409, "Payment is not awaiting confirmation")
    if not payment.external_payment_id or payment.external_payment_id != external_payment_id:
        raise HTTPException(409, "Payment provider identifier differs from initiated payment")
    payment.status = "PAID"
    payment.external_payment_id = external_payment_id
    payment.paid_at = datetime.now(UTC)
    record(session, order_id=order_id, actor_id=payment.operator_id,
           event_type="payment.paid", key=key,
           payload={"payment_id": str(payment.id), "amount": str(payment.amount),
                    "external_payment_id": external_payment_id})
    return payment
