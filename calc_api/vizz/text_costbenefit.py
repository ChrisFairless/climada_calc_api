from string import Template
from millify import millify
import numpy as np

from calc_api.vizz.util import options_return_period_to_description, options_scenario_to_description
from calc_api.vizz import schemas_widgets
from calc_api.vizz.enums import get_currency_options


def generate_costbenefit_widget_text():
    return [
        schemas_widgets.GeneratedText(
            template='[[COSTBENEFIT PLACEHOLDER]]',
            values=[]
        )
    ]