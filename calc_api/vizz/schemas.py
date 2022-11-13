from django.utils import timezone
from ninja import Schema, ModelSchema
from typing import List
import datetime
import uuid
import json
from time import sleep
import logging
import numpy as np
from celery.result import AsyncResult

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.models import JobLog, Measure
from climada_calc import celery_app as app
from calc_api.vizz import enums
from calc_api.calc_methods.util import standardise_scenario, bbox_to_wkt
from calc_api.calc_methods.geocode import standardise_location
from calc_api.vizz import schemas_geocoding
from calc_api.vizz.enums import get_option_choices, get_option_parameter, get_exposure_types, get_hazard_type_names
from calc_api.vizz import units
from calc_api import util

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))

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

    # TODO replace calls to from_task_id and from_joblog with calls to this
    @classmethod
    def from_request(cls, request):
        return cls.from_task_id(request.get_id(), request.get_full_path())

    @classmethod
    def from_task_id(cls, task_id, location_root):
        if conf.DATABASE_MODE in ['read', 'update', 'fail_missing']:
            existing_task = JobLog.objects.filter(job_hash=str(task_id))
            if len(existing_task) == 1 and existing_task.result:
                uri = existing_task.result.metadata.uri if hasattr(existing_task.result.metadata, 'uri') else None
                return cls(
                    job_id=task_id,
                    location=location_root + '/' + task_id,
                    status="SUCCESS",
                    request={},  # TODO work out where to get this from if the job didn't succeed. Probably add to the DB model
                    completed_at=None,
                    expires_at=None,
                    response=existing_task.result,
                    response_uri=uri,
                    code=None,
                    message=None
                )
        job = app.AsyncResult(task_id)
        return cls.from_asyncresult(job, location_root)

    @classmethod
    def from_joblog(cls, job: JobLog, location_root):
        if job.result is None:
            raise ValueError('JobLog has no result')

        request = job.args
        result = json.loads(job.result)
        if '__class__' in result.keys():
            _ = result.pop('__class__')
        uri = result['metadata']['uri'] if 'uri' in result['metadata'] else None
        output = cls(
            job_id=job.job_hash,
            location=location_root + '/' + job.job_hash,
            status="SUCCESS",
            request={},  # TODO work out where to get this from
            completed_at=None,
            expires_at=None,
            response=result,
            response_uri=uri,
            code=None,
            message=None
        )
        return output


    @classmethod
    # TODO refactor so that location_root is a class attribute
    def from_asyncresult(cls, task: AsyncResult, location_root):
        # Note: we call the parameter 'task' here, but it's actually some task's AsyncResult
        # Sometimes all the results will be cached, so waiting a fraction of a second will let the workers assemble them
        sleep(1)

        if task.ready():
            if task.successful():
                response = task.get()
                uri = task.result.metadata.uri if hasattr(task.result.metadata, 'uri') else None
                expiry = task.date_done + datetime.timedelta(seconds=conf.JOB_TIMEOUT)
                request_dict = {
                    # 'schema': cls.__name__,
                    'args': task.args,
                    'kwargs': task.kwargs
                }

            else:
                print(f"Task failed but there's no code to handle this yet. \nTask: {task} \nInfo: {task.info}")
                task.forget()
                response, uri, expiry = None, None, None
                request_dict = {}

                # TODO deal with failed tasks
                # task.forget()
                # print("FORGETTING")
                # raise ValueError(f"Task failed but there's no code to handle this yet. \nTask: \n{task}")
        else:
            response, uri, expiry = None, None, None
            request_dict = {}

        output = cls(
            job_id=task.id,
            location=location_root + '/' + task.id,
            status=task.status,
            request=request_dict,  # TODO work out where to get this from if the job didn't succeed
            completed_at=task.date_done,
            expires_at=expiry,
            response=response,
            response_uri=uri,
            code=None,
            message=None
        )

        if conf.DATABASE_MODE in ['create', 'update'] and task.successful():
            try:
                print("UPDATING JOB")
                print(str(task.id))
                job = JobLog.objects.get(job_hash=str(task.id))
                if not job.result:
                    json_result = util.encode(response, include_class=False)
                    job.result = json_result
                    job.save(update_fields=['result'])
                else:
                    LOGGER.warning(
                        'Unexpectedly found a job with a result already saved. Are we using this in a new way?')
            except JobLog.DoesNotExist as e:
                LOGGER.warning(f'Expected to find an existing record for this job. Investigate. Error: {e}')

        return output

    @classmethod
    def from_db_hash(cls, job_hash, location_root):
        task = JobLog.objects.get(job_hash=str(job_hash))
        uri = task.result.metadata.uri if hasattr(task.result.metadata, 'uri') else None
        # expiry = task.date_done + datetime.timedelta(seconds=conf.JOB_TIMEOUT)

        return cls(
            job_id=task.request.id,
            location=location_root + '/' + task.request.id,
            status=task.status,
            request={},  # TODO work out where to get this from
            completed_at=task.date_done,
            expires_at=None,
            response=task.result,
            response_uri=uri,
            code=None,
            message=None
        )


