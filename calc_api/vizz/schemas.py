from django.utils import timezone
from ninja import Schema, ModelSchema
from typing import List
import datetime
import uuid
import json

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.models import Job, Measure
from climada_calc import celery_app as app
from calc_api.vizz import enums
from calc_api.calc_methods.util import standardise_scenario
from calc_api.calc_methods.geocode import standardise_location
from calc_api.vizz import schemas_geocoding
from calc_api.vizz.enums import get_option_choices, get_option_parameter

conf = ClimadaCalcApiConfig()

# TODO extend schemas to include 'impact type' as well as exposure type
# TODO add 'standardise' methods to each of these classes (possibly as part of an __init__)


# We don't actually use this: we create similar schema later with typed responses.
class JobSchema(Schema):
    job_id: uuid.UUID
    location: str
    status: str
    request: dict
    submitted_at: datetime.datetime = None
    completed_at: datetime.datetime = None
    expires_at: datetime.datetime = None
    response: dict = None  # This will be replaced in child classes
    response_uri: str = None
    code: int = None
    message: str = None

    @classmethod
    # TODO refactor so that location_root is a class attribute
    def from_task_id(cls, task_id, location_root):
        # task = TaskResult.objects.get(task_id=task_id)
        # response_schema = globals().copy()
        # response_schema = response_schema.get(response_schema_name)
        task = app.AsyncResult(task_id)
        if task.ready():
            if task.successful():
                response = task.get()
                uri = task.result.metadata.uri if hasattr(task.result.metadata, 'uri') else None
                expiry = task.date_done + datetime.timedelta(seconds=conf.JOB_TIMEOUT)
            else:
                # TODO deal with failed tasks
                task.forget()
                print("FORGETTING")
                raise ValueError(f"Task failed but there's no code to handle this yet. Task: {task}")
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
    units: str = None
    items: List[CategoricalLegendItem]


class PlaceSchema(Schema):
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: List[List[float]] = None
    geocoding: schemas_geocoding.GeocodePlace = None   # TODO make this private somehow?

    def standardise(self):
        geocoded = standardise_location(
            location_name=self.location_name,
            location_code=self.location_code,
            location_scale=self.location_scale,
            location_poly=self.location_poly)
        self.location_name = geocoded.name
        self.location_code = geocoded.id
        self.location_scale = geocoded.scale
        self.location_poly = geocoded.poly
        self.geocoding = geocoded

        # Check units make sense
        if hasattr(self, 'units_hazard'):
            haz_unit_type = get_option_parameter(['data', 'filters', self.hazard_type], parameter="unit_type")
            allowed_units = get_option_choices(['data', 'units', haz_unit_type], get_value='value')
            if self.units_hazard not in allowed_units:
                raise ValueError(f'Units incompatible with hazard in {type(self).__name__}. '
                                 f'\nHazard type: {self.hazard_type} '
                                 f'\nUnits provided: {self.units_hazard} '
                                 f'\nAllowed units: {allowed_units}')

        if hasattr(self, 'units_exposure'):
            exp_unit_type = get_option_choices(
                options_path=['data', 'filters', self.hazard_type, "scenario_options", "impact_type"],
                parameters={'exposure_type': self.exposure_type},
                get_value='unit_type'
            )
            exp_unit_type = list(set(exp_unit_type))
            if len(exp_unit_type) != 1:
                raise ValueError(f'Expected exactly one exposure to match with the setup '
                                 f'{self.hazard_type} (hazard type) and'
                                 f'{self.exposure_type} (exposure type). '
                                 f'Matches: {exp_unit_type}')
            allowed_units = get_option_choices(['data', 'units', exp_unit_type[0]], get_value='value')
            if self.units_exposure not in allowed_units:
                raise ValueError(f'Units incompatible with exposure in {type(self).__name__}. '
                                 f'\nExposure type: {self.exposure_type} '
                                 f'\nUnits provided: {self.units_exposure} '
                                 f'\nAllowed units: {allowed_units}')

        if hasattr(self, 'units_warming'):
            allowed_units = get_option_choices(['data', 'units', 'temperature'], get_value='value')
            if self.units_warming not in allowed_units:
                raise ValueError(f'Units incompatible with temperature in {type(self).__name__}. '
                                 f'\nUnits provided: {self.units_warming} '
                                 f'\nAllowed units: {allowed_units}')



