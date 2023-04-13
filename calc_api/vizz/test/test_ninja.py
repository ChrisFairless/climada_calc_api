# Tests run with a running server
import requests
import unittest
import logging
import time
import importlib
import numpy as np

# ---------------

# This is a script that systematically runs through all possible endpoint queries and makes a
# request for each of them. If they aren't in the database, and the server is able to calculate
# new data, it will set off a calculation.
#
# If new data are being calculated, you'll need to run this a second time to collect and log the
# results for future use.
#
# It's terrible for testing because it doesn't always tell you what's going wrong unless you're
# testing against a server that can't set off asynchronous calculations (recommended before deploy).
#
# Note to future developers: write tests. It would have saved so much time.

# ---------------

LOGGER = logging.getLogger(__name__)

server_address = 'http://0.0.0.0:8000/'
#server_address = 'https://reca-api.herokuapp.com/'
#server_address = 'https://reca-api-v1-at4us.ondigitalocean.app/'

wait_between_requests = 0.0
# measure_id_list = [5]
measure_id_list = [4]


location_list = ['Jamaica', 'Saint Kitts and Nevis', 'Port-au-Prince', 'Havana, Cuba']
# location_list = ['country.37', 'country.57', 'subregion.1024', 'region.942']
#location_list = ['Havana, Cuba', 'region.942']
#location_list = ['Toamasina', 'Mozambique', 'Manila, Philippines']
# location_list = ['Freetown, Sierra Leone']
#location_list = ['place.3038559']
# location_list = ['Freetown, Sierra Leone', 'place.3038559']

hazards_list = ['tropical_cyclone']
# hazards_list = ['extreme_heat']

test_fast = False

calculation_endpoints = {
    # 'rest/vizz/map/hazard/climate': 'MapHazardClimateReqauest',
    #  'rest/vizz/map/hazard/event',
    # 'rest/vizz/map/exposure': 'MapExposureRequest',
    # 'rest/vizz/map/impact/climate': 'MapImpactClimateRequest',
    # 'rest/vizz/map/impact/event',
    # 'rest/vizz/timeline/hazard': 'TimelineHazardRequest',
    # 'rest/vizz/timeline/exposure': 'TimelineExposureRequest',
    # 'rest/vizz/timeline/impact': 'TimelineImpactRequest',
    'rest/vizz/widgets/cost-benefit': 'CostBenefitWidgetRequest',
    'rest/vizz/widgets/risk-timeline': 'TimelineWidgetRequest',
    'rest/vizz/widgets/social-vulnerability': 'SocialVulnerabilityWidgetRequest',
    'rest/vizz/widgets/biodiversity': 'BiodiversityWidgetRequest',
    # 'rest/vizz/exceedance/hazard': 'ExceedanceHazardRequest',
    # 'rest/vizz/exceedance/impact': 'ExceedanceImpactRequest',
}
# TODO add vtest endpoints


def dynamic_request_create(endpoint, class_string, request_dict):
    if 'widgets' in endpoint:
        module = importlib.import_module('calc_api.vizz.schemas_widgets')
    else:
        module = importlib.import_module('calc_api.vizz.schemas')
    request = getattr(module, class_string)()
    for key, value in request_dict:
        if key in request.dict().keys():
            request[key] = value
    return request


