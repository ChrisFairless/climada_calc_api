import logging
import numpy as np
import json

from django.db import transaction
from celery import chain, shared_task
from celery_singleton import Singleton

from climada.engine.impact import Impact
from climada.entity import ImpactFunc, ImpactFuncSet, ImpfTropCyclone, Exposures
from climada.hazard import Hazard
import climada.util.coordinates as u_coord

from calc_api.vizz.schemas import schemas
from calc_api.calc_methods.util import country_iso_from_parameters
from calc_api.config import ClimadaCalcApiConfig
from calc_api.calc_methods.profile import profile
from calc_api.calc_methods.colourmaps import Legend
from calc_api.calc_methods.calc_hazard import get_hazard_event, get_hazard_by_return_period
from calc_api.vizz.endpoints.get_exposure import get_exposure
from calc_api.calc_methods.calc_impact import get_impact_event, get_impact_by_return_period
from calc_api.calc_methods.colourmaps import PALETTE_HAZARD_COLORCET, PALETTE_EXPOSURE_COLORCET, PALETTE_IMPACT_COLORCET

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))

# TODO: change the looping structures when multiple countries are involved. It's cheaper to assign centroids etc before
#  everything gets merged (though there might be an issue with multicountry polygon aggregations?)

# TODO: separate the calculations logic from the formatting to a schema. Attach the formatting to the API version.


def map_hazard_climate(request: schemas.MapHazardClimateRequest):
    country_iso = country_iso_from_parameters(
            location_scale=request.location_scale,
            location_code=request.location_code,
            location_name=request.location_name,
            location_poly=request.location_poly,
            representation="alpha3"
    )
    # Initiate chain of calculations:
    #with transaction.atomic():
    res = chain(
        get_hazard_by_return_period.s(
            country=country_iso,
            hazard_type=request.hazard_type,
            return_period=request.hazard_rp,
            scenario_name=request.scenario_name,
            scenario_climate=request.scenario_climate,
            scenario_year=request.scenario_year,
            location_poly=request.location_poly,
            aggregation_scale=request.aggregation_scale
        ),
        points_to_map_response.s('intensity', PALETTE_HAZARD_COLORCET)
    ).apply_async()
    out = res.id
    return out


def map_hazard_event(request: schemas.MapHazardEventRequest):
    # Initiate chain of calculations:
    #with transaction.atomic():

    country_iso = country_iso_from_parameters(
        location_name=request.location_name,
        location_code=request.location_code,
        location_scale=request.location_scale,
        location_poly=request.location_poly,
        representation="alpha3"
    )
    res = chain(
        get_hazard_event.s(
            country=country_iso,
            hazard_type=request.hazard_type,
            scenario_name=request.scenario_name,
            scenario_climate=request.scenario_climate,
            scenario_year=request.scenario_year,
            event_name=request.hazard_event_name,
            location_poly=request.location_poly,
            aggregation_scale=request.aggregation_scale
        ),
        points_to_map_response.s('intensity', PALETTE_HAZARD_COLORCET)
    ).apply_async()
    out = res.id
    return out


def map_exposure(request: schemas.MapExposureRequest):
    # Initiate chain of calculations:
    #with transaction.atomic():
    res = chain(
        get_exposure.s(request),
        points_to_map_response.s('value', PALETTE_EXPOSURE_COLORCET)
    ).apply_async()
    out = res.id
    return out


def map_impact_climate(request: schemas.MapImpactClimateRequest):
    country_iso = country_iso_from_parameters(
        location_name=request.location_name,
        location_code=request.location_code,
        location_scale=request.location_scale,
        location_poly=request.location_poly,
        representation="alpha3"
    )

    # Initiate chain of calculations:
    #with transaction.atomic():
    res = chain(
        get_impact_by_return_period.s(
            country_list=country_iso,
            hazard_type=request.hazard_type,
            return_period=request.hazard_rp,
            exposure_type=request.exposure_type,
            impact_type=None,
            scenario_name=request.scenario_name,
            scenario_growth=request.scenario_growth,
            scenario_climate=request.scenario_climate,
            hazard_year=request.scenario_year,
            exposure_year=request.scenario_year,
            location_poly=request.location_poly,
            aggregation_scale=request.aggregation_scale
        ),
        points_to_map_response.s('value', PALETTE_IMPACT_COLORCET)
    ).apply_async()
    out = res.id
    return out


