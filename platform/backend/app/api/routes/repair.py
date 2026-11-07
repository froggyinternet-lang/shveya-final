"""Repair workflow REST API. All reads are scoped by role and ownership."""

import secrets
import uuid
import re
import hashlib
from io import BytesIO
from math import asin, cos, radians, sin, sqrt
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
import httpx
from pydantic import BaseModel, Field as PField
from pydantic import EmailStr
from sqlmodel import func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.domain import (
    customer_price, effective_role, master_profile, markup, money, order_for_user,
    record, replay, require_role, transition,
)
from app.delivery_offers import get_lockable_offers
from app.domain_models import (
    ChannelIdentity, DeliveryLeg, DeliveryProofPhoto, DeliveryTariff, EstimateVersion, EventLog, Garment, GarmentPhoto,
    MasterLinkCode, MasterProfile, Payment, PriceLock, RepairOrder,
)
from app.models import Token, User
from app.payments import initiate_payment
from app.yandex_dispatch import dispatch_yandex_leg
from app.integrations.master_notifications import notify_assignment

router = APIRouter(tags=["repair"])
Idempotency = Annotated[str | None, Header(alias="Idempotency-Key")]


class LoginBody(BaseModel):
    username: str
    password: str


class GarmentIn(BaseModel):
    name: str = PField(min_length=1, max_length=200)
    problem: str = PField(min_length=1, max_length=2000)
    category: str | None = PField(default=None, max_length=100)
    declared_value: Decimal | None = None


class OrderIn(BaseModel):
    address: str = PField(min_length=5, max_length=500)
    description: str = PField(default="", max_length=4000)
    garments: list[GarmentIn] = PField(min_length=1, max_length=10)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    pickup_mode: Literal["entrance", "door"] = "entrance"
    pickup_requested_at: datetime | None = None


class MasterIn(BaseModel):
    name: str = PField(min_length=1, max_length=255)
    phone: str | None = None
    contact_email: EmailStr | None = None
    skills: list[str] = PField(default_factory=list)
    zone: str | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    markup_percent: Decimal = Decimal("30")
    capacity: int = PField(default=5, ge=1, le=100)


class AssignIn(BaseModel):
    master_id: uuid.UUID


class QuoteIn(BaseModel):
    markup_percent: Decimal | None = None
    pickup_delivery_price: Decimal | None = None
    return_delivery_price: Decimal | None = None
    delivery_quote_mode: Literal["partner", "yandex"] | None = None
    delivery_quote_reference: str | None = None
    delivery_quote_created_at: datetime | None = None


class DispatchIn(BaseModel):
    mode: Literal["partner", "yandex"] = "partner"
    quoted_price: Decimal | None = None
    requested_at: datetime | None = None


class EstimateIn(BaseModel):
    amount: Decimal


class TariffIn(BaseModel):
    zone: str = PField(min_length=1, max_length=120)
    pickup_price: Decimal
    return_price: Decimal
    active: bool = True
    allow_free: bool = False


class CoordinatesIn(BaseModel):
    latitude: Decimal = PField(ge=-90, le=90)
    longitude: Decimal = PField(ge=-180, le=180)


class MasterLocationIn(CoordinatesIn):
    address: str = PField(min_length=5, max_length=500)
    capacity: int | None = PField(default=None, ge=1, le=100)
    phone: str | None = None
    contact_email: EmailStr | None = None


class GarmentCategoryIn(BaseModel):
    category: str = PField(min_length=1, max_length=100)


class DeclaredValueIn(BaseModel):
    amount: Decimal


class ProblemIn(BaseModel):
    reason: str = PField(min_length=3, max_length=2000)


class ReturnIn(BaseModel):
    requested_at: datetime
    mode: Literal["partner", "yandex"] = "partner"
    handoff_mode: Literal["entrance", "door"] = "entrance"
    quoted_price: Decimal | None = None


class PayIn(BaseModel):
    receipt_email: EmailStr


class ContactIn(BaseModel):
    phone: str
    receipt_email: EmailStr | None = None


def master_dict(profile: MasterProfile, user: User | None = None) -> dict:
    return {"id": str(profile.id), "user_id": str(profile.user_id),
            "name": user.full_name if user else None, "phone": profile.phone,
            "contact_email": profile.contact_email,
            "skills": profile.skills, "zone": profile.zone, "address": profile.address,
            "markup_percent": str(profile.markup_percent), "is_available": profile.is_available,
            "capacity": profile.capacity}


def order_dict(session: SessionDep, order: RepairOrder, *, detail: bool = False) -> dict:
    result = {"id": str(order.id), "customer_id": str(order.customer_id),
              "master_id": str(order.master_id) if order.master_id else None,
              "status": order.status, "description": order.description,
              "address": order.customer_address, "garment_count": order.garment_count,
              "markup_percent": str(order.markup_percent),
              "estimated_cost": str(order.estimated_cost) if order.estimated_cost is not None else None,
              "quoted_repair_price": str(order.quoted_repair_price) if order.quoted_repair_price is not None else None,
              "quoted_pickup_price": str(order.quoted_pickup_price) if order.quoted_pickup_price is not None else None,
              "quoted_return_price": str(order.quoted_return_price) if order.quoted_return_price is not None else None,
              "customer_total": str(order.quoted_total) if order.quoted_total is not None else None,
              "pickup_delivery_price": str(order.quoted_pickup_price) if order.quoted_pickup_price is not None else None,
              "return_delivery_price": str(order.quoted_return_price) if order.quoted_return_price is not None else None,
              "pickup_mode": order.pickup_handoff_mode,
              "pickup_requested_at": order.pickup_requested_at.isoformat() if order.pickup_requested_at else None,
              "quote_version": order.quote_version,
              "delivery_quote_mode": order.delivery_quote_mode,
              "currency": order.currency, "created_at": order.created_at.isoformat()}
    if order.customer_latitude is None or order.customer_longitude is None:
        result["assignment_status"] = "needs_address"
    elif not all(g.category for g in session.exec(select(Garment).where(Garment.order_id == order.id)).all()):
        result["assignment_status"] = "needs_classification"
    else:
        result["assignment_status"] = "assigned" if order.master_id else "needs_master"
    payment = session.exec(select(Payment).where(Payment.order_id == order.id)).first()
    result["payment_status"] = payment.status if payment else None
    if detail:
        garments = session.exec(select(Garment).where(Garment.order_id == order.id)).all()
        legs = session.exec(select(DeliveryLeg).where(DeliveryLeg.order_id == order.id).order_by(DeliveryLeg.sequence)).all()
        lock = session.exec(select(PriceLock).where(PriceLock.order_id == order.id)).first()
        result["garments"] = [garment_dict(session, garment) for garment in garments]
        result["delivery_legs"] = [leg_dict(leg) for leg in legs]
        result["price_lock"] = ({"repair_price": str(lock.repair_price), "cost": str(lock.cost),
                                  "pickup_delivery_price": str(lock.pickup_delivery_price),
                                  "return_delivery_price": str(lock.return_delivery_price),
                                  "customer_total": str(lock.customer_total),
                                  "markup_percent": str(lock.markup_percent), "created_at": lock.created_at.isoformat()}
                                 if lock else None)
        result["payment"] = ({"id": str(payment.id), "status": payment.status,
                               "amount": str(payment.amount)} if payment else None)
    return result