class AnalysisSchema(PlaceSchema):
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    scenario_year: int = None
    aggregation_scale: str = None
    aggregation_method: str = None

    def standardise(self):
        super().standardise()
        # Scenario
        self.scenario_name, self.scenario_growth, self.scenario_climate = \
            standardise_scenario(
                self.scenario_name,
                self.scenario_growth,
                self.scenario_climate,
                self.scenario_year)
        if self.aggregation_scale == self.geocoding.scale:
            self.aggregation_scale = 'all'
        enums.assert_in_enum(self.scenario_name, enums.ScenarioNameEnum)
        enums.assert_in_enum(self.scenario_growth, enums.ScenarioGrowthEnum)
        enums.assert_in_enum(self.scenario_climate, enums.ScenarioClimateEnum)


class MapHazardClimateRequest(AnalysisSchema):
    hazard_type: enums.HazardTypeEnum
    hazard_rp: str = None
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_hazard: str = None


class MapHazardEventRequest(AnalysisSchema):
    hazard_type: enums.HazardTypeEnum
    hazard_event_name: str
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_hazard: str = None


class MapExposureRequest(AnalysisSchema):
    exposure_type: str
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_exposure: str = None


class MapImpactClimateRequest(AnalysisSchema):
    hazard_type: enums.HazardTypeEnum
    hazard_rp: str = None
    exposure_type: str
    impact_type: str
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_hazard: str = None
    units_exposure: str = None

    def standardise(self):
        super().standardise()
        if self.exposure_type:
            enums.validate_exposure_type_from_impact_type(self.exposure_type, self.impact_type)
        else:
            self.exposure_type = enums.exposure_type_from_impact_type(self.impact_type)


class MapImpactEventRequest(AnalysisSchema):
    hazard_type: enums.HazardTypeEnum
    hazard_event_name: str
    exposure_type: str
    impact_type: str
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_hazard: str = None
    units_exposure: str = None

    def standardise(self):
        super().standardise()
        if self.exposure_type:
            enums.validate_exposure_type_from_impact_type(self.exposure_type, self.impact_type)
        else:
            self.exposure_type = enums.exposure_type_from_impact_type(self.impact_type)


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
    metadata: MapMetadata = None


class MapJobSchema(JobSchema):
    response: MapResponse = None

    @staticmethod
    def location_root():
        return ""


class ExceedanceHazardRequest(AnalysisSchema):
    hazard_type: str
    hazard_event_name: str = None
    units_hazard: str = None


class ExceedanceImpactRequest(AnalysisSchema):
    hazard_type: str
    hazard_event_name: str = None
    exposure_type: str = None
    impact_type: str = None
    units_hazard: str = None
    units_exposure: str = None


class ExceedanceCurvePoint(Schema):
    return_period: float
    intensity: float


class ExceedanceCurve(Schema):
    items: List[ExceedanceCurvePoint]
    scenario_name: str
    slug: str


class ExceedanceCurveSet(Schema):
    items: List[ExceedanceCurve]
    units_return_period: str
    units_intensity: str
    legend: CategoricalLegend


class ExceedanceCurveMetadata(Schema):
    description: str


class ExceedanceResponse(Schema):
    data: ExceedanceCurveSet
    metadata: ExceedanceCurveMetadata


class ExceedanceJobSchema(JobSchema):
    response: ExceedanceResponse = None


# Timelines
# =========

