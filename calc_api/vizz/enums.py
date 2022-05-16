from enum import Enum
from calc_api.vizz.util import get_options


def impact_exposure_map(impact_type):
    imp_map = {
        'people_affected': 'people',
        'economic_loss': 'economic_assets',
        'assets_affected': 'economic_assets'
    }
    if impact_type not in imp_map.keys():
        raise ValueError('impact type must be one of: ' + str(list(imp_map.keys())))
    return imp_map[impact_type]


def get_options(options_path, just_values=False):
    options = get_options()
    for opt in options_path:
        options = options[opt]
    if options.__class__ == dict and 'choices' in options.keys():
        options = options['choices']
    if just_values:
        return options
    return [opt['value'] for opt in options]


def get_hazard_type_names():
    return get_options(['data', 'filters'], just_values=True)


def get_year_options(hazard_type, just_values=False):
    return get_options(['data', 'filters', hazard_type, 'scenario_options', 'year'], just_values)


def get_scenario_options(hazard_type, just_values=False):
    return get_options(['data', 'filters', hazard_type, 'scenario_options', 'climate_scenario'], just_values)


def get_impact_options(hazard_type, just_values=False):
    return get_options(['data', 'filters', hazard_type, 'scenario_options', 'impact'], just_values)


def get_rp_options(hazard_type, just_values=False):
    return get_options(['data', 'filters', hazard_type, 'scenario_options', 'return_period'], just_values)


def get_exposure_types(hazard_type):
    impact_list = get_impact_options(hazard_type, just_values=True)
    return list(set([impact_exposure_map[impact] for impact in impact_list]))


class HazardTypeEnum(str, Enum):
    tropical_cyclone = "tropical_cyclone"
    extreme_heat = "extreme_heat"