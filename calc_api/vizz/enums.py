from enum import Enum
from typing import List
import numpy as np

from calc_api.vizz.util import get_options


# TODO generate all these from the options
class HazardTypeEnum(str, Enum):
    tropical_cyclone = 'tropical_cyclone'
    extreme_heat = 'extreme_heat'


class ApiExposureTypeEnum(str, Enum):
    litpop = 'litpop_tccentroids'
    ssp_population = 'ssp_population'


class ExposureTypeEnum(str, Enum):
    people = 'people'
    economic_assets = 'economic_assets'


class ImpactTypeEnum(str, Enum):
    people_affected = 'people_affected'
    economic_impact = 'economic_impact'
    assets_affected = 'assets_affected'


class ScenarioNameEnum(str, Enum):
    historical = 'historical'
    ssp126 = 'ssp126'
    ssp245 = 'ssp245'
    ssp560 = 'ssp560'


class ScenarioGrowthEnum(str, Enum):
    historical = 'historical'
    ssp1 = 'ssp1'
    ssp2 = 'ssp2'
    ssp3 = 'ssp3'
    ssp4 = 'ssp4'
    ssp5 = 'ssp5'


class ScenarioClimateEnum(str, Enum):
    historical = 'historical'
    rcp26 = 'rcp26'
    rcp45 = 'rcp45'
    rcp60 = 'rcp60'


def assert_in_enum(value, enum_class):
    assert value in [e.value for e in enum_class]


# TODO is this the right place to store this data?
SCENARIO_LOOKUPS = {
    'historical': {'scenario_name': 'historical', 'scenario_growth': 'historical', 'scenario_climate': 'historical'},
    'ssp126': {'scenario_name': 'rcp126', 'scenario_growth': 'ssp1', 'scenario_climate': 'rcp26'},
    'ssp245': {'scenario_name': 'rcp245', 'scenario_growth': 'ssp2', 'scenario_climate': 'rcp45'},
    'ssp560': {'scenario_name': 'rcp560', 'scenario_growth': 'ssp5', 'scenario_climate': 'rcp60'}
}

IMPACT_TO_EXPOSURE = {
    'people_affected': 'people',
    'economic_impact': 'economic_assets',
    'assets_affected': 'economic_assets'
}

EXPOSURE_TO_UNIT_TYPE = {
    'people': 'people',
    'economic_assets': 'currency'
}

HAZARD_TO_ABBREVIATION = {
    'tropical_cyclone': 'TC',
    'extreme_heat': 'EH'
}


def exposure_type_from_impact_type(impact_type):
    if impact_type not in IMPACT_TO_EXPOSURE.keys():
        raise ValueError('impact type must be one of: ' + str(list(IMPACT_TO_EXPOSURE.keys())))
    return IMPACT_TO_EXPOSURE[impact_type]


def validate_exposure_type_from_impact_type(exposure_type, impact_type):
    if impact_type not in IMPACT_TO_EXPOSURE.keys():
        raise ValueError('impact type must be one of: ' + str(list(IMPACT_TO_EXPOSURE.keys())))
    if exposure_type not in IMPACT_TO_EXPOSURE.values():
        raise ValueError('exposure type must be one of: ' + str(list(IMPACT_TO_EXPOSURE.values())))
    if IMPACT_TO_EXPOSURE[impact_type] != exposure_type:
        raise ValueError(f'The requested exposure and impact types are not compatible. '
                         f'\nImpact requested: {impact_type}'
                         f'\nExposure requested: {exposure_type}'
                         f'\nExposure compatible with this impact: {IMPACT_TO_EXPOSURE[impact_type]}')


def get_option_parameter(options_path: List[str], parameter):
    options = get_options()
    for opt in options_path:
        options = options[opt]
    return options[parameter]


def get_option_choices(options_path: List[str], get_value: str = None, parameters: dict = None):
    options = get_options()
    for opt in options_path:
        options = options[opt]
    if options.__class__ == dict and 'choices' in options.keys():
        options = options['choices']
    if parameters:
        for key, value in parameters.items():
            options = [opt for opt in options if opt[key] == value]
    if get_value:
        return [opt[get_value] for opt in options]

    if len(options) == 0:
        raise ValueError(f'No valid options found. Path: {options_path}, value: {get_value}, parameters {None}')
    return options


def get_hazard_type_names():
    return get_option_choices(['data', 'filters'])


def get_year_options(hazard_type, get_value=None, parameters=None):
    return get_option_choices(['data', 'filters', hazard_type, 'scenario_options', 'year'], get_value, parameters)


def get_scenario_options(hazard_type, get_value=None, parameters=None):
    return get_option_choices(['data', 'filters', hazard_type, 'scenario_options', 'climate_scenario'], get_value, parameters)


def get_impact_options(hazard_type, get_value=None, parameters=None):
    return get_option_choices(['data', 'filters', hazard_type, 'scenario_options', 'impact_type'], get_value, parameters)


def get_rp_options(hazard_type, get_value=None, parameters=None):
    return get_option_choices(['data', 'filters', hazard_type, 'scenario_options', 'return_period'], get_value, parameters)


def get_unit_options(unit_type):
    return get_option_choices(['data', 'units', unit_type], get_value='value')


def get_exposure_types(hazard_type=None):
    if hazard_type:
        impact_list = get_impact_options(hazard_type, get_value='value')
    else:
        haz_names = get_hazard_type_names()
        list_of_impact_lists = [get_impact_options(haz, get_value='value') for haz in haz_names]
        impact_list = list(np.concatenate([np.array(impacts) for impacts in list_of_impact_lists]))
    return list(set([exposure_type_from_impact_type(impact) for impact in impact_list]))

