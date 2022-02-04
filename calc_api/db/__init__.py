from typing import Dict, List
from urllib.parse import quote
from django.db import connection

from django.utils import timezone
from ninja import Schema
from typing import List

from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()

from enum import Enum

class HazardTypeEnum(str, Enum):
    tropical_cyclone = "tropical cyclone"
    extreme_heat = "extreme heat"


class MapHazardClimateRequest(Schema):
    hazard_type: HazardTypeEnum
    scenario_name: str = conf.DEFAULT_SCENARIO_NAME
    scenario_year: int = conf.DEFAULT_SCENARIO_YEAR
    scenario_rp: float = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_level: str = None
    aggregation_method: str = None


class MapHazardEventRequest(Schema):
    hazard_type: HazardTypeEnum
    hazard_event_name: str
    scenario_name: str = conf.DEFAULT_SCENARIO_NAME
    scenario_year: int = conf.DEFAULT_SCENARIO_YEAR
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None


class MapExposureRequest(Schema):
    exposure_type: HazardTypeEnum
    scenario_name: str = conf.DEFAULT_SCENARIO_NAME
    scenario_year: int = conf.DEFAULT_SCENARIO_YEAR
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None


class MapImpactClimateRequest(Schema):
    hazard_type: HazardTypeEnum
    exposure_type: str
    scenario_name: str = conf.DEFAULT_SCENARIO_NAME
    scenario_year: int = conf.DEFAULT_SCENARIO_YEAR
    scenario_rp: float = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None


class MapImpactEventRequest(Schema):
    hazard_type: HazardTypeEnum
    hazard_event_name: str
    exposure_type: str
    scenario_name: str = conf.DEFAULT_SCENARIO_NAME
    scenario_year: int = conf.DEFAULT_SCENARIO_YEAR
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None


class MapEntry(Schema):
    #TODO is the best way to encode this info?
    lat: float    # of floats
    lon: float    # of floats
    geom: str = None  # of WKB/WKT geometries (tbd)
    value: float  # of floats
    color: str


class MapMetadata(Schema):
    description: str
    units: str
    legend: List[float]
    legend_colors: List[str]
    custom_fields: dict = None


class MapResponse(Schema):
    data: List[MapEntry]
    metadata: MapMetadata


class ExceedanceHazardRequest(Schema):
    hazard_type: str
    hazard_event_name: str
    scenario_name: str
    scenario_year: int
    location_scale: str
    location_code: str
    location_poly: str
    aggregation_scale: str
    aggregation_method: str


class ExceedanceImpactRequest(Schema):
    hazard_type: str
    hazard_event_name: str
    exposure_type: str
    scenario_name: str
    scenario_year: int
    location_scale: str
    location_code: str
    location_poly: str
    aggregation_scale: str
    aggregation_method: str


class ExceedanceCurveData(Schema):
    return_period: List[float]
    intensity: List[float]
    return_period_units: str
    intensity_units: str


class ExceedanceResponse(Schema):
    data: ExceedanceCurveData
    metadata: dict       # we'll expand this later...


class GeocodeAutocompleteResponse(Schema):
    data: List[str]


class FileSchema(Schema):
    file_name: str
    file_format: str = None
    file_size: int = None
    check_sum: str = None
    url: str

