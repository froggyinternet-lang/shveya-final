"""Persist server-side delivery offers before customer price lock."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session, select

from app.domain import money
from app.domain_models import DeliveryLeg, DeliveryTariff, MasterProfile, RepairOrder


def save_offers(
    session: Session,
    order: RepairOrder,
    *,
    mode: str,
    pickup_price: Decimal,
    return_price: Decimal,
    pickup_reference: str | None = None,
    return_reference: str | None = None,
    quote_expires_at: datetime | None = None,
    provider: str | None = None,
    indicative_return: bool = True,
    pickup_requested_at: datetime | None = None,
    door_to_door: bool = False,
) -> tuple[DeliveryLeg, DeliveryLeg]:
    """Called by a verified delivery adapter. Does not commit or call a provider."""
    if order.status not in {"ESTIMATING", "QUOTED"}:
        raise HTTPException(409, "Delivery offer phase is closed")
    if mode not in {"partner", "yandex"}:
        raise HTTPException(422, "Unsupported delivery mode")
    if pickup_requested_at is not None and pickup_requested_at.tzinfo is None:
        raise HTTPException(422, "Pickup time must include timezone")
    master = session.get(MasterProfile, order.master_id)
    if not master or not master.address:
        raise HTTPException(409, "Master address is missing")
    if mode == "partner":
        tariff = session.exec(select(DeliveryTariff).where(
            DeliveryTariff.zone == master.zone, DeliveryTariff.active == True)).first()  # noqa: E712
        if not tariff:
            raise HTTPException(409, "Partner tariff is not configured for this zone")
        # Partner prices are owner-configured in PostgreSQL, never supplied by a client.
        pickup_price, return_price = tariff.pickup_price, tariff.return_price
        provider = "partner"
        pickup_reference = f"tariff:{tariff.id}"
        return_reference = pickup_reference
    else:
        if not provider or not pickup_reference or not return_reference:
            raise HTTPException(422, "External offers require provider references")
        if not quote_expires_at or quote_expires_at.tzinfo is None or quote_expires_at <= datetime.now(UTC):
            raise HTTPException(422, "External offer must have a future expiry")
        if quote_expires_at > datetime.now(UTC) + timedelta(minutes=10):
            quote_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    prices = [money(pickup_price, allow_zero=True), money(return_price, allow_zero=True)]
    legs = []
    for seq, price, reference, origin, destination in (
        (1, prices[0], pickup_reference, order.customer_address, master.address),
        (2, prices[1], return_reference, master.address, order.customer_address),
    ):
        leg = session.exec(select(DeliveryLeg).where(
            DeliveryLeg.order_id == order.id, DeliveryLeg.sequence == seq)).first()
        if leg and leg.status != "OFFERED":
            raise HTTPException(409, "Delivery leg is already in progress")
        if not leg:
            leg = DeliveryLeg(order_id=order.id, sequence=seq,
                              origin_address=origin, destination_address=destination)
        leg.mode = mode
        leg.status = "OFFERED"
        leg.origin_address = origin
        leg.destination_address = destination
        leg.quoted_price = price
        leg.provider = provider
        leg.offer_reference = reference
        leg.quote_expires_at = quote_expires_at
        leg.indicative = indicative_return if seq == 2 else False
        leg.handoff_mode = "door" if door_to_door else "entrance"
        if seq == 1:
            leg.requested_at = pickup_requested_at or order.pickup_requested_at
        session.add(leg)
        legs.append(leg)
    session.flush()
    return legs[0], legs[1]


def get_lockable_offers(session: Session, order: RepairOrder) -> tuple[DeliveryLeg, DeliveryLeg]:
    legs = session.exec(select(DeliveryLeg).where(DeliveryLeg.order_id == order.id)).all()
    by_sequence = {leg.sequence: leg for leg in legs}
    if set(by_sequence) != {1, 2}:
        raise HTTPException(409, "Both delivery offers are required")
    first, second = by_sequence[1], by_sequence[2]
    if any(leg.status != "OFFERED" or leg.quoted_price is None for leg in (first, second)):
        raise HTTPException(409, "Both delivery offers must be current")
    if first.mode != second.mode:
        raise HTTPException(409, "Delivery offer modes differ")
    if first.mode == "yandex":
        now = datetime.now(UTC)
        if any(not leg.offer_reference or not leg.quote_expires_at or leg.quote_expires_at <= now
               for leg in (first, second)):
            raise HTTPException(409, "Delivery offer expired; request a new quote")
    return first, second