def garment_dict(session: SessionDep, garment: Garment) -> dict:
    photos = session.exec(select(GarmentPhoto).where(GarmentPhoto.garment_id == garment.id)).all()
    return {"id": str(garment.id), "order_id": str(garment.order_id),
            "master_id": str(garment.master_id) if garment.master_id else None,
            "name": garment.name, "category": garment.category, "problem": garment.problem,
            "qr_code": garment.qr_code, "status": garment.status,
            "declared_value": str(garment.declared_value) if garment.declared_value is not None else None,
            "estimate": str(garment.estimate) if garment.estimate is not None else None,
            "problem_reason": garment.problem_reason,
            "photos": [{"id": str(p.id), "kind": p.kind,
                        "url": f"/api/garments/photos/{p.id}",
                        "moderation_status": p.moderation_status,
                        "created_at": p.created_at.isoformat()} for p in photos]}


def leg_dict(leg: DeliveryLeg) -> dict:
    return {"id": str(leg.id), "order_id": str(leg.order_id), "sequence": leg.sequence,
            "mode": leg.mode, "status": leg.status, "origin_address": leg.origin_address,
            "destination_address": leg.destination_address,
            "quoted_price": str(leg.quoted_price) if leg.quoted_price is not None else None,
            "requested_at": leg.requested_at.isoformat() if leg.requested_at else None,
            "handoff_mode": leg.handoff_mode,
            "indicative": leg.indicative,
            "offer_reference": leg.offer_reference,
            "quote_expires_at": leg.quote_expires_at.isoformat() if leg.quote_expires_at else None,
            "actual_cost": str(leg.actual_cost) if leg.actual_cost is not None else None,
            "variance": str(leg.variance) if leg.variance is not None else None,
            "courier_id": str(leg.courier_id) if leg.courier_id else None}


def get_master_garment(session: SessionDep, user: User, garment_id: uuid.UUID) -> tuple[Garment, RepairOrder]:
    profile = master_profile(session, user)
    garment = session.get(Garment, garment_id)
    if not garment or garment.master_id != profile.id:
        raise HTTPException(404, "Job not found")
    order = session.get(RepairOrder, garment.order_id)
    if not order or order.master_id != profile.id:
        raise HTTPException(404, "Job not found")
    return garment, order


def eligible_masters(session: SessionDep, order: RepairOrder) -> list[tuple[MasterProfile, float]]:
    if order.customer_latitude is None or order.customer_longitude is None:
        return []
    garments = session.exec(select(Garment).where(Garment.order_id == order.id)).all()
    categories = {g.category.casefold() for g in garments if g.category}
    if len(categories) == 0 or any(not g.category for g in garments):
        return []
    latitude, longitude = float(order.customer_latitude), float(order.customer_longitude)
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return []
    masters = session.exec(select(MasterProfile).where(MasterProfile.is_available == True)).all()  # noqa: E712
    candidates = []
    for master in masters:
        if master.latitude is None or master.longitude is None or not master.address:
            continue
        skills = {s.casefold() for s in master.skills}
        if "*" not in skills and not categories.issubset(skills):
            continue
        active = session.exec(select(func.count()).select_from(RepairOrder).where(
            RepairOrder.master_id == master.id,
            RepairOrder.status.not_in(["DELIVERED", "CANCELLED"]))).one()
        if active >= master.capacity:
            continue
        dlat = radians(float(master.latitude) - latitude)
        dlon = radians(float(master.longitude) - longitude)
        a = sin(dlat / 2) ** 2 + cos(radians(latitude)) * cos(radians(float(master.latitude))) * sin(dlon / 2) ** 2
        distance = 6371 * 2 * asin(sqrt(a))
        candidates.append((master, round(distance, 2)))
    return sorted(candidates, key=lambda item: item[1])


def get_courier_leg(session: SessionDep, user: User, leg_id: uuid.UUID) -> DeliveryLeg:
    require_role(user, "courier")
    leg = session.get(DeliveryLeg, leg_id)
    if not leg or leg.mode != "partner" or (leg.courier_id and leg.courier_id != user.id):
        raise HTTPException(404, "Delivery leg not found")
    return leg


def save_photo(upload: UploadFile) -> tuple[str, str]:
    return save_photo_bytes(upload.file.read(10_000_001), upload.content_type or "")


def save_photo_bytes(content: bytes, media_type: str) -> tuple[str, str]:
    if len(content) > 10_000_000:
        raise HTTPException(413, "Photo exceeds 10 MB")
    signatures = {"image/jpeg": content.startswith(b"\xff\xd8\xff"),
                  "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
                  "image/webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP"}
    if not signatures.get(media_type, False):
        raise HTTPException(415, "Only JPEG, PNG or WebP photos are accepted")
    try:
        image = Image.open(BytesIO(content))
        if image.width * image.height > 20_000_000:
            raise HTTPException(413, "Photo dimensions are too large")
        image.load()
        oriented = ImageOps.exif_transpose(image)
        mode = "RGB" if media_type == "image/jpeg" else ("RGBA" if "A" in oriented.getbands() else "RGB")
        clean = Image.new(mode, oriented.size)
        clean.paste(oriented.convert(mode))
        buffer = BytesIO()
        clean.save(buffer, format={"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}[media_type])
        content = buffer.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(415, "Invalid image")
    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[media_type]
    path = Path(settings.PHOTO_DIR)
    path.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{suffix}"
    (path / filename).write_bytes(content)
    return filename, media_type


@router.post("/auth/login", response_model=Token)
def auth_login(body: LoginBody, session: SessionDep) -> Token:
    user = crud.authenticate(session=session, email=body.username, password=body.password)
    if not user or not user.is_active:
        raise HTTPException(401, "Invalid credentials")
    return Token(access_token=create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)))


@router.get("/me")
def me(user: CurrentUser) -> dict:
    return {"id": str(user.id), "email": user.email, "name": user.full_name,
            "role": effective_role(user), "is_active": user.is_active,
            "phone": user.phone, "receipt_email": user.receipt_email}


