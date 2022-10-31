import json
import datetime
import logging
from decorator import decorator
from time import sleep

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.models import JobLog
from calc_api.util import get_hash, get_args_dict, encode

conf = ClimadaCalcApiConfig()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


@decorator
def database_job(func, *args, **kwargs):
    args_dict = get_args_dict(func.__name__, *args, **kwargs)
    job_hash = get_hash(args_dict)
    if conf.DATABASE_MODE == 'off':
        return func(*args, **kwargs)

    elif conf.DATABASE_MODE == 'read':
        try:
            existing_result = JobLog.objects.get(job_hash=str(job_hash)).result
            return existing_result
        except JobLog.DoesNotExist:
            return func(*args, **kwargs)

    elif conf.DATABASE_MODE == 'create':
        try:
            existing_result = JobLog.objects.get(job_hash=str(job_hash)).result
            print(">>>Existing result found")
            return existing_result
        except JobLog.DoesNotExist:
            result = func(*args, **kwargs)
            _ = JobLog.objects.create(
                job_hash=str(job_hash),
                func=func.__name__,
                args=str(args_dict),
                kwargs=str(kwargs),
                result=result
            )
            return result

    elif conf.DATABASE_MODE == 'update':
        result = func(*args, **kwargs)
        _, _ = JobLog.objects.update_or_create(
            job_hash=str(job_hash),
            func=func.__name__,
            args=str(args_dict),
            kwargs=str(kwargs),
            result=result
        )
        return result

    elif conf.DATABASE_MODE == 'fail_missing':
        try:
            job = JobLog.objects.get(job_hash=str(job_hash)).result
            return job
        except JobLog.DoesNotExist as e:
            # raise JobLog.DoesNotExist(f'Not in precalculated database: \nFunction: {func.__name__} \n'
            #                           f'Args: {args_dict} \nError: {e}')
            LOGGER.warning(f'Not in precalculated database: \nFunction: {func.__name__} \n'
                           f'Args: {args_dict} \nError: {e}')
            
    else:
        raise ValueError(f'Could not process the configuration parameter database_mode. Value: {conf.DATABASE_MODE}')



@decorator
def endpoint_cache(func, return_class=None, location_root=None, *args, **kwargs):
    if not return_class:
        raise ValueError('endpoint_cache decorator needs return_class to be set')
    if not location_root:
        raise ValueError('endpoint_cache decorator needs location_root to be set')
    assert len(args) == 2
    assert len(kwargs) == 0
    request, data = args[0], args[1]
    print("\n\nCHECKING INPUTS ARE GOOD")
    print("DATA")
    print(data)
    # args_dict = get_args_dict(endpoint, data, {})
    # job_hash = get_hash(args_dict)
    job_hash = data.get_id()
    print('HASH')
    print(job_hash)

    # TODO make these schema class methods too
    if conf.DATABASE_MODE == 'off':
        return func(request, data=data)

    elif conf.DATABASE_MODE == 'read':
        try:
            job = JobLog.objects.get(job_hash=str(job_hash))
            if job.result is not None:
                return return_class.from_joblog(job, location_root)
        except JobLog.DoesNotExist:
            pass  # This is fine
        return func(request, data=data)

    elif conf.DATABASE_MODE == 'create':
        try:
            print("Create: checking for existing results")
            job = JobLog.objects.get(job_hash=str(job_hash))
            if job.result is not None:
                print("Found.\n" + str(job))
                return return_class.from_joblog(job, location_root)
            LOGGER.warning("Job with no result found, is the job already running? Resubmitting anyway.")
        except JobLog.DoesNotExist:
            print("Not found")
            _ = JobLog.objects.create(
                job_hash=str(job_hash),
                func=return_class.__name__,
                args=data,
                kwargs={},
                result=None
            )
        return func(request, data=data)

    elif conf.DATABASE_MODE == 'update':
        job = JobLog.objects.filter(job_hash=str(job_hash))
        if len(job) == 0:
            _ = JobLog.objects.create(
                job_hash=str(job_hash),
                func=return_class.__name__,
                args=data,
                kwargs={},
                result=None
            )
        return func(request, data=data)

    elif conf.DATABASE_MODE == 'fail_missing':
        try:
            job = JobLog.objects.get(job_hash=str(job_hash))
            if job.result is not None:
                return return_class.from_joblog(job, location_root)
            else:
                raise JobLog.DoesNotExist('The job DOES exist but it has no result.')
        except JobLog.DoesNotExist as e:
            # raise JobLog.DoesNotExist(f'Not in precalculated database: \nFunction: {func.__name__} \n'
            #                           f'Args: {args_dict} \nError: {e}')
            raise JobLog.DoesNotExist(f'Not in precalculated database: \nFunction: {func.__name__} \n'
                                      f'Request info: {data} \nError: {e}')

    else:
        raise ValueError(f'Could not process the configuration parameter database_mode. Value: {conf.DATABASE_MODE}')
