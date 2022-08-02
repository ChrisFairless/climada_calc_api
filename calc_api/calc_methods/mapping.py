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

import calc_api.vizz.schemas as schemas
from calc_api.calc_methods.util import country_iso_from_parameters
from calc_api.config import ClimadaCalcApiConfig
from calc_api.calc_methods.profile import profile
from calc_api.calc_methods.colourmaps import Legend
from calc_api.calc_methods.calc_hazard import get_hazard_event, get_hazard_by_return_period
from calc_api.calc_methods.calc_exposure import get_exposure
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
        location_scale=request.location_scale,
        location_code=request.location_code,
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
    country_iso = country_iso_from_parameters(
        location_scale=request.location_scale,
        location_code=request.location_code,
        location_poly=request.location_poly,
        representation="alpha3"
    )
    res = chain(
        get_exposure.s(
            country=country_iso,
            exposure_type=request.exposure_type,
            scenario_name=request.scenario_name,
            scenario_growth=request.scenario_growth,
            scenario_year=request.scenario_year,
            location_poly=request.location_poly,
            aggregation_scale=request.aggregation_scale
        ),
        points_to_map_response.s('value', PALETTE_EXPOSURE_COLORCET)
    ).apply_async()
    out = res.id
    return out


def map_impact_climate(request: schemas.MapImpactClimateRequest):
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
        get_impact_by_return_period.s(
            country_list=country_iso,
            hazard_type=request.hazard_type,
            return_periods=request.hazard_rp,
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
        location_scale=request.location_scale,
        location_code=request.location_code,
        location_name=request.location_name,
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


@profile()
def _outdated_map_hazard_from_parameters(hazard_type: str,
                               hazard_event_name: str,
                               scenario_name: str,
                               scenario_year: int,
                               scenario_rp: float,
                               location_scale: str,
                               location_code: str,
                               location_poly: str,
                               aggregation_scale: str = None,
                               aggregation_method: str = None):

    country_iso3alpha = country_iso_from_parameters(location_scale, location_code, location_poly, representation="alpha3")

    # TODO: validate scenario_name, scenario_year
    # TODO: parallelize all the following by country

    # Query hazard data
    if hazard_event_name:
        haz_array = get_hazard_event(
            country_list=country_iso3alpha,
            scenario_name=scenario_name,
            scenario_year=scenario_year,
            event_name=hazard_event_name,
            location_poly=location_poly,
            aggregation_scale=aggregation_scale
        )
    # Calculate hazard at return period
    elif scenario_rp:
        haz_lat, haz_lon, haz_array = get_hazard_by_return_period(
            country_list=country_iso3alpha,
            scenario_name=scenario_name,
            scenario_year=scenario_year,
            return_period=scenario_rp,
            location_poly=location_poly,
            aggregation_scale=aggregation_scale
        )
    else:
        raise ValueError("Either an event name or a return period must be provided")


    ix = haz_array != 0

    legend = Legend(haz_array[ix], PALETTE_HAZARD_COLORCET, n_cols=12, reverse=True)

    outdata = schemas.Map(
        items=[
            schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
            for lat, lon, v, c
            in zip(haz_lat[ix], haz_lon[ix], legend.values, legend.colors)
        ],
        legend=schemas.ColorbarLegend(
            title="Dummy hazard dataset",
            units="m/s",
            value="18.1",
            items=[
                schemas.ColorbarLegendItem(band_min=lo, band_max=hi, color=col)
                for lo, hi, col in zip(legend.intervals[:-1], legend.intervals[1:], legend.colorscale)
            ]
        )
    )

    return schemas.MapResponse(
        data=outdata,
        metadata=schemas.MapMetadata(
            description="Test hazard map",
            units="m/s"
        )
    )


@profile()
def _outdated_map_exposure_from_parameters(exposure_type: str,
                                 scenario_name: str,
                                 scenario_year: int,
                                 location_scale: str,
                                 location_code: str,
                                 location_poly: str,
                                 aggregation_scale: str = None,
                                 aggregation_method: str = None):

    country_iso3alpha_list = country_iso_from_parameters(location_scale, location_code, location_poly)

    # TODO: validate scenario_name, scenario_year


    if scenario_name:
        LOGGER.warning("API can't deal with exposure scenarios yet. Ignoring.")
    if scenario_year > 2022:
        LOGGER.warning("API can't deal with exposure scenarios yet. Ignoring.")

    if exposure_type == 'assets':
        exponents = '(1,1)'
        fin_mode = 'pc'
    elif exposure_type == 'people':
        exponents = '(0,1)'
        fin_mode = 'pop'
    else:
        raise ValueError("exposure_type must be either 'assets' or 'people'")

    # Query hazard data
    client = Client()
    exp = Exposures.concat([
        client.get_exposures(exposures_type='litpop', properties={'spatial_coverage': 'country',
                                                                  'country_iso3alpha': country,
                                                                  'exponents': exponents,
                                                                  'fin_mode': fin_mode})
        for country in country_iso3alpha_list
    ])

    if location_poly:
        raise ValueError("API doesn't handle polygons yet")  # TODO
        # haz = hazard_subset_extent(haz, bbox, nearest=True, drop_empty_events=True)

    if aggregation_scale:
        raise ValueError("API doesn't aggregate output yet")  # TODO

    ix = exp.gdf.value != 0
    if not all(ix):
        print("Info: removing zero-value exposures from the exposure on file")

    return schemas.MapResponse(lat=list(exp.gdf.latitude[ix]),
                       lon=list(exp.gdf.longitude[ix]),
                       value=list(exp.gdf.value[ix]),
                       metadata={}).check()



@profile()
def _outdated_map_impact_from_parameters(hazard_type: str,
                               hazard_event_name: str,
                               exposure_type: str,
                               scenario_name: str,
                               scenario_year: int,
                               scenario_rp: float,
                               location_scale: str,
                               location_code: str,
                               location_poly: str,
                               aggregation_scale: str = None,
                               aggregation_method: str = None):

    country_iso3alpha_list = country_iso_from_parameters(location_scale, location_code, location_poly, representation="alpha3")

    # TODO: validate scenario_name, scenario_year

    # Query hazard data
    # TODO could we can set off workers to get the hazard and exposure data in parallel?
    # TODO check hazard concat concatenates centroids/events correctly!
    client = Client()
    haz = Hazard.concat([
        client.get_hazard(hazard_type, properties={'spatial_coverage': 'country',
                                                   'country_iso3alpha': country,
                                                   'nb_synth_tracks': str(conf.DEFAULT_N_TRACKS),
                                                   'climate_scenario': scenario_name,
                                                   'ref_year': str(scenario_year)})
        for country in country_iso3alpha_list
    ])

    # Subset to events if specified
    if hazard_event_name:
        haz = haz.select(event_names=[hazard_event_name])

    # Set up exposures
    if exposure_type == 'assets':
        exponents = '(1,1)'
        fin_mode = 'pc'
        impf = ImpfTropCyclone.from_emanuel_usa()
    elif exposure_type == 'people':
        exponents = '(0,1)'
        fin_mode = 'pop'
        step_threshold = 50
        impf = ImpactFunc.from_step_impf(intensity=(0, step_threshold, 200))  # TODO make this better
        impf.name = 'Step function ' + str(step_threshold) + ' m/s'
    else:
        raise ValueError("exposure_type must be either 'assets' or 'people'")

    impf.haz_type = haz.tag.haz_type
    impf.unit = haz.units

    # TODO impact functions!
    impf_set = ImpactFuncSet()
    impf_set.append(impf)

    # Query exposure data
    exp = Exposures.concat([
        client.get_exposures(exposures_type='litpop', properties={'spatial_coverage': 'country',
                                                                  'country_iso3alpha': country,
                                                                  'exponents': exponents,
                                                                  'fin_mode': fin_mode})
        for country in country_iso3alpha_list
    ])

    # map exposures to hazard centroids
    centroid_mapping_colname = 'centr_' + haz.tag.haz_type
    if centroid_mapping_colname not in exp.gdf.columns:
        # TODO we might be able to speed this up with a raster method
        exp.assign_centroids(haz, distance='euclidean', threshold=conf.DEFAULT_MIN_DIST_TO_CENTROIDS)

    # Calculate impacts
    imp = Impact()
    imp.calc(exp, impf_set, haz, save_mat=True)

    if hazard_event_name:
        imp_array = imp.imp_mat.todense().A1
    elif scenario_rp:
        imp_array = imp.local_exceedance_imp(return_periods=(scenario_rp))
    else:
        raise ValueError("Either an event name or a return period must be provided")

    if location_poly:
        raise ValueError("API doesn't handle polygons yet")  # TODO
        # haz = hazard_subset_extent(haz, bbox, nearest=True, drop_empty_events=True)

    if aggregation_scale:
        raise ValueError("API doesn't aggregate output yet")  # TODO

    ix = imp_array != 0

    return schemas.MapResponse(lat=list(exp.gdf['latitude'][ix]),
                               lon=list(exp.gdf['longitude'][ix]),
                               value=list(imp_array[ix]),
                               metadata={}).check()
