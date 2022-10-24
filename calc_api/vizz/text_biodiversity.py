from string import Template
import logging
from millify import millify
import numpy as np

from calc_api.vizz.util import options_return_period_to_description, options_scenario_to_description
from calc_api.vizz import schemas_widgets
from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


def generate_biodiversity_widget_text(
        habitat_description,
        hazard_type,
        location_name,
):
    return [
        schemas_widgets.GeneratedText(
            template='',
            values=[]
        )
    ]

    intro_text = _generate_social_vulnerability_widget_intro_text()
    haz_overview_text = _generate_social_vulnerability_widget_hazard_overview_text(hazard_type)
    soc_vuln_distribution_text = _generate_social_vulnerability_distribution_text(
        habitat_description,
        location_name
    )

    # TODO make useful social vulnerability information here
    return [intro_text, haz_overview_text, soc_vuln_distribution_text]
