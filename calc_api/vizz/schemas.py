from django.utils import timezone
from ninja import Schema, ModelSchema
from typing import List
from enum import Enum

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.models import Job

conf = ClimadaCalcApiConfig()

job_fields = ["job_id", "location", "status", "request", "submitted_at",
              "completed_at", "runtime", "response_uri", "code", "message"]  # excludes response


# We don't actually use this: we create similar schema later with typed responses.
class JobSchema(ModelSchema):
    class Config:
        model = Job
        model_fields = job_fields  # i.e. all fields. Derived classes overwrite response.


class FileSchema(Schema):
    file_name: str
    file_format: str = None
    file_size: int = None
    check_sum: str = None
    url: str


class HazardTypeEnum(str, Enum):
    tropical_cyclone = "tropical cyclone"
    extreme_heat = "extreme heat"


class MapHazardClimateRequest(Schema):
    hazard_type: HazardTypeEnum
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    scenario_year: int = None
    scenario_rp: float = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_level: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_FORMAT
    units: str = conf.DEFAULT_UNITS


class MapHazardEventRequest(Schema):
    hazard_type: HazardTypeEnum
    hazard_event_name: str
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    scenario_year: int = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_FORMAT
    units: str = conf.DEFAULT_UNITS



class MapExposureRequest(Schema):
    exposure_type: HazardTypeEnum
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    scenario_year: int = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_FORMAT
    units: str = conf.DEFAULT_UNITS



class MapImpactClimateRequest(Schema):
    hazard_type: HazardTypeEnum
    exposure_type: str
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    scenario_year: int = None
    scenario_rp: float = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_FORMAT
    units: str = conf.DEFAULT_UNITS



class MapImpactEventRequest(Schema):
    hazard_type: HazardTypeEnum
    hazard_event_name: str
    exposure_type: str
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    scenario_year: int = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_FORMAT
    units: str = conf.DEFAULT_UNITS



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
    bounding_box: List[float]
    file_uri: str = None


class MapResponse(Schema):
    data: List[MapEntry] = None
    metadata: MapMetadata


class MapJobSchema(JobSchema):
    response: MapResponse = None


class ExceedanceHazardRequest(Schema):
    hazard_type: str
    hazard_event_name: str
    scenario_name: str
    scenario_year: int
    location_name: str = None
    location_scale: str
    location_code: str
    location_poly: str
    aggregation_scale: str
    aggregation_method: str
    format: str = conf.DEFAULT_FORMAT
    units: str = conf.DEFAULT_UNITS



class ExceedanceImpactRequest(Schema):
    hazard_type: str
    hazard_event_name: str
    exposure_type: str
    scenario_name: str
    scenario_year: int
    location_name: str
    location_scale: str
    location_code: str
    location_poly: str
    aggregation_scale: str
    aggregation_method: str
    format: str = conf.DEFAULT_FORMAT
    units: str = conf.DEFAULT_UNITS



class ExceedanceCurveData(Schema):
    return_period: List[float]
    intensity: List[float]
    return_period_units: str
    intensity_units: str


class ExceedanceResponse(Schema):
    data: ExceedanceCurveData
    metadata: dict       # we'll expand this later...


class ExceedanceJobSchema(JobSchema):
    response: ExceedanceResponse = None


class GeocodePlace(Schema):
    """Response data provided in a geocoding query"""
    name: str
    id: str
    bbox: List[float]


class GeocodePlaceList(Schema):
    data: List[GeocodePlace]


