import logging
import sys
import pandas as pd
from pathlib import Path
from csv import DictReader
from django.core.management import BaseCommand

from calc_api.vizz.models import CountryData
from calc_api.calc_methods.widget_social_vulnerability import get_soc_vuln_data
from calc_api.calc_methods.geocode import standardise_location
from climada_calc.settings import BASE_DIR

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class Command(BaseCommand):
    # Show this when the user types help
    help = "Populates the database with country statistics"

    def handle(self, *args, **options):
        LOGGER.info("Creating country summaries for the database")

        # Clear out existing objects (this is a hacky bugfix)
        CountryData.objects.all().delete()

        # TODO get place options from the options.json
        place_list = [
            'St Kitts and Nevis',
            'Cuba',
            'Jamaica',
            'Haiti'
        ]

        for placename in place_list:
            LOGGER.info('Working on ' + placename)

            # TODO get the country population too

            country_iso = standardise_location(location_name=placename).country_id
            socvuln = get_soc_vuln_data(country_iso=country_iso, drop_zeroes=False)
            if socvuln[0]['value'] is None:
                # TODO let these be null
                socvuln_min = 0
                socvuln_max = 0
            else:
                df = pd.DataFrame(socvuln)
                socvuln_max = max(df['value'])
                socvuln_min = min(df['value'])

            _, _ = CountryData.objects.update_or_create(
                country_name=placename,
                country_iso3alpha=country_iso,
                population=0,
                socvuln_min=socvuln_min,
                socvuln_max=socvuln_max)