class ResponseSchema(Schema):

    def convert_units(self, units_dict):
        if not set(units_dict.keys()).issubset(units.API_DEFAULT_UNITS.keys()):
            raise ValueError(f'convert_units parameter units_dict must have keys that are a subset of '
                             f'{units.API_DEFAULT_UNITS.keys()}. \nProvided: {units_dict.keys()}')

        mapping_dict = self.get_unit_change_mapping(units_dict)

        for att, mapping in mapping_dict.items():
            from_unit, to_unit = mapping

            # TODO in the v1 iteration rewrite the schemas so that values and units are always kept together
            # Remembering all this is a huge mental overhead. Maybe create a Unit schema/use pint so that the
            # unit type is also included in the metadata
            if att == 'units':
                # Data structures we know in advance:
                # - Schema has attributes 'units' and 'value(s)'
                # - Schemas has attribute 'items' which is a list of schemas with value(s) attributes
                # - Schemas has attribute 'items.items', which is a list of schemas with value(s) attributes
                # A curse on these overcomplicated data structures!
                scale_function = units.make_conversion_function(from_unit, to_unit)
                if hasattr(self, 'value') or hasattr(self, 'values'):
                    self.scale_values(scale_function)
                if hasattr(self, 'items'):
                    if self.items:
                        assert isinstance(self.items, list)
                        if hasattr(self.items[0], 'items'):  # Sometimes the values are buried two lists deep
                            items_list_list = [it.items for it in self.items]
                        else:
                            items_list_list = [self.items]
                        for items_list in items_list_list:
                            _ = [obj.scale_values(scale_function) for obj in items_list]
                self.__setattr__(att, to_unit)

        # Convert all children
        for att in self.dict().keys():
            att_value = self.__getattribute__(att)
            if isinstance(att_value, Schema):
                assert isinstance(att_value, ResponseSchema)   # All subschema should also be ResponseSchema
                att_value.convert_units(units_dict)
            elif isinstance(att_value, list) and len(att_value) > 0:
                if isinstance(att_value[0], Schema):
                    _ = [entry.convert_units(units_dict) for entry in att_value]

    def get_unit_change_mapping(self, units_dict):
        # Find the Schema's unit attributes (e.g. units, unit_hazard, unit_intensity, unit_currency)
        unit_attributes = self.unit_attributes.keys()
        mappings = {}
        for att in unit_attributes:
            from_unit = self.__getattribute__(att)
            if from_unit in units.UNITS_NOT_TO_CONVERT:
                continue
            unit_type = units.UNIT_TYPES[from_unit]
            if unit_type in units_dict.keys():
                to_unit = units_dict[unit_type]
            else:
                raise ValueError(
                    f'Found unit data with no instructions on how to convert: '
                    f'\nUnit: {from_unit} (type: {unit_type})'
                    f'\nIf you want to use the API defaults, use the convert_units_with_api_defaults method.'
                )
            mappings[att] = (from_unit, to_unit)
        return mappings

    def scale_values(self, scale_function):
        if hasattr(self, 'value'):
            if self.value:
                if not isinstance(self.__getattribute__('value'), float):
                    raise ValueError(f"Class {type(self).__name__} has a non-float 'value' attribute: "
                                     f"{type(self.__getattribute__('value')).__name__}: "
                                     f"{self.__getattribute__('value')}")
                self.__setattr__('value', scale_function(self.value))
        elif hasattr(self, 'values'):
            if self.values:
                if not isinstance(self.__getattribute__('values'), list):
                    raise ValueError(f"Class {type(self).__name__} has a non-list 'values' attribute: "
                                     f"{type(self.__getattribute__('values')).__name__}")
                if not isinstance(self.__getattribute__('values')[0], float):
                    raise ValueError(f"Class {type(self).__name__} has 'values' attribute containing list of non-float objects: "
                                     f"{type(self.__getattribute__('values')[0]).__name__}")
                self.__setattr__('values', scale_function(self.values))
        else:
            raise ValueError(f"Expected either 'value' or 'values' attribute in class {str(type(self).__name__)}")

    def convert_to_climada_units(self):
        self.convert_units(units_dict=units.NATIVE_UNITS_CLIMADA)

    def convert_units_with_api_defaults(self, units_dict=None):
        if not units_dict:
            units_dict = units.API_DEFAULT_UNITS
        else:
            missing_types = {key: value for key, value in units.API_DEFAULT_UNITS if key not in units_dict.keys()}
            units_dict = units_dict.union(missing_types)
        self.convert_units(units_dict)

    @property
    def unit_attributes(self):
        return {
            att: unit_name for att, unit_name in self.dict().items()
            if att.startswith('unit')
        }



