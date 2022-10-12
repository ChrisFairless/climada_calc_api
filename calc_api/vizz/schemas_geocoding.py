from ninja import Schema
from typing import List

from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()


class GeocodePlace(Schema):
    """Response data provided in a geocoding query"""
    name: str
    # TODO decide what the ID is for and use it consistently
    id: str
    scale: str = None   # -> Enum
    country: str = None
    country_id: str = None
    admin1: str = None
    admin1_id: str = None
    admin2: str = None
    admin2_id: str = None
    bbox: List[List[float]] = None
    poly: List[List[float]] = None


class GeocodePlaceList(Schema):
    data: List[GeocodePlace]
