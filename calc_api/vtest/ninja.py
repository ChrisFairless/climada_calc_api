import datetime as dt
import json
from time import sleep
import pandas as pd
from pathlib import Path
import base64

from django.contrib import auth
from django.middleware import csrf

from ninja import NinjaAPI, Router
from ninja.security import HttpBearer, HttpBasicAuth

import climada.util.coordinates as u_coord

from calc_api.config import ClimadaCalcApiConfig
from calc_api.util import get_client_ip, get_hash
from climada_calc.settings import BASE_DIR, STATIC_ROOT
import calc_api.vizz.models as models
import calc_api.vizz.schemas as schemas
from calc_api.calc_methods.colourmaps import values_to_colours
from calc_api.calc_methods.colourmaps import PALETTE_HAZARD_COLORCET, PALETTE_EXPOSURE_COLORCET, PALETTE_IMPACT_COLORCET
from calc_api.calc_methods.geocode import geocode_autocomplete

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


_default = NinjaAPI(title='CLIMADA Calc API', urls_namespace='vtest', description=description)
_restricted = NinjaAPI(title='CLIMADA Calc API', version='vtest_restricted', description=description, csrf=True)

_api = Router()
_rapi = Router(auth=AuthBearer(), tags=['restricted'])
_dapi = Router(auth=AuthBearer(), tags=['dangerous'])


def make_dummy_job(request_schema, location):
    return models.Job(
        job_id="test",
        location=location,
        status="submitted",
        request=request_schema.__dict__,
        submitted_at=dt.datetime(2020, 1, 1)
    )


@_api.get("/debug", tags=["debug"], summary="Short wait and return")
def map_debug(request):
    sleep(4)
    return {"success": "true"}


@_api.get("/options", tags=["options"], summary="Options in the RECA web tool")
def get_options(request):
    return json.load(open(OPTIONS_FILE))


#TODO handle errors, write error messages/statuses
#TODO should all this work with schemas? We need some way to validate all the inputs?

@_api.post("/map/hazard/climate", tags=["map"], response=schemas.MapJobSchema,
           summary="Submit job to construct climatological hazard map data")
def _api_submit_map_hazard_climate(request, data: schemas.MapHazardClimateRequest = None):
    """
    Return a Job Schema without actually submitting a job or adding to DB
    """
    job = make_dummy_job(data, "/map/hazard/climate?job_id=" + "test")
    job = schemas.MapJobSchema(**job.__dict__)
    return job


@_api.get("/map/hazard/climate", tags=["map"], response=schemas.MapJobSchema,
           summary="Poll job for climatological hazard map data")
def _api_poll_map_hazard_climate(request, job_id: str):
    """
    Return a completed mapping job. Always the same.
    """
    haz_path = Path(SAMPLE_DIR, "map_haz_rp.csv")
    df = pd.read_csv(haz_path)

    colours, legend_values, legend_colours = values_to_colours(df['intensity'], PALETTE_HAZARD_COLORCET, reverse=True)

    outdata = [schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
               for lat, lon, v, c
               in zip(df['lat'], df['lon'], df['intensity'], colours)]

    lat_res, lon_res = u_coord.get_resolution(df['lat'], df['lon'])
    if abs(abs(lat_res) - abs(lon_res)) > 0.001:
        raise ValueError("Mismatch in x and y resolutions: " + str(lon_res) + " vs " + str(lat_res))
    bounds = u_coord.latlon_bounds(df['lat'], df['lon'], buffer=lon_res)

    raster_path = Path("/rest", "vtest", "img", "map_haz_rp.tif")
    raster_uri = request.build_absolute_uri(raster_path)

    metadata = schemas.MapMetadata(
        description="Test hazard climatology map",
        units="m/s",
        legend=legend_values,
        legend_colors=legend_colours,
        bounding_box=list(bounds),
        file_uri=raster_uri
    )

    response = schemas.MapResponse(data=outdata,
                                   metadata=metadata)

    job = schemas.MapJobSchema(
        job_id="test",
        location="/map/hazard/climate?job_id=" + "test",
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        runtime=86400,
        response=response,
        response_uri=raster_uri
    )
    return job



@_api.post("/map/hazard/event", tags=["map"], response=schemas.MapJobSchema,
           summary="Construct hazard data for one event")
def _api_submit_map_hazard_event(request, data: schemas.MapHazardEventRequest = None):
    """
    Return a Job Schema without actually submitting a job or adding to DB
    """
    job = make_dummy_job(data, "/map/hazard/event?job_id=" + "test")
    return schemas.MapJobSchema(**job.__dict__)


