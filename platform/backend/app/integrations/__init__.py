"""Optional external integrations. No adapter mutates application state."""

from .delivery import DeliveryResult, PartnerDelivery, YandexDelivery
from .delivery_dispatch import ClaimProgress, DispatchResult, dispatch_leg, final_cost, resume_claim
from .geocoder import GeocodeResult, YandexGeocoder
from .max_messenger import MaxBot
from .master_notifications import AssignmentNotification, notify_assignment
from .messaging import IncomingMessage, MediaRef, Position
from .speechkit import SpeechKit
from .telegram import TelegramBot
from .vk import VKBot
from .yookassa import YooKassa

__all__ = [
    "DeliveryResult",
    "ClaimProgress",
    "DispatchResult",
    "GeocodeResult",
    "IncomingMessage",
    "MaxBot",
    "AssignmentNotification",
    "MediaRef",
    "PartnerDelivery",
    "Position",
    "SpeechKit",
    "TelegramBot",
    "VKBot",
    "YandexDelivery",
    "YandexGeocoder",
    "YooKassa",
    "dispatch_leg",
    "final_cost",
    "resume_claim",
    "notify_assignment",
]
