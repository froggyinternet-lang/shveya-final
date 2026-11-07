"""Normalized channel intake. Webhook routes must authenticate providers first."""

import secrets
import uuid
import re
import hashlib
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.routes.repair import (
    EstimateIn, eligible_masters, master_accept, master_estimate, master_ready,
    save_photo_bytes,
)
from app.core.security import get_password_hash
from app.domain import record, replay
from app.domain_models import ChannelIdentity, Garment, GarmentPhoto, IntakeDraft, MasterLinkCode, RepairOrder
from app.models import User


def _position(incoming: object) -> tuple[Decimal | None, Decimal | None]:
    position = getattr(incoming, "position", None)
    if isinstance(position, dict):
        lat = position.get("latitude", position.get("lat"))
        lon = position.get("longitude", position.get("lon"))
    elif isinstance(position, (tuple, list)) and len(position) == 2:
        lat, lon = position
    else:
        lat = getattr(position, "latitude", None)
        lon = getattr(position, "longitude", None)
    if lat is None or lon is None:
        return None, None
    latitude, longitude = Decimal(str(lat)), Decimal(str(lon))
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(422, "Invalid location coordinates")
    return latitude, longitude


def ingest_message(
    session: Session,
    incoming: object,
    *,
    photos: list[tuple[bytes, str]] | None = None,
) -> dict:
    """Persist a verified message and create an order only after explicit location/photo.

    `incoming` is the adapter's IncomingMessage. No location is inferred from IP.
    """
    channel = str(getattr(incoming, "channel", ""))
    external_user_id = str(getattr(incoming, "sender_id", ""))
    event_id = str(getattr(incoming, "event_id", ""))
    if channel not in {"telegram", "vk", "max"} or not external_user_id or not event_id:
        raise HTTPException(422, "Invalid normalized channel event")
    key = f"intake:{channel}:{event_id}"
    if len(key) > 160:
        raise HTTPException(422, "Event identifier too long")
    previous = replay(session, key, "intake.received")
    if previous:
        return {**previous.payload, "replayed": True}
    if getattr(incoming, "callback_data", None):
        # Callback actions need a verified channel-to-user binding and are handled
        # separately; never interpret arbitrary text as an authorized button.
        return {"status": "needs_link", "reason": "callback_requires_verified_identity"}
    identity = session.exec(select(ChannelIdentity).where(
        ChannelIdentity.channel == channel,
        ChannelIdentity.external_user_id == external_user_id)).first()
    if not identity:
        uid = uuid.uuid4()
        user = User(id=uid, email=f"customer-{uid.hex}@internal.shveyamozg.local",
                    role="customer", hashed_password=get_password_hash(secrets.token_urlsafe(32)))
        identity = ChannelIdentity(user_id=uid, channel=channel,
                                   external_user_id=external_user_id,
                                   chat_id=str(getattr(incoming, "chat_id", "")))
        session.add(user)
        session.add(identity)
        session.flush()
    draft = session.exec(select(IntakeDraft).where(IntakeDraft.identity_id == identity.id)).first()
    if not draft:
        draft = IntakeDraft(identity_id=identity.id)
    elif draft.status == "CREATED":
        draft.text = ""
        draft.address = None
        draft.latitude = None
        draft.longitude = None
        draft.photo_files = []
        draft.media_refs = []
    text = str(getattr(incoming, "text", "") or "").strip()
    explicit_address = re.match(r"^(?:адрес\s*[:：]|/address\s+)(.+)$", text, re.IGNORECASE | re.DOTALL)
    if explicit_address:
        candidate = explicit_address.group(1).strip()
        if len(candidate) >= 5:
            draft.address = candidate[:500]
    elif text:
        draft.text = text[:4000]
    raw = getattr(incoming, "raw", None)
    address = raw.get("address") if isinstance(raw, dict) else None
    if isinstance(address, str) and len(address.strip()) >= 5:
        draft.address = address.strip()[:500]
    latitude, longitude = _position(incoming)
    if latitude is not None and longitude is not None:
        draft.latitude, draft.longitude = latitude, longitude
    stored = list(draft.photo_files)
    for blob, mime_type in photos or []:
        storage_key, content_type = save_photo_bytes(blob, mime_type)
        stored.append({"storage_key": storage_key, "content_type": content_type})
    draft.photo_files = stored
    refs = list(draft.media_refs)
    for media in getattr(incoming, "media", []) or []:
        reference = getattr(media, "reference", None)
        if reference:
            refs.append({"kind": str(getattr(media, "kind", "photo")),
                         "reference": str(reference)[:1000],
                         "mime_type": str(getattr(media, "mime_type", ""))[:100]})
    draft.media_refs = refs
    draft.updated_at = datetime.now(UTC)
    result: dict = {"status": "needs_address", "customer_id": str(identity.user_id)}
    if draft.address and draft.latitude is not None and draft.longitude is not None:
        if not draft.photo_files:
            draft.status = "NEEDS_PHOTO_TRANSFER"
            result["status"] = "needs_photo_transfer"
        elif not draft.text:
            draft.status = "NEEDS_DESCRIPTION"
            result["status"] = "needs_description"
        else:
            order = RepairOrder(customer_id=identity.user_id,
                                customer_address=draft.address,
                                customer_latitude=draft.latitude,
                                customer_longitude=draft.longitude,
                                description=draft.text, garment_count=1,
                                intake_channel=channel)
            session.add(order)
            session.flush()
            garment = Garment(order_id=order.id, name="Вещь клиента",
                              category="general", problem=draft.text)
            session.add(garment)
            session.flush()
            candidates = eligible_masters(session, order)
            if candidates:
                master = candidates[0][0]
                order.master_id = master.id
                order.markup_percent = master.markup_percent
                order.status = "ESTIMATING"
                garment.master_id = master.id
            for photo in draft.photo_files:
                session.add(GarmentPhoto(garment_id=garment.id, kind="BEFORE_CUSTOMER",
                                         storage_key=photo["storage_key"],
                                         content_type=photo["content_type"],
                                         uploader_id=identity.user_id))
            draft.photo_files = []
            draft.status = "CREATED"
            result = {"status": "created", "order_id": str(order.id),
                      "garment_ids": [str(garment.id)],
                      "garment_id": str(garment.id),
                      "customer_id": str(identity.user_id),
                      "assignment_status": "assigned" if candidates else "needs_master",
                      "master_id": str(order.master_id) if order.master_id else None}
    else:
        draft.status = "NEEDS_ADDRESS"
    session.add(draft)
    record(session, order_id=uuid.UUID(result["order_id"]) if result.get("order_id") else None,
           actor_id=identity.user_id, event_type="intake.received", key=key, payload=result)
    return result


