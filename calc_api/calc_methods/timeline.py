import logging
import pandas as pd
import numpy as np
from millify import millify

from django.db import transaction
from celery import chain, chord, shared_task
from celery_singleton import Singleton

import calc_api.vizz.schemas as schemas
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.enums import get_year_options, get_rp_options
from calc_api.calc_methods.calc_impact import get_impact_event, get_impact_by_return_period
from calc_api.vizz.units import NATIVE_UNITS_CLIMADA, UNIT_TYPES
from calc_api.job_management.job_management import database_job
from calc_api.job_management.standardise_schema import standardise_schema

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


@standardise_schema
def set_up_timeline_calculations(request: schemas.TimelineImpactRequest):
    if request.scenario_name == 'historical':
        LOGGER.warning('Making a timeline calculation where all scenario components are historical')
    year_choices = get_year_options(request.hazard_type)
    years_to_calculate = [year['value'] for year in year_choices]

    def is_historical(haz_year, exp_year):
        return (haz_year == exp_year) and (haz_year == 2020)

    job_config_list = [{
        'haz_year': int(haz_year),
        'exp_year': int(exp_year),
        # 'scenario_name': 'historical' if is_historical(haz_year, exp_year) else request.scenario_name,
        # 'scenario_growth': 'historical' if is_historical(haz_year, exp_year) else request.scenario_growth,
        # 'scenario_climate': 'historical' if is_historical(haz_year, exp_year) else request.scenario_climate,
        'economic_growth': int(exp_year) != 2020,
        'climate_change': int(haz_year) != 2020,
        'hazard_type': request.hazard_type,
        'hazard_rp': request.hazard_rp,
        'impact_type': request.impact_type,
        'units_exposure': request.units_exposure,
        'units_warming': request.units_warming
        }
        for exp_year in years_to_calculate
        for haz_year in np.unique([2020, exp_year])
    ]

    print("\n\nJOB CONFIG")
    print(str(job_config_list[0]))

    chord_header = [
        get_impact_by_return_period.s(
            country=request.geocoding.country_id,
            hazard_type=request.hazard_type,
            return_periods=request.hazard_rp,
            exposure_type=request.exposure_type,
            impact_type=request.impact_type,
            scenario_name=request.scenario_name,
            scenario_growth=request.scenario_growth,
            scenario_climate=request.scenario_climate,
            hazard_year=job_config['haz_year'],
            exposure_year=job_config['exp_year'],
            location_poly=request.location_poly,
            aggregation_scale='all',
            save_frequency_curve=True
        )
        for job_config in job_config_list
    ]

    return job_config_list, chord_header


@shared_task(base=Singleton)
@database_job
def combine_impacts_to_timeline(impacts_list, job_config_list):
    return combine_impacts_to_timeline_no_celery(impacts_list, job_config_list)


def combine_impacts_to_timeline_no_celery(impacts_list, job_config_list):
    for i, _ in enumerate(job_config_list):
        if len(impacts_list[i]) != 1:
            raise ValueError('Impacts provided to timeline calculation have more than one location')
        job_config_list[i]['impact'] = impacts_list[i][0]['value']

    # When multiple return periods are used, cells with impact data contain ARRAYS in this data frame
    df = pd.DataFrame(job_config_list)
    df['impact'] = pd.Series([np.array(impact) for impact in df['impact']])
    df.sort_values(by=['exp_year', 'haz_year'], inplace=True)

    haz_type = job_config_list[0]["hazard_type"]
    year_list = np.sort(np.unique(df['exp_year']))
    current_climate = np.array(df[(df['haz_year'] == 2020) & (df['exp_year'] == 2020)]['impact'][0])
    future_climate = pd.Series(df[(df['haz_year'] == df['exp_year'])]['impact'])
    only_growth = pd.Series(df[(df['haz_year'] == 2020)]['impact'])
    growth_change = pd.Series(scenario_growth - current_climate for scenario_growth in only_growth)
    climate_change = pd.Series(
        scenario_future - scenario_growth for scenario_future, scenario_growth in zip(future_climate, only_growth)
    )

    timeline_list = []

    # Create a timeline item for each input return period:
    for i, rp in enumerate(job_config_list[0]['hazard_rp']):

        exposure_units_type = UNIT_TYPES[job_config_list[0]['units_exposure']]

        # Create a list of bar items for each return period
        timeline_bars = [
            schemas.BreakdownBar(
                year_label=str(year),
                year_value=int(year),
                temperature=None,
                current_climate=float(current_climate[i]),
                growth_change=float(pop[i]),
                climate_change=float(clim[i]),
                future_climate=float(fut[i])
            )
            for year, fut, pop, clim in zip(year_list, future_climate, growth_change, climate_change)
        ]

        rp_description = get_rp_options(
            hazard_type=haz_type,
            get_value='name',
            parameters={'value': rp}
        )[0]

        title = f'Components of {haz_type} risk: {rp_description}'
        description = f'Components of {haz_type} risk: {rp_description}'  # TODO expand
        example_value = millify(max(df['impact'][0]))

        legend = schemas.CategoricalLegend(
            title=title,
            units=NATIVE_UNITS_CLIMADA[exposure_units_type],
            items=[
                schemas.CategoricalLegendItem(label="Risk today", slug="current_climate"),
                schemas.CategoricalLegendItem(label="+ growth", slug="growth_change"),
                schemas.CategoricalLegendItem(label="+ climate change", slug="climate_change")
            ]
        )

        timeline = schemas.Timeline(
            items=timeline_bars,
            legend=legend,
            units_warming=NATIVE_UNITS_CLIMADA['temperature'],
            units_response=NATIVE_UNITS_CLIMADA[exposure_units_type]
        )

        metadata = schemas.TimelineMetadata(
            description=description
        )

        output_timeline = schemas.TimelineResponse(data=timeline, metadata=metadata)
        output_timeline.convert_units({
            'temperature': job_config_list[0]['units_warming'],
            exposure_units_type: job_config_list[0]['units_exposure']
        })
        timeline_list.append(output_timeline)

    # LOGGER.debug('RESPONSE')
    # LOGGER.debug(schemas.TimelineResponse(data=timeline, metadata=metadata))

    return timeline_list
