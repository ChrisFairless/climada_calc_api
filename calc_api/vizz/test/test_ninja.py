# Tests run with a running server
import requests
import unittest
import logging
import time
import importlib

LOGGER = logging.getLogger(__name__)

server_address = 'http://0.0.0.0:8000/'

#location_name = 'Saint Kitts and Nevis'
location_name = 'Cuba'

calculation_endpoints = {
    # 'rest/vizz/map/hazard/climate': 'MapHazardClimateRequest',
    #  'rest/vizz/map/hazard/event',
    # 'rest/vizz/map/exposure': 'MapExposureRequest',
    # 'rest/vizz/map/impact/climate': 'MapImpactClimateRequest',
    # 'rest/vizz/map/impact/event',
    # 'rest/vizz/timeline/hazard': 'TimelineHazardRequest',
    # 'rest/vizz/timeline/exposure': 'TimelineExposureRequest',
    'rest/vizz/timeline/impact': 'TimelineImpactRequest',
    'rest/vizz/widgets/risk-timeline': 'TimelineWidgetRequest',
    # 'rest/vizz/widgets/biodiversity': 'BiodiversityWidgetRequest',
    'rest/vizz/widgets/social-vulnerability': 'SocialVulnerabilityWidgetRequest',
    # 'rest/vizz/exceedance/hazard': 'ExceedanceHazardRequest',
    # 'rest/vizz/exceedance/impact': 'ExceedanceImpactRequest',
}


def dynamic_request_create(endpoint, class_string, request_dict):
    if 'widgets' in endpoint:
        module = importlib.import_module('calc_api.vizz.schemas_widgets')
    else:
        module = importlib.import_module('calc_api.vizz.schemas')
    request = getattr(module, class_string)()
    for key, value in request_dict:
        if key in request.__dict__().keys():
            request[key] = value
    return request


class TestEndpoints(unittest.TestCase):

    # For now, just tests all endpoints respond

    def test_options_endpoint(self):
        LOGGER.debug("Testing options endpoint")
        url = server_address + 'rest/vizz/options'
        response = requests.request("GET", url, headers={}, data={})
        self.assertEqual(response.status_code, 200)

    def test_geocode_endpoint(self):
        LOGGER.debug("Testing geocoding endpoint")
        url = server_address + 'rest/vizz/geocode/autocomplete?query=Miami'
        response = requests.request("GET", url, headers={}, data={})
        self.assertEqual(response.status_code, 200)

    @staticmethod
    def submit_job(endpoint, haz_name, exposure_type, impact_type, year, climate_scenario, return_period, aggregation_scale, aggregation_method, units):
        key = endpoint + ' ' + haz_name + ' ' + str(year) + ' ' + \
              climate_scenario + ' ' + return_period

        request_settings = {
            'hazard_type': haz_name,
            'hazard_event_name': None,
            'hazard_rp': return_period,
            'exposure_type': exposure_type,
            'impact_type': impact_type,
            'scenario_name': climate_scenario,
            'scenario_climate': None,  # Test these later
            'scenario_growth': None,
            'scenario_year': year,
            'location_scale': 'country',
            'location_code': None,
            'location_poly': None,
            'location_name': location_name,
            'aggregation_scale': aggregation_scale,
            'aggregation_method': aggregation_method,
            'format': 'tif',
            'units': units,
            'units_warming': 'degrees Fahrenheit',
            'units_response': units,
            'units_area': 'square miles'
        }

        # req = dynamic_request_create(endpoint, calculation_endpoints[endpoint], request_settings)
        req = request_settings

        url = server_address + endpoint
        response = requests.post(url, headers={}, json=req)
        return key, response

    def test_all_calculation_endpoints(self):
        # Test all endpoints for all scenarios. Takes a while.
        LOGGER.debug("Testing all calculations endpoints")
        job_dict = {}
        url = server_address + 'rest/vizz/options'
        options = requests.request("GET", url, headers={}, data={})
        options = options.json()['data']['filters']
        for endpoint in calculation_endpoints.keys():
            if 'map' in endpoint:
                aggregation_scale = None
                # LOGGER.warning(f"Skipping map endpoints for now: {endpoint}")
                # continue
            else:
                aggregation_scale = 'country'
            for haz_name, haz_options in options.items():
                if haz_name == "extreme_heat":
                    LOGGER.warning("Skipping extreme heat for now")
                    exposure_type = 'people'
                    impact_type = 'people_affected'
                    units = 'people'
                    continue
                elif haz_name == 'tropical_cyclone':
                    exposure_type = 'economic_assets'
                    impact_type = 'economic_impact'
                    units = 'dollars'
                else:
                    raise ValueError('haz_name must be extreme_heat or tropical_cyclone')
                year_options = [yr['value'] for yr in haz_options['scenario_options']['year']['choices']]
                scenario_options = [scen['value'] for scen in haz_options['scenario_options']['climate_scenario']['choices']]
                rp_options = [rp['value'] for rp in haz_options['scenario_options']['return_period']['choices']]
                if 'impact' not in endpoint:
                    rp_options = [rp for rp in rp_options if rp != "aai"]
                aggregation_method = 'max' if 'hazard' in endpoint else 'sum'
                for year in year_options:
                    for climate_scenario in scenario_options:
                        if climate_scenario == 'historical' and 'timeline' in endpoint:
                            continue
                        if climate_scenario == scenario_options[1]:
                            rp_list = rp_options
                        else:
                            rp_list = [rp_options[-1]]
                        for return_period in rp_list:
                            key, response = self.submit_job(endpoint, haz_name, exposure_type, impact_type, year,
                                                            climate_scenario, return_period, aggregation_scale,
                                                            aggregation_method, units)
                            job_details = f"""
Endpoint:\n
{endpoint}\n
Request:\n
{str(response.request.body)}\n
Response:\n
{response.json()}
                            """
                            LOGGER.debug(job_details)
                            if response.status_code != 200:
                                LOGGER.warning(job_details)
                            self.assertEqual(response.status_code, 200)

                            job_dict[key] = {'endpoint': endpoint,
                                             'job_id': response.json()['job_id']}

                            value = job_dict[key]
                            url = server_address + value['endpoint'] + '/' + value['job_id']
                            status = ''
                            while status not in ['SUCCESS', 'FAILURE']:
                                LOGGER.info(f"...polling. Status: {status}  URL: {url}")
                                response = requests.request('GET', url, headers={})
                                status = response.json()['status']
                                time.sleep(3)
                            if status != "SUCCESS":
                                LOGGER.info(f"not a success: {response.json()}")
                            self.assertEqual(response.status_code, 200)
                            self.assertEqual(status, 'SUCCESS')
                            break
                        break
                    break
                break
            # break


        for key, value in job_dict.items():
            url = server_address + value['endpoint'] + '/' + value['job_id']
            status = 'submitted'
            while status not in ['SUCCESS', 'FAILURE']:
                LOGGER.info(f"...polling. Status: {status}  URL: {url}")
                response = requests.request('GET', url, headers={})
                status = response.json()['status']
                time.sleep(3)
            if status != "SUCCESS":
                LOGGER.info(f"not a success: {response.json()}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(status, 'SUCCESS')

            image_uri = response.json()['response_uri']
            if image_uri is not None:
                image_response = requests.request('GET', image_uri, headers={}, data={})
                self.assertEqual(image_response.status_code, 200)
                self.assertEqual(image_response.headers['Content-Type'], 'image/tiff')


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    TESTS = unittest.TestLoader().loadTestsFromTestCase(TestEndpoints)
    unittest.TextTestRunner(verbosity=2).run(TESTS)
