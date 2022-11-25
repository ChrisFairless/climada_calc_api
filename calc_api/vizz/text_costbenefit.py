from string import Template
from millify import millify
import numpy as np

from calc_api.vizz.util import options_return_period_to_description, options_scenario_to_description
from calc_api.vizz import schemas_widgets


def generate_costbenefit_widget_text(
        measure_name=None,
        measure_description=None
):
    return [
        schemas_widgets.GeneratedText(
            template='[[COSTBENEFIT PLACEHOLDER]]',
            values=[]
        )
    ]

    text_costben_intro = _generate_costben_intro_text()
    text_measure_description = _generate_measure_description_text(measure_description)
    text_measure_effect = _generate_measure_effect_text(
        measure_name,
    )

    return [
        schemas_widgets.GeneratedText(
            template='[[COSTBENEFIT PLACEHOLDER]]',
            values=[]
        )
    ]


def _generate_costben_intro_text():
    text = Template(
        'By introducing adaptation measures we can offset some of the risk that we face.'
    )
    return schemas_widgets.GeneratedText(
        template=text,
        values=[]
    )


def _generate_measure_description_text(measure_description):
    text = Template(measure_description)
    return schemas_widgets.GeneratedText(
        template=text,
        values=[]
    )


def _generate_measure_effect_text(
        measure_name,
        # cost,
        # costbenefit
):
    # benefit = cost * costbenefit
    return schemas_widgets.GeneratedText(
        template='By implementing this measure at a cost of {{{cost}}, an estimated ',
        values=[]
    )