import logging
from shapely.geometry import Polygon
from shapely import wkt

from celery import shared_task
from climada.util.coordinates import country_to_iso
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.enums import SCENARIO_LOOKUPS

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# TODO probably make this a class
def standardise_scenario(scenario_name=None, scenario_growth=None, scenario_climate=None, scenario_year=None):

    if not scenario_name and (scenario_climate is None or scenario_growth is None):
        raise ValueError('When scenario_name is not set, scenario_climate and scenario_growth must be')

    if scenario_year and int(scenario_year) == 2020:
        return 'historical', 'historical', 'historical'

    if scenario_name and not scenario_growth:
        scenario_growth = SCENARIO_LOOKUPS[scenario_name]['scenario_growth']
    if scenario_name and not scenario_climate:
        scenario_climate = SCENARIO_LOOKUPS[scenario_name]['scenario_climate']

    return scenario_name, scenario_growth, scenario_climate


def convert_to_polygon(location_poly):
    if isinstance(location_poly, list):
        if isinstance(location_poly[0], list):
            location_poly = Polygon(location_poly)
        else:
            if len(location_poly) != 4:
                raise ValueError(f'Could not read location polygon: {location_poly}')
            else:
                location_poly = bbox_to_wkt(location_poly)
    if isinstance(location_poly, str):
        location_poly = wkt.loads(location_poly)
    if len(location_poly.exterior.coords[:]) - 1 != 4:
        LOGGER.warning("API doesn't handle non-bounding box polygons yet: converting to box")
    return location_poly

def bbox_to_wkt(bbox):
    if len(bbox) != 4:
        raise ValueError('Expected bbox to have four points')
    # TODO use climada utils to standardise around 180 degrees longitude
    lat_list = [bbox[i] for i in [1, 3, 3, 1]]
    lon_list = [bbox[i] for i in [0, 0, 2, 2]]
    polygon = Polygon([[lon, lat] for lat, lon in zip(lat_list, lon_list)])
    return polygon.wkt
