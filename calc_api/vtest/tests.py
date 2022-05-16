from django.test import TestCase

from calc_api.client import Client, NoResult, FailedPostRequest
from calc_api.config import ClimadaCalcApiConfig

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