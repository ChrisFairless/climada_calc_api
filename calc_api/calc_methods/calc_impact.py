import logging
from cache_memoize import cache_memoize
from celery import shared_task
from celery_singleton import Singleton
import pandas as pd
import numpy as np

from climada.hazard import Hazard
from climada.entity import Exposures, ImpactFunc, ImpactFuncSet, ImpfTropCyclone
from climada.engine import Impact
from climada.util.api_client import Client
import climada.util.coordinates as u_coord

from calc_api.calc_methods.profile import profile
from calc_api.config import ClimadaCalcApiConfig
from calc_api.calc_methods.calc_hazard import get_hazard_from_api, subset_hazard_extent
from calc_api.calc_methods.calc_exposure import get_exposure_from_api, subset_exposure_extent
from calc_api.vizz.enums import exposure_type_from_impact_type, HAZARD_TO_ABBREVIATION
from calc_api.calc_methods.util import standardise_scenario
from calc_api.job_management.job_management import database_job

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))



@shared_task(base=Singleton)
@database_job
# @profile()
# @cache_memoize(timeout=conf.CACHE_TIMEOUT)
def get_impact_by_return_period(
        country,
        hazard_type,
        return_periods,
        exposure_type=None,
        impact_type=None,
        scenario_name=None,
        scenario_growth=None,
        scenario_climate=None,
        hazard_year=None,
        exposure_year=None,
        location_poly=None,
        aggregation_scale=None,
        save_frequency_curve=False):

    LOGGER.debug('Starting impact by RP calculation. Locals: ' + str(locals()))

    if not exposure_type:
        exposure_type = exposure_type_from_impact_type(impact_type)

    scenario_name, scenario_growth, scenario_climate = standardise_scenario(scenario_name, scenario_growth, scenario_climate)
    scenario_climate = scenario_climate if int(hazard_year) != 2020 else 'historical'
    scenario_growth = scenario_growth if int(exposure_year) != 2020 else 'historical'

    # TODO: consider making these simultaneous calls?
    haz = get_hazard_from_api(hazard_type, country, scenario_climate, hazard_year)
    exp = get_exposure_from_api(country, exposure_type, impact_type, scenario_name, scenario_growth, exposure_year)

    if location_poly:
        haz = subset_hazard_extent(haz, location_poly)
        exp = subset_exposure_extent(exp, location_poly)

    save_mat = save_frequency_curve or aggregation_scale != 'all'
    impact_funcs = infer_impactfuncset(hazard_type, exposure_type, impact_type)
    impf_name = impact_funcs.get_func(haz_type=haz.tag.haz_type, fun_id=1).name
    exp.gdf[impf_name] = 1

    imp = Impact()
    imp.calc(exp, impact_funcs, haz, save_mat=save_mat)

    return_periods = np.array(return_periods)
    return_periods_aai = return_periods == 'aai'
    return_periods_int = return_periods != 'aai'

    if any(return_periods_int):
        rps = [int(rp) for rp in return_periods[return_periods_int]]

    if aggregation_scale:
        if aggregation_scale == 'all':
            imp_by_rp = np.full(len(return_periods), None, dtype=float)
            if any(return_periods_aai):
                imp_rp_aai = imp.aai_agg
                imp_by_rp[return_periods_aai] = imp_rp_aai
            if any(return_periods_int):
                freq_curve = imp.calc_freq_curve()
                new_impact_by_return_period = np.interp(rps, freq_curve.return_per, freq_curve.impact)
                imp_by_rp[return_periods_int] = new_impact_by_return_period

                # Reduce the amount of data in the frequency curve
                ix = [rp > 1 for rp in freq_curve.return_per]
                freq_curve_dict = {
                    "return_per": list(freq_curve.return_per[ix]),
                    "impact": list(freq_curve.impact[ix])
                }
        else:
            raise ValueError("Can't yet deal with aggregation scales that aren't 'all'.")

        # TODO is this the right way to assess change in intensity/impacts?
        # TODO make the return values for this function consistent! (the pointwise return data doesn't have this)
        total_freq = sum(imp.frequency)
        mean_imp = np.average(imp.at_event, weights=imp.frequency)

        return [
            {"lat": float(np.median(exp.gdf['latitude'])),
             "lon": float(np.median(exp.gdf['longitude'])),
             "value": list(imp_by_rp),
             "total_freq": total_freq,
             "mean_imp": mean_imp,
             "freq_curve": freq_curve_dict if save_frequency_curve else None}
        ]



    # TODO should this be a separate celery job? with the (admittedly large) result above cached?
    if any(return_periods_aai):
        imp_rp_aai = imp.eai_exp
    else:
        imp_rp_aai = []

    if any(return_periods_int):
        imp_rp_int = imp.local_exceedance_imp(return_periods=rps)
    else:
        imp_rp_int = []
    combined_rp_imp = np.empty_like(return_periods)
    combined_rp_imp[return_periods_aai] = imp_rp_aai
    combined_rp_imp[return_periods_int] = imp_rp_int

    return [
        {"lat": float(coords[0]), "lon": float(coords[1]), "value": np.array(value)}
        for coords, value
        in zip(imp.coord_exp, zip(combined_rp_imp))
    ]


def get_impact_event(
        country,
        hazard_type,
        exposure_type,
        impact_type,
        scenario_name,
        scenario_year,
        event_name,
        location_poly=None,
        aggregation_scale=None):

    # TODO
    haz = get_hazard_from_api(hazard_type, country, scenario_name, scenario_year)
    exp = get_exposure_from_api(exposure_type, country, scenario_name, scenario_year)

    haz = haz.select(event_names=[event_name])
    # TODO update this calculation request!
    #imp = _make_impact(haz, exp, hazard_type, exposure_type, impact_type)

    # TODO test this
    return [
        {"lat": coords[0], "lon": coords[1], "value": value}
        for value, coords
        in zip(imp.imp_mat.todense().flatten(), imp.coord_exp)
        if value >= 0
    ]


def infer_impactfuncset(
        hazard_type,
        exposure_type,
        impact_type
):

    # TODO make into another lookup
    if exposure_type == 'economic_assets':
        if impact_type == 'economic_impact':
            impf = ImpfTropCyclone.from_emanuel_usa()
        elif impact_type == 'assets_affected':
            impf = ImpactFunc.from_step_impf(intensity=(0, 33, 500))  # Cat 1 storm in m/s
            impf.haz_type = 'TC'
        else:
            raise ValueError(f'impact_type with economic_assets must be economic_impact or assets_affected. Type = {impact_type}')
    elif exposure_type == 'people':
        if hazard_type == 'tropical_cyclone':
            impf = ImpactFunc.from_step_impf(intensity=(0, 33, 300))
            impf.haz_type = 'TC'
        elif hazard_type == 'extreme_heat':
            impf = ImpactFunc.from_step_impf(intensity=(0, 1, 100))
            impf.haz_type = 'EH'
        else:
            raise ValueError("hazard_type must be either 'tropical_cyclone' or 'extreme_heat'")
    else:
        raise ValueError("exposure_type must be either 'economic_assets' or 'people'")

    abbrv = HAZARD_TO_ABBREVIATION[hazard_type]
    impf.name = 'impf_' + abbrv

    impact_funcs = ImpactFuncSet()
    impact_funcs.append(impf)

    return impact_funcs



