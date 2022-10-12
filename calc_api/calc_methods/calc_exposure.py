import logging
from cache_memoize import cache_memoize
from celery import shared_task
from celery_singleton import Singleton
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from time import sleep

from climada.entity.exposures import Exposures
from climada.util.api_client import Client
import climada.util.coordinates as u_coord

from calc_api.calc_methods.profile import profile
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.enums import exposure_type_from_impact_type
from calc_api.calc_methods.util import standardise_scenario
from calc_api.vizz.enums import ScenarioGrowthEnum, ExposureTypeEnum, ApiExposureTypeEnum
from calc_api.job_management.job_management import database_job

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# TODO organise these functions better. get_exposure should just be admin, get_exposure_from_api should do the work
# TODO split this into two functions, once that gets aggregated exposure, one that gets gridded exposure.
#  We don't want to be saving gridded results to our database, and besides, they return different sorts of objects.
@shared_task(base=Singleton)
@database_job
# @profile()
# @cache_memoize(timeout=conf.CACHE_TIMEOUT)
def get_exposure(
        country,
        exposure_type=None,
        impact_type=None,
        scenario_name=None,
        scenario_growth=None,
        scenario_year=None,
        location_poly=None,
        aggregation_scale=None,
        aggregation_method=None,
        drop_zeroes=True):

    LOGGER.debug('Starting get_exposure calculation. Locals: ' + str(locals()))

    exp = get_exposure_from_api(country, exposure_type, impact_type, scenario_name, scenario_growth, scenario_year)

    if drop_zeroes:
        exp.gdf = exp.gdf[exp.gdf['value'] != 0]

    # TODO handle polygons, be sure it's not more efficient to make this another link of the chain
    if location_poly:
        if len(location_poly) != 4:
            raise ValueError("API doesn't handle polygons yet")
        exp = subset_exposure_extent(exp, location_poly)

    # TODO implement, consider splitting from the chain
    if aggregation_scale:
        if not aggregation_method:
            raise ValueError("Need an aggregation method when aggregation_scale is set")
        if aggregation_scale != 'all':
            raise ValueError("API doesn't aggregate output to sublevels yet: set aggregation_scale to 'all'")
        else:
            if aggregation_method == 'sum':
                aggregation_method = np.sum
            elif aggregation_method == 'mean':
                aggregation_method = np.mean
            elif aggregation_method == 'median':
                aggregation_method = np.median
            elif aggregation_method == 'max':
                aggregation_method = np.max
            else:
                raise ValueError('aggregation method must be one of sum, mean, median or max')
        return [{'lat': float(np.median(exp.gdf['latitude'])),
                 'lon': float(np.median(exp.gdf['longitude'])),
                 'value': float(aggregation_method(exp.gdf['value']))}]

    return [
        {"lat": float(row['latitude']), "lon": float(row['longitude']), "value": float(row['value'])}
        for _, row in exp.gdf.iterrows()
    ]


def get_api_exposure_properties(
        exposure_type,
        scenario_name,
        scenario_year,
        scenario_growth,
        country):

    properties = {
        'spatial_coverage': 'country',
        'country_iso3alpha': country,
    }

    is_historical = (scenario_year == 2020) or (scenario_name == 'historical')
    if exposure_type == 'people':
        if is_historical:
            properties['data_type'] = 'litpop_tccentroids'
            properties['exponents'] = '(0,1)'
            properties['fin_mode'] = 'pop'
            properties['status'] = "preliminary"
            properties['version'] = "newest"
            # LOGGER.warning('Using 2020 SSP when we should really be getting LitPop')
            # return 'ssp_population', None
        else:
            properties['data_type'] = 'ssp_population'
            properties['ref_year'] = str(scenario_year)
            properties['ssp'] = scenario_growth
            properties['res_arcsec'] = '150'
            properties['status'] = "preliminary"
            properties['version'] = "newest"

    elif exposure_type == 'economic_assets':
        properties['data_type'] = 'litpop_tccentroids'
        properties['exponents'] = '(1,1)'
        properties['fin_mode'] = 'pc'
        properties['status'] = "preliminary"
        properties['version'] = "newest"
    else:
        raise ValueError(f'Unrecognised exposure definition: {exposure_type}, {scenario_name}, {scenario_year}')

    return properties