class FileSchema(Schema):
    file_name: str
    file_format: str = None
    file_size: int = None
    check_sum: str = None
    url: str


class ColorbarLegendItem(ResponseSchema):
    band_min: float
    band_max: float
    color: str


class ColorbarLegend(ResponseSchema):
    title: str
    units: str
    value: float
    items: List[ColorbarLegendItem]

    def convert_units(self, units_dict):
        unit_type = units.UNIT_TYPES[self.units]
        from_unit, to_unit = self.units, units_dict[unit_type]
        scale_function = units.make_conversion_function(from_unit, to_unit)
        self.value = scale_function(self.value)
        self.units = to_unit
        for legend in self.items:
            legend.band_min = scale_function(legend.band_min)
            legend.band_max = scale_function(legend.band_max)


class CategoricalLegendItem(ResponseSchema):
    label: str
    slug: str
    value: float = None


class CategoricalLegend(ResponseSchema):
    title: str
    units: str = None
    items: List[CategoricalLegendItem]


class PlaceSchema(Schema):
    location_name: str = None
    location_scale: str = None
    location_code: str = None
    location_poly: str = None
    geocoding: schemas_geocoding.GeocodePlace = None   # TODO make this private somehow?

    # TODO move standardisation to a separate, ur-class
    def standardise(self):
        # We assume that if all these values are filled in, then they are correct. This is probably fine.
        if not all([self.location_name, self.location_scale, self.location_code, self.location_poly, self.geocoding]):
            geocoded = standardise_location(
                location_name=self.location_name,
                location_code=self.location_code,
                location_scale=self.location_scale,
                location_poly=self.location_poly)
            self.location_name = geocoded.name
            self.location_code = geocoded.id
            self.location_scale = geocoded.scale
            self.geocoding = geocoded
            if not self.location_poly:
                self.location_poly = bbox_to_wkt(geocoded.bbox)

        self.rename_units()

        # TODO these methods are all a mess and are half or fully implemented elsewhere. Make consistent

        # Check hazard units make sense
        if hasattr(self, 'units_hazard'):
            haz_unit_type = units.HAZARD_UNIT_TYPES[self.hazard_type]
            allowed_units = units.UNIT_OPTIONS[haz_unit_type]
            if self.units_hazard not in allowed_units:
                raise ValueError(f'Units incompatible with hazard in {type(self).__name__}. '
                                 f'\nHazard type: {self.hazard_type} '
                                 f'\nUnits provided: {self.units_hazard} '
                                 f'\nAllowed units: {allowed_units}')

        if hasattr(self, 'hazard_type') and hasattr(self, 'exposure_type') and not hasattr(self, 'impact_type'):
            raise ValueError('I thought I made sure this would never happen')

        # check impact type is consistent with exposure
        if hasattr(self, 'impact_type'):
            assert(hasattr(self, 'hazard_type'))
            assert(self.impact_type is not None)
            exposure_type = enums.exposure_type_from_impact_type(self.impact_type)
            if hasattr(self, 'exposure_type'):
                if self.exposure_type:
                    if self.exposure_type != exposure_type:
                        raise ValueError(f'Requested exposure type ({self.exposure_type}) mismatch with '
                                         f'exposure type inferred from impact ({self.impact_type} gives '
                                         f'{exposure_type}')
                else:
                    self.__setattr__('exposure_type', exposure_type)

        # check exposure units are consistent with exposure
        if hasattr(self, 'exposure_type') or hasattr(self, 'impact_type'):
            if not hasattr(self, 'impact_type'):
                exposure_type = self.exposure_type
            assert(exposure_type in get_exposure_types())

            if hasattr(self, 'hazard_type'):
                valid_exposure_units = units.get_valid_exposure_units(self.hazard_type, exposure_type)
            else:
                valid_exposure_units = units.get_valid_exposure_units(exposure_type=exposure_type)

            if self.units_exposure not in valid_exposure_units:
                raise ValueError(f'Units incompatible with exposure in {type(self).__name__}. '
                                 f'\nExposure type: {exposure_type} '
                                 f'\nUnits provided: {self.units_exposure} '
                                 f'\nAllowed units: {allowed_units}')
        elif hasattr(self, 'units_exposure'):
            raise ValueError('There should be a check for valid exposures somehow here.')

        if hasattr(self, 'units_currency') and hasattr(self, 'units_exposure'):
            if self.units_exposure and self.units_exposure != 'people':  # TODO make this is units type check from the enums
                if self.units_exposure != self.units_currency:
                    raise ValueError(f'When using financial exposures in a cost-benefit, the units should be the same:'
                                     f'\nCost: {self.units_currency}'
                                     f'\nExposure {self.units_exposure}')

        if hasattr(self, 'units_warming'):
            allowed_units = get_option_choices(['data', 'units', 'temperature'], get_value='value')
            if self.units_warming not in allowed_units:
                raise ValueError(f'Units incompatible with temperature in {type(self).__name__}. '
                                 f'\nUnits provided: {self.units_warming} '
                                 f'\nAllowed units: {allowed_units}')

    def rename_units(self):
        # Rename common units to our internally standard name (e.g. celsius -> degC, dollars -> USD)
        schema_units = units.get_request_unit_parameters(self)
        for unit_param in schema_units:
            unit_name = self.__getattribute__(unit_param)
            if unit_name and unit_name.lower() in units.UNIT_NAME_CORRECTIONS.keys():
                self.__setattr__(unit_param, units.UNIT_NAME_CORRECTIONS[unit_name.lower()])

    def get_id(self):
        return util.get_hash(self)


