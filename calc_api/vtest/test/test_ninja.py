# Tests run with a running server
import requests
import unittest
import logging

LOGGER = logging.getLogger(__name__)

server_address = 'http://0.0.0.0:8000/'
# server_address = 'https://reca-api.herokuapp.com/'

calculation_endpoints = [
        'rest/vtest/map/hazard/climate',
        'rest/vtest/map/hazard/event',
        'rest/vtest/map/exposure',
        'rest/vtest/map/impact/climate',
        'rest/vtest/map/impact/event',
        'rest/vtest/exceedance/hazard',
        'rest/vtest/exceedance/impact',
        'rest/vtest/timeline/hazard',
        'rest/vtest/timeline/exposure',
        'rest/vtest/timeline/impact',
        'rest/vtest/widgets/risk-timeline',
        'rest/vtest/widgets/biodiversity',
        'rest/vtest/widgets/social-vulnerability',
]

map_files = {
    'rest/vtest/map/hazard/climate': 'rest/vtest/img/map_haz_rp.tif',
    'rest/vtest/map/hazard/event': 'rest/vtest/img/map_haz_rp.tif',
    'rest/vtest/map/exposure': 'rest/vtest/img/map_exp.tif',
    'rest/vtest/map/impact/climate': 'rest/vtest/img/map_imp_rp.tif',
    'rest/vtest/map/impact/event': 'rest/vtest/img/map_imp_rp.tif',
}


class TestEndpoints(unittest.TestCase):

    # For now, just tests all endpoints respond

    def test_options_endpoint(self):
        url = server_address + 'rest/vtest/options'
        response = requests.request("GET", url, headers={}, data={})
        self.assertEqual(response.status_code, 200)

    def test_geocode_endpoint(self):
        url = server_address + 'rest/vtest/geocode/autocomplete?query=Miami'
        response = requests.request("GET", url, headers={}, data={})
        self.assertEqual(response.status_code, 200)

    def test_all_calculation_endpoints(self):
        for endpoint in calculation_endpoints:
            for method in ['POST', 'GET']:
                LOGGER.info(endpoint + ': ' + method)
                url = server_address + endpoint
                response = requests.request(method, url, headers={}, data={})
                self.assertEqual(response.status_code, 200)
                if method == 'GET':
                    self.assertNotEqual(response.json()['response'], None)

    def test_map_files_are_served(self):
        for endpoint, file_uri in map_files.items():
            url = server_address + file_uri
            response = requests.request("GET", url, headers={}, data={})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Content-Type'], 'image/tiff')


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    TESTS = unittest.TestLoader().loadTestsFromTestCase(TestEndpoints)
    unittest.TextTestRunner(verbosity=2).run(TESTS)
