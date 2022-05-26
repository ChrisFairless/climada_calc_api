import logging
import json
import pandas as pd
import numpy as np
from millify import millify

from django.db import transaction
from celery import chain, chord, shared_task
from celery_singleton import Singleton

from climada.engine.impact import Impact
from climada.entity import ImpactFunc, ImpactFuncSet, ImpfTropCyclone, Exposures
from climada.hazard import Hazard

import calc_api.vizz.schemas as schemas
from calc_api.calc_methods.util import country_iso_from_parameters
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.enums import get_year_options, get_rp_options
from calc_api.calc_methods.calc_hazard import get_hazard_event, get_hazard_by_return_period
from calc_api.calc_methods.calc_exposure import get_exposure
from calc_api.calc_methods.calc_impact import get_impact_event, get_impact_by_return_period
from calc_api.calc_methods.mapping import points_to_map_response
from calc_api.calc_methods.colourmaps import Legend, PALETTE_HAZARD_COLORCET, PALETTE_EXPOSURE_COLORCET, PALETTE_IMPACT_COLORCET
from calc_api.vizz.util import options_return_period_to_description

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


def timeline_hazard(request: schemas.TimelineHazardRequest):
    raise ValueError('Endpoint not ready')


def timeline_impact(request: schemas.TimelineImpactRequest):
    job_config_list, chord_header = set_up_timeline_calculations(request)

    # with transaction.atomic():
    res = chord(chord_header)(
        combine_impacts_to_timeline.s(job_config_list)
    )
    out = res.id
    return out


def set_up_timeline_calculations(request: schemas.TimelineImpactRequest):
    if request.scenario_name == 'historical':
        LOGGER.warning('Making a timeline calculation where all scenario components are historical')
    year_choices = get_year_options(request.hazard_type)
    years_to_calculate = [year['value'] for year in year_choices]
    country_iso3 = country_iso_from_parameters(
        location_scale=request.location_scale,
        location_code=request.location_code,
        location_name=request.location_name,
        location_poly=request.location_poly,
        representation="alpha3"
    )

    def is_historical(haz_year, exp_year):
        return (haz_year == exp_year) and (haz_year == 2020)

    job_config_list = [{
        'haz_year': int(haz_year),
        'exp_year': int(exp_year),
        # 'scenario_name': 'historical' if is_historical(haz_year, exp_year) else request.scenario_name,
        # 'scenario_growth': 'historical' if is_historical(haz_year, exp_year) else request.scenario_growth,
        # 'scenario_climate': 'historical' if is_historical(haz_year, exp_year) else request.scenario_climate,
        'climate_change': int(haz_year) != 2020,
        'economic_growth': int(exp_year) != 2020,
        'hazard_type': request.hazard_type,
        'hazard_rp': request.hazard_rp,
        'impact_type': request.impact_type,
        'units_response': request.units_response,
        'units_warming': request.units_warming
        }
        for exp_year in years_to_calculate
        for haz_year in np.unique([2020, exp_year])
    ]

    chord_header = [
        get_impact_by_return_period.s(
            country=country_iso3,
            hazard_type=request.hazard_type,
            return_period=request.hazard_rp,
            exposure_type=request.exposure_type,
            impact_type=request.impact_type,
            scenario_name=request.scenario_name,
            scenario_growth=request.scenario_growth,
            scenario_climate=request.scenario_climate,
            hazard_year=job_config['haz_year'],
            exposure_year=job_config['exp_year'],
            location_poly=request.location_poly,
            aggregation_scale=request.location_scale
        )
        for job_config in job_config_list
    ]

    return job_config_list, chord_header


@shared_task(base=Singleton)
def combine_impacts_to_timeline(impacts_list, job_config_list):
    return combine_impacts_to_timeline_no_celery(impacts_list, job_config_list)