def map_impact_event(request: schemas.MapImpactEventRequest):
    # Initiate chain of calculations:
    #with transaction.atomic():
    country_iso = country_iso_from_parameters(
        location_name=request.location_name,
        location_code=request.location_code,
        location_scale=request.location_scale,
        location_poly=request.location_poly,
        representation="alpha3"
    )
    res = chain(
        get_impact_event.s(
            country=country_iso,
            hazard_type=request.hazard_type,
            exposure_type=request.exposure_type,
            impact_type=None,
            scenario_name=request.scenario_name,
            scenario_growth=request.scenario_growth,
            scenario_climate=request.scenario_climate,
            scenario_year=request.scenario_year,
            return_period=request.hazard_event_name,
            location_poly=request.location_poly,
            aggregation_scale=request.aggregation_scale
        ),
        points_to_map_response.s('value', PALETTE_IMPACT_COLORCET)
    ).apply_async()
    out = res.id
    return out


@shared_task(base=Singleton)
def points_to_map_response(data_list, value_name, color_palette):
    data_list = [entry for entry in data_list if entry[value_name] != 0]

    bounds = u_coord.latlon_bounds(np.array([entry['lat'] for entry in data_list]),
                                   np.array([entry['lon'] for entry in data_list]))


    legend = Legend([entry['intensity'] for entry in data_list],
                    color_palette,
                    n_cols=12,
                    reverse=True)

    outdata = schemas.Map(
        items=[
            schemas.MapEntry(lat=entry['lat'], lon=entry['lon'], value=entry[value_name], geom='null', color=c)
            for entry, c
            in zip(data_list, legend.colors)
        ],
        legend=schemas.ColorbarLegend(
            title="Dummy hazard dataset",  #TODO set dynamically
            units="m/s",
            value="18.1",
            items=[
                schemas.ColorbarLegendItem(band_min=lo, band_max=hi, color=col)
                for lo, hi, col in zip(legend.intervals[:-1], legend.intervals[1:], legend.colorscale)
            ]
        )
    )

    metadata = schemas.MapMetadata(
        description="Test hazard map",  #TODO set all these too
        file_uri="",
        units='m/s',
        custom_fields={},
        bounding_box=list(bounds)
    )

    LOGGER.debug('ITEMS')
    for entry in outdata.items:
        LOGGER.debug(entry)
        LOGGER.debug('lat')
        LOGGER.debug(entry.lat)
        LOGGER.debug(json.dumps(entry.lat))
        LOGGER.debug('lon')
        LOGGER.debug(entry.lon)
        LOGGER.debug(json.dumps(entry.lon))
        LOGGER.debug('geom')
        LOGGER.debug(entry.geom)
        LOGGER.debug(json.dumps(entry.geom))
        LOGGER.debug('value')
        LOGGER.debug(entry.value)
        LOGGER.debug(json.dumps(entry.value))
        LOGGER.debug('color')
        LOGGER.debug(entry.color)
        LOGGER.debug(json.dumps(entry.color))
        LOGGER.debug('dict')
        LOGGER.debug(entry.__dict__)
        LOGGER.debug(json.dumps(entry.__dict__))

    return json.dumps(schemas.MapResponse(data=outdata, metadata=metadata))

    # from calc_api.vizz.schemas_examples import make_dummy_mapjobschema
    # import uuid
    # from pathlib import Path
    # import pandas as pd
    # from climada_calc.settings import STATIC_ROOT
    # from calc_api.calc_methods.colourmaps import PALETTE_HAZARD_COLORCET, PALETTE_EXPOSURE_COLORCET, \
    #     PALETTE_IMPACT_COLORCET
    # job_id = uuid.uuid4()
    # SAMPLE_DIR = Path(STATIC_ROOT, "sample_data")
    # haz_path = Path(SAMPLE_DIR, "map_haz_rp.csv")
    # df = pd.read_csv(haz_path)
    # raster_path = Path("/rest", "vtest", "img", "map_haz_rp.tif")
    # raster_uri = 'test'
    # location = "/map/hazard/climate/" + str(job_id)
    # mapjob = make_dummy_mapjobschema(
    #     lat_array=df['lat'],
    #     lon_array=df['lon'],
    #     values=df['intensity'],
    #     palette=PALETTE_HAZARD_COLORCET,
    #     title="Dummy hazard dataset",
    #     description="Test hazard climatology map",
    #     units="m/s",
    #     location='test',
    #     example_value="18.1",
    #     raster_uri='test',
    #     job_id=job_id
    # )
    #
    # LOGGER.debug('MAPJOBSCHEMA')
    # LOGGER.debug(mapjob)
    # return mapjob
