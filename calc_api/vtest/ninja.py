import datetime as dt
import json
from time import sleep
import pandas as pd
from pathlib import Path
import base64
import uuid
from typing import List
from millify import millify

from django.contrib import auth
from django.middleware import csrf

from ninja import NinjaAPI, Router
from ninja.security import HttpBearer, HttpBasicAuth

import climada.util.coordinates as u_coord

from calc_api.config import ClimadaCalcApiConfig
from calc_api.util import get_client_ip
from climada_calc.settings import BASE_DIR, STATIC_ROOT
import calc_api.vizz.models as models
from calc_api.vizz import schemas, schemas_widgets, schemas_geocoding
from calc_api.calc_methods.geocode import geocode_autocomplete
from calc_api.vizz import schemas_examples

conf = ClimadaCalcApiConfig()

SAMPLE_DIR = Path(STATIC_ROOT, "sample_data")
OPTIONS_FILE = Path(BASE_DIR, "calc_api", "options.json")


description = f"""
<table>
  <tr>
    <td>
      GitHub:
      <a target=_blank {conf.REPOSITORY_URL}>
        climada-data-api
      </a>
    </td>
    <td>
      <a target=_blank href={conf.LOGO_LINK}>
        <img src={conf.LOGO_SRC} height=100>
      </a>
    </td>
  </tr>
</table>
"""

class AuthBasic(HttpBasicAuth):
    def authenticate(self, request, username, password):
        return _basic_auth(request, username, password)


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            post_lock = PostLock.objects.latest('id')

            # signed out?
            if post_lock.signedout:
                return False
            # expired?
            if post_lock.expired():
                return False

            # same user?
            if request.user.username != post_lock.username:
                return False
            # same ip
            if get_client_ip(request) != post_lock.ipaddress:
                return False

            # token
            if token == post_lock.token:
                post_lock.expires = dt.datetime.now() + dt.timedelta(minutes=conf.LOCK_TIMEOUT)
                post_lock.save()
                return True

        except Exception:
            return False


def _basic_auth(request, username, password):
    user = auth.authenticate(request, username=username, password=password)

    if user is None or not user.is_staff:
        return None

    auth.login(request, user)

    return user


def basic_auth(request):
    try:
        username = request.POST['username']
        password = request.POST['password']
    except KeyError:
        return None
    return _basic_auth(request, username, password)


_default = NinjaAPI(
    title='CLIMADA Calc API',
    urls_namespace='vtest',
    description=description,
    # renderer=SchemaJSONRenderer()
)
_restricted = NinjaAPI(
    title='CLIMADA Calc API',
    version='vtest_restricted',
    description=description,
    csrf=True,
    # renderer=SchemaJSONRenderer()
)

_api = Router()
_rapi = Router(auth=AuthBearer(), tags=['restricted'])
_dapi = Router(auth=AuthBearer(), tags=['dangerous'])


@_api.get("/debug", tags=["debug"], summary="Short wait and return")
def map_debug(request):
    sleep(4)
    return {"success": "true"}


@_api.get("/options", tags=["options"], summary="Options in the RECA web tool")
def get_options(request):
    return json.load(open(OPTIONS_FILE))


#TODO handle errors, write error messages/statuses
#TODO should all this work with schemas? We need some way to validate all the inputs?

@_api.post(
    "/map/hazard/climate",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job to construct climatological hazard map data"
)
def _api_map_hazard_climate_submit(request, data: schemas.MapHazardClimateRequest = None):
    """
    Return a Job Schema without actually submitting a job or adding to DB
    """
    job = schemas_examples.make_dummy_job(data, "/map/hazard/climate?job_id=", uuid.uuid4())
    job = schemas.MapJobSchema(**job.__dict__)
    return job


@_api.get(
    "/map/hazard/climate",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll job for climatological hazard map data"
)
def _api_map_hazard_climate_poll(request, job_id: uuid.UUID = None):
    """
    Return a completed mapping job. Always the same.
    """
    return schemas_examples.make_dummy_mapjobschema_hazard(request, job_id)



@_api.post(
    "/map/hazard/event",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Construct hazard data for one event"
)
def _api_map_hazard_event_submit(request, data: schemas.MapHazardEventRequest = None):
    """
    Return a Job Schema without actually submitting a job or adding to DB
    """
    job = schemas_examples.make_dummy_job(data, "/map/hazard/event?job_id=", uuid.uuid4())
    return schemas.MapJobSchema(**job.__dict__)


