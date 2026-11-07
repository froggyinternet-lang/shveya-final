"""Critical workflow tests. Run against PostgreSQL after `alembic upgrade head`."""

import uuid
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import Session, select, func

from app.api.deps import get_current_user, get_db
from app.api.routes.repair import (
    OrderIn, GarmentIn, QuoteIn, confirm_quote, create_order, dispatch_pickup,
    issue_quote,
)
from app.core.db import engine
from app.domain import customer_price, markup, money, order_for_user
from app.domain_models import (
    DeliveryLeg, DeliveryTariff, EstimateVersion, EventLog, Garment, GarmentPhoto,
    MasterProfile, Payment, PriceLock, RepairOrder,
)
from app.main import app
from app.models import User
from app.payments import mark_paid
from app.core.config import settings


@pytest.fixture
def session():
    """Never delete audit records: roll back the outer PostgreSQL transaction."""
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            yield db
        transaction.rollback()


def user(session: Session, role: str) -> User:
    account = User(email=f"{uuid.uuid4().hex}@example.test", hashed_password="x",
                   role=role, is_superuser=role == "owner")
    session.add(account)
    session.flush()
    return account


def order_with_garment(session: Session, customer: User) -> tuple[RepairOrder, Garment]:
    order = RepairOrder(customer_id=customer.id, customer_address="Пермь, ул. Ленина, 1",
                        customer_latitude=Decimal("58.000000"),
                        customer_longitude=Decimal("56.000000"), garment_count=1)
    session.add(order)
    session.flush()
    garment = Garment(order_id=order.id, name="Куртка", category="zipper",
                      problem="Заменить молнию")
    session.add(garment)
    session.flush()
    return order, garment


def test_decimal_pricing_and_markup_floor() -> None:
    assert money("100.005") == Decimal("100.01")
    assert customer_price(Decimal("600.00"), Decimal("30")) == Decimal("780.00")
    with pytest.raises(HTTPException) as exc:
        markup(Decimal("29.99"))
    assert exc.value.status_code == 422


