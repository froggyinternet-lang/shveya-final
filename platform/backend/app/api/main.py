from fastapi import APIRouter

from app.api.routes import delivery_offers, integrations, items, login, private, repair, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(repair.router)
api_router.include_router(delivery_offers.router)
api_router.include_router(integrations.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
