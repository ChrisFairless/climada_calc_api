import requests
from typing import List

from climada_calc.settings import GEOCODE_URL
from calc_api.vizz.schemas import GeocodePlaceList, GeocodePlace


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
        return None

    exact_response = [r for r in response if r['display_name'] == s]
    if exact_response:
        return osmnames_to_schema(exact_response[0])
    elif not exact:
        return osmnames_to_schema(response[0])
    else:
        return None


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
    suggestions = [osmnames_to_schema(p) for p in response]
    return GeocodePlaceList(data=suggestions)
