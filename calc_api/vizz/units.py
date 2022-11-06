from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.enums import get_unit_options, get_option_parameter, HazardTypeEnum, get_exposure_types
from pint import UnitRegistry
from forex_python.converter import CurrencyRates

conf = ClimadaCalcApiConfig()
ureg = UnitRegistry()


# Units used in CLIMADA Data API products
NATIVE_UNITS_CLIMADA = {
    "economic_assets": "USD",
    "people": "people",
    "currency": "USD",
    "speed": "ms",
    "temperature": "degC",
    "distance": "kilometres",     # For centroids matching. (Arcseconds otherwise but we're not using those utils)
    # "units_area": "square_kilometres",
    # "units_return_period": "years",     # Currently this is fixed
}

UNITS_NOT_TO_CONVERT = ['fraction', '%', 'percent', 'years', 'people']

# Dictionary of units chosen by default in the API config, by unit type (e.g. 'speed': 'mph')
API_DEFAULT_UNITS = conf.DEFAULT_UNITS

# Dictionary of valid options for each unit type, according to the API options.json (e.g. 'speed': ['mph', 'm/s'])
UNIT_OPTIONS = {
    unit_type: get_unit_options(unit_type)
    for unit_type in API_DEFAULT_UNITS.keys()
}

# Dictionary mapping each available unit to its unit type (e.g. 'mph': 'speed')
UNIT_TYPES = {unit_name: unit_type for unit_type, options_list in UNIT_OPTIONS.items() for unit_name in options_list}

HAZARD_UNIT_TYPES = {
    haz: get_option_parameter(['data', 'filters', haz], parameter="unit_type") for haz in HazardTypeEnum
}

def make_conversion_function(units_from, units_to):
    if units_from in UNIT_OPTIONS['currency']:
        c = CurrencyRates()
        return lambda x: x * c.get_rate(units_from, units_to)
    else:
        return lambda x: ureg.Quantity(x, ureg(units_from)).to(ureg(units_to)).m


def get_request_unit_parameters(s):
    return [
        att for att in s.dict().keys()
        if att.startswith('unit')
    ]


def get_request_unittype_to_unitname_mapping(s):
    unit_parameters = get_request_unit_parameters(s)
    requested_units = {}
    for param in unit_parameters:
        unit_name = s.dict()[param]
        if unit_name not in UNIT_TYPES.keys():
            raise ValueError(f'Processing parameter request: did not recognise {unit_name} as a unit request variable. '
                             f'Valid units: {UNIT_TYPES.keys()}')
        unit_type = UNIT_TYPES[unit_name]
        if unit_type in requested_units.keys() and requested_units[unit_type] != unit_name:
            raise ValueError(
                f'Units clash. Conflicting units have been provided for unit type {unit_type}. '
                f'\n Requested units: {requested_units[unit_type]} and {unit_name}. '
                f'\n Full {type(s).__name__} request: {s.POST.dict()}'
            )
        requested_units[unit_type] = unit_name
    return requested_units


def get_request_parameter_to_unittype_mapping(s):
    unit_parameters = get_request_unit_parameters(s)
    requested_units = {}
    for param in unit_parameters:
        unit_name = s.dict()[param]
        if unit_name not in UNIT_TYPES.keys():
            raise ValueError(f'Processing parameter request: did not recognise {unit_name} as a unit request variable. '
                             f'Valid units: {UNIT_TYPES.keys()}')
        unit_type = UNIT_TYPES[unit_name]
        requested_units[param] = unit_type
    return requested_units


def get_valid_exposure_units(hazard_type=None):
    exposure_types = get_exposure_types(hazard_type)
    exposure_units = set()
    for unit_type in exposure_types:
        exposure_units = exposure_units.union(set(UNIT_OPTIONS[unit_type]))
    return list(exposure_units)
