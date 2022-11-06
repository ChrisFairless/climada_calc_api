from pathlib import Path

import yaml

from climada_calc.settings import BASE_DIR


def human_to_int(hsize):
    try:
        return int(hsize)
    except ValueError:
        isize = int(hsize[:-1])
        hunit = hsize[-1].upper()
        for unit in ['K', 'M', 'G', 'T']:
            isize *= 1024
            if unit == hunit:
                return isize
        raise ValueError('cannot parse size from {hsize}')


class ClimadaCalcApiConfig:

    def read_config(self):
        with open(BASE_DIR / 'climada_calc-config.yaml') as stream:
            cdac = yaml.safe_load(stream)
            return cdac

    def __init__(self):
        cdac = self.read_config()
        self.LOG_LEVEL = cdac['log_level']
        self.DATA_ROOT = Path(cdac['data']['path-root'])
        self.DATA_URL = cdac['data']['url-root']
        self.GEOCODER = cdac['geocoder']
        self.TEST_FILE = Path(cdac['test']['file'])
        self.TEST_FORMAT = cdac['test']['format']
        self.TEMP_FILE = Path(cdac['test']['tmp'])
        self.API_URL = cdac['rest']['url-root']
        self.CHUNK_SIZE = human_to_int(cdac['chunk-size'])
        self.LOGO_LINK = cdac['climada-logo']['link']
        self.LOGO_SRC = cdac['climada-logo']['img-src']
        self.REPOSITORY_URL = cdac['repository_url']
        self.DEFAULT_LICENSE = cdac['defaults']['data-license']
        self.LOCK_TIMEOUT = int(cdac['lock-timeout'])
        self.DEFAULT_UNITS = {
            var: cdac['defaults']['units'][var]
            for var in ['temperature', 'distance', 'speed', 'area', 'currency', "people"]
        }
        self.DEFAULT_IMAGE_FORMAT = cdac['defaults']['image_format']
        self.DEFAULT_SCENARIO_NAME = cdac['defaults']['api_parameters']['scenario_name']
        self.DEFAULT_SCENARIO_YEAR = cdac['defaults']['api_parameters']['scenario_year']
        self.DEFAULT_N_TRACKS = cdac['defaults']['api_parameters']['n_tracks']
        self.DEFAULT_MIN_DIST_TO_CENTROIDS = float(cdac['defaults']['api_parameters']['min_dist_to_centroids'])
        self.CACHE_TIMEOUT = int(cdac['cache']['timeout'])
        self.JOB_TIMEOUT = int(cdac['job']['timeout'])
        self.DATABASE_MODE = cdac['database_mode']
