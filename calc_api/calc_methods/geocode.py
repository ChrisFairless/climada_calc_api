import requests
import logging
from typing import List
from ninja import Schema
import os

from climada.util.coordinates import country_to_iso

from climada_calc.settings import GEOCODE_URL, MAPTILER_KEY
from calc_api.vizz.schemas import GeocodePlaceList, GeocodePlace
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz import schemas

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
        return schemas.GeocodePlace(
            name=location_name,
            id=code,
            scale='country',
            country=location_name,
            country_id=code,
            admin1=None,
            admin1_id=None,
            admin2=None,
            admin2_id=None,
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
    elif conf.GEOCODER == 'nominatim_web':
        if location_code:
            url = f'https://nominatim.openstreetmap.org/lookup?q=N{location_name}&format=json'
        else:
            url = f'https://nominatim.openstreetmap.org/search?q={location_name}&format=json'
        place = requests.request('GET', url)
        return osmnames_to_schema(place.json())
    elif conf.GEOCODER == 'maptiler':
        if location_code:
            url = f'https://api.maptiler.com/geocoding/{s}.json?key={MAPTILER_KEY}'
        else:
            url = f'https://api.maptiler.com/geocoding/{s}.json?key={MAPTILER_KEY}'
        place = requests.request.get(url=url, headers={'Origin': 'reca-api.herokuapp.com'})  # TODO split this to a setting?
        return maptiler_to_schema(place.json())
    else:
        raise ValueError(f"No valid geocoder selected. Set in climada_calc-config.yaml. Possible values: osmnames, nominatim_web. Current value: {conf.GEOCODER}")



### Self-deployed geocoder

def osmnames_to_schema(place):
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


def maptiler_to_schema(place):
    if len(list(place['place_type'])) > 1:
        LOGGER.debug(f'Geocoder was given multiple place types: {place["place_type"]}')
    return GeocodePlace(
        name=place['place_name'],
        id=place['id'],
        type=place['place_type'][0],
        city=_get_place_context_type(place, 'city'),
        county=_get_place_context_type(place, 'county'),
        state=_get_place_context_type(place, 'state'),
        country=_get_place_context_type(place, 'country'),
        bbox=place['bbox']
    )


def _get_place_context_type(place, type):
    name = [context['text'] for context in place['context'] if type in context['id']]
    return None if len(name) == 0 else name[0]


def query_place(s):
    if conf.GEOCODER == 'osmnames':
        query = GEOCODE_URL + "q/" + s
        response = requests.get(query).json()['results']
    elif conf.GEOCODER == 'nominatim_web':
        query = f'https://nominatim.openstreetmap.org/search?q={s}&format=json'
        response = requests.get(query).json()
    elif conf.GEOCODER == 'maptiler':
        query = f'https://api.maptiler.com/geocoding/{s}.json?key={MAPTILER_KEY}'
        response = requests.get(query, headers={'Origin': 'reca-api.herokuapp.com'}).json()['features']
    else:
        ValueError(
            f"No valid geocoder selected. Set in climada_calc-config.yaml. Possible values: osmnames, nominatim_web. Current value: {conf.GEOCODER}")
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
    if conf.GEOCODER in ['osmnames', 'nominatim_web']:
        suggestions = [osmnames_to_schema(p) for p in response]
    elif conf.GEOCODER == 'maptiler':
        suggestions = [maptiler_to_schema(p) for p in response]
    else:
        raise ValueError('GEOCODE must be one of osmnames, nominatim_web or maptiler')
    return GeocodePlaceList(data=suggestions)


def bbox_to_poly(bbox):
    lat_list = [bbox[i] for i in [1, 3, 3, 1]]
    lon_list = [bbox[i] for i in [0, 0, 2, 2]]
    return [{'lat': lat, 'lon': lon} for lat, lon in zip(lat_list, lon_list)]