class ScenarioSchema(PlaceSchema):
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    scenario_year: int = None

    def standardise(self):
        super().standardise()
        # Scenario
        self.scenario_name, self.scenario_growth, self.scenario_climate = \
            standardise_scenario(
                self.scenario_name,
                self.scenario_growth,
                self.scenario_climate,
                self.scenario_year)
        enums.assert_in_enum(self.scenario_name, enums.ScenarioNameEnum)
        enums.assert_in_enum(self.scenario_growth, enums.ScenarioGrowthEnum)
        enums.assert_in_enum(self.scenario_climate, enums.ScenarioClimateEnum)


class MapHazardClimateRequest(ScenarioSchema):
    hazard_type: enums.HazardTypeEnum
    hazard_rp: str = None
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_hazard: str = None


class MapHazardEventRequest(ScenarioSchema):
    hazard_type: enums.HazardTypeEnum
    hazard_event_name: str
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_hazard: str = None


class MapExposureRequest(ScenarioSchema):
    exposure_type: str
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_exposure: str = None


class MapImpactClimateRequest(ScenarioSchema):
    hazard_type: enums.HazardTypeEnum
    hazard_rp: str = None
    exposure_type: str
    impact_type: str
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_hazard: str = None
    units_exposure: str = None

    def standardise(self):
        super().standardise()
        if self.exposure_type:
            enums.validate_exposure_type_from_impact_type(self.exposure_type, self.impact_type)
        else:
            self.exposure_type = enums.exposure_type_from_impact_type(self.impact_type)


