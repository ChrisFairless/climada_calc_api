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
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units: str = None


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
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units: str = None



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
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units: str = None



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
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units: str = None



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
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units: str = None



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
    hazard_event_name: str = None
    scenario_name: str = None
    scenario_year: int = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units: str = None


class ExceedanceImpactRequest(Schema):
    hazard_type: str
    hazard_event_name: str = None
    exposure_type: str = None
    scenario_name: str = None
    scenario_year: int = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units: str = None


class ExceedanceCurvePoint(Schema):
    return_period: float
    intensity: float


class ExceedanceCurveMetadata(Schema):
    return_period_units: str
    intensity_units: str


class ExceedanceResponse(Schema):
    data: List[ExceedanceCurvePoint]
    metadata: ExceedanceCurveMetadata


class ExceedanceJobSchema(JobSchema):
    response: ExceedanceResponse = None


class TimelineHazardRequest(Schema):
    hazard_type: str
    hazard_event_name: str = None
    scenario_name: str = None
    scenario_rp: int = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    units_warming: str = None
    units_response: str = None


class TimelineExposureRequest(Schema):
    exposure_type: str = None
    scenario_name: str = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    units_warming: str = None
    units_response: str = None


class TimelineImpactRequest(Schema):
    hazard_type: str
    hazard_event_name: str = None
    exposure_type: str = None
    scenario_name: str = None
    scenario_rp: int = None
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    units_warming: str = None
    units_response: str = None


class TimelineBar(Schema):
    year: float
    temperature: float
    risk_baseline: float
    risk_population_change: float
    risk_climate_change: float


class TimelineMetadata(Schema):
    units_warming: str
    units_response: str


class TimelineResponse(Schema):
    data: List[TimelineBar]
    metadata: TimelineMetadata


class TimelineJobSchema(Schema):
    response: TimelineResponse = None


class GeocodePlace(Schema):
    """Response data provided in a geocoding query"""
    name: str
    id: str
    bbox: List[float]


class GeocodePlaceList(Schema):
    data: List[GeocodePlace]


