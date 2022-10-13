from ninja import Schema, ModelSchema
from typing import List

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.models import Location

conf = ClimadaCalcApiConfig()


class GeocodePlace(ModelSchema):
    """Response data provided in a geocoding query"""
    class Config:
        model = Location
        model_fields = ["name", "id", "scale", "country", "country_id", "admin1", "admin1_id", "admin2",
                        "admin2_id", "bbox", "poly"]


class GeocodePlaceList(Schema):
    data: List[GeocodePlace]
