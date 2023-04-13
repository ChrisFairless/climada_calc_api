import logging
import pandas as pd
from django.core.management import BaseCommand

from calc_api.vizz.models import Location
from calc_api.vizz.schemas import PlaceSchema

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# TODO get place options from the options.json
LOCATIONS = [
    'St Kitts and Nevis',
    'Havana, Cuba',
    'Jamaica',
    'Port-au-Prince, Haiti',
    'Freetown, Sierra Leone'
]

class Command(BaseCommand):
    # Show this when the user types help
    help = "Populates the database with a list of countries with precalculated data. Does not calculate the data."

    def handle(self, *args, **options):
        LOGGER.info("Creating country summaries for the database")

        # Clear out existing objects (this is a hacky bugfix)
        Location.objects.all().delete()

        for placename in LOCATIONS:
            LOGGER.info('Working on ' + placename)

            place = PlaceSchema(location_name=placename)
            place.standardise()
            location = place.geocoding.to_location_model()
            location.save()
