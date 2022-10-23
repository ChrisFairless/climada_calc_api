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
            existing_result = JobLog.objects.get(job_hash=job_hash).result
            return existing_result
        except JobLog.DoesNotExist:
            return func(*args, **kwargs)

    elif conf.DATABASE_MODE == 'create':
        try:
            existing_result = JobLog.objects.get(job_hash=job_hash).result
            return existing_result
        except JobLog.DoesNotExist:
            result = func(*args, **kwargs)
            _ = JobLog.objects.create(
                job_hash=job_hash,
                func=func.__name__,
                args=str(args_dict),
                kwargs=str(kwargs),
                result=result
            )
            return result

    elif conf.DATABASE_MODE == 'update':
        result = func(*args, **kwargs)
        _, _ = JobLog.objects.update_or_create(
            job_hash=job_hash,
            func=func.__name__,
            args=str(args_dict),
            kwargs=str(kwargs),
            result=result
        )
        return result

    elif conf.DATABASE_MODE == 'fail_missing':
        try:
            job = JobLog.objects.get(job_hash=job_hash).result
            return job
        except JobLog.DoesNotExist as e:
            # raise JobLog.DoesNotExist(f'Not in precalculated database: \nFunction: {func.__name__} \n'
            #                           f'Args: {args_dict} \nError: {e}')
            LOGGER.warning(f'Not in precalculated database: \nFunction: {func.__name__} \n'
                           f'Args: {args_dict} \nError: {e}')
            
    else:
        raise ValueError(f'Could not process the configuration parameter database_mode. Value: {conf.DATABASE_MODE}')


@decorator
def endpoint_cache(func, endpoint=None, *args, **kwargs):
    if not endpoint:
        raise ValueError('database_job decorator needs endpoint to be set')
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

    if conf.DATABASE_MODE == 'off':
        return func(request, data=data)

    elif conf.DATABASE_MODE == 'read':
        try:
            job = JobLog.objects.get(job_hash=job_hash).result
            if job is not None:
                return job
        except JobLog.DoesNotExist:
            pass  # This is fine
        return func(request, data=data)

    elif conf.DATABASE_MODE == 'create':
        try:
            job = JobLog.objects.get(job_hash=job_hash).result
            if job is not None:
                print(str(job))
                return job
        except JobLog.DoesNotExist:
            print("EXCEPTING")
            _ = JobLog.objects.create(
                job_hash=job_hash,
                func=endpoint,
                args=data,
                kwargs={},
                result=None
            )
        return func(request, data=data)

    elif conf.DATABASE_MODE == 'update':
        job = JobLog.objects.filter(job_hash=job_hash)
        if len(job) == 0:
            _ = JobLog.objects.create(
                job_hash=job_hash,
                func=endpoint,
                args=data,
                kwargs={},
                result=None
            )
        return func(request, data=data)

    elif conf.DATABASE_MODE == 'fail_missing':
        try:
            job = JobLog.objects.get(job_hash=job_hash).result
            if job is not None:
                return job
            else:
                raise JobLog.DoesNotExist('The job DOES exist but it has no result.')
        except JobLog.DoesNotExist as e:
            # raise JobLog.DoesNotExist(f'Not in precalculated database: \nFunction: {func.__name__} \n'
            #                           f'Args: {args_dict} \nError: {e}')
            raise JobLog.DoesNotExist(f'Not in precalculated database: \nFunction: {func.__name__} \n'
                                      f'Request info: {data} \nError: {e}')

    else:
        raise ValueError(f'Could not process the configuration parameter database_mode. Value: {conf.DATABASE_MODE}')
