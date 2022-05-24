import time
from datetime import datetime as dt
from datetime import timezone

from django.test import TestCase

from calc_api.client import Client, NoResult, FailedPostRequest
from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz import ninja
from calc_api.vizz import schemas
CONF = ClimadaCalcApiConfig()


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

# TODO make the other tests work like this?
def FunctionalityTest(TestCase):
    def test_map_hazard(self):
        hazard_map_job = ninja._api_submit_map_hazard_climate(None)
        self.assertEqual(isinstance(hazard_map_job, schemas.MapResponse), True)