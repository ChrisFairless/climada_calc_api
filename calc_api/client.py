import json
from pathlib import Path
import requests
from urllib.parse import quote, unquote

from .config import ClimadaCalcApiConfig
from .util import file_checksum

CONF = ClimadaCalcApiConfig()


def _passes(cds, properties):
    if properties:
        obj_properties = cds['properties']
        for key, val in properties.items():
            if val != obj_properties.get(key, ''):
                return False
    return True


class AmbiguousResult(Exception):
    pass


class NoResult(Exception):
    pass


class FailedPostRequest(Exception):
    pass


class Client(object):
    def __init__(self, host=CONF.API_URL):
        self.host = host.rstrip("/")
        self.headers = {
            "accept": "application/json",
        }
        self.session = requests.session()