class MapImpactEventRequest(ScenarioSchema):
    hazard_type: enums.HazardTypeEnum
    hazard_event_name: str
    exposure_type: str
    impact_type: str
    aggregation_scale: str = None
    aggregation_method: str = None
    format: str = conf.DEFAULT_IMAGE_FORMAT
    units_hazard: str = None
    units_exposure: str = None

    def standardise(self):
        super().standardise()
        if self.exposure_type:
            enums.validate_exposure_type_from_impact_type(self.exposure_type, self.impact_type)
        else:
            self.exposure_type = enums.exposure_type_from_impact_type(self.impact_type)


class MapEntry(ResponseSchema):
    #TODO is the best way to encode this info?
    lat: float    # of floats
    lon: float    # of floats
    geom: str = None  # of WKB/WKT geometries (tbd)
    value: float  # of floats
    color: str


class Map(ResponseSchema):
    items: List[MapEntry]
    legend: ColorbarLegend
    units: str


class MapMetadata(ResponseSchema):
    description: str
    file_uri: str = None
    custom_fields: dict = None
    bounding_box: List[float]


class MapResponse(ResponseSchema):
    data: Map = None
    metadata: MapMetadata = None


class MapJobSchema(JobSchema):
    response: MapResponse = None

    @staticmethod
    def location_root():
        return ""


class ExceedanceHazardRequest(ScenarioSchema):
    hazard_type: str
    hazard_event_name: str = None
    # aggregation_method: str = 'max'
    units_hazard: str = None


class ExceedanceImpactRequest(ScenarioSchema):
    hazard_type: str
    hazard_event_name: str = None
    exposure_type: str = None
    impact_type: str = None
    # aggregation_method: str = 'sum'
    units_hazard: str = None
    units_exposure: str = None


class ExceedanceCurvePoint(ResponseSchema):
    return_period: float
    value: float


class ExceedanceCurve(ResponseSchema):
    items: List[ExceedanceCurvePoint]
    scenario_name: str
    slug: str


class ExceedanceCurveSet(ResponseSchema):
    items: List[ExceedanceCurve]
    units_return_period: str
    units: str
    legend: CategoricalLegend


class ExceedanceCurveMetadata(ResponseSchema):
    description: str


class ExceedanceResponse(ResponseSchema):
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
    # aggregation_method: str = 'max'
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
    # aggregation_method: str = 'sum'
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


