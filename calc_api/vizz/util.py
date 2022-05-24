import json
from pathlib import Path
from climada_calc.settings import BASE_DIR

OPTIONS_FILE = Path(BASE_DIR, "calc_api", "options.json")


def get_options():
    return json.load(open(OPTIONS_FILE))


def options_return_period_to_description(rp, hazard_type):
    rp = str(rp)
    options = get_options(hazard_type)
    out = [opt['description'] for opt in options if opt['value'] == rp]
    if len(out) == 0:
        raise ValueError(f'No option matches found for {rp}-year return period and hazard {hazard_type}')
    if len(out) > 1:
        raise ValueError(f'Too many matches found for {rp}-year return period and hazard {hazard_type}: {out}')
    return out[0]


def options_scenario_to_description(scenario, hazard_type):
    # TODO deal with custom scenarios
    options = get_options()['data']['filters'][hazard_type]['scenario_options']['climate_scenario']['choices']
    out = [opt['description'] for opt in options if opt['value'] == scenario]
    if len(out) == 0:
        raise ValueError(f'No option matches found for {scenario} scenario and hazard {hazard_type}')
    if len(out) > 1:
        raise ValueError(f'Too many matches found for {scenario} scenario and hazard {hazard_type}: {out}')
    return out[0]


