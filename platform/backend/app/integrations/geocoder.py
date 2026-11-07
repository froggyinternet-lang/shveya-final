"""Yandex Maps HTTP Geocoder for addresses explicitly supplied by users.

https://yandex.ru/maps-api/docs/geocoder-api/request.html
Requires a Maps API Geocoder product key and applicable commercial terms.
Results are not persisted by this adapter; license terms govern any caching.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from .messaging import IntegrationError, Position, request_json


@dataclass(frozen=True)
class GeocodeResult:
    position: Position
    formatted_address: str
    precision: str
    kind: str

    @property
    def exact_house(self) -> bool:
        return self.precision == "exact" and self.kind == "house"


class YandexGeocoder:
    API = "https://geocode-maps.yandex.ru/v1/"

    def __init__(self, client: httpx.AsyncClient, *, api_key: str | None = None) -> None:
        self.client = client
        self.api_key = api_key or os.getenv("YANDEX_GEOCODER_KEY")

    async def geocode(self, address: str) -> GeocodeResult | None:
        if not self.api_key:
            raise IntegrationError("yandex_geocoder", "configuration")
        if len(address.strip()) < 5:
            raise ValueError("explicit street address is required")
        response = await request_json(
            self.client, "yandex_geocoder", "geocode", "GET", self.API,
            params={"apikey": self.api_key, "geocode": address, "lang": "ru_RU", "format": "json", "results": 1},
            timeout=10,
        )
        try:
            members = response["response"]["GeoObjectCollection"]["featureMember"]
            geo = members[0]["GeoObject"]
            metadata = geo["metaDataProperty"]["GeocoderMetaData"]
            longitude_text, latitude_text = geo["Point"]["pos"].split()
            longitude, latitude = float(longitude_text), float(latitude_text)
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                raise ValueError("coordinates out of range")
            address_data = metadata.get("Address") or {}
            if address_data.get("country_code") not in (None, "RU"):
                return None
            return GeocodeResult(
                position=Position(latitude, longitude),
                formatted_address=str(address_data.get("formatted") or metadata.get("text") or ""),
                precision=str(metadata.get("precision") or ""),
                kind=str(metadata.get("kind") or ""),
            )
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            return None

    async def geocode_house(self, address: str) -> GeocodeResult | None:
        result = await self.geocode(address)
        return result if result and result.exact_house else None
