import requests

from climada_calc.settings import GEOCODE_URL
from calc_api.calc_methods.util import Bbox
from calc_api.db import GeocodeAutocompleteResponse


def query_place(s):
    query = GEOCODE_URL + "q/" + s
    response = requests.get(query).json()['results']
    if len(response) == 0:
        return {}
    else:
        return response


def get_place(s, exact=True):
    response = query_place(s)
    if len(response) == 0:
        return {}

    exact_response = [r for r in response if r['display_name'] == s]
    if exact_response:
        return dict(name=exact_response[0]['display_name'],
                    bbox=Bbox(exact_response[0]['boundingbox']))
    elif not exact:
        return dict(name=response[0]['display_name'],
                    bbox=Bbox(response[0]['boundingbox']))
    else:
        return {}


# TODO make this more resilient to unexpected failures to match
def get_place_hierarchy(s, exact=True):
    place = get_place(s, exact)
    if len(place) == 0:
        return {}
    else:
        address = place['name'].split(', ')
        out = [
            get_place(", ".join(address[i:len(address)]), exact=True)
            for i in range(len(address))
        ]
        for i in range(len(out)):
            out[i]['hierarchy'] = i
        return out


def geocode_autocomplete(s):
    response = query_place(s)
    if len(response) == 0:
        return []
    suggestions = [p['display_name'] for p in response]
    return GeocodeAutocompleteResponse(data=suggestions)
