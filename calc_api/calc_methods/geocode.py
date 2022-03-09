import requests
from typing import List

from climada_calc.settings import GEOCODE_URL
from calc_api.vizz.schemas import GeocodePlaceList, GeocodePlace


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
        return GeocodePlace(name=exact_response[0]['display_name'],
                            id=exact_response[0]['osm_id'],
                            bbox=exact_response[0]['boundingbox'])
    # is a close match acceptable?
    elif not exact:
        return GeocodePlace(name=response[0]['display_name'],
                            id=response[0]['osm_id'],
                            bbox=response[0]['boundingbox'])
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
    suggestions = [GeocodePlace(name=p['display_name'], id=p['osm_id'], bbox=p['boundingbox']) for p in response]
    return GeocodePlaceList(data=suggestions)
