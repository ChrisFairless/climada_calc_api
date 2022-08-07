import json
import datetime
import logging
from decorator import decorator

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.models import JobLog
import calc_api.vizz.schemas as schemas
from calc_api.util import get_hash

conf = ClimadaCalcApiConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


@decorator
def database_job(func, *args, **kwargs):

    args_dict = {str(i): a for i, a in enumerate(args)}
    args_dict.update(kwargs)
    job_hash = get_hash(args_dict)

    try:
        existing_result = JobLog.objects.get(job_hash=job_hash)
        return existing_result.result
    except JobLog.DoesNotExist:
        result = func(*args, **kwargs)
        job = JobLog(job_hash=job_hash, func=func.__name__, args=str(args_dict), kwargs=str(kwargs), result=result)
        job_id = job.save()
        return result
