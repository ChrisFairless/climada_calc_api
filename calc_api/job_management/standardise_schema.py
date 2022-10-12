import logging
from decorator import decorator
from ninja import Schema

from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


@decorator
def standardise_schema(func, *args):
    assert len(args) == 1
    assert isinstance(args[0], Schema)
    assert hasattr(args[0], 'standardise')

    args[0].standardise()

    return func(args[0])