@router.put("/app/contact")
def set_customer_contact(body: ContactIn, session: SessionDep,
                         user: CurrentUser, key: Idempotency = None) -> dict:
    require_role(user, "customer")
    if not re.fullmatch(r"\+7\d{10}", body.phone):
        raise HTTPException(422, "Phone must be a Russian +7 number")
    if replay(session, key, "customer.contact_updated"):
        return {"phone": user.phone, "receipt_email": user.receipt_email}
    user.phone = body.phone
    if body.receipt_email:
        user.receipt_email = body.receipt_email
    record(session, order_id=None, actor_id=user.id, event_type="customer.contact_updated",
           key=key, payload={"has_phone": True, "has_receipt_email": bool(user.receipt_email)})
    return {"phone": user.phone, "receipt_email": user.receipt_email}


@router.get("/app/orders")
def customer_orders(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "customer")
    orders = session.exec(select(RepairOrder).where(RepairOrder.customer_id == user.id).order_by(RepairOrder.created_at.desc())).all()
    return {"data": [order_dict(session, o) for o in orders], "count": len(orders)}


@router.post("/app/orders")
def create_order(body: OrderIn, session: SessionDep, user: CurrentUser,
                 key: Idempotency = None) -> dict:
    require_role(user, "customer")
    previous = replay(session, key, "order.created")
    if previous:
        order = order_for_user(session, uuid.UUID(previous.payload["order_id"]), user)
        return order_dict(session, order, detail=True)
    if body.pickup_requested_at is not None and body.pickup_requested_at.tzinfo is None:
        raise HTTPException(422, "Pickup time must include timezone")
    order = RepairOrder(customer_id=user.id, customer_address=body.address,
                        customer_latitude=body.latitude, customer_longitude=body.longitude,
                        description=body.description, garment_count=len(body.garments),
                        pickup_handoff_mode=body.pickup_mode,
                        pickup_requested_at=body.pickup_requested_at)
    session.add(order)
    session.flush()
    for item in body.garments:
        session.add(Garment(order_id=order.id, name=item.name, category=item.category,
                            problem=item.problem,
                            declared_value=money(item.declared_value, allow_zero=True) if item.declared_value is not None else None))
    record(session, order_id=order.id, actor_id=user.id, event_type="order.created", key=key,
           payload={"order_id": str(order.id)})
    return order_dict(session, order, detail=True)


@router.post("/app/orders/{order_id}/confirm-quote")
def confirm_quote(order_id: uuid.UUID, session: SessionDep, user: CurrentUser,
                  key: Idempotency = None) -> dict:
    require_role(user, "customer")
    order = order_for_user(session, order_id, user)
    previous = replay(session, key, "quote.confirmed")
    if previous:
        return order_dict(session, order, detail=True)
    if order.status != "QUOTED" or order.estimated_cost is None or order.quoted_repair_price is None or order.quoted_total is None:
        raise HTTPException(409, "Order has no active repair quote")
    if order.delivery_quote_mode == "yandex" and (not order.quote_created_at or datetime.now(UTC) - order.quote_created_at > timedelta(minutes=10)):
        raise HTTPException(409, "Delivery quote expired; request a new quote")
    first, second = get_lockable_offers(session, order)
    if first.quoted_price != order.quoted_pickup_price or second.quoted_price != order.quoted_return_price:
        raise HTTPException(409, "Delivery offer changed; request a new quote")
    if session.exec(select(PriceLock).where(PriceLock.order_id == order.id)).first():
        raise HTTPException(409, "Repair price is already locked")
    version = session.exec(select(EstimateVersion).where(EstimateVersion.order_id == order.id,
                           EstimateVersion.version_number == order.quote_version)).first()
    if not version or order.quoted_by is None:
        raise HTTPException(409, "Offer snapshot missing")
    lock = PriceLock(order_id=order.id, estimate_version_id=version.id,
                     cost=version.cost, repair_price=version.repair_price,
                     pickup_delivery_price=version.pickup_delivery_price,
                     return_delivery_price=version.return_delivery_price,
                     customer_total=version.customer_total,
                     markup_percent=version.markup_percent, confirmed_by=user.id)
    session.add(lock)
    session.flush()
    session.add(Payment(order_id=order.id, price_lock_id=lock.id,
                        amount=lock.customer_total, status="PENDING",
                        operator_id=order.quoted_by))
    transition(order, "CONFIRMED")
    record(session, order_id=order.id, actor_id=user.id, event_type="quote.confirmed", key=key,
           payload={"customer_total": str(lock.customer_total), "estimate_version_id": str(version.id)})
    return order_dict(session, order, detail=True)


@router.post("/app/orders/{order_id}/confirm-return")
async def confirm_return(order_id: uuid.UUID, body: ReturnIn, session: SessionDep,
                         user: CurrentUser, key: Idempotency = None) -> dict:
    require_role(user, "customer")
    order = order_for_user(session, order_id, user)
    if replay(session, key, "return.confirmed"):
        return order_dict(session, order, detail=True)
    if order.status != "READY":
        raise HTTPException(409, "Order is not ready for return")
    if body.requested_at.tzinfo is None or body.requested_at <= datetime.now(UTC):
        raise HTTPException(422, "Choose a future time with timezone")
    master = session.get(MasterProfile, order.master_id)
    if not master or not master.address:
        raise HTTPException(409, "Master pickup address is missing")
    lock = session.exec(select(PriceLock).where(PriceLock.order_id == order.id)).first()
    if not lock:
        raise HTTPException(409, "Price lock missing")
    if body.quoted_price is not None and money(body.quoted_price, allow_zero=True) != lock.return_delivery_price:
        raise HTTPException(409, "Customer delivery price is locked")
    leg = session.exec(select(DeliveryLeg).where(DeliveryLeg.order_id == order.id, DeliveryLeg.sequence == 2)).first()
    if not leg or leg.status != "OFFERED":
        raise HTTPException(409, "Return leg is unavailable")
    leg.status = "PLANNED"
    if body.mode != leg.mode:
        raise HTTPException(409, "Return mode differs from locked customer offer")
    leg.handoff_mode = body.handoff_mode
    leg.requested_at = body.requested_at
    session.add(leg)
    record(session, order_id=order.id, actor_id=user.id, event_type="return.confirmed", key=key,
           payload={"leg_id": str(leg.id), "mode": leg.mode, "handoff_mode": leg.handoff_mode})
    if leg.mode == "yandex":
        await dispatch_yandex_leg(session, leg)
    return order_dict(session, order, detail=True)


@router.post("/app/orders/{order_id}/pay")
async def pay_order(order_id: uuid.UUID, body: PayIn, session: SessionDep,
                    user: CurrentUser) -> dict:
    require_role(user, "customer")
    order = order_for_user(session, order_id, user)
    return await initiate_payment(session, order=order, user=user,
                                  receipt_email=body.receipt_email)


