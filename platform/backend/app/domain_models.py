"""Repair-domain persistence. Money is NUMERIC; photos belong to garments."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, JSON, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


def money_field(default: Decimal | None = None):
    return Field(default=default, sa_type=Numeric(12, 2))


class MasterProfile(SQLModel, table=True):
    __tablename__ = "master_profile"
    __table_args__ = (CheckConstraint("markup_percent >= 30", name="master_markup_minimum"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", unique=True, index=True)
    phone: str | None = Field(default=None, max_length=32)
    contact_email: str | None = Field(default=None, max_length=255)
    zone: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=500)
    latitude: Decimal | None = Field(default=None, sa_type=Numeric(9, 6))
    longitude: Decimal | None = Field(default=None, sa_type=Numeric(9, 6))
    skills: list[str] = Field(default_factory=list, sa_type=JSON)
    markup_percent: Decimal = Field(default=Decimal("30.00"), sa_type=Numeric(6, 2))
    is_available: bool = True
    capacity: int = Field(default=5)
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class RepairOrder(SQLModel, table=True):
    __tablename__ = "repair_order"
    __table_args__ = (
        CheckConstraint("markup_percent >= 30", name="order_markup_minimum"),
        CheckConstraint("garment_count BETWEEN 1 AND 10", name="order_garment_count"),
        Index("ix_repair_order_customer_status", "customer_id", "status"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    customer_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    master_id: uuid.UUID | None = Field(default=None, foreign_key="master_profile.id", index=True)
    status: str = Field(default="NEW", max_length=24, index=True)
    description: str = Field(default="", max_length=4000)
    customer_address: str = Field(max_length=500)
    customer_latitude: Decimal | None = Field(default=None, sa_type=Numeric(9, 6))
    customer_longitude: Decimal | None = Field(default=None, sa_type=Numeric(9, 6))
    garment_count: int = Field(default=1)
    markup_percent: Decimal = Field(default=Decimal("30.00"), sa_type=Numeric(6, 2))
    estimated_cost: Decimal | None = money_field()
    quoted_repair_price: Decimal | None = money_field()
    quoted_pickup_price: Decimal | None = money_field()
    quoted_return_price: Decimal | None = money_field()
    quoted_total: Decimal | None = money_field()
    quote_version: int = 0
    quoted_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    quote_created_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    delivery_quote_mode: str | None = Field(default=None, max_length=16)
    delivery_quote_reference: str | None = Field(default=None, max_length=4096)
    pickup_handoff_mode: str = Field(default="entrance", max_length=16)
    pickup_requested_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    currency: str = Field(default="RUB", max_length=3)
    intake_channel: str = Field(default="web", max_length=24)
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class Garment(SQLModel, table=True):
    __tablename__ = "garment"
    __table_args__ = (Index("ix_garment_order_master", "order_id", "master_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    qr_code: str = Field(default_factory=lambda: f"SHV-{uuid.uuid4().hex.upper()}", unique=True, max_length=40)
    order_id: uuid.UUID = Field(foreign_key="repair_order.id", index=True)
    master_id: uuid.UUID | None = Field(default=None, foreign_key="master_profile.id", index=True)
    name: str = Field(max_length=200)
    category: str | None = Field(default=None, max_length=100)
    problem: str = Field(max_length=2000)
    declared_value: Decimal | None = money_field()
    completeness: str | None = Field(default=None, max_length=1000)
    material: str | None = Field(default=None, max_length=200)
    status: str = Field(default="RECEIVED", max_length=24)
    estimate: Decimal | None = money_field()
    problem_reason: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class GarmentPhoto(SQLModel, table=True):
    __tablename__ = "garment_photo"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    garment_id: uuid.UUID = Field(foreign_key="garment.id", index=True)
    kind: str = Field(max_length=24)
    storage_key: str = Field(max_length=500, unique=True)
    content_type: str = Field(max_length=100)
    moderation_status: str = Field(default="PENDING", max_length=16)
    uploader_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class DeliveryLeg(SQLModel, table=True):
    __tablename__ = "delivery_leg"
    __table_args__ = (
        CheckConstraint("sequence IN (1, 2)", name="delivery_leg_sequence"),
        UniqueConstraint("order_id", "sequence", name="uq_delivery_order_sequence"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="repair_order.id", index=True)
    sequence: int
    mode: str = Field(default="partner", max_length=16)
    status: str = Field(default="PLANNED", max_length=24)
    origin_address: str = Field(max_length=500)
    destination_address: str = Field(max_length=500)
    quoted_price: Decimal | None = money_field()
    actual_cost: Decimal | None = money_field()
    variance: Decimal | None = money_field()
    provider: str | None = Field(default=None, max_length=32)
    offer_reference: str | None = Field(default=None, max_length=4096)
    quote_expires_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    indicative: bool = False
    handoff_mode: str = Field(default="entrance", max_length=16)
    requested_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    external_request_id: str | None = Field(default=None, max_length=120, unique=True)
    external_claim_id: str | None = Field(default=None, max_length=160, unique=True)
    provider_status: str | None = Field(default=None, max_length=80)
    expected_gross: Decimal | None = money_field()
    expected_net: Decimal | None = money_field()
    courier_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class DeliveryTariff(SQLModel, table=True):
    __tablename__ = "delivery_tariff"
    __table_args__ = (UniqueConstraint("zone", name="uq_delivery_tariff_zone"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    zone: str = Field(max_length=120)
    pickup_price: Decimal = money_field(Decimal("0.00"))
    return_price: Decimal = money_field(Decimal("0.00"))
    active: bool = True
    allow_free: bool = False
    updated_by: uuid.UUID = Field(foreign_key="user.id")
    updated_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class DeliveryProofPhoto(SQLModel, table=True):
    __tablename__ = "delivery_proof_photo"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    leg_id: uuid.UUID = Field(foreign_key="delivery_leg.id", index=True)
    stage: str = Field(max_length=16)
    storage_key: str = Field(max_length=500, unique=True)
    content_type: str = Field(max_length=100)
    uploader_id: uuid.UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class PriceLock(SQLModel, table=True):
    """Final repair price captured once at customer confirmation."""

    __tablename__ = "price_lock"
    __table_args__ = (CheckConstraint("markup_percent >= 30", name="price_lock_markup_minimum"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="repair_order.id", unique=True, index=True)
    estimate_version_id: uuid.UUID = Field(foreign_key="estimate_version.id")
    cost: Decimal = money_field(Decimal("0.00"))
    repair_price: Decimal = money_field(Decimal("0.00"))
    pickup_delivery_price: Decimal = money_field(Decimal("0.00"))
    return_delivery_price: Decimal = money_field(Decimal("0.00"))
    customer_total: Decimal = money_field(Decimal("0.00"))
    markup_percent: Decimal = Field(sa_type=Numeric(6, 2))
    confirmed_by: uuid.UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class EstimateVersion(SQLModel, table=True):
    """Append-only customer offer. Superseded versions remain auditable."""

    __tablename__ = "estimate_version"
    __table_args__ = (UniqueConstraint("order_id", "version_number", name="uq_estimate_order_version"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="repair_order.id", index=True)
    version_number: int
    cost: Decimal = money_field(Decimal("0.00"))
    repair_price: Decimal = money_field(Decimal("0.00"))
    pickup_delivery_price: Decimal = money_field(Decimal("0.00"))
    return_delivery_price: Decimal = money_field(Decimal("0.00"))
    customer_total: Decimal = money_field(Decimal("0.00"))
    markup_percent: Decimal = Field(sa_type=Numeric(6, 2))
    delivery_quote_mode: str = Field(max_length=16)
    delivery_quote_reference: str | None = Field(default=None, max_length=4096)
    created_by: uuid.UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class Payment(SQLModel, table=True):
    __tablename__ = "payment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="repair_order.id", unique=True, index=True)
    price_lock_id: uuid.UUID = Field(foreign_key="price_lock.id", unique=True)
    amount: Decimal = money_field(Decimal("0.00"))
    status: str = Field(default="PENDING", max_length=24)
    provider: str = Field(default="yookassa", max_length=24)
    external_payment_id: str | None = Field(default=None, max_length=160, unique=True)
    confirmation_url: str | None = Field(default=None, max_length=2048)
    operator_id: uuid.UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    paid_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class EventLog(SQLModel, table=True):
    """Append-only audit/outbox event, globally deduplicated by idempotency key."""

    __tablename__ = "event_log"
    __table_args__ = (Index("ix_event_order_time", "order_id", "created_at"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID | None = Field(default=None, foreign_key="repair_order.id", index=True)
    actor_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    event_type: str = Field(max_length=80)
    idempotency_key: str = Field(max_length=160, unique=True, index=True)
    payload: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class ChannelIdentity(SQLModel, table=True):
    __tablename__ = "channel_identity"
    __table_args__ = (UniqueConstraint("channel", "external_user_id", name="uq_channel_identity"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    channel: str = Field(max_length=24)
    external_user_id: str = Field(max_length=160)
    chat_id: str | None = Field(default=None, max_length=160)
    active_garment_id: uuid.UUID | None = Field(default=None, foreign_key="garment.id")
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))


class MasterLinkCode(SQLModel, table=True):
    __tablename__ = "master_link_code"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    master_user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    code_hash: str = Field(max_length=64, unique=True)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    used_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class IntakeDraft(SQLModel, table=True):
    __tablename__ = "intake_draft"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    identity_id: uuid.UUID = Field(foreign_key="channel_identity.id", unique=True)
    text: str = Field(default="", max_length=4000)
    address: str | None = Field(default=None, max_length=500)
    latitude: Decimal | None = Field(default=None, sa_type=Numeric(9, 6))
    longitude: Decimal | None = Field(default=None, sa_type=Numeric(9, 6))
    photo_files: list[dict] = Field(default_factory=list, sa_type=JSON)
    media_refs: list[dict] = Field(default_factory=list, sa_type=JSON)
    status: str = Field(default="NEEDS_ADDRESS", max_length=24)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