@_api.get("/map/hazard/event", tags=["map"], response=schemas.MapJobSchema,
          summary="Poll for hazard event map data")
def _api_poll_map_hazard_event(request, job_id: str):
    return _api_poll_map_hazard_climate(request, job_id)


@_api.post("/map/exposure", tags=["map"], response=schemas.MapJobSchema,
           summary="Submit job to construct exposure map data")
def _api_submit_map_exposure(request, data: schemas.MapExposureRequest = None):
    """
    Return a Job Schema without actually submitting a job or adding to DB
    """
    job = make_dummy_job(data, "/map/exposure?job_id=" + "test")
    return schemas.MapJobSchema(**job.__dict__)


@_api.get("/map/exposure", tags=["map"], response=schemas.MapJobSchema,
          summary="Poll for exposure map data")
def _api_poll_map_exposure(request, job_id: str):
    exp_path = Path(SAMPLE_DIR, "map_exp.csv")
    df = pd.read_csv(exp_path)

    colours, legend_values, legend_colours = values_to_colours(df['value'], PALETTE_EXPOSURE_COLORCET, reverse=True)

    outdata = [
        schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
        for lat, lon, v, c
        in zip(df['lat'], df['lon'], df['value'], colours)
    ]

    lat_res, lon_res = u_coord.get_resolution(df['lat'], df['lon'])
    if abs(abs(lat_res) - abs(lon_res)) > 0.001:
        raise ValueError("Mismatch in x and y resolutions: " + str(lon_res) + " vs " + str(lat_res))
    bounds = u_coord.latlon_bounds(df['lat'], df['lon'], buffer=lon_res)

    raster_path = Path("/rest", "vtest", "img", "map_exp_rp.tif")
    raster_uri = request.build_absolute_uri(raster_path)

    metadata = schemas.MapMetadata(
        description="Test exposure climatology map",
        units="people",
        legend=legend_values,
        legend_colors=legend_colours,
        bounding_box=list(bounds),
        file_uri=raster_uri
    )

    response = schemas.MapResponse(data=outdata, metadata=metadata)

    job = schemas.MapJobSchema(
        job_id="test",
        location="/map/exposure/climate?job_id=" + "test",
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        runtime=86400,
        response=response,
        response_uri=raster_uri
    )
    return job


@_api.post("/map/impact/climate", tags=["map"], response=schemas.MapJobSchema,
           summary="Submit job for climatological impact map data")
def _api_submit_map_impact_climate(request, data: schemas.MapImpactClimateRequest = None):
    """
    Return a Job Schema without actually submitting a job or adding to DB
    """
    job = make_dummy_job(data, "/map/impact/climate?job_id=" + "test")
    return schemas.MapJobSchema(**job.__dict__)


@_api.get("/map/impact/climate", tags=["map"], response=schemas.MapJobSchema,
          summary="Poll for climatological impact map data")
def _api_poll_map_impact_climate(request, job_id: str):
    imp_path = Path(SAMPLE_DIR, "map_imp_rp.csv")
    df = pd.read_csv(imp_path)
    colours, legend_values, legend_colours = values_to_colours(df['value'], PALETTE_IMPACT_COLORCET, reverse=True)

    outdata = [
        schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
        for lat, lon, v, c
        in zip(df['lat'], df['lon'], df['value'], colours)
    ]

    lat_res, lon_res = u_coord.get_resolution(df['lat'], df['lon'])
    if abs(abs(lat_res) - abs(lon_res)) > 0.001:
        raise ValueError("Mismatch in x and y resolutions: " + str(lon_res) + " vs " + str(lat_res))
    bounds = u_coord.latlon_bounds(df['lat'], df['lon'], buffer=lon_res)

    raster_path = Path("/rest", "vtest", "img", "map_imp_rp.tif")
    raster_uri = request.build_absolute_uri(raster_path)

    metadata = schemas.MapMetadata(
        description="Test impact climatology map",
        units="people affected",
        legend=legend_values,
        legend_colors=legend_colours,
        bounding_box=list(bounds),
        file_uri=raster_uri
    )

    response = schemas.MapResponse(data=outdata, metadata=metadata)

    job = schemas.MapJobSchema(
        job_id="test",
        location="/map/impact/climate?job_id=" + "test",
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        runtime=86400,
        response=response,
        response_uri=raster_uri
    )
    return job

@_api.post("/map/impact/event", tags=["map"], response=schemas.MapJobSchema,
           summary="Submit job to get impact map data for one event")
