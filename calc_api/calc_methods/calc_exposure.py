import logging
import numpy as np
from time import sleep

from climada.util.api_client import Client

# TODO get from env variable
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, 'DEBUG'))


def get_exposure(
        country,
        exposure_type=None,
        scenario_growth=None,
        scenario_year=None,
        location_poly=None,
        aggregation_scale=None,
        aggregation_method=None,
        units=None):

    if not scenario_year and scenario_growth == 'historic':
        scenario_year = '2020'

    exp = _get_exposure_from_api(country, exposure_type, scenario_growth, scenario_year)

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
        if not aggregation_method:
            raise ValueError("Need an aggregation method when aggregation_scale is set")
        if aggregation_scale != 'country':
            raise ValueError("API doesn't aggregate output to non-country levels yet")
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
                raise ValueError('aggregation method must be either ')
        return [{'lat': float(np.median(exp.gdf['latitude'])),
                 'lon': float(np.median(exp.gdf['longitude'])),
                 'value': float(aggregation_method(exp.gdf['value']))}]

    return [
        {"lat": float(row['latitude']), "lon": float(row['longitude']), "value": float(row['value'])}
        for row in exp.gdf.iterrows()
    ]


def determine_api_exposure_type(exposure_type, scenario_growth, scenario_year):
    is_historical = (scenario_year == 2020) or (scenario_growth == 'historical')
    if exposure_type == 'people':
        if is_historical:
            return 'litpop_tccentroids', '(0,1)'
        else:
            return 'ssp_population', None
    elif exposure_type == 'economic_assets':
        return 'litpop_tccentroids', '(1,1)'
    else:
        raise ValueError(f'Unrecognised exposure definition: {exposure_type}, {scenario_growth}, {scenario_year}')


def get_gdp_scaling(country, scenario_year):
    LOGGER.warning('Using dummy scaling!!')
    return 1 + (int(scenario_year) - 2020) / 200


# TODO this is a quick fix and we need to store this info in a database
def _get_exposure_from_api(
        country,
        exposure_type=None,
        scenario_growth=None,
        scenario_year=None):

    api_exposure_type, exponents = determine_api_exposure_type(exposure_type, scenario_growth, scenario_year)

    request_properties = {
        'spatial_coverage': 'country',
        'country_iso3alpha': country,
    }

    if api_exposure_type != 'litpop_tccentroids':
        request_properties['ref_year'] = str(scenario_year)
        request_properties['climate_scenario'] = scenario_growth

    if 'litpop' in api_exposure_type:
        if exposure_type == 'people':
            request_properties['exponents'] = '(0,1)'
            request_properties['fin_mode'] = 'pop'
        elif exposure_type == 'economic_assets':
            request_properties['exponents'] = '(1,1)'
            request_properties['fin_mode'] = 'pc'
        else:
            raise ValueError('Exposure only handles people and economic_assets types right now')

    status, version = ("preliminary", "v1") if 'tccentroids' in api_exposure_type else ("active", None)

    LOGGER.debug(f'Requesting {status} {api_exposure_type} {version} exposure from Data API. Request properties: {request_properties}')
    client = Client()

    # TODO use a sane way of sharing data across processes
    i, exp = 0, None
    while exp is None:
        try:
            exp = client.get_exposures(
                exposures_type=api_exposure_type,
                properties=request_properties,
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
