import logging
from django.core.management import BaseCommand

from calc_api.vizz.models import JobLog

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class Command(BaseCommand):
    # Show this when the user types help
    help = "Clear all cached results from the database JobLog table."

    def handle(self, *args, **options):
        LOGGER.info("Clearing cached DB results")

        # Clear out existing objects (this is a hacky bugfix)
        JobLog.objects.all().delete()