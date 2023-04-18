import logging
import copy
import pandas as pd
import numpy as np

from django.db import transaction
from celery import chain, chord, shared_task
from celery_singleton import Singleton

import calc_api.vizz.schemas as schemas
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.enums import get_rp_options, exposure_type_from_impact_type, EXPOSURE_TO_UNIT_TYPE
from calc_api.vizz import units
from calc_api.calc_methods.calc_impact import get_impact_event, get_impact_by_return_period
from calc_api.job_management import standardise_schema
from calc_api.job_management.job_management import database_job

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# TODO get this working
def costbenefit(request: schemas.CostBenefitRequest):
    # For some worrying reason this throws an error when I use the @standardise_schema decorator
    # but nothing uses this for now so it's ok?
    request.standardise()
    job_config_list, chord_header = set_up_costbenefit_calculations(request)

    # with transaction.atomic():
    res = chord(chord_header)(
        combine_impacts_to_costbenefit.s(job_config_list)
    )
    out = res.id
    return out


def set_up_costbenefit_calculations(request: schemas.CostBenefitRequest):
    LOGGER.debug('Setting up costbenefit celery tasks')
    job_config_list = []
    baseline_config = {
        'job_name': 'baseline risk',
        'haz_year': 2020,
        'exp_year': 2020,
        'climate_change': False,
        'economic_growth': False,
        'measures': None,
        'hazard_type': request.hazard_type,
        'impact_type': request.impact_type,
    }
    job_config_list.append(baseline_config)

    growth_config = copy.deepcopy(baseline_config)
    growth_config.update({
        'job_name': 'baseline + growth',
        'exp_year': request.scenario_year,
        'economic_growth': True
    })
    if request.scenario_year != 2020:
        job_config_list.append(growth_config)

    climate_config = copy.deepcopy(growth_config)
    climate_config.update({
        'job_name': 'baseline + growth + climate change',
        'haz_year': request.scenario_year,
        'climate_change': True
    })
    if request.scenario_year != 2020:
        job_config_list.append(climate_config)

    if request.measures:
        for m in request.measures:
            m = schemas.MeasureSchema(**m)
            m.convert_to_climada_units()
            measure_config = copy.deepcopy(baseline_config)
            measure_config.update({
                'job_name': f'current climate with {m.name}',
                'measures': [m.dict()],
            })
            job_config_list.append(measure_config)
            measure_config_climate = copy.deepcopy(climate_config)
            measure_config_climate.update({
                'job_name': f'future climate with {m.name}',
                'measures': [m.dict()],
            })
            job_config_list.append(measure_config_climate)
        # # For now we won't do combined measures calculations
        # if len(request.measures) > 1:
        #     all_measures = copy.deepcopy(climate_config)
        #     all_measures.update({
        #         'job_name': 'future climate with all measures combined',
        #         'measures': [m.to_dict() for m in request.measures]
        #     })
        #     job_config_list = job_config_list.append(all_measures)

    chord_header = [
        get_impact_by_return_period.s(
            country=request.geocoding.country_id,
            hazard_type=request.hazard_type,
            return_periods='aai',
            exposure_type=request.exposure_type,
            impact_type=request.impact_type,
            scenario_name=request.scenario_name,
            scenario_growth=request.scenario_growth,
            scenario_climate=request.scenario_climate,
            measures=job_config['measures'],
            hazard_year=job_config['haz_year'],
            exposure_year=job_config['exp_year'],
            location_poly=request.location_poly,
            aggregation_scale='all',
            save_frequency_curve=False
        )
        for job_config in job_config_list
    ]

    return job_config_list, chord_header


@shared_task()
def combine_impacts_to_costbenefit(impacts_list, job_config_list):
    return combine_impacts_to_costbenefit_no_celery(impacts_list, job_config_list)


