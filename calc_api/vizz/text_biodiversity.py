from string import Template
import logging
import numpy as np
import pandas as pd

from calc_api.vizz.util import options_return_period_to_description, options_scenario_to_description
from calc_api.vizz import schemas_widgets
from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))

# TODO should we limit the land use analysis to locations where a certain hazard severity is present? With large countries it doens't make sense to talk about everything. E.g. the Alaskan tundra is irrelevant to US TC adaptation.


def generate_biodiversity_widget_text(
        habitat_description,
        hazard_type,
        location_name,
):

    intro_text = _generate_biodiversity_widget_intro_text()
    biodiversity_distribution_text = _generate_biodiversity_distribution_text(
        habitat_description,
        location_name
    )
    conclusion_text = _generate_biodiversity_widget_conclusion_text()

    return [intro_text] + biodiversity_distribution_text + [conclusion_text]


def _generate_biodiversity_widget_intro_text():
    return schemas_widgets.GeneratedText(
            template='The risks that communities face and the most effective ways to adapt are closely related to the '
                     'regional climate and local land use.',
            values=[]
    )


def _generate_biodiversity_distribution_text(habitat_description_lvl1, location_name):
    # {
    #     'location': location_name,
    #     'n_grid_cells': n_grid_cells,
    #     'habitat_breakdown': [
    #         {
    #             'category': row['category'],
    #             'category_code': row['category_code'],
    #             'fraction': row['value'] / total_area
    #         } for _, row in landuse_by_cat.iterrows()
    #     ]
    # }
    df = pd.DataFrame(habitat_description_lvl1['habitat_breakdown'])
    df = df[df['fraction'] != 0]

    text_list = [
        schemas_widgets.GeneratedText(
            template=f'The land-use in {location_name} breaks down as follows. ',
            values=[]
        )
    ]

    def generate_landuse_text(category, text):
        print("Land use for " + category)
        varname = category.replace(" ", "_").lower()
        category_string = category.replace("_", " ").title()
        if category_string == "Wetlands Inland":
            category_string = "Wetlands inland"  # Inconsistent name formatting in source data
        value = schemas_widgets.TextVariable(
            key=varname + '_pct',
            value=100 * df['fraction'][df['category'] == category_string],
            units='%'
        )
        return schemas_widgets.GeneratedText(
            template=text,
            values=[value]
        )

    categories = df[df['fraction'] >= 0.01]['category'].values
    if 'Forest' in categories:
        text = 'Forests cover {{forest_pct}} of the land. These may be wild or managed and ' \
               'are important to maintaining biodiversity in the region. They also store water ' \
               'following heavy rain, r educe the local temperature through evapotranspiration and ' \
               'store significant amounts of carbon. '
        text = generate_landuse_text('forest', text)
        text_list.append(text)

    if 'Artificial - Terrestrial' in categories:
        text = 'Settlements and agriculture cover {{artificial_-_terrestrial_pct}} of the area. The land ' \
        'is highly managed. Many adaptation measures will focus here, through urban infrastructure, land management ' \
        'and initiatives with the population.'
        text = generate_landuse_text('artificial_-_terrestrial', text)
        text_list.append(text)

    if 'Savanna' in categories:
        text = 'Savanna is {{savanna_pct}} of the area. The land is important for biodiversity and ' \
               'carbon storage. '
        text = generate_landuse_text('savanna', text)
        text_list.append(text)

    if 'Shrubland' in categories:
        text = 'Shrubland is {{shrubland_pct}} of the area. It is important for biodiversity ' \
               'and carbon storage. '
        text = generate_landuse_text('shrubland', text)
        text_list.append(text)

    if 'Grassland' in categories:
        text = 'Grassland is {{grassland_pct}} of the area. It is important for biodiversity ' \
               'and carbon storage. '
        text = generate_landuse_text('grassland', text)
        text_list.append(text)

    if 'Wetlands inland' in categories:
        text = 'Inland wetlands are {{wetlands_inland_pct}} of the area. These are ' \
               'important for biodiversity, and for storing flood water and carbon. '
        text = generate_landuse_text('wetlands_inland', text)
        text_list.append(text)

    if 'Rocky Areas' in categories:
        text = 'Rocky areas are {{rocky_areas_pct}} of the area. '
        text = generate_landuse_text('rocky_areas', text)
        text_list.append(text)

    if 'Desert' in categories:
        text = 'Desert is {{desert_pct}} of the area. '
        text = generate_landuse_text('desert', text)
        text_list.append(text)

    if 'Marine - intertidal' in categories:
        text = 'Coastal intertidal areas are {{marine_-_intertidal_pct}} of the area. These can be regions of ' \
               'high biodiversity and need careful management to protect communities from coastal hazards.'
        text = generate_landuse_text('marine_-_intertidal', text)
        text_list.append(text)

    return text_list


def _generate_biodiversity_widget_conclusion_text():
    return schemas_widgets.GeneratedText(
            template='This tool does not tell you the best way to take climate and land use into account '
                     'for climate adaptation. For this you will need to speak with regional literature and experts.',
            values=[]
    )