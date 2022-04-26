from django.utils import timezone
from ninja import Schema, ModelSchema
from typing import List
from enum import Enum
import datetime
import uuid
import json
from celery.result import AsyncResult

from calc_api.config import ClimadaCalcApiConfig
from django_celery_results.models import TaskResult
from calc_api.vizz.models import Measure
from climada_calc import celery_app as app

conf = ClimadaCalcApiConfig()


# We don't actually use this: we create similar schema later with typed responses.
class JobSchema(Schema):
    job_id: uuid.UUID
    location: str
    status: str
    request: dict
    completed_at: datetime.datetime = None
    expires_at: datetime.datetime = None
    response: dict = None  # This will be replaced in child classes
    response_uri: str = None
    code: int = None
    message: str = None

    @classmethod
    def from_task_id(cls, task_id, response_schema_name, location_root):
        # task = TaskResult.objects.get(task_id=task_id)
        # response_schema = globals().copy()
        # response_schema = response_schema.get(response_schema_name)
        task = app.AsyncResult(task_id)
        if task.ready():
            if task.successful():
                response = task.get()
                uri = task.result['metadata']['uri']
                expiry = task.date_done + datetime.timedelta(seconds=conf.JOB_TIMEOUT)
            else:
                # TODO deal with failed tasks
                task.forget()
                return ValueError("Task failed but there's no code to handle this yet.")
        else:
            response, uri, expiry = None, None, None

        return cls(
            job_id=task.id,
            location=location_root + '/' + task.id,
            status=task.status,
            request={},  # TODO work out where to get this from
            completed_at=task.date_done,
            expires_at=expiry,
            response=response,
            response_uri=uri,
            code=None,
            message=None
        )



class FileSchema(Schema):
    file_name: str
    file_format: str = None
    file_size: int = None
    check_sum: str = None
    url: str


class ColorbarLegendItem(Schema):
    band_min: float
    band_max: float
    color: str


class ColorbarLegend(Schema):
    title: str
    units: str
    value: str
    items: List[ColorbarLegendItem]


class CategoricalLegendItem(Schema):
    label: str
    slug: str
    value: str


class CategoricalLegend(Schema):
    title: str
    units: str
    items: List[CategoricalLegendItem]


class TextVariable(Schema):
    key: str
    value: str
    unit: str = None


class GeneratedText(Schema):
    template: str
    values: List[TextVariable]

class HazardTypeEnum(str, Enum):
    tropical_cyclone = "tropical_cyclone"
    extreme_heat = "extreme_heat"


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
    aggregation_scale: str = None
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


class Map(Schema):
    items: List[MapEntry]
    legend: ColorbarLegend


class MapMetadata(Schema):
    description: str
    file_uri: str = None
    units: str
    custom_fields: dict = None
    bounding_box: List[float]


class MapResponse(Schema):
    data: Map = None
    metadata: MapMetadata


class MapJobSchema(JobSchema):
    response: MapResponse = None

    @staticmethod
    def location_root():
        return ""


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


class ExceedanceCurve(Schema):
    items: List[ExceedanceCurvePoint]
    scenario_name: str
    slug: str

class ExceedanceCurveSet(Schema):
    items: List[ExceedanceCurve]
    return_period_units: str
    intensity_units: str
    legend: CategoricalLegend


class ExceedanceCurveMetadata(Schema):
    description: str


class ExceedanceResponse(Schema):
    data: ExceedanceCurveSet
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
    yearLabel: str
    yearValue: float
    temperature: float
    current_climate: float
    population_growth: float
    climate_change: float


class Timeline(Schema):
    items: List[TimelineBar]
    legend: CategoricalLegend
    units_temperature: str
    units_response: str


class TimelineMetadata(Schema):
    description: str


class TimelineResponse(Schema):
    data: Timeline
    metadata: TimelineMetadata


class TimelineJobSchema(JobSchema):
    response: TimelineResponse = None


class ExposureBreakdownRequest(Schema):
    exposure_type: str = None
    exposure_categorisation: str
    scenario_year: int = None
    location_name: List[str] = None
    location_scale: List[str] = None
    location_code: List[str] = None
    location_poly: List[str] = None
    aggregation_method: str = None
    units: str = None


class ExposureBreakdownBar(Schema):
    label: str
    category_labels: List[str]
    values: List[float]


class ExposureBreakdown(Schema):
    items: List[ExposureBreakdownBar]
    legend: CategoricalLegend


class ExposureBreakdownResponse(Schema):
    data: ExposureBreakdown
    metadata: dict


class ExposureBreakdownJob(JobSchema):
    response: ExposureBreakdownResponse = None



class MeasureSchema(ModelSchema):
    class Config:
        model = Measure
        model_fields = ["name", "description", "hazard_type", "exposure_type", "cost_type", "cost", "annual_upkeep",
                        "priority", "percentage_coverage", "percentage_effectiveness", "is_coastal",
                        "max_distance_from_coast", "hazard_cutoff", "return_period_cutoff", "hazard_change_multiplier",
                        "hazard_change_constant", "cobenefits", "units_currency", "units_hazard", "units_distance",
                        "user_generated"]


class CreateMeasureSchema(ModelSchema):
    class Config:
        model = Measure
        model_exclude = ['id', 'user_generated']


class MeasureRequestSchema(Schema):
    ids: List[uuid.UUID] = None
    include_defaults: bool = None
    hazard: str = None


class GeocodePlace(Schema):
    """Response data provided in a geocoding query"""
    name: str
    id: str
    type: str
    adminLevel: str = None
    city: str = None
    county: str = None
    state: str = None
    country: str = None
    bbox: List[float]


class GeocodePlaceList(Schema):
    data: List[GeocodePlace]


