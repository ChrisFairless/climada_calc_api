import logging
from decorator import decorator
from ninja import Schema

from calc_api.config import ClimadaCalcApiConfig

conf = ClimadaCalcApiConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


@decorator
def standardise_schema(func, *args, **kwargs):
    ix_args_schema = [i for i, a in enumerate(args) if isinstance(a, Schema)]
    ix_kwargs_schema = [key for key, item in kwargs.items() if isinstance(item, Schema)]

    for i in ix_args_schema:
        assert hasattr(args[i], 'standardise')
        args[i].standardise()

    for key in ix_kwargs_schema:
        assert hasattr(kwargs[key], 'standardise')
        kwargs[key].standardise()

    return func(*args, **kwargs)
