import logging
from climada.util.coordinates import country_to_iso
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.schemas.enums import SCENARIO_LOOKUPS

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# TODO probably make this a class
def standardise_scenario(scenario_name=None, scenario_growth=None, scenario_climate=None, scenario_year=None):

    if not scenario_name and (scenario_climate is None or scenario_growth is None):
        raise ValueError('When scenario_name is not set, scenario_climate and scenario_growth must be')

    if scenario_year and int(scenario_year) == 2020:
        return 'historical', 'historical', 'historical'

    if scenario_name and not scenario_growth:
        scenario_growth = SCENARIO_LOOKUPS[scenario_name]['scenario_growth']
    if scenario_name and not scenario_climate:
        scenario_climate = SCENARIO_LOOKUPS[scenario_name]['scenario_climate']

    return scenario_name, scenario_growth, scenario_climate


def country_iso_from_parameters(location_name=None,
                                location_code=None,
                                location_scale=None,
                                location_poly=None,
                                representation="alpha3"):
    """
    Decode location parameters to country codes to pass to the API

    Parameters
    ----------
    location_scale: str
        One of 'global', 'ISO3', 'country', 'admin0', 'admin1', 'admin2'
    location_code: str
        String representation of the location of interest as exact encoding (if known)
    location_name: str
        String representation of the location of interest
    location_poly: str
        Not yet implemented
    representation: str
        One of "alpha3", "alpha2", "numeric", "name"
    """
    # Identify ISO3 codes needed for query
    if location_poly:
        raise ValueError("API doesn't handle polygon queries yet")

    if not location_scale:
        raise ValueError("API requires location_scale data (for now)")  # TODO

    if location_scale == "global":
        raise ValueError("API doesn't handle global queries yet")  # TODO
    elif location_scale in ['ISO3', 'admin0', 'country']:
        if location_code:
            country_iso3alpha = country_to_iso(location_code, representation)
            if country_iso3alpha is None:
                raise ValueError(f'The location code did not match a country. ' +
                                 f'Provided: {location_code}')
            if country_iso3alpha != location_code:
                raise Warning(f'The location code did not match its decoded ISO3 code. Did you mean location_name? ' +
                              f' Provided: {location_code}  Derived: {country_iso3alpha}')
        elif location_name:
            country_iso3alpha = country_to_iso(location_name, representation)
            if country_iso3alpha is None:
                raise ValueError(f'The location name did not match a country. ' +
                                 f'Provided: {location_name}')
        else:
            raise ValueError("API requires location_code or location_name data")  # TODO
    elif location_scale == "admin1":
        raise ValueError("API doesn't handle admin1 data yet")  # TODO
    elif location_scale == "admin2":
        raise ValueError("API doesn't handle admin2 data yet")  # TODO
    else:
        raise ValueError("location_scale parameter must be one of 'ISO3', 'admin0', 'admin1', 'admin2'")

    if not isinstance(country_iso3alpha, list):
        country_iso3alpha = [country_iso3alpha]

    if len(country_iso3alpha) > 1:
        raise ValueError("Can't handle multiple countries yet")

    # TODO make this able to handle lists!!
    return country_iso3alpha[0]