def test_third_delivery_leg_rejected_by_postgres(session: Session) -> None:
    customer = user(session, "customer")
    order, _ = order_with_garment(session, customer)
    for sequence in (1, 2):
        session.add(DeliveryLeg(order_id=order.id, sequence=sequence,
                                origin_address="A", destination_address="B"))
    session.flush()
    session.add(DeliveryLeg(order_id=order.id, sequence=3,
                            origin_address="A", destination_address="B"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_price_lock_cannot_update_in_postgres(session: Session) -> None:
    customer = user(session, "customer")
    owner = user(session, "owner")
    order, _ = order_with_garment(session, customer)
    version = EstimateVersion(order_id=order.id, version_number=1,
                              cost=Decimal("600"), repair_price=Decimal("780"),
                              pickup_delivery_price=Decimal("100"),
                              return_delivery_price=Decimal("100"),
                              customer_total=Decimal("980"), markup_percent=Decimal("30"),
                              delivery_quote_mode="partner", created_by=owner.id)
    session.add(version)
    session.flush()
    lock = PriceLock(order_id=order.id, estimate_version_id=version.id,
                     cost=version.cost, repair_price=version.repair_price,
                     pickup_delivery_price=version.pickup_delivery_price,
                     return_delivery_price=version.return_delivery_price,
                     customer_total=version.customer_total,
                     markup_percent=version.markup_percent, confirmed_by=customer.id)
    session.add(lock)
    session.flush()
    with pytest.raises(DBAPIError):
        session.execute(text("UPDATE price_lock SET customer_total=1 WHERE id=:id"), {"id": lock.id})


def test_duplicate_event_key_rejected_by_postgres(session: Session) -> None:
    key = f"test:{uuid.uuid4()}"
    session.add(EventLog(event_type="test", idempotency_key=key))
    session.flush()
    session.add(EventLog(event_type="test", idempotency_key=key))
    with pytest.raises(IntegrityError):
        session.flush()


def test_rbac_scopes_order_and_admin_route(session: Session) -> None:
    customer = user(session, "customer")
    other = user(session, "customer")
    order, _ = order_with_garment(session, customer)
    with pytest.raises(HTTPException) as exc:
        order_for_user(session, order.id, other)
    assert exc.value.status_code == 404
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: other
    try:
        with TestClient(app) as client:
            assert client.get("/api/admin/orders").status_code == 403
            response = client.get("/api/app/orders")
            assert response.status_code == 200
            assert response.json()["data"] == []
    finally:
        app.dependency_overrides.clear()


def test_photo_route_scopes_owner_master_and_customer(session: Session, tmp_path) -> None:
    owner = user(session, "owner")
    customer = user(session, "customer")
    other = user(session, "customer")
    master_user = user(session, "master")
    master = MasterProfile(user_id=master_user.id, skills=["zipper"])
    session.add(master)
    session.flush()
    order, garment = order_with_garment(session, customer)
    order.master_id = master.id
    garment.master_id = master.id
    photo = GarmentPhoto(garment_id=garment.id, kind="BEFORE_CUSTOMER",
                         storage_key="test.jpg", content_type="image/jpeg",
                         uploader_id=customer.id, moderation_status="PENDING")
    session.add(photo)
    session.flush()
    (tmp_path / "test.jpg").write_bytes(b"\xff\xd8\xff")
    original = settings.PHOTO_DIR
    settings.PHOTO_DIR = str(tmp_path)
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            for principal, expected in ((other, 404), (master_user, 404),
                                        (customer, 200), (owner, 200)):
                def override_user():
                    return principal
                app.dependency_overrides[get_current_user] = override_user
                assert client.get(f"/api/garments/photos/{photo.id}").status_code == expected
    finally:
        app.dependency_overrides.clear()
        settings.PHOTO_DIR = original


def test_single_upfront_lock_and_payment_idempotency(session: Session) -> None:
    owner = user(session, "owner")
    customer = user(session, "customer")
    master_user = user(session, "master")
    master = MasterProfile(user_id=master_user.id, zone="Мотовилиха",
                           address="Пермь, ул. Крупской, 2", latitude=Decimal("58.01"),
                           longitude=Decimal("56.01"), skills=["zipper"])
    session.add(master)
    session.flush()
    order, garment = order_with_garment(session, customer)
    order.master_id = master.id
    order.status = "ESTIMATING"
    garment.master_id = master.id
    garment.estimate = Decimal("600.00")
    session.add(DeliveryTariff(zone="Мотовилиха", pickup_price=Decimal("100"),
                               return_price=Decimal("100"), updated_by=owner.id))
    session.flush()
    from app.delivery_offers import save_offers
    save_offers(session, order, mode="partner", pickup_price=Decimal("999"),
                return_price=Decimal("999"))
    offer = issue_quote(order.id, QuoteIn(markup_percent=Decimal("30")), session, owner)
    assert offer["customer_total"] == "980.00"
    confirmed = confirm_quote(order.id, session, customer, key="confirm-1")
    assert confirmed["payment"]["amount"] == "980.00"
    assert confirm_quote(order.id, session, customer, key="confirm-1")["price_lock"]["customer_total"] == "980.00"
    with pytest.raises(HTTPException) as exc:
        issue_quote(order.id, QuoteIn(markup_percent=Decimal("50")), session, owner)
    assert exc.value.status_code == 409
    from app.api.routes.repair import DispatchIn
    with pytest.raises(HTTPException) as exc:
        asyncio.run(dispatch_pickup(order.id, DispatchIn(mode="partner"), session, owner))
    assert exc.value.status_code == 409
    payment_record = session.exec(select(Payment).where(Payment.order_id == order.id)).one()
    payment_record.external_payment_id = "pay-test-1"  # simulated verified create response
    session.add(payment_record)
    session.commit()
    paid = mark_paid(session, order_id=order.id, external_payment_id="pay-test-1",
                     amount=Decimal("980.00"), currency="RUB", event_id="event-test-1")
    assert paid.status == "PAID"
    assert mark_paid(session, order_id=order.id, external_payment_id="pay-test-1",
                     amount=Decimal("980.00"), currency="RUB", event_id="event-test-1").id == paid.id
    dispatch = asyncio.run(dispatch_pickup(order.id, DispatchIn(mode="partner"), session, owner))
    assert dispatch["delivery_legs"][0]["status"] == "PLANNED"


def test_order_creation_replay(session: Session) -> None:
    customer = user(session, "customer")
    payload = OrderIn(address="Пермь, ул. Ленина, 1",
                      garments=[GarmentIn(name="Брюки", problem="Подшить")])
    first = create_order(payload, session, customer, key="create-test-1")
    second = create_order(payload, session, customer, key="create-test-1")
    assert first["id"] == second["id"]
    assert session.exec(select(func.count()).select_from(RepairOrder).where(
        RepairOrder.customer_id == customer.id)).one() == 1
