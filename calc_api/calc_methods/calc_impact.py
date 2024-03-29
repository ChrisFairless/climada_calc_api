import logging
from cache_memoize import cache_memoize
from celery import shared_task
from celery_singleton import Singleton
import numpy as np
import copy
from scipy import interpolate

from climada.entity import Exposures, ImpactFunc, ImpactFuncSet, ImpfTropCyclone, Entity, MeasureSet, Measure
from climada.engine import Impact

from calc_api.calc_methods.profile import profile
from calc_api.config import ClimadaCalcApiConfig
from calc_api.calc_methods.calc_hazard import get_hazard_from_api, subset_hazard_extent
from calc_api.calc_methods.calc_exposure import get_exposure_from_api, subset_exposure_extent
from calc_api.vizz.enums import exposure_type_from_impact_type, HAZARD_TO_ABBREVIATION
from calc_api.calc_methods.util import standardise_scenario
from calc_api.vizz import units
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
        measures=None,
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

    if not measures:
        imp = Impact()
        imp.calc(exp, impact_funcs, haz, save_mat=save_mat)
    else:
        measure_set = MeasureSet()
        basic_impf = impact_funcs.get_func(fun_id=1)[0]
        if len(measures) > 1:
            LOGGER.warning('Currently we only apply the first measure. Combined measures comes later.')
        for measure_dict in measures:
            # TODO wrap this in another method (or write an __init__ for the climada class)
            gonna_need_a_new_impf = measure_dict['hazard_cutoff'] is not None and measure_dict['hazard_cutoff'] > 0
            if gonna_need_a_new_impf:
                new_impf = copy.deepcopy(basic_impf)
                new_impf.id = 2
                cutoff = measure_dict['hazard_cutoff']
                extra_points = np.array([cutoff, cutoff])
                new_impf.intensity = np.sort(np.append(basic_impf.intensity, extra_points))
                f_interpolate_mdd = interpolate.interp1d(basic_impf.intensity, basic_impf.mdd)
                cutoff_mdd_value = f_interpolate_mdd(cutoff)
                ix = np.array(basic_impf.intensity < cutoff)
                new_impf.mdd = np.append(np.append(np.zeros(sum(ix) + 1), cutoff_mdd_value), basic_impf.mdd[~ix])
                new_impf.paa = np.ones_like(new_impf.mdd)
                impact_funcs.append(new_impf)

            m = Measure()
            m.name = measure_dict['name']
            haz_abbrv = HAZARD_TO_ABBREVIATION[measure_dict['hazard_type']]
            m.haz_type = haz_abbrv
            m.cost = measure_dict['cost']  # TODO fix measure costs and implement scaling elsewhere
            if measure_dict['return_period_cutoff']:
                m.hazard_freq_cutoff = 1 / measure_dict['return_period_cutoff']

            hazard_scaling = [1, 0]
            if measure_dict['hazard_change_multiplier']:
                hazard_scaling[0] = measure_dict['hazard_change_multiplier']
            if measure_dict['hazard_change_constant']:
                hazard_scaling[1] = measure_dict['hazard_change_constant']
            m.hazard_inten_imp = tuple(hazard_scaling)

            if gonna_need_a_new_impf:
                m.imp_fun_map = '1to2'

            # m.mdd_impact = (1, 0)  # parameter a and b
            # m.paa_impact = (1, 0)  # parameter a and b

            if measure_dict['percentage_coverage'] != 100:
                raise ValueError('Percentage coverage not yet implemented')
            if measure_dict['percentage_effectiveness'] != 100:
                raise ValueError('Percentage assets affected not yet implemented')

            measure_set.append(m)

            # for name in measure_set.get_names():
            #     LOGGER.info("\nMEASURES:")
            #     LOGGER.info(name)
            #     for property, value in m.__dict__.items():
            #         LOGGER.info((property, ":", value))

            # TODO use CostBenefit module here
            LOGGER.warning('Not doing a full cost benefit calculation - no discounting')

            imp, _ = m.calc_impact(exposures=exp, imp_fun_set=impact_funcs, hazard=haz)

    if isinstance(return_periods, list):
        return_periods = np.array(return_periods)
    if isinstance(return_periods, (int, float, str)):
        return_periods = np.array([return_periods])

    return_periods_aai = np.array([rp == 'aai' for rp in return_periods])
    return_periods_int = ~return_periods_aai

    if any(return_periods_int):
        rps = [int(rp) for i, rp in enumerate(return_periods) if return_periods_int[i]]

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
                ix_nonzero = [i for i, imp in enumerate(freq_curve.impact) if imp != 0]
                if len(ix_nonzero) == 0:
                    LOGGER.warning('All calculated impacts are zero')
                    ix_last_zero = 0
                else:
                    ix_last_zero = ix_nonzero[0] - 1
                    ix_last_zero = max(0, ix_last_zero)
                freq_curve.return_per = freq_curve.return_per[ix_last_zero:]
                freq_curve.impact = freq_curve.impact[ix_last_zero:]

                ix = [rp > 1 for rp in freq_curve.return_per]
                freq_curve_dict = {
                    "return_per": list(freq_curve.return_per[ix]),
                    "impact": list(freq_curve.impact[ix])
                }
            else:
                if save_frequency_curve:
                    LOGGER.warning("Can't save a frequency curve for an AAI calculation. Ignoring.")
                    freq_curve_dict = None
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
             "freq_curve": None if not save_frequency_curve else freq_curve_dict
             }
        ]



    # TODO should this be a separate celery job? with the (admittedly large) result above cached?
    # The code here hasn't been used operationally ... activate with care
    LOGGER.warning("THIS CODE ISN'T READY YET: EDIT calc_impact.py")
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
        if hazard_type == 'tropical_cyclone':
            if impact_type == 'economic_impact':
                # TODO use Eberenz globally calibrated functions
                impf = ImpfTropCyclone.from_emanuel_usa()
            elif impact_type == 'assets_affected':
                impf = ImpactFunc.from_step_impf(intensity=(0, 33, 500))  # Cat 1 storm in m/s
                impf.haz_type = 'TC'
            else:
                raise ValueError(f'impact_type with economic_assets must be economic_impact or assets_affected. Type = {impact_type}')
        else:
            raise ValueError("We can't handle economic impacts with non-tropical cyclone hazards yet.")
    elif exposure_type == 'people':
        if hazard_type == 'tropical_cyclone':
            impf = ImpactFunc.from_step_impf(intensity=(0, 33, 300))
            impf.haz_type = 'TC'
        elif hazard_type == 'extreme_heat':
            impf = ImpactFunc.from_step_impf(intensity=(0, 35, 100))
            LOGGER.warning('Using a fake impact function for heat')
            impf.haz_type = 'EH'
        else:
            raise ValueError("hazard_type must be either 'tropical_cyclone' or 'extreme_heat'")
    else:
        raise ValueError("exposure_type must be either 'economic_assets' or 'people'")

    abbrv = HAZARD_TO_ABBREVIATION[hazard_type]
    impf.name = 'impf_' + abbrv
    impf.id = 1

    impact_funcs = ImpactFuncSet()
    impact_funcs.append(impf)

    return impact_funcs



