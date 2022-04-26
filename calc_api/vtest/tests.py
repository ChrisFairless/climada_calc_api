import time
from datetime import datetime as dt
from datetime import timezone
from pathlib import Path

from django.test import TestCase

from calc_api.client import Client, NoResult, FailedPostRequest
from calc_api.config import ClimadaCalcApiConfig
import calc_api.vizz.schemas as schemas
import calc_api.vtest.ninja as api

CONF = ClimadaCalcApiConfig()


def dummy_submitted_map_job(request, endpoint):
    location = endpoint + "?job_id=tests"
    return schemas.MapJobSchema(
        job_id="tests",
        location=location,
        status="submitted",
        request=request.__dict__,
        submitted_at=dt.datetime(2020, 1, 1)
    )


def dummy_completed_map_job(request, endpoint, filename):
    location = endpoint + "?job_id=tests"
    path = Path(endpoint, filename)
    uri =  request.build_absolute_uri(path)
    return schemas.MapJobSchema(
        job_id="tests",
        location=location,
        status="submitted",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        runtime=60*60*24,
        response_uri=uri,
    )


class ClientTest(TestCase):
    def setUp(self):
        pass

    def test_authorize(self):
        client = Client()
        client2 = Client()
        self.assertEqual(client.host, 'http://localhost:8000')
        with self.assertRaises(FailedPostRequest):
            client.resign()
        client.authorize('climadapi', 'climapass')
        with self.assertRaises(FailedPostRequest):
            client2.authorize('climadapi', 'climapass')
        client.resign()


class EndpointTest(TestCase):

    submit_map_endpoints = {
        '/map/hazard/climate': api._api_submit_map_hazard_climate,
        '/map/hazard/event': api._api_submit_map_hazard_event,
        '/map/exposure': api._api_submit_map_exposure,
        'map/impact/climate': api._api_submit_map_impact_climate,
        'map/impact/event': api._api_submit_map_impact_event,
    }

    poll_map_endpoints = {
        '/map/hazard/climate': api._api_poll_map_hazard_climate,
        '/map/hazard/event': api._api_poll_map_hazard_event,
        '/map/exposure': api._api_poll_map_exposure,
        'map/impact/climate': api._api_poll_map_impact_climate,
        'map/impact/event': api._api_poll_map_impact_event,
    }

    poll_map_files = {
        '/map/hazard/climate': '/vtest/img/map_haz_rp.tif',
        '/map/hazard/event': '/vtest/img/map_haz_rp.tif',
        '/map/exposure': '/vtest/img/map_exp.tif',
        'map/impact/climate': '/vtest/img/map_imp_rp.tif',
        'map/impact/event': '/vtest/img/map_imp_rp.tif',
    }

    def test_submit_endpoints_return_jobs(self):
        for location, endpoint in self.submit_map_endpoints:
            request = None
            response = endpoint(request, location)
            self.assertEqual(response, dummy_submitted_map_job(request, endpoint))

    def test_poll_endpoints_return_results(self):
        for location, endpoint in self.submit_map_endpoints:
            request = None
            response = endpoint(request, location)
            desired_response = dummy_completed_map_job(request, self.poll_map_files[endpoint])
            self.assertEqual(response, desired_response)

    def test_jobs_contain_requests(self):
        example_request = schemas.MapHazardClimateRequest(
            hazard_type="tropical_cyclone",
            scenario_name="historical",
            scenario_climate="SSP585",
            scenario_rp=100,
            location_name="Orlando, Orange County, Florida, United States of America",
        )
        response = api._api_submit_map_hazard_climate(None, example_request)



