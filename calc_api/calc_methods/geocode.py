import requests
import logging
from typing import List
from ninja import Schema

from climada.util.coordinates import country_to_iso

from climada_calc.settings import GEOCODE_URL
from calc_api.vizz.schemas.schemas_geocode import GeocodePlaceList, GeocodePlace
from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


# TODO probably make this a class
def standardise_location(location_name=None, location_code=None, location_scale=None, location_poly=None):
    if not location_name and not location_code:
        raise ValueError('geocode_from_schema requires location_name or location_code to be properties')

    if not location_scale:
        LOGGER.warning("Watch out! Assuming location_scale is 'country'")
        location_scale = 'country'

    if location_scale != 'country':
        raise ValueError("For now geocoding only works with countries. Sorry!")  # Normally: determine scale

    if location_poly:
        raise ValueError("For now geocoding can't handle polygons. Sorry!")

    if location_scale in ['country', 'admin0']:
        code = location_code if location_code else location_name
        code = country_to_iso(code, representation='alpha3')
        return GeocodePlace(
            name=location_name,
            id=code,
            scale='country',
            country=location_name,
            admin1=None,
            admin2=None,
            bbox=None,  # TODO
            poly=None  # TODO
        )

    if location_scale in ['admin1']:
        raise ValueError("For now geocoding can't handle admin1. Sorry!")

    if conf.GEOCODER == 'osmnames':
        if location_code:
            try:
                return get_one_place(location_code, exact=True)
            except ValueError as msg:
                LOGGER.warning(f'Failed to get an exact match from on the location_code parameter '
                               '{request.location_code}. '
                               'Did you mean to provide a location_name instead? '
                               'Code will try again for a non-exact match. '
                               'Error message: {msg}')
        return get_one_place(location_name, exact=False)

    else:
        raise ValueError(f"No valid geocoder selected. Set in climada_calc-config.yaml. Current value: {conf.GEOCODER}")



### Self-deployed geocoder

def osmnames_to_schema(place):
    level = 'suburb'
    return GeocodePlace(
        name=place['display_name'],
        id=place['osm_id'],
        type=place['type'],
        city=place['city'],
        county=place['county'],
        state=place['state'],
        country=place['country'],
        bbox=place['boundingbox']
    )

def query_place(s):
    query = GEOCODE_URL + "q/" + s
    response = requests.get(query).json()['results']
    if len(response) == 0:
        return None
    else:
        return response


def get_one_place(s, exact=True):
    response = query_place(s)
    if len(response) == 0:
        raise ValueError(f'Could not identify a place corresponding to {s}')

    exact_response = [r for r in response if r['display_name'] == s]
    if exact_response:
        return osmnames_to_schema(exact_response[0])
    elif not exact:
        return osmnames_to_schema(response[0])
    else:
        raise ValueError(f'Could not exactly identify a place corresponding to {s}. Closest match: {response[0]["display_name"]}')


# TODO make this more resilient to unexpected failures to match
def get_place_hierarchy(s, exact=True):
    place = get_one_place(s, exact)
    if not place:
        return None

    address = place.name.split(', ')
    out = [
        get_one_place(", ".join(address[i:len(address)]), exact=True)
        for i in range(len(address))
    ]
    return GeocodePlaceList(data=out)


def geocode_autocomplete(s):
    response = query_place(s)
    if not response:
        return GeocodePlaceList(data=[])
    suggestions = [
        GeocodePlace(
            name=p['display_name'],
            id=p['osm_id'],
            bbox=p['boundingbox'],
            poly=bbox_to_poly(p['boundingbox'])
        )
        for p in response
    ]
    return GeocodePlaceList(data=suggestions)


def bbox_to_poly(bbox):
    lat_list = [bbox[i] for i in [1, 3, 3, 1]]
    lon_list = [bbox[i] for i in [0, 0, 2, 2]]
    return [{'lat': lat, 'lon': lon} for lat, lon in zip(lat_list, lon_list)]
