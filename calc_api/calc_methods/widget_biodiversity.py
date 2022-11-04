import logging
import numpy as np
import pandas as pd
from celery import chain, chord, group, shared_task
from celery_singleton import Singleton
from shapely import wkt

from climada.util.api_client import Client

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz import schemas, schemas_widgets
from calc_api.vizz.text_biodiversity import generate_biodiversity_widget_text
from calc_api.calc_methods.calc_exposure import get_exposure, subset_dataframe_extent, subset_exposure_extent
from calc_api.job_management.job_management import database_job
from calc_api.job_management.standardise_schema import standardise_schema

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


@standardise_schema
def widget_biodiversity(data: schemas_widgets.BiodiversityWidgetRequest):
    request_id = data.get_id()

    if data.location_poly and len(wkt.loads(data.location_poly).exterior.coords[:]) - 1 != 4:
        LOGGER.warning('Ignoring location polygon data for soc vuln calculations: using location bbox')

    # TODO in the case of a country-scale calculation, I think we'll do it twice due to the location_poly attribute. Ehh
    chord_header = [
        create_habitat_breakdown.s(
            country_iso=data.geocoding.country_id,
            location_name=data.geocoding.country,
            location_poly=None
        )
    ]

    chord_callback = create_biodiversity_widget_from_habitat.s(
        hazard_type=data.hazard_type,
        location_name=data.location_name,
        country_name=data.geocoding.country
    )

    res = chord(chord_header, task_id=str(request_id))(chord_callback)

    return res.id


@shared_task(base=Singleton)
@database_job   # TODO is this the right place to be cacheing?
def create_habitat_breakdown(
        country_iso,
        location_name=None,
        location_poly=None
):

    # TODO maybe parallelise this
    exp_landuse = get_habitat_from_api(country_iso)
    if not exp_landuse:
        raise ValueError(f'No landuse data found in the API for country {country_iso}')

    if location_poly:
        exp_landuse = subset_exposure_extent(exp_landuse, location_poly, buffer=150)

    df_landuse = exp_landuse.gdf
    n_grid_cells = df_landuse.shape[0]
    if n_grid_cells == 0:
        raise ValueError(f'No landuse points when subsetting for {country_iso}: {location_name}')

    landuse_by_cat = df_landuse.groupby(['category', 'category_code']).agg({'value': 'sum'}).reset_index()
    total_area = sum(landuse_by_cat['value'])
    # TODO make this a class or a schema
    return {
        'location': location_name,
        'n_grid_cells': n_grid_cells,
        'habitat_breakdown': [
            {
                'category': row['category'],
                'category_code': row['category_code'],
                'fraction': row['value'] / total_area
            } for _, row in landuse_by_cat.iterrows()
        ]
    }


def get_habitat_from_api(country_iso, level=1):
    request_properties = {
        'spatial_coverage': 'country',
        'country_iso3alpha': country_iso,
        'level': str(level)
    }

    LOGGER.debug(
        f'Requesting habitat land use from Data API. Request properties: {request_properties}')
    client = Client()

    try:
        # TODO maybe make some of these parameters into settings
        habitat = client.get_exposures(
            exposures_type='habitat_classification',
            properties=request_properties,
            status='preliminary',
            version='newest'
        )
    except Client.NoResult as err:
        LOGGER.warning(f'No habitat data found for {country_iso}: returning None')
        return None

    return habitat


@shared_task()
def create_biodiversity_widget_from_habitat(
        habitat_description_list,
        hazard_type,
        location_name,
        country_name):

    habitat_description = habitat_description_list[0]
    breakdown = habitat_description['habitat_breakdown']
    location_shortname = location_name.split(',')[0]

    if breakdown is not None:  # if there's soc vuln data for this place
        widget_text = generate_biodiversity_widget_text(
            habitat_description,
            hazard_type,
            location_shortname
        )

        widget_bars = [
            schemas.ExposureBreakdownBar(
                label=f'Habitat breakdown at {location_shortname}',
                location_scale='location',
                category_labels=[cat['category'] for cat in breakdown],
                values=[cat['fraction'] for cat in breakdown]
            )
        ]

        widget_legend = schemas.CategoricalLegend(
            title=f'Habitat breakdown in {location_shortname}',
            units=None,
            items=[
                schemas.CategoricalLegendItem(
                    label=cat['category'],
                    slug=cat['category'].replace(' - ', '_').replace(' ', '_').lower()
                )
                for cat in breakdown
            ]
        )

        widget_chart = schemas.ExposureBreakdown(
            items=widget_bars,
            legend=widget_legend
        )

    else:
        raise ValueError('No habitat data received for widget.')

    widget_data = schemas_widgets.BiodiversityWidgetData(
        text=widget_text,
        chart=widget_chart
    )

    return schemas_widgets.BiodiversityWidgetResponse(
        data=widget_data,
        metadata={}
    )
