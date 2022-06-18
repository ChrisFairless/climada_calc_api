import json
import datetime

from calc_api.config import ClimadaCalcApiConfig
from calc_api.vizz.models import Job
import calc_api.vizz.schemas as schemas
from calc_api.util import get_hash

conf = ClimadaCalcApiConfig()



# Currently unused!
def create_job(request, location_root):
    job_hash = get_hash(request)
    existing_job = Job.objects.filter(job_id=job_hash)
    if len(existing_job) == 1:
        existing_job.refresh_expiry()
        return existing_job

    job = Job(
        job_id=job_hash,
        location=location_root + '?job_id=' + job_hash,
        status='submitted',
        request=json.dumps(request),
        submitted_at=datetime.datetime.now(),
        expires_at=datetime.datetime.now() + datetime.timedelta(seconds=conf.JOB_TIMEOUT),
        code=200
    )