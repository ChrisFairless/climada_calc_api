import logging
import numpy as np
import pandas as pd
from typing import List
from celery import chain, chord, group, shared_task
from celery_singleton import Singleton

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz import schemas, schemas_widgets
import calc_api.vizz.models as models
from calc_api.vizz.text_costbenefit import generate_costbenefit_widget_text
from calc_api.calc_methods import costbenefit
from calc_api.job_management.job_management import database_job

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


def get_default_measures(measure_id=None, hazard_type: str = None, exposure_type: str = None):
    measures = models.Measure.objects.filter(user_generated=False)
    if measure_id:
        if isinstance(measure_id, (int, float)):
            measure_id = [measure_id]
        measures = measures.filter(id__in=tuple(measure_id))
    if hazard_type:
        measures = measures.filter(hazard_type=hazard_type)
    if exposure_type:
        measures = measures.filter(exposure_type=exposure_type)
    return [schemas.MeasureSchema(**m.__dict__) for m in measures]


def widget_costbenefit(data: schemas_widgets.CostBenefitWidgetRequest):
    data.standardise()
    data_dict = data.dict()
    if data.measure_ids and len(data.measure_ids) > 0:
        measures = get_default_measures(measure_id=data.measure_ids)
        measures = [m.to_dict() for m in measures]
        data_dict.update({'measures': measures})
        costbenefit.check_valid_measures(data_dict['measures'], data.hazard_type, data.exposure_type)
    else:
        measures = []

    if len(measures) == 0:
        valid_measures = get_default_measures(hazard_type=data.hazard_type, exposure_type=data.exposure_type)
        raise ValueError(f'No valid measures found for the cost-benefit calculation'
                         f'\nMeasure ids provided: {data.measure_ids}'
                         f'\nHazard type: {data.hazard_type}'
                         f'\nExposure type: {data.exposure_type}'
                         f'\nValid IDs: {[m.id for m in valid_measures]}'
                         f'\nValid names: {[m.name for m in valid_measures]}'
                         )

    request = schemas.CostBenefitRequest(**data_dict)

    # from calc_api.calc_methods.timeline import set_up_timeline_calculations
    job_config_list, chord_header = costbenefit.set_up_costbenefit_calculations(request)
    callback = combine_impacts_to_costbenefit_widget.s(job_config_list=job_config_list)

    # with transaction.atomic():
    res = chord(chord_header)(callback)

    out = res.id
    return out


@shared_task(base=Singleton)
def combine_impacts_to_costbenefit_widget(impacts_list, job_config_list):
    costbenefit_data = costbenefit.combine_impacts_to_costbenefit_no_celery(
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