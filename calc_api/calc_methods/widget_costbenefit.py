import logging
from celery import chain, chord, group, shared_task
from celery_singleton import Singleton

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz import schemas, schemas_widgets, enums
import calc_api.vizz.models as models
from calc_api.vizz.text_costbenefit import generate_costbenefit_widget_text
from calc_api.calc_methods import calc_costbenefit
from calc_api.job_management.job_management import database_job
from calc_api.job_management.standardise_schema import standardise_schema
from calc_api.calc_methods import util
from calc_api.vizz import units

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


def get_default_measures(
        measure_id: int = None,
        slug: str = None,
        hazard_type: str = None,
        exposure_type: str = None,
        units_hazard: str = None,
        units_currency: str = None,
        units_distance: str = None,
        units_temperature: str = None,
        units_speed: str = None
):
    # TODO: one day we'll want to make this work with any hazard unit type, even unknown ones.
    #  So we'll need to abstract this.
    units_dict = {}
    if units_hazard:
        if not hazard_type:
            raise ValueError('The units_hazard parameter can only be used when hazard_type is set. '
                             'Use units_temperature and units_speed otherwise')
        unit_type = units.UNIT_TYPES[units_hazard]
        if unit_type == "temperature":
            assert units_hazard == units_temperature
        elif unit_type == "speed":
            assert units_hazard == units_speed
        else:
            raise ValueError(f'Unexpected hazard unit type. Units: {units_hazard}. Type: {unit_type}')
        units_dict[unit_type] = units_hazard
    else:
        if units_temperature:
            units_dict['temperature'] = units_temperature
        if units_speed:
            units_dict['speed'] = units_speed
    units_dict['currency'] = units_currency

    measures = models.Measure.objects.filter(user_generated=False)
    if measure_id:
        measures = measures.filter(id=measure_id)
    if slug:
        measures = measures.filter(slug=slug)
    if hazard_type:
        measures = measures.filter(hazard_type=hazard_type)
    if exposure_type:
        measures = measures.filter(exposure_type=exposure_type)
    measures_list = [schemas.MeasureSchema(**m.__dict__) for m in measures]
    _ = [measure.convert_units(units_dict) for measure in measures_list]
    return measures_list



@standardise_schema
def widget_costbenefit(data: schemas_widgets.CostBenefitWidgetRequest):
    request_id = data.get_id()
    data_dict = data.dict()
    if not data.location_poly:
        data_dict['location_poly'] = util.bbox_to_wkt(data_dict['geocoding']['bbox'])
    data_dict['exposure_type'] = enums.exposure_type_from_impact_type(data.impact_type)
    if data.measure_ids and len(data.measure_ids) > 0:
        measures = [get_default_measures(measure_id=m_id) for m_id in data.measure_ids]
    else:
        measures = []

    # TODO move this into a schema validation/standardise method
    if len(measures) == 0 or any([len(m) == 0 for m in measures]):
        valid_measures = get_default_measures(hazard_type=data.hazard_type, exposure_type=data_dict['exposure_type'])
        raise ValueError(f'Valid measures not found for the cost-benefit calculation'
                         f'\nMeasure ids provided: {data.measure_ids}'
                         f'\nHazard type: {data.hazard_type}'
                         f'\nExposure type: {data_dict["exposure_type"]}'
                         f'\nValid IDs: {[m.id for m in valid_measures]}'
                         f'\nValid names: {[m.name for m in valid_measures]}'
                         )

    measures = [m[0].to_dict() for m in measures]
    data_dict.update({'measures': measures})
    calc_costbenefit.check_valid_measures(data_dict['measures'], data.hazard_type, data_dict['exposure_type'])

    request = schemas.CostBenefitRequest(**data_dict)

    # TODO make a costbenefit_calc class. Maybe it and timeline extend some calculations ur-class
    job_config_list, chord_header = calc_costbenefit.set_up_costbenefit_calculations(request)
    callback = combine_impacts_to_costbenefit_widget.s(job_config_list=job_config_list)

    # with transaction.atomic():
    res = chord(chord_header, task_id=str(request_id))(callback)

    out = res.id
    return out


@shared_task()
def combine_impacts_to_costbenefit_widget(impacts_list, job_config_list):
    LOGGER.debug('Combining impacts to costbenefit widget')
    costbenefit_data = calc_costbenefit.combine_impacts_to_costbenefit_no_celery(
        impacts_list=impacts_list,
        job_config_list=job_config_list
    )
    costbenefit_text = generate_costbenefit_widget_text()

    widget_data = schemas_widgets.CostBenefitWidgetData(
        text=costbenefit_text,
        chart=costbenefit_data.data
    )

    metadata = schemas.CostBenefitMetadata(
        description=''
    )

    return schemas_widgets.CostBenefitWidgetResponse(
        data=widget_data,
        metadata=metadata
    )