class BreakdownBar(ResponseSchema):
    year_label: str
    year_value: float
    temperature: float = None     # Actually the change in temperature
    current_climate: float = None
    growth_change: float = None
    climate_change: float = None
    future_climate: float = None
    measure_names: List[str] = None
    measure_change: List[float] = None
    measure_climate: List[float] = None
    combined_measure_change: float = None
    combined_measure_climate: float = None

    def convert_breakdown_units(self, temperature_units, response_units):
        if self.temperature:
            delta_units = ('delta_' + temperature_units[0], 'delta_' + temperature_units[1])
            temp_scale_fn = units.make_conversion_function(delta_units[0], delta_units[1])
            self.__setattr__('temperature', temp_scale_fn(self.temperature))

        if response_units[0] not in units.UNITS_NOT_TO_CONVERT:
            response_scale_fn = units.make_conversion_function(response_units[0], response_units[1])
            for response_var in ['current_climate', 'growth_change', 'climate_change', 'future_climate',
                                 'combined_measure_change', 'combined_measure_climate']:
                old_value = self.__getattribute__(response_var)
                if old_value:
                    self.__setattr__(response_var, response_scale_fn(old_value))
            for response_list in ['measure_change', 'measure_climate']:
                old_value = self.__getattribute__(response_list)
                if old_value:
                    self.__setattr__(response_list, [response_scale_fn(x) for x in old_value])


class Timeline(ResponseSchema):
    items: List[BreakdownBar]
    legend: CategoricalLegend
    units_warming: str
    units_response: str

    def convert_units(self, units_dict):
        response_type = units.UNIT_TYPES[self.units_response]
        response_from_to = (self.units_response, units_dict[response_type])
        temperature_from_to = (self.units_warming, units_dict['temperature'])
        _ = [bar.convert_breakdown_units(temperature_from_to, response_from_to) for bar in self.items]
        ResponseSchema.convert_units(self, units_dict)


class TimelineMetadata(ResponseSchema):
    description: str


class TimelineResponse(ResponseSchema):
    data: Timeline
    metadata: TimelineMetadata


class TimelineJobSchema(JobSchema):
    response: TimelineResponse = None


# CostBenefit
# ===========

#TODO refactor all this with dual class schemas. One day.
class MeasureSchema(ModelSchema, ResponseSchema):
    class Config:
        model = Measure
        model_fields = ["id", "name", "slug", "description", "hazard_type", "exposure_type", "cost_type", "cost",
                        "annual_upkeep", "priority", "percentage_coverage", "percentage_effectiveness", "is_coastal",
                        "max_distance_from_coast", "hazard_cutoff", "return_period_cutoff", "hazard_change_multiplier",
                        "hazard_change_constant", "cobenefits", "units_currency", "units_hazard", "units_distance",
                        "user_generated"]

    # Don't understand why these are necessary here but...
    def to_dict(self):
        return self.dict()

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def convert_units(self, units_dict):
        haz_from = self.__getattribute__("units_hazard")
        haz_type = units.UNIT_TYPES[haz_from]
        haz_to = units_dict[haz_type]
        haz_scale_function = units.make_conversion_function(haz_from, haz_to)
        # TODO write a one-line function that scales attributes. I was careless here and lost an hour to a bug
        self.__setattr__("hazard_cutoff", haz_scale_function(self.__getattribute__("hazard_cutoff")))
        self.__setattr__("hazard_change_constant", haz_scale_function(self.__getattribute__("hazard_change_constant")))
        haz_multiplier = self.__getattribute__("hazard_change_multiplier")
        if haz_type == "temperature" and haz_multiplier and haz_multiplier != 1:
            raise ValueError("You shouldn't be using linear scaling with temperature-based hazards!")
        self.__setattr__("hazard_change_multiplier", haz_scale_function(haz_multiplier))
        self.__setattr__("units_hazard", haz_to)

        cost_from = self.__getattribute__("units_currency")
        cost_to = units_dict["currency"]
        cost_scale_function = units.make_conversion_function(cost_from, cost_to)
        self.__setattr__("cost", cost_scale_function(self.__getattribute__("cost")))
        self.__setattr__("annual_upkeep", cost_scale_function(self.__getattribute__("annual_upkeep")))

        if "distance" in units_dict.keys():
            dist_from = self.__getattribute__("units_distance")
            dist_to = units_dict["distance"]
            dist_scale_function = units.make_conversion_function(dist_from, dist_to)
            self.__setattr__("max_distance_from_coast", dist_scale_function(self.__getattribute__("max_distance_from_coast")))
        else:
            LOGGER.warning("No instructions for distance units in measure ")