def get_gdp_scaling(country, scenario_year):
    LOGGER.warning('Using dummy scaling!!')
    return 1 + (int(scenario_year) - 2020) / 200


# TODO this is a quick fix and we need to store this info in a database
def get_exposure_from_api(
        country,
        exposure_type=None,
        impact_type=None,
        scenario_name=None,
        scenario_growth=None,
        scenario_year=None):

    if not scenario_year and scenario_growth == 'historic':
        scenario_year = '2020'

    scenario_name, scenario_growth, _ = standardise_scenario(scenario_name=scenario_name, scenario_growth=scenario_growth)

    if impact_type and exposure_type is None:
        exposure_type = exposure_type_from_impact_type(impact_type)

    properties = get_api_exposure_properties(exposure_type, scenario_name, scenario_year, scenario_growth, country)

    LOGGER.debug(f'Requesting exposure from Data API. Request details: {properties}')
    exposures_type = properties.pop('data_type')
    status = properties.pop('status')
    version = properties.pop('version')

    client = Client()

    # TODO use a sane way of sharing data across processes
    i, exp = 0, None
    while exp is None:
        try:
            exp = client.get_exposures(
                exposures_type=exposures_type,
                properties=properties,
                status=status,
                version=version
            )
        except Client.NoResult as err:
            raise Client.NoResult(err)
        except Exception as err:
            LOGGER.debug(f'Waiting for exposure file to free up: {err}')
            i = i + 1
            if i == 20:
                raise IOError("Couldn't access exposure file in a reasonable amount of time")
            sleep(2)

    if exposure_type == 'economic_assets' and str(scenario_year) != '2020':
        scaling = get_gdp_scaling(country, scenario_year)
    else:
        scaling = 1
    exp.gdf['value'] = exp.gdf['value'] * scaling

    return exp


# TODO make this work with a GeocodePlace object as well?
def subset_exposure_extent(
        exp,
        location_poly,
        buffer=150,  # arcseconds
        latlon_names=('latitude', 'longitude')
):
    df_query = _make_df_subset_query(exp.gdf, location_poly, buffer, latlon_names)
    exp.gdf = gpd.GeoDataFrame(exp.gdf.query(df_query))
    if exp.gdf.shape[0] == 0:
        raise ValueError('Subsetting the exposure went wrong: no exposure points found')
    return exp


def subset_dataframe_extent(
        exp,
        location_poly,
        buffer=150,  # arcseconds
        latlon_names=('latitude', 'longitude')
):
    df_query = _make_df_subset_query(exp, location_poly, buffer, latlon_names)
    exp = pd.DataFrame(exp.query(df_query))
    if exp.shape[0] == 0:
        raise ValueError('Subsetting the exposure went wrong: no exposure points found')
    return exp


def _make_df_subset_query(
        exp,
        location_poly,
        buffer,
        latlon_names
):
    if len(location_poly) != 4:
        LOGGER.warning("API doesn't handle non-bounding box polygons yet: converting to box")

    buffer_deg = buffer / (60 * 60)
    latmin = np.min([coord[0] for coord in location_poly]) - buffer_deg
    lonmin = np.min([coord[1] for coord in location_poly]) - buffer_deg
    latmax = np.max([coord[0] for coord in location_poly]) + buffer_deg
    lonmax = np.max([coord[1] for coord in location_poly]) + buffer_deg

    return f'{latlon_names[0]} >= {latmin} & \
        {latlon_names[0]} <= {latmax} & \
        {latlon_names[1]} >= {lonmin} & \
        {latlon_names[1]} <= {lonmax}'