def handle_master_message(
    session: Session,
    incoming: object,
    *,
    photos: list[tuple[bytes, str]] | None = None,
) -> dict | None:
    """Telegram master link, estimate, and three-button workflow."""
    if str(getattr(incoming, "channel", "")) != "telegram":
        return None
    sender = str(getattr(incoming, "sender_id", ""))
    event_id = str(getattr(incoming, "event_id", ""))
    text = str(getattr(incoming, "text", "") or "").strip()
    link_match = re.fullmatch(r"/link\s+([A-Za-z0-9_-]{16,80})", text)
    if link_match:
        identity = session.exec(select(ChannelIdentity).where(
            ChannelIdentity.channel == "telegram",
            ChannelIdentity.external_user_id == sender)).first()
        if identity:
            return {"status": "already_linked"}
        digest = hashlib.sha256(link_match.group(1).encode()).hexdigest()
        link = session.exec(select(MasterLinkCode).where(MasterLinkCode.code_hash == digest).with_for_update()).first()
        if not link or link.used_at or link.expires_at <= datetime.now(UTC):
            return {"status": "invalid_link"}
        master = session.get(User, link.master_user_id)
        if not master or master.role != "master":
            return {"status": "invalid_link"}
        identity = ChannelIdentity(user_id=master.id, channel="telegram",
                                   external_user_id=sender,
                                   chat_id=str(getattr(incoming, "chat_id", sender)))
        link.used_at = datetime.now(UTC)
        session.add(identity)
        record(session, order_id=None, actor_id=master.id,
               event_type="master.linked", key=f"master:link:{event_id}",
               payload={"identity_id": str(identity.id)})
        return {"status": "master_linked", "master_user_id": str(master.id)}
    identity = session.exec(select(ChannelIdentity).where(
        ChannelIdentity.channel == "telegram",
        ChannelIdentity.external_user_id == sender)).first()
    if not identity:
        return None
    master = session.get(User, identity.user_id)
    if not master or master.role != "master":
        return None
    callback = str(getattr(incoming, "callback_data", "") or "")
    if callback.startswith("master:"):
        parts = callback.split(":")
        if len(parts) != 3 or parts[1] not in {"accept", "ready"}:
            return {"status": "unsupported_master_action"}
        try:
            garment_id = uuid.UUID(parts[2])
        except ValueError:
            return {"status": "invalid_job"}
        key = f"master:telegram:{event_id}"
        if parts[1] == "accept":
            result = master_accept(garment_id, session, master, key=key)
            identity.active_garment_id = garment_id
            session.add(identity)
            session.commit()
            return {"status": "accepted", "garment": result}
        result = master_ready(garment_id, session, master, key=key)
        return {"status": "ready", "garment": result}
    if not identity.active_garment_id:
        return {"status": "needs_job_selection"}
    garment = session.get(Garment, identity.active_garment_id)
    if not garment or garment.master_id is None:
        return {"status": "needs_job_selection"}
    order = session.get(RepairOrder, garment.order_id)
    if not order:
        return {"status": "invalid_job"}
    amount_match = re.fullmatch(r"(?:цена\s*[:：]?\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:₽|руб\.?)?", text, re.IGNORECASE)
    if amount_match and order.status == "ESTIMATING":
        amount = Decimal(amount_match.group(1).replace(",", "."))
        result = master_estimate(garment.id, EstimateIn(amount=amount), session, master,
                                 key=f"master:telegram:{event_id}")
        return {"status": "estimated", "garment": result}
    if photos and order.status == "IN_WORK":
        prior = replay(session, f"master:telegram:{event_id}", "garment.after_photo_added")
        if prior:
            return {"status": "after_photo_saved", "garment_id": str(garment.id), "replayed": True}
        for blob, mime_type in photos:
            storage_key, content_type = save_photo_bytes(blob, mime_type)
            session.add(GarmentPhoto(garment_id=garment.id, kind="AFTER_MASTER",
                                     storage_key=storage_key, content_type=content_type,
                                     uploader_id=master.id))
        record(session, order_id=order.id, actor_id=master.id,
               event_type="garment.after_photo_added", key=f"master:telegram:{event_id}",
               payload={"garment_id": str(garment.id), "count": len(photos)})
        return {"status": "after_photo_saved", "garment_id": str(garment.id)}
    return {"status": "master_message_unrecognized"}