class TestEndpoints(unittest.TestCase):

    # For now, just tests all endpoints respond

    def test_options(self):
        LOGGER.debug("Testing options endpoint")
        url = server_address + 'rest/vizz/options'
        response = requests.request("GET", url, headers={}, data={})
        self.assertEqual(response.status_code, 200)

        def check_defaults(l):
            if isinstance(l, dict):
                [check_defaults(item) for item in l.values()]
            if isinstance(l, list):
                has_defaults = np.sum([hasattr(item, 'default') for item in l])
                if has_defaults > 0:
                    n_default = np.sum([item['default'] for item in l if hasattr(item, 'default')])
                    names = [item.name for item in l if hasattr(item, "name")]
                    print(names)
                    if n_default == 0:
                        raise ValueError(f'Items have no default value set: {names}')
                    if n_default > 1:
                        raise ValueError(f'Items have too many defaults value set: {names}')
                # print("nesting")
                [check_defaults(item) for item in l]
            return True

        # TODO this isn't working yet
        self.assertTrue(check_defaults(response.json()))

    def test_geocode_id(self):
        LOGGER.debug("Testing geocoding endpoint: by id")
        url = server_address + 'rest/vizz/geocode/id/place.3038559'
        response = requests.request("GET", url, headers={}, data={})
        self.assertEqual(response.status_code, 200)

    def test_geocode_autocomplete(self):
        LOGGER.debug("Testing geocoding endpoint: by name")
        url = server_address + 'rest/vizz/geocode/autocomplete?query=Port-au-Prince'
        response = requests.request("GET", url, headers={}, data={})
        self.assertEqual(response.status_code, 200)

    @staticmethod
    def submit_job(
            endpoint,
            location_name,
            haz_name,
            impact_type,
            measure_list,
            year,
            climate_scenario,
            return_period,
            # aggregation_scale,
            # aggregation_method,
            units_hazard,
            units_exposure):

        key = f'{location_name} {endpoint} {haz_name} {impact_type} {year}, ' \
              f'{climate_scenario} {return_period} {measure_list}'
        LOGGER.info(key)

        request_settings = {
            'hazard_type': haz_name,
            'hazard_event_name': None,
            'hazard_rp': return_period,
            'impact_type': impact_type,
            'scenario_name': climate_scenario,
            'scenario_climate': None,  # Test these later
            'scenario_growth': None,
            'scenario_year': year,
            'measure_ids': measure_list,
            # 'location_scale': 'country',
            'location_code': None,
            'location_poly': None,
            'location_name': location_name,
            # 'aggregation_scale': aggregation_scale,
            # 'aggregation_method': aggregation_method,
            'format': 'tif',
            'units_currency': 'USD',
            'units_hazard': units_hazard,
            'units_warming': 'degF',
            'units_exposure': units_exposure,
            'units_distance': 'miles'
        }

        # req = dynamic_request_create(endpoint, calculation_endpoints[endpoint], request_settings)
        req = request_settings

        url = server_address + endpoint
        response = requests.post(url, headers={}, json=req)
        LOGGER.info(response.json()['job_id'])

        return key, response

    def test_all_calculation_endpoints(self):
        # Test all endpoints for all scenarios. Takes a while.
        LOGGER.debug("Testing all calculations endpoints")
        job_dict = {}
        url = server_address + 'rest/vizz/options'
        options = requests.request("GET", url, headers={}, data={})
        options = options.json()['data']['filters']
        for location_name in location_list:
            for endpoint in calculation_endpoints.keys():
                if 'map' in endpoint:
                    aggregation_scale = None
                    # LOGGER.warning(f"Skipping map endpoints for now: {endpoint}")
                    # continue
                else:
                    aggregation_scale = 'all'
                for haz_name, haz_options in options.items():
                    if haz_name not in hazards_list:
                        print(f"Skipping {haz_name} for now. Update hazards_list to include")
                        continue
                    if haz_name == "extreme_heat":
                        haz_unit = 'degF'
                        exposures = [{
                            'exposure_type': 'people',
                            'impact_type': 'people_affected',
                            'units': 'people'
                        }]
                    elif haz_name == 'tropical_cyclone':
                        haz_unit = 'mph'
                        exposures = [
                            {
                                'exposure_type': 'economic_assets',
                                'impact_type': 'economic_impact',
                                'units': 'dollars'
                            },
                            {
                                'exposure_type': 'economic_assets',
                                'impact_type': 'assets_affected',
                                'units': 'dollars'
                            },
                            {
                                'exposure_type': 'people',
                                'impact_type': 'people_affected',
                                'units': 'people'
                            }
                        ]
                    else:
                        raise ValueError('haz_name must be extreme_heat or tropical_cyclone')

                    year_options = [yr['value'] for yr in haz_options['scenario_options']['year']['choices'] if yr['value']!=2020]
                    scenario_options = [scen['value'] for scen in haz_options['scenario_options']['climate_scenario']['choices']]
                    rp_options = [rp['value'] for rp in haz_options['scenario_options']['return_period']['choices']]
                    if endpoint in ['rest/vizz/widgets/social-vulnerability', 'rest/vizz/widgets/biodiversity']:
                        year_options = [year_options[0]]
                        scenario_options = [scenario_options[0]]
                        rp_options = [rp_options[0]]
                        exposures = [exposures[0]]
                    aggregation_method = 'max' if 'hazard' in endpoint else 'sum'

                    for exp in exposures:
                        # TODO when there are two hazards this will have to be smarter
                        if endpoint == 'rest/vizz/widgets/cost-benefit':
                            rp_options = ['aai']
                            if haz_name == 'tropical_cyclone' and exp['impact_type'] in ['assets_affected', 'economic_impact']:
                                measure_options = [[m_id] for m_id in measure_id_list]
                            elif haz_name == 'extreme_heat' and exp['impact_type'] == 'people_affected':
                                measure_options = [[m_id] for m_id in measure_id_list]
                            else:
                                continue
                        else:
                            measure_options = [None]

                        for year in year_options:
                            for climate_scenario in scenario_options:
                                # if climate_scenario == 'historical' and 'timeline' in endpoint:
                                #     continue
                                #if climate_scenario == scenario_options[1]:
                                rp_list = rp_options
                                #else:
                                #    rp_list = [rp_options[-1]]

                                for return_period in rp_list:
                                    for measure_list in measure_options:
                                        key, response = self.submit_job(endpoint, location_name,
                                                                        haz_name,
                                                                        exp['impact_type'],
                                                                        measure_list,
                                                                        year, climate_scenario, return_period,
                                                                        # aggregation_scale, aggregation_method,
                                                                        haz_unit, exp['units'])
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
                                            LOGGER.warning(f'Job submission had trouble: {response}')
                                        self.assertEqual(response.status_code, 200)

                                        status = response.json()['status']
                                        if status == "SUCCESS":
                                            LOGGER.debug("Job was a success")
                                        else:
                                            job_dict[key] = {'endpoint': endpoint,
                                                             'job_id': response.json()['job_id'],
                                                             'request': response.request.body,
                                                             'response': response.json()}

                                            value = job_dict[key]
                                            url = server_address + value['endpoint'] + '/' + value['job_id']
                                            response = requests.request('GET', url, headers={})
                                            status = response.json()['status']
                                            if status not in ['SUCCESS', 'FAILURE', 'PENDING']:
                                                LOGGER.warning(f"Job submission not a success: {response.json()}")
                                        if wait_between_requests > 0:
                                            time.sleep(wait_between_requests)
                                    # self.assertEqual(response.status_code, 200)
                                    # self.assertEqual(status, 'SUCCESS')
                                        if test_fast:
                                            break
                                    if test_fast:
                                        break
                                if test_fast:
                                    break
                            if test_fast:
                                break
                        if test_fast:
                            break
                    # if test_fast: # Comment out to test all hazards
                    #     break
                if test_fast:
                    break
            if test_fast:
                break


        # Code to run through the results. Not used right now. Instead run the whole
        # script a second time to see if everything logged well.
        if False:
            for key, value in job_dict.items():
                url = server_address + value['endpoint'] + '/' + value['job_id']
                response = requests.request('GET', url, headers={})
                status = response.json()['status']
                poll_count = 0
                if status != 'SUCCESS':
                    while status not in ['SUCCESS', 'FAILURE'] and poll_count < 8:
                        poll_count += 1
                        time.sleep(10)
                        LOGGER.info(f"...polling. Status: {status}  URL: {url}")
                        response = requests.request('GET', url, headers={})
                        status = response.json()['status']
                    if status != "SUCCESS":
                        LOGGER.info(f"Job was not a success.")
                        LOGGER.info(f"\n\nJob info: \n{response.json()}")
                        LOGGER.info(f"\n\nJob request: \n{value}")
                # self.assertEqual(response.status_code, 200)
                # self.assertEqual(status, 'SUCCESS')

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