@router.get("/admin/overview")
def admin_overview(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    orders = session.exec(select(RepairOrder).order_by(RepairOrder.created_at.desc())).all()
    profiles = session.exec(select(MasterProfile).where(MasterProfile.is_available == True)).all()  # noqa: E712
    locks = session.exec(select(PriceLock)).all()
    return {"orders_total": len(orders), "orders_active": sum(o.status not in {"DELIVERED", "CANCELLED"} for o in orders),
            "orders_ready": sum(o.status == "READY" for o in orders), "masters_active": len(profiles),
            "revenue_total": str(sum((p.repair_price for p in locks), Decimal("0.00"))),
            "queue": [order_dict(session, o) for o in orders[:20]]}


@router.get("/admin/orders")
def admin_orders(session: SessionDep, user: CurrentUser, status: str | None = None,
                 limit: int = 100, offset: int = 0) -> dict:
    require_role(user, "owner", "operator")
    if not 1 <= limit <= 200 or offset < 0:
        raise HTTPException(422, "Invalid pagination")
    query = select(RepairOrder)
    if status:
        query = query.where(RepairOrder.status == status)
    orders = session.exec(query.order_by(RepairOrder.created_at.desc()).offset(offset).limit(limit)).all()
    count = session.exec(select(func.count()).select_from(RepairOrder).where(RepairOrder.status == status)).one() if status else session.exec(select(func.count()).select_from(RepairOrder)).one()
    return {"data": [order_dict(session, o) for o in orders], "count": count}


@router.get("/admin/orders/{order_id}")
def admin_order_detail(order_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    return order_dict(session, order_for_user(session, order_id, user), detail=True)


@router.get("/admin/orders/{order_id}/suggest-masters")
def suggest_masters(order_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    order = order_for_user(session, order_id, user)
    if order.customer_latitude is None or order.customer_longitude is None:
        return {"status": "needs_address", "data": []}
    garments = session.exec(select(Garment).where(Garment.order_id == order.id)).all()
    if any(not garment.category for garment in garments):
        return {"status": "needs_classification", "data": []}
    candidates = eligible_masters(session, order)
    return {"status": "ready" if candidates else "no_eligible_master",
            "data": [{**master_dict(profile, session.get(User, profile.user_id)),
                      "distance_km": distance} for profile, distance in candidates]}


@router.patch("/admin/orders/{order_id}/location")
def set_order_location(order_id: uuid.UUID, body: CoordinatesIn,
                       session: SessionDep, user: CurrentUser,
                       key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    order = order_for_user(session, order_id, user)
    if replay(session, key, "order.location_verified"):
        return order_dict(session, order, detail=True)
    if order.status not in {"NEW", "ESTIMATING"}:
        raise HTTPException(409, "Location cannot change after quote")
    order.customer_latitude = body.latitude
    order.customer_longitude = body.longitude
    record(session, order_id=order.id, actor_id=user.id, event_type="order.location_verified",
           key=key, payload={"latitude": str(body.latitude), "longitude": str(body.longitude)})
    return order_dict(session, order, detail=True)


@router.patch("/admin/orders/{order_id}/contact")
def set_order_customer_contact(order_id: uuid.UUID, body: ContactIn,
                               session: SessionDep, user: CurrentUser,
                               key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    order = order_for_user(session, order_id, user)
    customer = session.get(User, order.customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    if not re.fullmatch(r"\+7\d{10}", body.phone):
        raise HTTPException(422, "Phone must be a Russian +7 number")
    if replay(session, key, "customer.contact_updated"):
        return {"phone": customer.phone, "receipt_email": customer.receipt_email}
    customer.phone = body.phone
    if body.receipt_email:
        customer.receipt_email = body.receipt_email
    record(session, order_id=order.id, actor_id=user.id, event_type="customer.contact_updated",
           key=key, payload={"customer_id": str(customer.id), "has_phone": True,
                             "has_receipt_email": bool(customer.receipt_email)})
    return {"phone": customer.phone, "receipt_email": customer.receipt_email}


@router.patch("/admin/garments/{garment_id}/category")
def set_garment_category(garment_id: uuid.UUID, body: GarmentCategoryIn,
                         session: SessionDep, user: CurrentUser,
                         key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    garment = session.get(Garment, garment_id)
    if not garment:
        raise HTTPException(404, "Garment not found")
    order = session.get(RepairOrder, garment.order_id)
    if not order or order.status not in {"NEW", "ESTIMATING"}:
        raise HTTPException(409, "Category cannot change after quote")
    if replay(session, key, "garment.classified"):
        return garment_dict(session, garment)
    garment.category = body.category.strip().casefold()
    record(session, order_id=order.id, actor_id=user.id, event_type="garment.classified",
           key=key, payload={"garment_id": str(garment.id), "category": garment.category})
    return garment_dict(session, garment)


@router.patch("/admin/garments/{garment_id}/declared-value")
def set_declared_value(garment_id: uuid.UUID, body: DeclaredValueIn,
                       session: SessionDep, user: CurrentUser,
                       key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    garment = session.get(Garment, garment_id)
    if not garment:
        raise HTTPException(404, "Garment not found")
    order = session.get(RepairOrder, garment.order_id)
    if not order or order.status not in {"NEW", "ESTIMATING", "QUOTED", "CONFIRMED"}:
        raise HTTPException(409, "Declared value can no longer change")
    if replay(session, key, "garment.value_declared"):
        return garment_dict(session, garment)
    garment.declared_value = money(body.amount, allow_zero=True)
    record(session, order_id=order.id, actor_id=user.id, event_type="garment.value_declared",
           key=key, payload={"garment_id": str(garment.id), "amount": str(garment.declared_value)})
    return garment_dict(session, garment)


@router.patch("/admin/masters/{master_id}/location")
def set_master_location(master_id: uuid.UUID, body: MasterLocationIn,
                        session: SessionDep, user: CurrentUser,
                        key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    master = session.get(MasterProfile, master_id)
    if not master:
        raise HTTPException(404, "Master not found")
    if replay(session, key, "master.location_verified"):
        return master_dict(master, session.get(User, master.user_id))
    master.address = body.address
    master.latitude = body.latitude
    master.longitude = body.longitude
    if body.capacity is not None:
        master.capacity = body.capacity
    if body.phone is not None:
        if not re.fullmatch(r"\+7\d{10}", body.phone):
            raise HTTPException(422, "Phone must be a Russian +7 number")
        master.phone = body.phone
    if body.contact_email is not None:
        master.contact_email = str(body.contact_email)
    record(session, order_id=None, actor_id=user.id, event_type="master.location_verified",
           key=key, payload={"master_id": str(master.id)})
    return master_dict(master, session.get(User, master.user_id))


@router.get("/admin/masters")
def admin_masters(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    profiles = session.exec(select(MasterProfile)).all()
    return {"data": [master_dict(p, session.get(User, p.user_id)) for p in profiles], "count": len(profiles)}


@router.get("/admin/tariffs")
def list_tariffs(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    tariffs = session.exec(select(DeliveryTariff)).all()
    return {"data": [{"id": str(t.id), "zone": t.zone,
                      "pickup_price": str(t.pickup_price), "return_price": str(t.return_price),
                      "active": t.active, "allow_free": t.allow_free} for t in tariffs], "count": len(tariffs)}


@router.put("/admin/tariffs/{zone}", operation_id="upsert_tariff_by_zone")
@router.post("/admin/tariffs", operation_id="create_tariff")
def upsert_tariff(body: TariffIn, session: SessionDep, user: CurrentUser,
                  key: Idempotency = None, zone: str | None = None) -> dict:
    require_role(user, "owner")
    if zone is not None and zone != body.zone:
        raise HTTPException(422, "Tariff zone does not match path")
    if replay(session, key, "tariff.updated"):
        tariff = session.exec(select(DeliveryTariff).where(DeliveryTariff.zone == body.zone)).first()
        if tariff:
            return {"id": str(tariff.id), "zone": tariff.zone, "pickup_price": str(tariff.pickup_price),
                    "return_price": str(tariff.return_price), "active": tariff.active}
    tariff = session.exec(select(DeliveryTariff).where(DeliveryTariff.zone == body.zone)).first()
    if not tariff:
        tariff = DeliveryTariff(zone=body.zone, updated_by=user.id)
    tariff.pickup_price = money(body.pickup_price, allow_zero=body.allow_free)
    tariff.return_price = money(body.return_price, allow_zero=body.allow_free)
    tariff.active = body.active
    tariff.allow_free = body.allow_free
    tariff.updated_by = user.id
    tariff.updated_at = datetime.now(UTC)
    session.add(tariff)
    record(session, order_id=None, actor_id=user.id, event_type="tariff.updated", key=key,
           payload={"tariff_id": str(tariff.id), "zone": tariff.zone})
    return {"id": str(tariff.id), "zone": tariff.zone, "pickup_price": str(tariff.pickup_price),
            "return_price": str(tariff.return_price), "active": tariff.active,
            "allow_free": tariff.allow_free}


@router.post("/admin/masters")
def create_master(body: MasterIn, session: SessionDep, user: CurrentUser,
                  key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    if replay(session, key, "master.created"):
        raise HTTPException(409, "Master already created; temporary password cannot be shown again")
    percent = markup(body.markup_percent)
    uid = uuid.uuid4()
    username = f"master-{uid.hex}@internal.shveyamozg.local"
    temporary_password = secrets.token_urlsafe(24)
    account = User(id=uid, email=username, hashed_password=get_password_hash(temporary_password),
                   full_name=body.name, role="master")
    profile = MasterProfile(user_id=uid, phone=body.phone, contact_email=str(body.contact_email) if body.contact_email else None,
                            skills=body.skills, zone=body.zone,
                            address=body.address, latitude=body.latitude, longitude=body.longitude,
                            markup_percent=percent, capacity=body.capacity)
    session.add(account)
    session.add(profile)
    record(session, order_id=None, actor_id=user.id, event_type="master.created", key=key,
           payload={"master_id": str(profile.id)})
    return {**master_dict(profile, account), "username": username,
            "temporary_password": temporary_password}


@router.post("/admin/masters/{master_id}/telegram-link")
def create_master_link(master_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    master = session.get(MasterProfile, master_id)
    if not master:
        raise HTTPException(404, "Master not found")
    code = secrets.token_urlsafe(18)
    link = MasterLinkCode(master_user_id=master.user_id,
                          code_hash=hashlib.sha256(code.encode()).hexdigest(),
                          expires_at=datetime.now(UTC) + timedelta(minutes=15))
    session.add(link)
    record(session, order_id=None, actor_id=user.id, event_type="master.link_issued",
           key=None, payload={"master_id": str(master.id), "link_id": str(link.id)})
    return {"code": code, "expires_at": link.expires_at.isoformat(),
            "instructions": f"Отправьте боту: /link {code}"}


@router.post("/admin/orders/{order_id}/assign")
async def assign_master(order_id: uuid.UUID, body: AssignIn, session: SessionDep,
                        user: CurrentUser, key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    order = order_for_user(session, order_id, user)
    if replay(session, key, "order.assigned"):
        return order_dict(session, order, detail=True)
    if order.status not in {"NEW", "ESTIMATING"}:
        raise HTTPException(409, "Cannot reassign after quote")
    master = session.get(MasterProfile, body.master_id)
    if not master or master.id not in {p.id for p, _ in eligible_masters(session, order)}:
        raise HTTPException(409, "Master is not eligible; check address, skills and capacity")
    order.master_id = master.id
    order.markup_percent = master.markup_percent
    if order.status == "NEW":
        transition(order, "ESTIMATING")
    for garment in session.exec(select(Garment).where(Garment.order_id == order.id)).all():
        garment.master_id = master.id
        garment.estimate = None
        garment.status = "RECEIVED"
        session.add(garment)
    order.estimated_cost = None
    order.quoted_repair_price = None
    record(session, order_id=order.id, actor_id=user.id, event_type="order.assigned", key=key,
           payload={"master_id": str(master.id)})
    result = order_dict(session, order, detail=True)
    identity = session.exec(select(ChannelIdentity).where(
        ChannelIdentity.user_id == master.user_id,
        ChannelIdentity.channel == "telegram")).first()
    if not identity or not identity.chat_id:
        result["notification_status"] = "needs_telegram_link"
        return result
    try:
        async with httpx.AsyncClient() as client:
            for garment in session.exec(select(Garment).where(Garment.order_id == order.id)).all():
                approved = session.exec(select(GarmentPhoto).where(
                    GarmentPhoto.garment_id == garment.id,
                    GarmentPhoto.moderation_status == "APPROVED")).all()
                images = []
                for photo in approved:
                    path = Path(settings.PHOTO_DIR) / photo.storage_key
                    if path.is_file():
                        images.append(path.read_bytes())
                await notify_assignment(client, chat_id=identity.chat_id,
                                        order_id=order.id, garment_id=garment.id,
                                        garment_name=garment.name, problem=garment.problem,
                                        photos=images)
        result["notification_status"] = "sent"
    except Exception:
        # Assignment stays committed and the failure is visible for operator retry.
        record(session, order_id=order.id, actor_id=user.id,
               event_type="master.notification_failed", key=None,
               payload={"master_id": str(master.id)})
        result["notification_status"] = "failed"
    return result


@router.post("/admin/orders/{order_id}/quote")
def issue_quote(order_id: uuid.UUID, body: QuoteIn, session: SessionDep,
                user: CurrentUser, key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    order = order_for_user(session, order_id, user)
    if replay(session, key, "quote.issued"):
        return order_dict(session, order, detail=True)
    if order.status not in {"ESTIMATING", "QUOTED"}:
        raise HTTPException(409, "Order cannot be quoted now")
    if session.exec(select(PriceLock).where(PriceLock.order_id == order.id)).first():
        raise HTTPException(409, "Price is locked")
    garments = session.exec(select(Garment).where(Garment.order_id == order.id)).all()
    if len(garments) != order.garment_count or any(g.estimate is None for g in garments):
        raise HTTPException(409, "Every garment needs a master estimate")
    percent = markup(body.markup_percent if body.markup_percent is not None else order.markup_percent)
    pickup_offer, return_offer = get_lockable_offers(session, order)
    if body.delivery_quote_mode and body.delivery_quote_mode != pickup_offer.mode:
        raise HTTPException(409, "Delivery mode differs from server offer")
    if body.pickup_delivery_price is not None and money(body.pickup_delivery_price, allow_zero=True) != pickup_offer.quoted_price:
        raise HTTPException(409, "Pickup price differs from server offer")
    if body.return_delivery_price is not None and money(body.return_delivery_price, allow_zero=True) != return_offer.quoted_price:
        raise HTTPException(409, "Return price differs from server offer")
    pickup_price = pickup_offer.quoted_price
    return_price = return_offer.quoted_price
    assert pickup_price is not None and return_price is not None
    quote_time = datetime.now(UTC)
    if body.delivery_quote_reference and body.delivery_quote_reference != pickup_offer.offer_reference:
        raise HTTPException(409, "Delivery quote reference differs from server offer")
    cost = sum((g.estimate for g in garments if g.estimate is not None), Decimal("0.00"))
    order.estimated_cost = money(cost)
    order.markup_percent = percent
    order.quoted_repair_price = customer_price(order.estimated_cost, percent)
    order.quoted_pickup_price = pickup_price
    order.quoted_return_price = return_price
    order.quoted_total = order.quoted_repair_price + pickup_price + return_price
    order.quote_version += 1
    order.quoted_by = user.id
    order.quote_created_at = quote_time
    order.delivery_quote_mode = pickup_offer.mode
    order.delivery_quote_reference = pickup_offer.offer_reference
    session.add(EstimateVersion(order_id=order.id, version_number=order.quote_version,
                                cost=order.estimated_cost, repair_price=order.quoted_repair_price,
                                pickup_delivery_price=pickup_price, return_delivery_price=return_price,
                                customer_total=order.quoted_total, markup_percent=percent,
                                delivery_quote_mode=pickup_offer.mode,
                                delivery_quote_reference=pickup_offer.offer_reference,
                                created_by=user.id))
    if order.status == "ESTIMATING":
        transition(order, "QUOTED")
    record(session, order_id=order.id, actor_id=user.id, event_type="quote.issued", key=key,
           payload={"cost": str(order.estimated_cost), "repair_price": str(order.quoted_repair_price),
                    "pickup_price": str(pickup_price), "return_price": str(return_price),
                    "customer_total": str(order.quoted_total), "markup_percent": str(percent),
                    "quote_version": order.quote_version})
    return order_dict(session, order, detail=True)


@router.post("/admin/orders/{order_id}/dispatch-pickup")
async def dispatch_pickup(order_id: uuid.UUID, body: DispatchIn, session: SessionDep,
                          user: CurrentUser, key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    order = order_for_user(session, order_id, user)
    if replay(session, key, "pickup.requested"):
        return order_dict(session, order, detail=True)
    if order.status != "CONFIRMED":
        raise HTTPException(409, "Customer must confirm quote first")
    if not session.exec(select(PriceLock).where(PriceLock.order_id == order.id)).first():
        raise HTTPException(409, "Price lock missing")
    payment = session.exec(select(Payment).where(Payment.order_id == order.id)).first()
    if not payment or payment.status != "PAID":
        raise HTTPException(409, "Upfront payment has not been confirmed")
    leg = session.exec(select(DeliveryLeg).where(DeliveryLeg.order_id == order.id, DeliveryLeg.sequence == 1)).first()
    if not leg or leg.status != "OFFERED":
        raise HTTPException(409, "Pickup offer is unavailable")
    master = session.get(MasterProfile, order.master_id)
    if not master or not master.address:
        raise HTTPException(409, "Master address is missing")
    lock = session.exec(select(PriceLock).where(PriceLock.order_id == order.id)).first()
    if not lock or body.mode != order.delivery_quote_mode:
        raise HTTPException(409, "Pickup mode differs from locked customer offer")
    if body.quoted_price is not None and money(body.quoted_price, allow_zero=True) != lock.pickup_delivery_price:
        raise HTTPException(409, "Customer delivery price is locked")
    leg.status = "PLANNED"
    leg.handoff_mode = order.pickup_handoff_mode
    leg.requested_at = body.requested_at or order.pickup_requested_at
    session.add(leg)
    transition(order, "PICKUP")
    record(session, order_id=order.id, actor_id=user.id, event_type="pickup.requested", key=key,
           payload={"leg_id": str(leg.id), "mode": leg.mode})
    if leg.mode == "yandex":
        await dispatch_yandex_leg(session, leg)
    return order_dict(session, order, detail=True)


@router.post("/admin/legs/{leg_id}/dispatch")
async def retry_yandex_dispatch(leg_id: uuid.UUID, session: SessionDep,
                                user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    leg = session.get(DeliveryLeg, leg_id)
    if not leg or leg.mode != "yandex" or leg.status not in {"PLANNED", "PROVIDER_PENDING"}:
        raise HTTPException(409, "No pending Yandex leg")
    order = session.get(RepairOrder, leg.order_id)
    payment = session.exec(select(Payment).where(Payment.order_id == leg.order_id)).first()
    if not order or not payment or payment.status != "PAID":
        raise HTTPException(409, "Upfront payment is required")
    if leg.sequence == 2 and order.status != "READY":
        raise HTTPException(409, "Return delivery not confirmed")
    return await dispatch_yandex_leg(session, leg)


@router.get("/admin/finance")
def admin_finance(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    locks = session.exec(select(PriceLock)).all()
    legs = session.exec(select(DeliveryLeg)).all()
    repair = sum((x.repair_price for x in locks), Decimal("0.00"))
    delivery = sum((x.quoted_price for x in legs if x.quoted_price is not None), Decimal("0.00"))
    # Locked prices are commitments, not collected payments.
    return {"revenue_total": "0.00", "repair_revenue": "0.00", "delivery_revenue": "0.00",
            "orders_paid": 0, "repair_price_committed": str(repair),
            "delivery_price_quoted": str(delivery)}


@router.get("/master/jobs")
def master_jobs(session: SessionDep, user: CurrentUser) -> dict:
    profile = master_profile(session, user)
    jobs = session.exec(select(Garment).where(Garment.master_id == profile.id)).all()
    return {"data": [garment_dict(session, g) for g in jobs], "count": len(jobs)}


@router.post("/master/jobs/{garment_id}/estimate")
def master_estimate(garment_id: uuid.UUID, body: EstimateIn, session: SessionDep,
                    user: CurrentUser, key: Idempotency = None) -> dict:
    garment, order = get_master_garment(session, user, garment_id)
    if replay(session, key, "garment.estimated"):
        return garment_dict(session, garment)
    if order.status != "ESTIMATING":
        raise HTTPException(409, "Estimate phase is closed")
    garment.estimate = money(body.amount)
    garment.status = "INSPECTED"
    record(session, order_id=order.id, actor_id=user.id, event_type="garment.estimated", key=key,
           payload={"garment_id": str(garment.id), "amount": str(garment.estimate)})
    return garment_dict(session, garment)


@router.post("/master/jobs/{garment_id}/accept")
def master_accept(garment_id: uuid.UUID, session: SessionDep,
                  user: CurrentUser, key: Idempotency = None) -> dict:
    garment, order = get_master_garment(session, user, garment_id)
    if replay(session, key, "garment.accepted"):
        return garment_dict(session, garment)
    if order.status not in {"ESTIMATING", "IN_WORK"} or garment.status not in {"INSPECTED", "RECEIVED"}:
        raise HTTPException(409, "Job is not available for acceptance")
    garment.status = "INSPECTED" if order.status == "ESTIMATING" else "IN_WORK"
    record(session, order_id=order.id, actor_id=user.id, event_type="garment.accepted", key=key,
           payload={"garment_id": str(garment.id)})
    return garment_dict(session, garment)


@router.post("/master/jobs/{garment_id}/ready")
def master_ready(garment_id: uuid.UUID, session: SessionDep,
                 user: CurrentUser, key: Idempotency = None) -> dict:
    garment, order = get_master_garment(session, user, garment_id)
    if replay(session, key, "garment.ready"):
        return garment_dict(session, garment)
    if order.status not in {"IN_WORK", "QC"} or garment.status != "IN_WORK":
        raise HTTPException(409, "Garment is not in repair")
    after = session.exec(select(GarmentPhoto).where(GarmentPhoto.garment_id == garment.id, GarmentPhoto.kind == "AFTER_MASTER")).first()
    if not after:
        raise HTTPException(409, "Upload an after photo before marking ready")
    garment.status = "READY_FOR_RETURN"
    session.add(garment)
    session.flush()
    jobs = session.exec(select(Garment).where(Garment.order_id == order.id)).all()
    if all(g.status == "READY_FOR_RETURN" for g in jobs):
        if order.status == "IN_WORK":
            transition(order, "QC")
        transition(order, "READY")
    record(session, order_id=order.id, actor_id=user.id, event_type="garment.ready", key=key,
           payload={"garment_id": str(garment.id)})
    return garment_dict(session, garment)


@router.post("/master/jobs/{garment_id}/problem")
def master_problem(garment_id: uuid.UUID, body: ProblemIn, session: SessionDep,
                   user: CurrentUser, key: Idempotency = None) -> dict:
    garment, order = get_master_garment(session, user, garment_id)
    if replay(session, key, "garment.problem"):
        return garment_dict(session, garment)
    if order.status not in {"ESTIMATING", "PICKUP", "IN_WORK", "QC"}:
        raise HTTPException(409, "Cannot report problem in this status")
    garment.status = "UNREPAIRABLE"
    garment.problem_reason = body.reason
    transition(order, "DISPUTE")
    record(session, order_id=order.id, actor_id=user.id, event_type="garment.problem", key=key,
           payload={"garment_id": str(garment.id), "reason": body.reason})
    return garment_dict(session, garment)


@router.post("/garments/{garment_id}/photos")
def upload_garment_photo(garment_id: uuid.UUID, session: SessionDep, user: CurrentUser,
                         file: Annotated[UploadFile, File()],
                         stage: Annotated[Literal["BEFORE_CUSTOMER", "INTAKE", "INSPECTION", "BEFORE_MASTER", "AFTER_MASTER", "QC", "RETURN"], Form()] = "BEFORE_CUSTOMER") -> dict:
    garment = session.get(Garment, garment_id)
    if not garment:
        raise HTTPException(404, "Garment not found")
    order = order_for_user(session, garment.order_id, user)
    role = effective_role(user)
    if role == "master" and (stage not in {"BEFORE_MASTER", "AFTER_MASTER"} or order.status not in {"IN_WORK", "QC"}):
        raise HTTPException(403, "Master can upload after photos during repair")
    if role == "customer" and (stage != "BEFORE_CUSTOMER" or order.status not in {"NEW", "ESTIMATING"}):
        raise HTTPException(403, "Customer can upload before photos during intake")
    if role == "courier":
        raise HTTPException(403, "Courier photos belong to a delivery leg")
    storage_key, content_type = save_photo(file)
    photo = GarmentPhoto(garment_id=garment.id, kind=stage, storage_key=storage_key,
                         content_type=content_type, uploader_id=user.id)
    session.add(photo)
    record(session, order_id=order.id, actor_id=user.id, event_type="garment.photo_added", key=None,
           payload={"garment_id": str(garment.id), "photo_id": str(photo.id), "kind": stage})
    return {"id": str(photo.id), "garment_id": str(garment.id), "kind": stage,
            "created_at": photo.created_at.isoformat()}


@router.get("/garments/photos/{photo_id}")
def read_garment_photo(photo_id: uuid.UUID, session: SessionDep,
                       user: CurrentUser) -> FileResponse:
    photo = session.get(GarmentPhoto, photo_id)
    if not photo or photo.moderation_status == "REJECTED":
        raise HTTPException(404, "Photo not found")
    garment = session.get(Garment, photo.garment_id)
    if not garment:
        raise HTTPException(404, "Photo not found")
    order_for_user(session, garment.order_id, user)
    if photo.moderation_status != "APPROVED" and effective_role(user) not in {"owner", "operator"} and photo.uploader_id != user.id:
        raise HTTPException(404, "Photo is awaiting moderation")
    path = Path(settings.PHOTO_DIR) / photo.storage_key
    if not path.is_file():
        raise HTTPException(404, "Photo file missing")
    return FileResponse(path, media_type=photo.content_type,
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/admin/photos/{photo_id}/moderate")
def moderate_photo(photo_id: uuid.UUID, decision: Literal["APPROVED", "REJECTED"],
                   session: SessionDep, user: CurrentUser,
                   key: Idempotency = None) -> dict:
    require_role(user, "owner", "operator")
    photo = session.get(GarmentPhoto, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")
    if replay(session, key, "photo.moderated"):
        return {"id": str(photo.id), "moderation_status": photo.moderation_status}
    if photo.moderation_status != "PENDING":
        raise HTTPException(409, "Photo was already moderated")
    photo.moderation_status = decision
    garment = session.get(Garment, photo.garment_id)
    record(session, order_id=garment.order_id if garment else None, actor_id=user.id,
           event_type="photo.moderated", key=key,
           payload={"photo_id": str(photo.id), "decision": decision})
    return {"id": str(photo.id), "moderation_status": photo.moderation_status}


@router.post("/admin/photos/{photo_id}/approve")
def approve_photo(photo_id: uuid.UUID, session: SessionDep, user: CurrentUser,
                  key: Idempotency = None) -> dict:
    return moderate_photo(photo_id, "APPROVED", session, user, key)


@router.get("/courier/legs")
def courier_legs(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "courier")
    legs = session.exec(select(DeliveryLeg).where(DeliveryLeg.mode == "partner")).all()
    visible = [x for x in legs if x.courier_id in (None, user.id) and x.status != "DELIVERED"]
    return {"data": [leg_dict(x) for x in visible], "count": len(visible)}


@router.post("/courier/legs/{leg_id}/photo")
def courier_photo(leg_id: uuid.UUID, session: SessionDep, user: CurrentUser,
                  file: Annotated[UploadFile, File()],
                  stage: Annotated[Literal["pickup", "deliver"], Form()]) -> dict:
    leg = get_courier_leg(session, user, leg_id)
    required_status = "PLANNED" if stage == "pickup" else "PICKED_UP"
    if leg.status != required_status:
        raise HTTPException(409, "Photo stage does not match delivery status")
    storage_key, content_type = save_photo(file)
    photo = DeliveryProofPhoto(leg_id=leg.id, stage=stage, storage_key=storage_key,
                               content_type=content_type, uploader_id=user.id)
    session.add(photo)
    record(session, order_id=leg.order_id, actor_id=user.id, event_type="delivery.photo_added", key=None,
           payload={"leg_id": str(leg.id), "photo_id": str(photo.id), "stage": stage})
    return {"id": str(photo.id), "leg_id": str(leg.id), "stage": stage,
            "created_at": photo.created_at.isoformat()}


@router.post("/courier/legs/{leg_id}/pickup")
def courier_pickup(leg_id: uuid.UUID, session: SessionDep, user: CurrentUser,
                   key: Idempotency = None) -> dict:
    leg = get_courier_leg(session, user, leg_id)
    if replay(session, key, "delivery.picked_up"):
        return leg_dict(leg)
    if leg.status != "PLANNED":
        raise HTTPException(409, "Leg is not awaiting pickup")
    proof = session.exec(select(DeliveryProofPhoto).where(DeliveryProofPhoto.leg_id == leg.id,
                           DeliveryProofPhoto.stage == "pickup", DeliveryProofPhoto.uploader_id == user.id)).first()
    if not proof:
        raise HTTPException(409, "Pickup photo is required")
    leg.courier_id = user.id
    leg.status = "PICKED_UP"
    record(session, order_id=leg.order_id, actor_id=user.id, event_type="delivery.picked_up", key=key,
           payload={"leg_id": str(leg.id)})
    return leg_dict(leg)


@router.post("/courier/legs/{leg_id}/deliver")
def courier_deliver(leg_id: uuid.UUID, session: SessionDep, user: CurrentUser,
                    key: Idempotency = None) -> dict:
    leg = get_courier_leg(session, user, leg_id)
    if replay(session, key, "delivery.delivered"):
        return leg_dict(leg)
    if leg.status != "PICKED_UP" or leg.courier_id != user.id:
        raise HTTPException(409, "Leg has not been picked up by this courier")
    proof = session.exec(select(DeliveryProofPhoto).where(DeliveryProofPhoto.leg_id == leg.id,
                           DeliveryProofPhoto.stage == "deliver", DeliveryProofPhoto.uploader_id == user.id)).first()
    if not proof:
        raise HTTPException(409, "Delivery photo is required")
    order = session.get(RepairOrder, leg.order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if leg.sequence == 1:
        transition(order, "IN_WORK")
    elif leg.sequence == 2:
        transition(order, "DELIVERED")
    else:
        raise HTTPException(409, "Invalid delivery leg")
    leg.status = "DELIVERED"
    record(session, order_id=leg.order_id, actor_id=user.id, event_type="delivery.delivered", key=key,
           payload={"leg_id": str(leg.id), "sequence": leg.sequence})
    return leg_dict(leg)


@router.get("/admin/garments")
def admin_garments(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    garments = session.exec(select(Garment).limit(200)).all()
    return {"data": [garment_dict(session, g) for g in garments], "count": len(garments)}


@router.get("/admin/logistics")
def admin_logistics(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    legs = session.exec(select(DeliveryLeg).limit(200)).all()
    return {"data": [leg_dict(leg) for leg in legs], "count": len(legs)}


@router.get("/admin/customers")
def admin_customers(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    customers = session.exec(select(User).where(User.role == "customer").limit(200)).all()
    return {"data": [{"id": str(x.id), "name": x.full_name, "email": x.email} for x in customers],
            "count": len(customers)}


@router.get("/admin/disputes")
def admin_disputes(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    orders = session.exec(select(RepairOrder).where(RepairOrder.status == "DISPUTE")).all()
    return {"data": [order_dict(session, o) for o in orders], "count": len(orders)}


@router.get("/admin/pulse")
def admin_pulse(session: SessionDep, user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    events = session.exec(select(EventLog).order_by(EventLog.created_at.desc()).limit(100)).all()
    return {"data": [{"id": str(e.id), "event_type": e.event_type,
                      "order_id": str(e.order_id) if e.order_id else None,
                      "created_at": e.created_at.isoformat()} for e in events], "count": len(events)}


@router.get("/admin/{section}")
def admin_future_section(section: Literal["settings", "tasks", "system", "api-keys"],
                         user: CurrentUser) -> dict:
    require_role(user, "owner", "operator")
    return {"data": [], "count": 0, "section": section, "status": "not_configured"}
