from ninja import Schema, ModelSchema
from typing import List
from shapely import wkt

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.models import Location
from calc_api.calc_methods import util

conf = ClimadaCalcApiConfig()


class GeocodePlace(ModelSchema):
    """Response data provided in a geocoding query"""
    class Config:
        model = Location
        model_fields = ["name", "id", "scale", "country", "country_id", "admin1", "admin1_id", "admin2",
                        "admin2_id", "poly"]

    # Note that this overrides the database versions of these parameters, which are well-known text strings
    bbox: List[float] = None

    @classmethod
    def from_location_model(cls, loc: Location):
        bbox = wkt.loads(loc.bbox).bounds if loc.bbox else None
        loc.bbox = None
        loc = cls().from_orm(loc)
        loc.bbox = bbox
        return loc

    def to_location_model(self):
        loc_dict = self.dict()
        if self.bbox:
            loc_dict['bbox'] = util.bbox_to_wkt(self.bbox)
        return Location(**loc_dict)


class GeocodePlaceList(Schema):
    data: List[GeocodePlace]
