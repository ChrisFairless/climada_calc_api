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

    request = schemas.MeasureRequestSchema(
        measure_id=measure_id,
        slug=slug,
        hazard_type=hazard_type,
        exposure_type=exposure_type,
        units_hazard=units_hazard,
        units_currency=units_currency,
        units_distance=units_distance,
        units_temperature=units_temperature,
        units_speed=units_speed
    )
    request.standardise()

    # TODO: one day we'll want to make this work with any hazard unit type, even unknown ones.
    #  So we'll need to abstract this.
    units_dict = {}
    if request.units_hazard:
        unit_type = units.UNIT_TYPES[request.units_hazard]
        if unit_type == "temperature":
            if request.units_temperature:
                assert request.units_hazard == request.units_temperature
        elif unit_type == "speed":
            if request.units_speed:
                assert request.units_hazard == request.units_speed
        else:
            raise ValueError(f'Unexpected hazard unit type. Units: {request.units_hazard}. Type: {unit_type}')
        units_dict[unit_type] = request.units_hazard
    else:
        if request.units_temperature:
            units_dict['temperature'] = request.units_temperature
        if request.units_speed:
            units_dict['speed'] = request.units_speed
    units_dict['currency'] = request.units_currency

    if request.units_distance:
        units_dict['distance'] = request.units_distance
    else:
        units_dict['distance'] = units.NATIVE_UNITS_CLIMADA['distance']

    measures = models.Measure.objects.filter(user_generated=False)
    if request.measure_id:
        measures = measures.filter(id=request.measure_id)
    if request.slug:
        measures = measures.filter(slug=request.slug)
    if request.hazard_type:
        measures = measures.filter(hazard_type=request.hazard_type)
    if request.exposure_type:
        measures = measures.filter(exposure_type=request.exposure_type)
    measures_list = [schemas.MeasureSchema(**m.__dict__) for m in measures]
    # TODO can we move this conversion into the wrangle_units decorator like all the others?
    _ = [measure.convert_units(units_dict) for measure in measures_list]
    return measures_list


def widget_costbenefit(data: schemas_widgets.CostBenefitWidgetRequest):
    request_id = data.get_id()
    data_dict = data.dict()
    if not data.location_poly:
        data_dict['location_poly'] = util.bbox_to_wkt(data_dict['geocoding']['bbox'])
    data_dict['exposure_type'] = enums.exposure_type_from_impact_type(data.impact_type)

    if data.measure_ids and len(data.measure_ids) > 0:
        # TODO We work in CLIMADA native units and convert at the end
        measures = [
            get_default_measures(
                measure_id=m_id,
                units_hazard=data.units_hazard,
                units_currency=data.units_currency,
                units_distance=units.NATIVE_UNITS_CLIMADA['distance'],
            ) for m_id in data.measure_ids]
    else:
        measures = []

    # TODO move this into a schema validation/standardise method
    if len(measures) == 0 or any([len(m) == 0 for m in measures]):
        valid_measures = get_default_measures(
            hazard_type=data.hazard_type,
            exposure_type=data_dict['exposure_type'],
            units_hazard=data.units_hazard,
            units_currency=data.units_currency,
            units_speed=data.units_hazard,
            units_distance=units.NATIVE_UNITS_CLIMADA['distance'],
        )
        raise ValueError(f'Valid measures not found for the cost-benefit calculation'
                         f'\nMeasure ids provided: {data.measure_ids}'
                         f'\nHazard type: {data.hazard_type}'
                         f'\nExposure type: {data_dict["exposure_type"]}'
                         f'\nValid IDs: {[m.id for m in valid_measures]}'
                         f'\nValid names: {[m.name for m in valid_measures]}'
                         )

    units_dict = {
        units.UNIT_TYPES[data.units_hazard]: data.units_hazard,
        units.UNIT_TYPES[data.units_exposure]: data.units_exposure,
        'currency': data.units_currency
    }

    measures = [m[0].to_dict() for m in measures]
    data_dict.update({'measures': measures})
    calc_costbenefit.check_valid_measures(data_dict['measures'], data.hazard_type, data_dict['exposure_type'])

    request = schemas.CostBenefitRequest(**data_dict)

    if len(measures) > 1:
        raise ValueError('Sorry, this is a rush job and from this point onward we can only deal with one measure')

    callback_config = {
        'hazard_type': request.hazard_type,
        'scenario_name': request.scenario_name,
        'impact_type': request.impact_type,
        'units_exposure': request.units_exposure,
        'measure_name': measures[0]['name'],
        'measure_description': measures[0]['description'],
        'measure_cost': measures[0]['cost'],
        'units_currency': request.units_currency
    }

    # TODO make a costbenefit_calc class. Maybe it and timeline extend some calculations ur-class
    job_config_list, chord_header = calc_costbenefit.set_up_costbenefit_calculations(request)
    callback = combine_impacts_to_costbenefit_widget.s(
        job_config_list=job_config_list,
        report_year=data.scenario_year,
        config=callback_config
    )

    # with transaction.atomic():
    res = chord(chord_header, task_id=str(request_id))(callback)

    out = res.id
    return out


@shared_task()
def combine_impacts_to_costbenefit_widget(
        impacts_list,
        job_config_list,
        report_year,
        config
):
    LOGGER.debug('Combining impacts to costbenefit widget')
    costbenefit_data = calc_costbenefit.combine_impacts_to_costbenefit_no_celery(
        impacts_list=impacts_list,
        job_config_list=job_config_list
    )
    costbenefit_text = generate_costbenefit_widget_text(
        hazard_type=config['hazard_type'],
        scenario=config['scenario_name'],
        impact_type=config['impact_type'],
        measure_name=config['measure_name'],
        measure_description=config['measure_description'],
        measure_cost=costbenefit_data.data.cost[0],
        units_exposure=config['units_exposure'],
        units_currency=config['units_currency'],
        affected_present=costbenefit_data.data.items[0].current_climate,
        affected_measure=costbenefit_data.data.items[0].measure_change[0],
        affected_future=costbenefit_data.data.items[0].future_climate,
        affected_future_measure=costbenefit_data.data.items[0].measure_climate[0],
        future_year=report_year
    )

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