@_api.get(
    "/map/hazard/event",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll for hazard event map data"
)
def _api_map_hazard_event_poll(request, job_id: uuid.UUID = None):
    return _api_map_hazard_climate_poll(request, job_id)


@_api.post(
    "/map/exposure",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job to construct exposure map data"
)
def _api_map_exposure_submit(request, data: schemas.MapExposureRequest = None):
    """
    Return a Job Schema without actually submitting a job or adding to DB
    """
    job = schemas_examples.make_dummy_job(data, "/map/exposure?job_id=", uuid.uuid4())
    return schemas.MapJobSchema(**job.__dict__)


@_api.get(
    "/map/exposure",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll for exposure map data"
)
def _api_map_exposure_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_mapjobschema_exposure(request, job_id)


@_api.post(
    "/map/impact/climate",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job for climatological impact map data"
)
def _api_map_impact_climate_submit(request, data: schemas.MapImpactClimateRequest = None):
    """
    Return a Job Schema without actually submitting a job or adding to DB
    """
    job = schemas_examples.make_dummy_job(data, "/map/impact/climate?job_id=", uuid.uuid4())
    return schemas.MapJobSchema(**job.__dict__)


@_api.get(
    "/map/impact/climate",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll for climatological impact map data"
)
def _api_map_impact_climate_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_mapjobschema_impact(request, job_id)


@_api.post(
    "/map/impact/event",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job to get impact map data for one event"
)
def _api_map_impact_event_submit(request, data: schemas.MapImpactEventRequest = None):
    job = schemas_examples.make_dummy_job(data, "/map/impact/event?job_id=", uuid.uuid4())
    return schemas.MapJobSchema(**job.__dict__)


@_api.get(
    "/map/impact/event",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll for impact map data"
)
def _api_map_impact_event_poll(request, job_id: uuid.UUID = None):
    return _api_map_impact_climate_poll(request, job_id)


@_api.post(
    "/exceedance/hazard",
    tags=["exceedance"],
    response=schemas.ExceedanceJobSchema,
    summary="Submit job for hazard intensity exceedance curve data"
)
def _api_exceedance_hazard_submit(request, data: schemas.ExceedanceHazardRequest = None):
    job = schemas_examples.make_dummy_job(data, "/exceedance/hazard?job_id=", uuid.uuid4())
    return schemas.ExceedanceJobSchema(**job.__dict__)


@_api.get(
    "/exceedance/hazard",
    tags=["exceedance"],
    response=schemas.ExceedanceJobSchema,
    summary="Poll job for hazard intensity exceedance curve data"
)
def _api_exceedance_hazard_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_exceedance_hazard(job_id)

@_api.post(
    "/exceedance/impact",
    tags=["exceedance"],
    response=schemas.ExceedanceJobSchema,
    summary="Submit job for impact exceedance curve data"
)
def _api_exceedance_impact_submit(request, data: schemas.ExceedanceImpactRequest = None):
    job = schemas_examples.make_dummy_job(data, "/exceedance/impact?job_id=", uuid.uuid4())
    return schemas.ExceedanceJobSchema(**job.__dict__)


@_api.get(
    "/exceedance/impact",
    tags=["exceedance"],
    response=schemas.ExceedanceJobSchema,
    summary="Poll job for impact exceedance curve data"
)
def _api_exceedance_impact_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_exceedance_impact(job_id)


@_api.post(
    "/timeline/hazard",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Submit job for hazard intensity over time"
)
def _api_timeline_hazard_submit(request, data: schemas.TimelineHazardRequest = None):
    job = schemas_examples.make_dummy_job(data, "/timeline/hazard?job_id=", uuid.uuid4())
    return schemas.TimelineJobSchema(**job.__dict__)


@_api.get(
    "/timeline/hazard",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Poll job for hazard intensity over time"
)
def _api_timeline_hazard_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_timeline("m/s", 20, job_id=job_id)


@_api.post(
    "/timeline/exposure",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Submit job for exposure over time"
)
def _api_timeline_exposure_submit(request, data: schemas.TimelineExposureRequest = None):
    job = schemas_examples.make_dummy_job(data, "/timeline/exposure?job_id=", uuid.uuid4())
    return schemas.TimelineJobSchema(**job.__dict__)


@_api.get(
    "/timeline/exposure",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Poll job for exposure over time"
)
def _api_timeline_exposure_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_timeline("people", 1000000, job_id=job_id)