class CreateMeasureSchema(ModelSchema):
    class Config:
        model = Measure
        model_exclude = ['id', 'user_generated']


class MeasureRequestSchema(Schema):
    measure_id: int = None
    slug: str = None
    hazard_type: str = None
    exposure_type: str = None
    units_hazard: str = None
    units_currency: str = None
    units_distance: str = None
    units_temperature: str = None
    units_speed: str = None

    def standardise(self):
        # TODO add check that measure ids exist and are consistent
        PlaceSchema.rename_units(self)


class CostBenefitRequest(ScenarioSchema):
    hazard_type: str
    hazard_event_name: str = None
    exposure_type: str = None
    impact_type: str = None
    measures: List[dict] = None
    units_currency: str = None
    units_hazard: str = None
    units_exposure: str = None
    units_warming: str = None


class CostBenefit(ResponseSchema):
    items: List[BreakdownBar]
    legend: CategoricalLegend
    measure: List[MeasureSchema]
    cost: List[float]
    costbenefit: List[float]
    combined_cost: float = None
    combined_costbenefit: float = None
    units_currency: str
    units_warming: str
    units_response: str

    def convert_units(self, units_dict):
        response_type = units.UNIT_TYPES[self.units_response]
        response_from_to = (self.units_response, units_dict[response_type])
        temperature_from_to = (self.units_warming, units_dict['temperature'])

        response_conversion_fn = units.make_conversion_function(self.units_response, units_dict[response_type])
        cost_conversion_fn = units.make_conversion_function(self.units_currency, units_dict['currency'])
        costbenefit_conversion_factor = response_conversion_fn(1) / cost_conversion_fn(1)  # This is allowed because it's not temperature

        _ = [bar.convert_breakdown_units(temperature_from_to, response_from_to) for bar in self.items]
        self.cost = [cost_conversion_fn(x) for x in self.cost]
        self.costbenefit = [costbenefit_conversion_factor * x for x in self.costbenefit]
        if self.combined_cost:
            self.combined_cost = cost_conversion_fn(self.combined_cost)
            self.combined_costbenefit = costbenefit_conversion_factor * self.combined_costbenefit
        ResponseSchema.convert_units(self, units_dict)


class CostBenefitMetadata(ResponseSchema):
    description: str


class CostBenefitResponse(ResponseSchema):
    data: CostBenefit
    metadata: CostBenefitMetadata


class CostBenefitJobSchema(JobSchema):
    response: CostBenefitResponse = None


class ExposureBreakdownRequest(PlaceSchema):
    exposure_type: str = None
    exposure_categorisation: str
    scenario_year: int = None
    # aggregation_method: str = None
    units_exposure: str = None


class ExposureBreakdownBar(ResponseSchema):
    label: str
    location_scale: str = None
    category_labels: List[str]
    values: List[float]


class ExposureBreakdown(ResponseSchema):
    items: List[ExposureBreakdownBar]
    legend: CategoricalLegend
    units: str = None

    def convert_units(self, units_dict):
        if self.units:
            ResponseSchema.convert_units(self, units_dict)


class ExposureBreakdownResponse(ResponseSchema):
    data: ExposureBreakdown
    metadata: dict


class ExposureBreakdownJob(JobSchema):
    response: ExposureBreakdownResponse = None




