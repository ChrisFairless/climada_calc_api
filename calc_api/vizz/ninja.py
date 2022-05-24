import datetime as dt
from time import sleep
import logging

from django.contrib import auth
from django.middleware import csrf

from ninja import NinjaAPI, Router
from ninja.security import HttpBearer, HttpBasicAuth

from calc_api.config import ClimadaCalcApiConfig
from calc_api.util import get_client_ip
from calc_api.vizz.schemas import schemas, schemas_widgets, schemas_geocode
from calc_api.vizz.util import get_options
from calc_api.calc_methods import mapping, geocode, widgets, timeline

conf = ClimadaCalcApiConfig()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(getattr(logging, conf.LOG_LEVEL))


description = f"""
<table>
  <tr>
    <td>
      GitLab:
      <a target=_blank href={conf.REPOSITORY_URL}>
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
    urls_namespace='vizz',
    description=description,
    #renderer=renderers.SchemaJSONRenderer()
)
_restricted = NinjaAPI(
   title='CLIMADA Calc API',
   urls_namespace='vizz_restricted',
   description=description,
   csrf=True,
   #renderer=renderers.SchemaJSONRenderer()
)

_api = Router()
_rapi = Router(auth=AuthBearer(), tags=['restricted'])
_dapi = Router(auth=AuthBearer(), tags=['dangerous'])


@_api.get("/map/debug/", tags=["debug"])
def map_debug(request):
    sleep(4)
    return {"success": "true"}


@_api.get(
    "/options",
    tags=["options"],
    summary="Options in the RECA web tool"
)
def _api_get_options(request=None):
    return get_options()


#######################################
#
#  MAPPING
#
#######################################

@_api.post(
    "/map/hazard/climate",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job for climatological hazard map data"
)
def _api_submit_map_hazard_climate(request, data: schemas.MapHazardClimateRequest):
    """
    Submit job to get climatological hazard intensity data for a map layer.

    ---
    parameters (outdated!!):
    - name: hazard_type
      description: Acronym of the hazard type, e.g. 'TC'
      required: true
      type: string
    - name: hazard_rp
      description: Return period of interest
      required: false
      type: float
    - name: scenario_name
      description: String representation of the scenario, e.g. RCP85. If not provided, historical data are returned
      required: false
      type: string
    - name: scenario_year
      description: Year of the analysis. If not provided, 2020 is returned
      required: false
      type: int
    - name: location_scale
      description: Type of location described in the location_code parameter, if used. Either 'global', 'ISO3',
        'admin0', 'admin1', 'admin2'
      required: false
      type: string
    - name: location_code
      description: List of admin codes for the desired location. If ISO3 codes are used, accepts 2- and 3-letter country
        abbreviations, country names and 3-digit country codes. If location_poly is also provided, its intersection
        is calculated with the locations here. Defaults to global if not provided.
      required: false
      type: string
    - name: location_poly
      description: Bounding polygon for the analysis. Provided as a list with two entries, a list of vertex latitudes and a list of
         vertex longitudes. If not provided, location_scale and location_code must be provided instead. If all are
         provided, the intersection of the administrative regions with this polygon are taken.
      required: false
      type: string
    - name: aggregation_scale
      description: One of None, 'admin0', 'admin1', 'admin2', 'global'. The aggregation level at which to return
        results. If None, they are returned at the native resolution of the input data.
      required: false
      type: string
    - name: aggregation_method
      description: One of 'sum', 'mean', 'max', 'min'. The method to use to aggregate point/gridded statistics to administrative
        regions.
      required: false
      type: string
    """
    job_id = mapping.map_hazard_climate(data)
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/hazard/climate')


@_api.get(
    "/map/hazard/climate/{uuid:job_id}",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll job for climatological hazard map data"
)
def _api_get_map_hazard_climate(request, job_id):
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/hazard/climate')


@_api.post(
    "/map/hazard/event",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job for single event hazard map data"
)
def _api_submit_map_hazard_event(request, data: schemas.MapHazardClimateRequest = None):
    job_id = mapping.map_hazard_event(data)
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/hazard/event')


@_api.get(
    "/map/hazard/event/{uuid:job_id}",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll job for single event hazard map data"
)
def _api_get_map_hazard_event(request, job_id):
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/hazard/event')


@_api.post(
    "/map/exposure",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job for exposure map data"
)
def _api_submit_map_exposure(request, data: schemas.MapExposureRequest):
    job_id = mapping.map_exposure(data)
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/exposure')


@_api.get(
    "/map/exposure/{uuid:job_id}",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll job for exposure map data"
)
def _api_get_map_exposure(request, job_id):
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/exposure')


@_api.post(
    "/map/impact/climate",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job for climatological risk map data"
)
def _api_submit_map_hazard_climate(request, data: schemas.MapHazardClimateRequest):
    job_id = mapping.map_impact_climate(data)
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/impact/climate')


@_api.get(
    "/map/impact/climate/{uuid:job_id}",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll job for climatological risk map data"
)
def _api_get_map_hazard_climate(request, job_id):
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/impact/climate')


@_api.post(
    "/map/impact/event",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Submit job for single event impact map data"
)
def _api_submit_map_hazard_event(request, data: schemas.MapHazardClimateRequest = None):
    job_id = mapping.map_impact_event(data)
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/impact/event')


@_api.get(
    "/map/hazard/event/{uuid:job_id}",
    tags=["map"],
    response=schemas.MapJobSchema,
    summary="Poll job for single event impact map data"
)
def _api_get_map_hazard_event(request, job_id):
    return schemas.MapJobSchema.from_task_id(job_id, 'rest/vizz/map/impact/event')


#######################################
#
#  TIMELINES
#
#######################################

@_api.post(
    "/timeline/hazard",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Submit job for hazard timeline data"
)
def _api_timeline_hazard_submit(request, data: schemas.TimelineHazardRequest):
    job_id = timeline.timeline_hazard(data)
    return schemas.TimelineJobSchema.from_task_id(job_id, 'rest/vizz/timeline/hazard')


@_api.get(
    "/timeline/hazard/{uuid:job_id}",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Poll job for hazard timeline data"
)
def _api_timeline_hazard_poll(request, job_id):
    return schemas.TimelineJobSchema.from_task_id(job_id, 'rest/vizz/timeline/hazard')
    return {}


@_api.post(
    "/timeline/exposure",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Submit job for exposure timeline data"
)
def _api_timeline_exposure_submit(request, data: schemas.TimelineExposureRequest):
    return {}


@_api.get(
    "/timeline/exposure/{uuid:job_id}",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Poll job for exposure timeline data"
)
def _api_timeline_exposure_poll(request, job_id):
    return {}


@_api.post(
    "/timeline/impact",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Submit job for risk timeline data"
)
def _api_timeline_impact_submit(request, data: schemas.TimelineImpactRequest):
    job_id = timeline.timeline_impact(data)
    return schemas.TimelineJobSchema.from_task_id(job_id, 'rest/vizz/timeline/impact')



@_api.get(
    "/timeline/impact/{uuid:job_id}",
    tags=["timeline"],
    response=schemas.TimelineJobSchema,
    summary="Poll job for risk timeline data"
)
def _api_timeline_impact_poll(request, job_id):
    return schemas.TimelineJobSchema.from_task_id(job_id, 'rest/vizz/timeline/impact')


#######################################
#
#  EXCEEDANCE
#
#######################################

@_api.get("/exceedance/hazard", tags=["exceedance"])
def _api_exceedance_hazard_poll(
        request,
        hazard_type: str,
        hazard_event_name: str,
        scenario_name: str,
        scenario_year: int,
        location_scale: str,
        location_code: str,
        location_poly: str,
        aggregation_scale: str,
        aggregation_method: str):
    return {}


@_api.get("/exceedance/impact", tags=["exceedance"])
def _api_exceedance_impact_poll(
        request,
        hazard_type: str,
        hazard_event_name: str,
        exposure_type: str,
        scenario_name: str,
        scenario_year: int,
        location_scale: str,
        location_code: str,
        location_poly: str,
        aggregation_scale: str,
        aggregation_method: str):
    return {}


@_api.get("/geocode/autocomplete", tags=["geocode"], response=schemas_geocode.GeocodePlaceList,
          summary="Get suggested locations from a string")
def _api_geocode_autocomplete(request, query):
    return geocode.geocode_autocomplete(query)


#######################################
#
#   WIDGETS
#
#######################################

@_api.post(
    "/widgets/risk-timeline",
    tags=["widget"],
    response=schemas_widgets.TimelineWidgetJobSchema,
    summary="Create data for the risk over time section of the RECA site"
)
def _api_widget_risk_timeline_submit(request, data: schemas_widgets.TimelineWidgetRequest):
    job_id = widgets.widget_timeline(data)
    return schemas_widgets.TimelineWidgetJobSchema.from_task_id(job_id, 'rest/vizz/widgets/risk-timeline')


@_api.get(
    "/widgets/risk-timeline/{uuid:job_id}",
    tags=["widget"],
    response=schemas_widgets.TimelineWidgetJobSchema,
    summary="Create data for the risk over time section of the RECA site"
)
def _api_widget_risk_timeline_poll(request, job_id):
    return schemas_widgets.TimelineWidgetJobSchema.from_task_id(job_id, 'rest/vizz/widgets/risk-timeline')


@_api.post(
    "/widgets/biodiversity",
    tags=["widget"],
    response=schemas_widgets.BiodiversityWidgetJobSchema,
    summary="Create data for the biodiversity section of the RECA site"
)
def _api_widget_biodiversity_submit(request, data: schemas_widgets.BiodiversityWidgetRequest):
    job_id = widgets.widget_biodiversity(data)
    return schemas_widgets.BiodiversityWidgetJobSchema.from_task_id(job_id, 'rest/vizz/widgets/biodiversity')


@_api.get(
    "/widgets/biodiversity/{uuid:job_id}",
    tags=["widget"],
    response=schemas_widgets.BiodiversityWidgetJobSchema,
    summary="Poll for data for the biodiversity section of the RECA site"
)
def _api_widget_biodiversity_poll(request, job_id):
    return schemas_widgets.BiodiversityWidgetJobSchema.from_task_id(job_id, 'rest/vizz/widgets/biodiversity')


@_api.post(
    "/widgets/social-vulnerability",
    tags=["widget"],
    response=schemas_widgets.SocialVulnerabilityWidgetJobSchema,
    summary="Create data for the social vulnerability section of the RECA site"
)
def _api_widget_biodiversity_submit(request, data: schemas_widgets.SocialVulnerabilityWidgetRequest):
    job_id = widgets.widget_social_vulnerability(data)
    return schemas_widgets.SocialVulnerabilityWidgetJobSchema.from_task_id(job_id, 'rest/vizz/widgets/social-vulnerability')


@_api.get(
    "/widgets/social-vulnerability/{uuid:job_id}",
    tags=["widget"],
    response=schemas_widgets.SocialVulnerabilityWidgetJobSchema,
    summary="Poll for data for the social vulnerability section of the RECA site"
)
def _api_widget_socialvulnerability_poll(request, job_id):
    return schemas_widgets.SocialVulnerabilityWidgetJobSchema.from_task_id(job_id, 'rest/vizz/widgets/social-vulnerability')


@_rapi.get("/csrf", tags=['restricted'], auth=None, include_in_schema=False)
def _csrf(request):
    return csrf.get_token(request)


_default.add_router("/", _api)
resturls = _default.urls

_restricted.add_router("/", _rapi)
_restricted.add_router("/", _dapi)
restrictedurls = _restricted.urls
