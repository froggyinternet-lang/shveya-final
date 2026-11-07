"""Central repair workflow invariants. No external API calls are made here."""

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domain_models import DeliveryLeg, EventLog, Garment, MasterProfile, PriceLock, RepairOrder
from app.models import User

CENT = Decimal("0.01")
ORDER_STATES = {
    "NEW": {"ESTIMATING", "CANCELLED"},
    "ESTIMATING": {"QUOTED", "CANCELLED", "DISPUTE"},
    "QUOTED": {"ESTIMATING", "CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"PICKUP", "CANCELLED"},
    "PICKUP": {"IN_WORK", "DISPUTE"},
    "IN_WORK": {"QC", "DISPUTE"},
    "QC": {"READY", "IN_WORK", "DISPUTE"},
    "READY": {"DELIVERED", "DISPUTE"},
    "DELIVERED": set(),
    "CANCELLED": set(),
    "DISPUTE": {"IN_WORK", "CANCELLED"},
}


def money(value: Decimal | str | int, *, allow_zero: bool = False) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise HTTPException(422, "Invalid monetary amount")
    if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
        raise HTTPException(422, "Amount must be positive")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def markup(value: Decimal | str | int) -> Decimal:
    try:
        percent = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise HTTPException(422, "Invalid markup")
    if not percent.is_finite() or percent < 30 or percent > 500:
        raise HTTPException(422, "Markup must be between 30 and 500 percent")
    return percent.quantize(CENT, rounding=ROUND_HALF_UP)


def customer_price(cost: Decimal, percent: Decimal) -> Decimal:
    return (money(cost) * (Decimal("1") + markup(percent) / 100)).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def effective_role(user: User) -> str:
    return "owner" if user.is_superuser else user.role


def require_role(user: User, *roles: str) -> None:
    if effective_role(user) not in roles:
        raise HTTPException(403, "Insufficient role")


def order_for_user(session: Session, order_id: uuid.UUID, user: User) -> RepairOrder:
    order = session.get(RepairOrder, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    role = effective_role(user)
    if role in {"owner", "operator"}:
        return order
    if role == "customer" and order.customer_id == user.id:
        return order
    if role == "master":
        profile = session.exec(select(MasterProfile).where(MasterProfile.user_id == user.id)).first()
        if profile and order.master_id == profile.id:
            return order
    if role == "courier":
        leg = session.exec(select(DeliveryLeg).where(DeliveryLeg.order_id == order_id, DeliveryLeg.courier_id == user.id)).first()
        if leg:
            return order
    # Hide the existence of another customer's order.
    raise HTTPException(404, "Order not found")


def master_profile(session: Session, user: User) -> MasterProfile:
    require_role(user, "master")
    profile = session.exec(select(MasterProfile).where(MasterProfile.user_id == user.id)).first()
    if not profile:
        raise HTTPException(403, "Master profile missing")
    return profile


def transition(order: RepairOrder, next_status: str) -> None:
    if next_status not in ORDER_STATES.get(order.status, set()):
        raise HTTPException(409, f"Invalid order transition {order.status} -> {next_status}")
    order.status = next_status
    order.updated_at = datetime.now().astimezone()


def event_key(key: str | None) -> str:
    if key is None:
        return str(uuid.uuid4())
    if not 1 <= len(key) <= 160:
        raise HTTPException(422, "Invalid Idempotency-Key")
    return key


def replay(session: Session, key: str | None, event_type: str) -> EventLog | None:
    if key is None:
        return None
    event = session.exec(select(EventLog).where(EventLog.idempotency_key == key)).first()
    if event and event.event_type != event_type:
        raise HTTPException(409, "Idempotency key already used for another action")
    return event


def record(session: Session, *, order_id: uuid.UUID | None, actor_id: uuid.UUID | None,
           event_type: str, key: str | None, payload: dict | None = None) -> None:
    session.add(EventLog(order_id=order_id, actor_id=actor_id, event_type=event_type,
                         idempotency_key=event_key(key), payload=payload or {}))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # A concurrent request with the same idempotency key has committed.
        # Callers can reread state; no partial mutation survives the rollback.
        if key and replay(session, key, event_type):
            return
        raise


def ensure_leg_sequence(sequence: int) -> None:
    if sequence not in (1, 2):
        raise HTTPException(422, "Only outbound and return delivery legs are allowed")