def combine_impacts_to_timeline_no_celery(impacts_list, job_config_list):
    for i, job in enumerate(job_config_list):
        if len(impacts_list[i]) != 1:
            raise ValueError('Impacts provided to timeline calculation have more than one location')
        job['impact'] = impacts_list[i][0]['value']

    df = pd.DataFrame(job_config_list)
    df.sort_values(by=['exp_year', 'haz_year'], inplace=True)

    haz_type = job_config_list[0]["hazard_type"]
    year_list = np.sort(np.unique(df['exp_year']))
    current_climate = float(df[(df['haz_year'] == 2020) & (df['exp_year'] == 2020)]['impact'])
    future_climate = np.array(df[(df['haz_year'] == df['exp_year'])]['impact'])
    only_growth = np.array(df[(df['haz_year'] == 2020)]['impact'])
    population_change_array = only_growth - current_climate
    climate_change_array = future_climate - only_growth
    #
    # LOGGER.debug(df)
    # LOGGER.debug('ARRAYS')
    # LOGGER.debug('current_climate')
    # LOGGER.debug(current_climate)
    # LOGGER.debug('future_climate')
    # LOGGER.debug(future_climate)
    # LOGGER.debug('only_growth')
    # LOGGER.debug(only_growth)
    # LOGGER.debug('population_change')
    # LOGGER.debug(population_change_array)
    # LOGGER.debug('climate_change')
    # LOGGER.debug(climate_change_array)


    # population_change_list= [job['impact'] for job in impacts_list if job['haz_year']==2020]
    # climate_change_list = [job['impact'] for job in impacts_list if job['haz_year']==job['exp_year']]

    if job_config_list[0]['units_response'] not in ['dollars', 'people']:
        raise ValueError(f'Unit conversion not implemented yet. Units must be dollars or people. Provided: {job_config_list[0]["units_response"]}')

    timeline_bars = [
        schemas.TimelineBar(
            year_label=str(year),
            year_value=int(year),
            temperature=-999.0,
            current_climate=float(current_climate),
            future_climate=float(fut),
            population_change=float(pop),
            climate_change=float(clim),
        )
        for year, fut, pop, clim in zip(year_list, future_climate, population_change_array, climate_change_array)
    ]
    #
    # LOGGER.debug('dumping timelinebar')
    # LOGGER.debug(timeline_bars[0].__dict__)
    # LOGGER.debug(json.dumps(timeline_bars[0].yearLabel))
    # LOGGER.debug(json.dumps(timeline_bars[0].yearValue))
    # LOGGER.debug(json.dumps(timeline_bars[0].temperature))
    # LOGGER.debug(json.dumps(timeline_bars[0].current_climate))
    # LOGGER.debug(json.dumps(timeline_bars[0].future_climate))
    # LOGGER.debug(json.dumps(timeline_bars[0].population_change))
    # LOGGER.debug('internal dump method')
    # LOGGER.debug(timeline_bars[0].json(exclude_unset=True))
    # LOGGER.debug('internal include unset')
    # LOGGER.debug(timeline_bars[0].json())
    # LOGGER.debug('let us try the new dumps method then')

    rp_description = get_rp_options(
        hazard_type=haz_type,
        get_value='name',
        parameters={'value': job_config_list[0]['hazard_rp']}
    )[0]

    title = f'Components of {haz_type} risk: {rp_description}'
    description = f'Components of {haz_type} risk: {rp_description}'  # TODO expand
    example_value = millify(max(df['impact']))

    legend = schemas.CategoricalLegend(
        title=title,
        units=job_config_list[0]['units_response'],
        items=[
            schemas.CategoricalLegendItem(label="Risk today", slug="risk_today", value=example_value),
            schemas.CategoricalLegendItem(label="+ growth", slug="plus_growth", value=example_value),
            schemas.CategoricalLegendItem(label="+ climate change", slug="plus_climate_change", value=example_value)
        ]
    )

    timeline = schemas.Timeline(
        items=timeline_bars,
        legend=legend,
        units_temperature=job_config_list[0]['units_warming'],
        units_response=job_config_list[0]['units_response']
    )

    metadata = schemas.TimelineMetadata(
        description=description
    )

    # LOGGER.debug('RESPONSE')
    # LOGGER.debug(schemas.TimelineResponse(data=timeline, metadata=metadata))

    return schemas.TimelineResponse(data=timeline, metadata=metadata)