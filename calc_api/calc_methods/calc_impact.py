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
from calc_api.calc_methods.calc_hazard import get_hazard_from_api
from calc_api.calc_methods.calc_exposure import get_exposure, get_exposure_from_api, determine_api_exposure_type
from calc_api.vizz.enums import exposure_type_from_impact_type, HAZARD_TO_ABBREVIATION
from calc_api.calc_methods.util import standardise_scenario

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))



@shared_task(base=Singleton)
# @profile()
# @cache_memoize(timeout=conf.CACHE_TIMEOUT)
def get_impact_by_return_period(
        country,
        hazard_type,
        return_period,
        exposure_type=None,
        impact_type=None,
        scenario_name=None,
        scenario_growth=None,
        scenario_climate=None,
        hazard_year=None,
        exposure_year=None,
        location_poly=None,
        aggregation_scale=None):

    if not exposure_type:
        exposure_type = exposure_type_from_impact_type(impact_type)

    scenario_name, scenario_growth, scenario_climate = standardise_scenario(scenario_name, scenario_growth, scenario_climate)
    scenario_climate = scenario_climate if int(hazard_year) != 2020 else 'historical'
    scenario_growth = scenario_growth if int(exposure_year) != 2020 else 'historical'

    api_exposure_type, exponent = determine_api_exposure_type(exposure_type, scenario_growth, exposure_year)

    # TODO: consider making these simultaeous calls?
    haz = get_hazard_from_api(hazard_type, country, scenario_climate, hazard_year)
    exp = get_exposure_from_api(country, exposure_type, impact_type, scenario_name, scenario_growth, exposure_year)

    save_mat = (aggregation_scale != 'country')
    imp = _make_impact(haz, exp, hazard_type, exposure_type, impact_type, location_poly, save_mat)

    if aggregation_scale:
        if aggregation_scale == 'country':
            if return_period == 'aai':
                imp_rp = imp.aai_agg
            else:
                imp_rp = imp.calc_freq_curve((int(return_period))).impact
            imp_10yr_100yr = imp.calc_freq_curve((10, 100)).impact
        else:
            raise ValueError("Can't yet deal with aggregation scales that aren't country.")

        total_freq = sum(imp.frequency)
        mean_imp = np.average(imp.at_event, weights=imp.frequency) # TODO is this the right way to assess change in intensity/impacts?

        # TODO there's a better way to pass the freq/intensity info to the timeline widgets
        return [
            {"lat": float(np.median(exp.gdf['latitude'])),
             "lon": float(np.median(exp.gdf['longitude'])),
             "value": float(imp_rp),
             "total_freq": total_freq,
             "mean_imp": mean_imp,
             "imp_10yr": imp_10yr_100yr[0],
             "imp_100yr": imp_10yr_100yr[1]}
        ]

    # TODO should this be a separate celery job? with the (admittedly large) result above cached?
    if return_period == 'aai':
        imp_rp = imp.eai_exp
    else:
        imp_rp = imp.local_exceedance_imp(return_periods=(int(return_period)))[0]

    return [
        {"lat": float(coords[0]), "lon": float(coords[1]), "value": float(value)}
        for value, coords
        in zip(imp_rp, imp.coord_exp)
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
    imp = _make_impact(haz, exp, hazard_type, exposure_type, impact_type, location_poly, aggregation_scale)

    # TODO test this
    return [
        {"lat": coords[0], "lon": coords[1], "value": value}
        for value, coords
        in zip(imp.imp_mat.todense().flatten(), imp.coord_exp)
        if value >= 0
    ]



def _make_impact(haz,
                 exp,
                 hazard_type,
                 exposure_type,
                 impact_type,
                 location_poly,
                 save_mat):

    # TODO handle polygons, be sure it's not more efficient to make this another link of the chain
    if location_poly:
        raise ValueError("API doesn't handle polygons yet")

    # TODO make into another lookup
    if exposure_type == 'economic_assets':
        if impact_type == 'economic_loss':
            impf = ImpfTropCyclone.from_emanuel_usa()
        elif impact_type == 'assets_affected':
            impf = ImpactFunc.set_step_impf(intensity=(0, 33, 500))  # Cat 1 storm
        else:
            raise ValueError(f'impact_type with economic_assets must be economic_loss or assets_affected. Type = {impact_type}')
    elif exposure_type == 'people':
        if hazard_type == 'tropical_cyclone':
            impf = ImpactFunc.from_step_impf(intensity=(0, 54, 300))
        elif hazard_type == 'extreme_heat':
            impf = ImpactFunc.from_step_impf(intensity=(0, 1, 100))
        else:
            raise ValueError("hazard_type must be either 'tropical_cyclone' or 'extreme_heat'")
    else:
        raise ValueError("exposure_type must be either 'economic_assets' or 'people'")
    impact_funcs = ImpactFuncSet()
    impact_funcs.append(impf)

    abbrv = HAZARD_TO_ABBREVIATION[hazard_type]
    haz.tag.haz_type = abbrv
    impf_name = 'impf_' + abbrv
    exp.gdf[impf_name] = 1

    imp = Impact()
    imp.calc(exp, impact_funcs, haz, save_mat=save_mat)
    return imp