def _api_submit_map_impact_event(request, data: schemas.MapImpactEventRequest = None):
    job = make_dummy_job(data, "/map/impact/event?job_id=" + "test")
    return schemas.MapJobSchema(**job.__dict__)


@_api.get("/map/impact/event", tags=["map"], response=schemas.MapJobSchema,
           summary="Poll for impact map data")
def _api_poll_map_impact_event(request, job_id: str):
    return _api_poll_map_impact_climate(request, job_id)




@_api.post("/exceedance/hazard", tags=["exceedance"], response=schemas.ExceedanceJobSchema,
           summary="Submit job for hazard intensity exceedance curve data")
def _api_submit_exceedance_hazard(request, data: schemas.ExceedanceHazardRequest = None):
    job = make_dummy_job(data, "/exceedance/hazard/event?job_id=" + "test")
    return schemas.ExceedanceJobSchema(**job.__dict__)


@_api.get("/exceedance/hazard", tags=["exceedance"], response=schemas.ExceedanceJobSchema,
           summary="Poll job for hazard intensity exceedance curve data")
def _api_poll_exceedance_hazard(request, job_id: str):
    exceedance_path = Path(SAMPLE_DIR, "exceedance_haz.csv")
    df = pd.read_csv(exceedance_path)
    outdata = schemas.ExceedanceCurveData(
        return_period=list(df.return_period),
        intensity=list(df.intensity),
        return_period_units="years",
        intensity_units="m/s"
    )
    return schemas.ExceedanceResponse(data=outdata, metadata={})


@_api.post("/exceedance/impact", tags=["exceedance"], response=schemas.ExceedanceJobSchema,
           summary="Submit job for hazard intensity exceedance curve data")
def _api_submit_exceedance_impact(request, data: schemas.ExceedanceHazardRequest = None):
    job = make_dummy_job(data, "/exceedance/impact/event?job_id=" + "test")
    return schemas.ExceedanceJobSchema(**job.__dict__)


@_api.post("/exceedance/impact", tags=["exceedance"], response=schemas.ExceedanceJobSchema,
           summary="Poll job for impact exceedance curve data")
def _api_poll_exceedance_impact(request, job_id: str):
    exceedance_path = Path(SAMPLE_DIR, "exceedance_imp.csv")
    df = pd.read_csv(exceedance_path)
    outdata = schemas.ExceedanceCurveData(
        return_period=list(df.return_period),
        intensity=list(df.intensity),
        return_period_units="years",
        intensity_units="people affected"
    )
    return schemas.ExceedanceResponse(data=outdata, metadata={})


@_api.post("/timeline/hazard", tags=["timeline"], summary="Not yet implemented")
def _api_timeline_hazard(request,
                         hazard_type: str,
                         hazard_event_name: str,
                         scenario_name: str,
                         scenario_rp: int,
                         location_scale: str,
                         location_code: str,
                         location_poly: str,
                         aggregation_scale: str,
                         aggregation_method: str):
    return {}


@_api.post("/timeline/exposure", tags=["timeline"], summary="Not yet implemented")
def _api_timeline_exposure(request,
                           exposure_type: str,
                           scenario_name: str,
                           scenario_rp: int,
                           location_scale: str,
                           location_code: str,
                           location_poly: str,
                           aggregation_scale: str,
                           aggregation_method: str):
    return {}


@_api.post("/timeline/impact", tags=["timeline"], summary="Not yet implemented")
def _api_timeline_impact(request,
                         hazard_type: str,
                         hazard_event_name: str,
                         exposure_type: str,
                         scenario_name: str,
                         scenario_rp: int,
                         location_scale: str,
                         location_code: str,
                         location_poly: str,
                         aggregation_scale: str,
                         aggregation_method: str):
    return {}


@_api.get("/measures", tags=["adaptation measures"], summary="Not yet implemented")
def _api_get_adaptation_measures():
    return {}


@_api.post("/measures/add", tags=["adaptation measures"], summary="Not yet implemented")
def _api_get_adaptation_measures():
    return {}


@_api.get("/geocode/autocomplete", tags=["geocode"], response=schemas.GeocodePlaceList,
          summary="Get suggested locations from a string")
def _api_geocode_autocomplete(request, query):
    return geocode_autocomplete(query)


@_rapi.get("/csrf", tags=['restricted'], auth=None, include_in_schema=False)
def _csrf(request):
    return csrf.get_token(request)


_default.add_router("/", _api)
resturls = _default.urls

_restricted.add_router("/", _rapi)
_restricted.add_router("/", _dapi)
restrictedurls = _restricted.urls
