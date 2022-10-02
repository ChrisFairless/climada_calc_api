import logging
import sys
from pathlib import Path
from csv import DictReader
from django.core.management import BaseCommand

from calc_api.vizz.models import Cobenefit, Measure
from climada_calc.settings import BASE_DIR

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class Command(BaseCommand):
    # Show this when the user types help
    help = "Populates the database with measure and cobenefit data from staticfiles/data folder."

    def handle(self, *args, **options):
        LOGGER.info("Creating database entries for cobenefits and measures")

        data_directory = Path(BASE_DIR, "static", "data")
        cobenefits_file = Path(data_directory, "cobenefits.csv")
        measures_file = Path(data_directory, "measures.csv")

        # Create cobenefits
        for row in DictReader(open(cobenefits_file)):
            _, _ = Cobenefit.objects.get_or_create(**row)

        for row in DictReader(open(measures_file)):
            row = {key: (None if value == '' else value) for (key, value) in row.items()}
            cobenefit_list = row['cobenefits'].split(",") if row['cobenefits'] else None
            del row['cobenefits']
            measure, _ = Measure.objects.get_or_create(**row)

            if cobenefit_list:
                for cob in cobenefit_list:
                    cobenefit = Cobenefit.objects.get(value=cob)
                    measure.cobenefits.add(cobenefit)
                measure.save()