def combine_impacts_to_costbenefit_no_celery(impacts_list, job_config_list):
    if len(impacts_list) != len(job_config_list):
        raise ValueError(f'impacts and configs are not the same length: {len(impacts_list)} vs {len(job_config_list)}')

    for i, _ in enumerate(impacts_list):
        if len(impacts_list[i]) != 1:
            raise ValueError('Impacts provided to costben calculation have more than one location')
        job_config_list[i]['impact'] = impacts_list[i][0]['value']

    df = pd.DataFrame(job_config_list)
    df['hazard_rp'] = 'aai'
    df['impact'] = pd.Series([np.array(impact) for impact in df['impact']])

    future_year = max(df['exp_year'])
    haz_type = df['hazard_type'][0]
    rp = df['hazard_rp'][0]
    exposure_type = exposure_type_from_impact_type(job_config_list[0]['impact_type'])

    # This could maybe be simpler, but I was having bugs with celery duplicating jobs so we're copying the timeline code
    # Come back and simplify this maybe, but not now.
    ix_measures = np.array([isinstance(m, (list, np.ndarray)) for m in df['measures']])  # what's the RIGHT way to do this
    ix_current_climate = (df['haz_year'] == 2020) & (df['exp_year'] == 2020) & ~ix_measures
    ix_future_climate = (df['haz_year'] == future_year) & (df['exp_year'] == future_year) & ~ix_measures
    ix_only_growth = (df['haz_year'] == 2020) & (df['exp_year'] == future_year) & ~ix_measures
    ix_single_measures = [measure is not None and len(measure) == 1 for measure in df['measures']]
    # ix_all_measures = [measure is not None and len(measure) > 1 for measure in df['measures']]
    current_climate = np.array(df.loc[ix_current_climate]['impact'])
    future_climate = np.array(df.loc[ix_future_climate]['impact'])
    only_growth = np.array(df.loc[ix_only_growth]['impact'])

    growth_change = only_growth - current_climate
    climate_change = future_climate - only_growth

    if any(ix_single_measures):
        measures_list = [m[0] for m in df.loc[ix_single_measures]['measures']]
        measure_names = list(np.unique([m['name'] for m in measures_list]))
        ix_current_single_measures = ix_single_measures & (df['haz_year'] == 2020) & (df['exp_year'] == 2020)
        ix_future_single_measures = ix_single_measures & (df['haz_year'] == future_year) & (df['exp_year'] == future_year)
        measure_current_climate = pd.Series(df.loc[ix_current_single_measures]['impact'])
        measure_future_climate = pd.Series(df.loc[ix_future_single_measures]['impact'])
        measure_current_change = [m - current_climate for m in measure_current_climate]
        measure_future_change = [m - future_climate for m in measure_future_climate]
    else:
        measures_list = None
        measure_names = None
        measure_current_climate = None
        measure_future_climate = None
        measure_current_change = None
        measure_future_change = None

    # # For now we won't do all measures
    # if any(ix_all_measures):
    #     all_measure_climate = np.array(df.iloc[ix_all_measures]['impact'])
    #     combined_measure_change = all_measure_climate - climate_change
    # else:
    #     combined_measure_change = None

    costbenefit_breakdown = schemas.BreakdownBar(
        year_label=str(future_year),
        year_value=int(future_year),
        temperature=-999.0,
        current_climate=float(current_climate),
        growth_change=float(growth_change),
        climate_change=float(climate_change),
        future_climate=float(future_climate),
        measure_names=measure_names,
        measure_change=list(measure_future_change),
        measure_climate=list(measure_future_climate),
        combined_measure_change=None,
        combined_measure_climate=None
    )

    # TODO allow for any return period - the options limitations should happen somewhere else?
    rp_description = get_rp_options(
        hazard_type=haz_type,
        get_value='name',
        parameters={'value': rp}
    )
    if len(rp_description) == 0:
        all_rps = get_rp_options(hazard_type=haz_type, get_value='value')
        raise ValueError(f'Did not find {haz_type} return period data matching your request. Requested: {rp}, options: {all_rps}')
    rp_description = rp_description[0]

    if measure_names:
        title_measure_description = ' with measures ' + measure_names[0]
        if len(measure_names) > 1:
            for name in measure_names[1:]:
                title_measure_description = title_measure_description + ' and ' + name
    else:
        title_measure_description = ''

    title = f'Components of {haz_type} climate risk{title_measure_description}: {rp_description}'

    description = f'Components of {haz_type} risk with adaptation: {rp_description}'  # TODO expand

    legend_items = [
            schemas.CategoricalLegendItem(label="Risk today", slug="current_climate", value=current_climate),
            schemas.CategoricalLegendItem(label="change from growth", slug="growth_change", value=growth_change),
            schemas.CategoricalLegendItem(label="change from climate change", slug="climate_change", value=climate_change)
    ]
    if measure_names:
        legend_items = legend_items + [
            schemas.CategoricalLegendItem(
                label=f"change from adaptation measure: {name}",
                slug=f"adaptation_{i}",
                value=change)
            for i, (name, change) in enumerate(zip(measure_names, measure_future_change))
        ]
    # TODO add combined measures
    # legend_items = legend_items + [
    #     schemas.CategoricalLegendItem(label="+ combined measures", slug="plus_combined_measures", value=example_value)
    # ]

    climada_exposure_units = units.NATIVE_UNITS_CLIMADA[EXPOSURE_TO_UNIT_TYPE[exposure_type]]

    legend = schemas.CategoricalLegend(
        title=title,
        units=climada_exposure_units,
        items=legend_items
    )

    out_measures = [schemas.MeasureSchema(**m) for m in measures_list]
    out_costs = [m['cost'] for m in measures_list]
    n_years = future_year - 2020 + 1
    # TODO apply discount rates
    benefit_total_discounted = list(0.5 * (-np.array(measure_current_change) - np.array(measure_future_change)) * n_years)
    out_costbenefits = [benefit/cost for cost, benefit in zip(out_costs, benefit_total_discounted)]

    out_costbenefit = schemas.CostBenefit(
        items=[costbenefit_breakdown],
        legend=legend,
        measure=out_measures,
        cost=out_costs,
        benefit_current=[-m for m in measure_current_change],
        benefit_future=[-m for m in measure_future_change],
        benefit_total_discounted=benefit_total_discounted,
        costbenefit=out_costbenefits,
        combined_cost=None,
        combined_benefit_current=None,
        combined_benefit_future=None,
        combined_costbenefit_total_discounted=None,
        units_currency=units.NATIVE_UNITS_CLIMADA['currency'],
        units_warming=units.NATIVE_UNITS_CLIMADA['temperature'],
        units_response=climada_exposure_units
    )

    metadata = schemas.CostBenefitMetadata(
        description=description
    )

    output = schemas.CostBenefitResponse(data=out_costbenefit, metadata=metadata)

    return output


def check_valid_measures(measures_list, hazard_type, exposure_type):
    for measure in measures_list:
        if isinstance(measure, dict):
            measure = schemas.MeasureSchema.from_dict(measure)
        if measure.hazard_type != hazard_type:
            raise ValueError(f'Measure {measure.name} hazard type ({measure.hazard_type} does not match requested calculation ({hazard_type})')
        if measure.exposure_type != exposure_type:
            raise ValueError(f'Measure {measure.name} exposure type ({measure.exposure_type}) does not match requested calculation ({exposure_type})')