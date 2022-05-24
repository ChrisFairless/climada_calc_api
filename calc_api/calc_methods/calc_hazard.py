import logging
import numpy as np
from cache_memoize import cache_memoize
from celery import shared_task
from celery_singleton import Singleton
import pandas as pd

from climada.hazard import Hazard
from climada.util.api_client import Client
import climada.util.coordinates as u_coord

from calc_api.calc_methods.profile import profile
from calc_api.config import ClimadaCalcApiConfig
from calc_api.calc_methods.util import standardise_scenario
from calc_api.vizz.enums import ScenarioClimateEnum, HazardTypeEnum

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# TODO split this into get_hazard_by_return_period and get_hazard and make get_hazard_from_api an internal function
# i.e. this handles all the processing and decoding of a mess of different parameters
@shared_task(base=Singleton)
# @profile()
# @cache_memoize(timeout=conf.CACHE_TIMEOUT)
def get_hazard_by_return_period(
        country,
        hazard_type,
        return_period,
        scenario_name,
        scenario_climate,
        scenario_year,
        location_poly=None,
        aggregation_scale=None):

    scenario_name, _, scenario_climate = standardise_scenario(
        scenario_name=scenario_name,
        scenario_climate=scenario_climate,
        scenario_year=scenario_year
    )
    haz = get_hazard_from_api(hazard_type, country, scenario_name, scenario_year)
    # TODO handle polygons, be sure it's not more efficient to make this another link of the chain
    if location_poly:
        raise ValueError("API doesn't handle polygons yet")
        # haz = subset_hazard_extent(hazard_type,
        #                            country,
        #                            scenario_name,
        #                            scenario_year,
        #                            return_period,
        #                            location_poly,
        #                            aggregation_scale)

    # TODO implement, consider splitting from the chain
    if aggregation_scale:
        raise ValueError("API doesn't aggregate output yet")

    if return_period == "aai":
        raise ValueError("Can't calculate average annual statistics for hazard data")
    else:
        return_period = float(return_period)
        rp_intensity = haz.local_exceedance_inten([return_period])[[0]].flatten()

    return [
        {"lat": float(lat), "lon": float(lon), "intensity": float(intensity)}
        for lat, lon, intensity
        in zip(haz.centroids.lat, haz.centroids.lon, rp_intensity)
    ]




@shared_task(base=Singleton)
# @profile()
# @cache_memoize(timeout=conf.CACHE_TIMEOUT)
def get_hazard_by_location(
        country,
        hazard_type,
        scenario_name,
        scenario_year,
        location_poly=None,
        aggregation_scale=None):
    haz = get_hazard_from_api(hazard_type, country, scenario_name, scenario_year)
    # TODO the location bit
    if location_poly:
        raise ValueError("We don't subset by location yet")

    return haz


def get_hazard_from_api(
        hazard_type: HazardTypeEnum,
        country,
        scenario_climate: ScenarioClimateEnum,
        scenario_year):
    client = Client()
    request_properties = {
        'spatial_coverage': 'country',
        'country_iso3alpha': country,
        'nb_synth_tracks': str(conf.DEFAULT_N_TRACKS),
        'climate_scenario': scenario_climate}
    if scenario_climate != 'historical':
        request_properties['ref_year'] = str(scenario_year)

    status = 'preliminary' if hazard_type == "extreme_heat" else "active"

    LOGGER.debug(f'Requesting {status} {hazard_type} hazard from Data API. Request properties: {request_properties}')
    return client.get_hazard(hazard_type, properties=request_properties, status=status)


def get_hazard_event(hazard_type,
                     country,
                     scenario_name,
                     scenario_year,
                     event_name,
                     location_poly=None,
                     aggregation_scale=None):
    haz = get_hazard_from_api(hazard_type, country, scenario_name, scenario_year)
    haz = haz.select(event_names=[event_name])
    if location_poly:
        raise ValueError("API doesn't handle polygons yet")  # TODO
        # haz = hazard_subset_extent(haz, bbox, nearest=True, drop_empty_events=True)

    if aggregation_scale:
        raise ValueError("API doesn't aggregate output yet")  # TODO
    return haz.intensity.todense().A1



