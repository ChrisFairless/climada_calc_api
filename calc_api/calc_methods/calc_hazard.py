import logging
import numpy as np
from cache_memoize import cache_memoize
from celery import shared_task
from celery_singleton import Singleton
from shapely import wkt
from typing import List
from scipy import sparse

from climada.util.api_client import Client
from climada.hazard import Hazard, Centroids, Tag

from calc_api.calc_methods.profile import profile
from calc_api.config import ClimadaCalcApiConfig
from calc_api.calc_methods import util
from calc_api.vizz.enums import ScenarioClimateEnum, HazardTypeEnum
from calc_api.job_management.job_management import database_job

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# TODO split this into get_hazard_by_return_period and get_hazard and make get_hazard_from_api an internal function
# i.e. this handles all the processing and decoding of a mess of different parameters
# TODO make this work for multiple return periods too
@shared_task(base=Singleton)
# @database_job
# @profile()
# @cache_memoize(timeout=conf.CACHE_TIMEOUT)
def get_hazard_by_return_period(
        country: str,
        hazard_type: str,
        return_period: List[str],
        scenario_name: str,
        scenario_climate: str,
        scenario_year: int,
        location_poly=None,
        aggregation_scale=None,
        aggregation_method=None):

    LOGGER.debug('Starting get_hazard_by_return_period calculation. Locals: ' + str(locals()))

    if not all([scenario_name, scenario_climate, scenario_year]):
        scenario_name, _, scenario_climate = util.standardise_scenario(
            scenario_name=scenario_name,
            scenario_climate=scenario_climate,
            scenario_year=scenario_year
        )
    haz = get_hazard_from_api(hazard_type, country, scenario_name, scenario_year)
    # TODO handle polygons, be sure it's not more efficient to make this another link of the chain
    if location_poly:
        haz = subset_hazard_extent(haz, location_poly)

    # TODO implement, consider splitting from the chain
    if aggregation_scale:
        raise ValueError("API doesn't aggregate output yet")

    if return_period == "aai":
        raise ValueError("Can't calculate average annual statistics for hazard data")
    else:
        return_period = [float(rp) for rp in return_period] if isinstance(return_period, list) else [float(return_period)]
        rp_intensity = haz.local_exceedance_inten(return_period)[[0]].flatten()

    return [
        {"lat": float(lat), "lon": float(lon), "intensity": float(intensity)}
        for lat, lon, intensity
        in zip(haz.centroids.lat, haz.centroids.lon, rp_intensity)
    ]




@shared_task(base=Singleton)
@database_job
# @profile()
# @cache_memoize(timeout=conf.CACHE_TIMEOUT)
def get_hazard_by_location(
        country,
        hazard_type,
        scenario_name,
        scenario_year,
        location_poly=None,
        aggregation_scale=None,
        aggregation_method=None):
    haz = get_hazard_from_api(hazard_type, country, scenario_name, scenario_year)
    # TODO the location bit
    if location_poly:
        haz = subset_hazard_extent(haz, location_poly)
    if aggregation_scale:
        raise ValueError("API doesn't aggregate output yet")

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
        'climate_scenario': scenario_climate
    }
    if scenario_climate != 'historical':
        request_properties['ref_year'] = str(scenario_year)

    status = 'preliminary' if hazard_type == "extreme_heat" else "active"
    version = 'newest'

    if hazard_type == "extreme_heat":
        LOGGER.debug('Using dummy extreme heat data')
        centroids = Centroids()
        centroids.lat = np.array([8.48])
        centroids.lon = np.array([-13.27])

        modifier = 0 if scenario_climate == "historical" else 0.5
        haz = Hazard()
        haz.tag = Tag(haz_type="EH")
        haz.units = "degC"
        haz.centroids = centroids
        haz.event_id = np.array(['EH_dummy_' + str(i) for i in range(100)])
        haz.frequency = np.repeat(0.01, 100)
        haz.event_name = ['EH_dummy_' + str(i) for i in range(100)]
        haz.intensity = sparse.csr_matrix([np.random.normal(33 + modifier, 3, 1) for i in range(100)])
        haz.fraction = sparse.csr_matrix([[1] for i in range(100)])
        haz.check()
        return haz

    LOGGER.debug(f'Requesting {status} {hazard_type} hazard from Data API. Request properties: {request_properties}')
    return client.get_hazard(hazard_type, properties=request_properties, status=status, version=version)


def get_hazard_event(hazard_type,
                     country,
                     scenario_name,
                     scenario_year,
                     event_name,
                     location_poly=None,
                     aggregation_scale=None,
                     aggregation_method=None):
    haz = get_hazard_from_api(hazard_type, country, scenario_name, scenario_year)
    haz = haz.select(event_names=[event_name])
    if location_poly:
        raise ValueError("API doesn't handle polygons yet")  # TODO
        # haz = hazard_subset_extent(haz, bbox, nearest=True, drop_empty_events=True)

    if aggregation_scale:
        raise ValueError("API doesn't aggregate output yet")  # TODO
    return haz.intensity.todense().A1


def subset_hazard_extent(
        haz,
        location_poly,
        buffer=300      # arcseconds
):
    location_poly = util.convert_to_polygon(location_poly)

    buffer_deg = buffer / (60 * 60)
    lonmin, latmin, lonmax, latmax = location_poly.bounds
    latmin = latmin - buffer_deg
    lonmin = lonmin - buffer_deg
    latmax = latmax + buffer_deg
    lonmax = lonmax + buffer_deg

    extent = (lonmin, lonmax, latmin, latmax)

    haz = haz.select(extent=extent)
    if not haz:
        raise ValueError('The hazard did not intersect with the requested polygon: no centroids matched')
    return haz


