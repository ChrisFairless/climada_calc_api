from ninja.schema import Schema
from typing import List


class GeocodePlace(Schema):
    """Response data provided in a geocoding query"""
    name: str
    id: str
    scale: str = None   # -> Enum
    country: str = None
    admin1: str = None
    admin2: str = None
    bbox: List[float] = None
    poly: List[dict] = None


class GeocodePlaceList(Schema):
    data: List[GeocodePlace]