@_api.post(
    "/timeline/impact",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Submit job for risk over time"
)
def _api_timeline_impact_submit(request, data: schemas.TimelineImpactRequest = None):
    job = schemas_examples.make_dummy_job(data, "/timeline/impact?job_id=", uuid.uuid4())
    return schemas.TimelineJobSchema(**job.__dict__)


@_api.get(
    "/timeline/impact",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Poll job for risk over time"
)
def _api_timeline_impact_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_timeline("people", 1000000, job_id=job_id)



# TODO /breakdown/exposure endpoint





# @_api.post("/measures",
#            tags=["adaptation measures"],
#            response=schemas.MeasureSchema,
#            summary="Create an adaptation measure")
# def _api_adaptation_measure_create(request, measure_request: schemas.CreateMeasureSchema):
#     d = measure_request.__dict__
#     d['id'] = uuid.uuid4()
#     d['user_generated'] = True
#     return schemas.MeasureSchema(**d)
#
#
# @_api.get("/measures",
#           tags=["adaptation measures"],
#           response=List[schemas.MeasureSchema],
#           summary="Get adaptation measures")
# def _api_adaptation_measure_get(request, measure_request: schemas.MeasureRequestSchema = None):
#     measures = models.Measure.objects.filter(user_generated=False)
#     return [schemas.MeasureSchema(**m.__dict__) for m in measures]


@_api.get("/geocode/autocomplete", tags=["geocode"], response=schemas_geocoding.GeocodePlaceList,
          summary="Get suggested locations from a string")
def _api_geocode_autocomplete(request, query):
    return geocode_autocomplete(query)


# Widgets
# =========================================================

@_api.post(
    "/widgets/risk-timeline",
    tags=["widget"],
    response=schemas_widgets.TimelineWidgetJobSchema,
    summary="Create data for the risk over time section of the RECA site"
)
def _api_widget_risk_timeline_submit(request, data: schemas_widgets.TimelineWidgetRequest = None):
    job = schemas_examples.make_dummy_job(data, "/widgets/risk-timeline?job_id=", uuid.uuid4())
    return schemas_widgets.TimelineWidgetJobSchema(**job.__dict__)


@_api.get(
    "/widgets/risk-timeline",
    tags=["widget"],
    response=schemas_widgets.TimelineWidgetJobSchema,
    summary="Create data for the risk over time section of the RECA site"
)
def _api_widget_risk_timeline_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_timelinewidget_risk(job_id)


@_api.post(
    "/widgets/biodiversity",
    tags=["widget"],
    response=schemas_widgets.BiodiversityWidgetJobSchema,
    summary="Create data for the biodiversity section of the RECA site"
)
def _api_widget_biodiversity_submit(request, data: schemas_widgets.BiodiversityWidgetRequest = None):
    job = schemas_examples.make_dummy_job(data, "/widgets/biodiversity?job_id=", uuid.uuid4())
    return schemas_widgets.BiodiversityWidgetJobSchema(**job.__dict__)


@_api.get(
    "/widgets/biodiversity",
    tags=["widget"],
    response=schemas_widgets.BiodiversityWidgetJobSchema,
    summary="Poll for data for the biodiversity section of the RECA site"
)
def _api_widget_biodiversity_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_biodiversitywidget(job_id)


@_api.post(
    "/widgets/social-vulnerability",
    tags=["widget"],
    response=schemas_widgets.SocialVulnerabilityWidgetJobSchema,
    summary="Create data for the social vulnerability section of the RECA site"
)
def _api_widget_social_vulnerability_submit(request, data: schemas_widgets.SocialVulnerabilityWidgetRequest = None):
    job = schemas_examples.make_dummy_job(data, "/widgets/social_vulnerability/", uuid.uuid4())
    return schemas_widgets.SocialVulnerabilityWidgetJobSchema(**job.__dict__)


@_api.get(
    "/widgets/social-vulnerability",
    tags=["widget"],
    response=schemas_widgets.SocialVulnerabilityWidgetJobSchema,
    summary="Poll for data for the social vulnerability section of the RECA site"
)
def _api_widget_socialvulnerability_poll(request, job_id: uuid.UUID = None):
    return schemas_examples.make_dummy_socialvulnerability_widget(job_id)


@_rapi.get("/csrf", tags=['restricted'], auth=None, include_in_schema=False)
def _csrf(request):
    return csrf.get_token(request)


_default.add_router("/", _api)
resturls = _default.urls

_restricted.add_router("/", _rapi)
_restricted.add_router("/", _dapi)
restrictedurls = _restricted.urls