class TimelineHazardRequest(PlaceSchema):
    hazard_type: str
    hazard_event_name: str = None
    hazard_rp: str = None
    scenario_name: str = None
    scenario_climate: str = None
    aggregation_method: str = None
    units_hazard: str = None
    units_warming: str = None

    def standardise(self):
        super().standardise()
        # Scenario
        self.scenario_name, _, self.scenario_climate = \
            standardise_scenario(
                self.scenario_name,
                None,
                self.scenario_climate,
                None)


class TimelineExposureRequest(PlaceSchema):
    exposure_type: str = None
    scenario_name: str = None
    scenario_growth: str = None
    aggregation_method: str = None
    units_exposure: str = None
    units_warming: str = None

    def standardise(self):
        super().standardise()
        # Scenario
        self.scenario_name, self.scenario_growth, _ = \
            standardise_scenario(
                self.scenario_name,
                self.scenario_growth,
                None,
                None)


class TimelineImpactRequest(PlaceSchema):
    hazard_type: str
    hazard_event_name: str = None
    hazard_rp: List[str] = None
    exposure_type: str = None
    impact_type: str = None
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    aggregation_method: str = None
    units_hazard: str = None
    units_exposure: str = None
    units_warming: str = None

    def standardise(self):
        super().standardise()
        # Scenario
        self.scenario_name, self.scenario_growth, self.scenario_climate = \
            standardise_scenario(
                self.scenario_name,
                self.scenario_growth,
                self.scenario_climate,
                None)

        if self.exposure_type:
            enums.validate_exposure_type_from_impact_type(self.exposure_type, self.impact_type)
        else:
            self.exposure_type = enums.exposure_type_from_impact_type(self.impact_type)


class BreakdownBar(Schema):
    year_label: str
    year_value: float
    temperature: float = None
    current_climate: float = None
    growth_change: float = None
    climate_change: float = None
    future_climate: float = None
    measure_names: List[str] = None
    measure_change: List[float] = None
    measure_climate: List[float] = None
    combined_measure_change: float = None
    combined_measure_climate: float = None


class Timeline(Schema):
    items: List[BreakdownBar]
    legend: CategoricalLegend
    units_warming: str
    units_response: str


class TimelineMetadata(Schema):
    description: str


class TimelineResponse(Schema):
    data: Timeline
    metadata: TimelineMetadata


class TimelineJobSchema(JobSchema):
    response: TimelineResponse = None


# CostBenefit
# ===========

class MeasureSchema(ModelSchema):
    class Config:
        model = Measure
        model_fields = ["id", "name", "slug", "description", "hazard_type", "exposure_type", "cost_type", "cost",
                        "annual_upkeep", "priority", "percentage_coverage", "percentage_effectiveness", "is_coastal",
                        "max_distance_from_coast", "hazard_cutoff", "return_period_cutoff", "hazard_change_multiplier",
                        "hazard_change_constant", "cobenefits", "units_currency", "units_hazard", "units_distance",
                        "user_generated"]

    # Don't understand why these are necessary here but...
    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, dict):
        return cls(**dict)

class CreateMeasureSchema(ModelSchema):
    class Config:
        model = Measure
        model_exclude = ['id', 'user_generated']


# class MeasureRequestSchema(Schema):
#     ids: List[uuid.UUID] = None
#     include_defaults: bool = None
#     hazard: str = None


class CostBenefitRequest(AnalysisSchema):
    hazard_type: str
    hazard_event_name: str = None
    exposure_type: str = None
    impact_type: str = None
    measures: List[dict] = None
    units_hazard: str = None
    units_exposure: str = None
    units_warming: str = None


class CostBenefit(Schema):
    items: List[BreakdownBar]
    legend: CategoricalLegend
    units_warming: str
    units_response: str


class CostBenefitMetadata(Schema):
    description: str


class CostBenefitResponse(Schema):
    data: CostBenefit
    metadata: CostBenefitMetadata


class CostBenefitJobSchema(JobSchema):
    response: CostBenefitResponse = None


class ExposureBreakdownRequest(PlaceSchema):
    exposure_type: str = None
    exposure_categorisation: str
    scenario_year: int = None
    aggregation_method: str = None
    units_exposure: str = None


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




