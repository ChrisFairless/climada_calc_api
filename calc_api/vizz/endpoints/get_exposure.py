import logging
from celery import shared_task
from celery_singleton import Singleton
from requests import request

from climada_calc.settings import DIGITAL_OCEAN_URL, DIGITAL_OCEAN_FUNCTIONS
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.schemas import schemas
from calc_api.calc_methods.calc_exposure import get_exposure
from calc_api.calc_methods.geocode import standardise_location
from calc_api.calc_methods.util import country_iso_from_parameters

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# TODO organise these functions better. get_exposure should just be admin, get_exposure_from_api should do the work
@shared_task(base=Singleton)
# @profile()
# @cache_memoize(timeout=conf.CACHE_TIMEOUT)
def celery_get_exposure(exp_request: schemas.MapExposureRequest
        # country,
        # exposure_type=None,
        # impact_type=None,
        # scenario_name=None,
        # scenario_growth=None,
        # scenario_year=None,
        # location_poly=None,
        # aggregation_scale=None,
        # aggregation_method=None
):
    exp_request.standardise()

    country = country_iso_from_parameters(
        location_name=exp_request.location_name,
        location_code=exp_request.location_code,
        location_scale=exp_request.location_scale,
        location_poly=exp_request.location_poly,
        representation="alpha3"
    )

    if DIGITAL_OCEAN_FUNCTIONS:
        url = DIGITAL_OCEAN_URL + '/do/calc_exposures/get_exposure'
        params = {
            'country': country,
            'exposure_type': exp_request.exposure_type,
            'scenario_name': exp_request.scenario_name,
            'scenario_growth': exp_request.scenario_growth,
            'scenario_year': exp_request.scenario_year,
            'location_poly': exp_request.location_poly,
            'aggregation_scale': exp_request.aggregation_scale,
            'aggregation_method': exp_request.aggregation_method,
            'unit': exp_request.units
        }
        return request(url, params=params)

    return get_exposure(
        country,
        exp_request.exposure_type,
        exp_request.scenario_name,
        exp_request.scenario_growth,
        exp_request.scenario_year,
        exp_request.location_poly,
        exp_request.aggregation_scale,
        exp_request.aggregation_method,
        exp_request.units
    )
