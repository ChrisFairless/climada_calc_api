import datetime as dt
import json
from time import sleep
import pandas as pd
from pathlib import Path

from django.contrib import auth
from django.middleware import csrf

from ninja import NinjaAPI, Router
from ninja.security import HttpBearer, HttpBasicAuth
from celery import shared_task

from calc_api.config import ClimadaCalcApiConfig
from calc_api.util import get_client_ip
from climada_calc.settings import STATIC_ROOT
import calc_api.db as schemas
from calc_api.calc_methods.colourmaps import values_to_colours
from calc_api.calc_methods.colourmaps import PALETTE_HAZARD_COLORCET, PALETTE_EXPOSURE_COLORCET, PALETTE_IMPACT_COLORCET
from calc_api.calc_methods.geocode import geocode_autocomplete

conf = ClimadaCalcApiConfig()

SAMPLE_DIR = Path(STATIC_ROOT, "sample_data")
OPTIONS_FILE = Path(STATIC_ROOT, "options.json")


description = f"""
<table>
  <tr>
    <td>
      GitLab:
      <a target=_blank href=https://sissource.ethz.ch/schmide/climada-data-api>
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


@shared_task
@_api.get("/debug", tags=["debug"], summary="Short wait and return")
def map_debug(request):
    sleep(4)
    return {"success": "true"}


@_api.get("/options", tags=["options"], summary="Options in the RECA web tool")
def get_options(request):
    return json.load(open(OPTIONS_FILE))


#TODO handle errors, write error messages/statuses
#TODO should all this work with schemas? We need some way to validate all the inputs?

@shared_task
@_api.post("/map/hazard/climate", tags=["map"], response=schemas.MapResponse,
           summary="Construct climatological hazard map data")
def _api_map_hazard_climate(request, data: schemas.MapHazardClimateRequest):
    haz_path = Path(SAMPLE_DIR, "map_haz_rp.csv")
    df = pd.read_csv(haz_path)

    colours, legend_values, legend_colours = values_to_colours(df['intensity'], PALETTE_HAZARD_COLORCET, reverse=True)

    outdata = [schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
               for lat, lon, v, c
               in zip(df['lat'], df['lon'], df['intensity'], colours)]

    return schemas.MapResponse(data=outdata,
                               metadata=schemas.MapMetadata(description="Test hazard climatology map",
                                                            units="m/s",
                                                            legend=legend_values,
                                                            legend_colors=legend_colours))


@shared_task
@_api.post("/map/hazard/event", tags=["map"], response=schemas.MapResponse,
           summary="Construct hazard data for one event")
def _api_map_hazard_event(request, data: schemas.MapHazardEventRequest):
    haz_path = Path(SAMPLE_DIR, "map_haz_rp.csv")
    df = pd.read_csv(haz_path)

    colours, legend_values, legend_colours = values_to_colours(df['intensity'], PALETTE_HAZARD_COLORCET, reverse=True)

    outdata = [schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
               for lat, lon, v, c
               in zip(df['lat'], df['lon'], df['intensity'], colours)]

    return schemas.MapResponse(data=outdata,
                               metadata=schemas.MapMetadata(description="Test hazard event map",
                                                            units="m/s",
                                                            legend=legend_values,
                                                            legend_colors=legend_colours))


@shared_task
@_api.post("/map/exposure", tags=["map"], response=schemas.MapResponse,
           summary="Construct exposure map data")
def _api_map_exposure(request, data: schemas.MapExposureRequest):
    exp_path = Path(SAMPLE_DIR, "map_exp.csv")
    df = pd.read_csv(exp_path)

    colours, legend_values, legend_colours = values_to_colours(df['value'], PALETTE_EXPOSURE_COLORCET, reverse=True)

    outdata = [schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
               for lat, lon, v, c
               in zip(df['lat'], df['lon'], df['value'], colours)]

    return schemas.MapResponse(data=outdata,
                               metadata=schemas.MapMetadata(description="Test exposure map",
                                                            units="people",
                                                            legend=legend_values,
                                                            legend_colors=legend_colours))


@shared_task
@_api.post("/map/impact/climate", tags=["map"], response=schemas.MapResponse,
           summary="Construct climatological impact map data")
def _api_map_impact_climate(request, data: schemas.MapImpactClimateRequest):
    imp_path = Path(SAMPLE_DIR, "map_imp_rp.csv")
    df = pd.read_csv(imp_path)
    colours, legend_values, legend_colours = values_to_colours(df['value'], PALETTE_IMPACT_COLORCET, reverse=True)

    outdata = [schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
               for lat, lon, v, c
               in zip(df['lat'], df['lon'], df['value'], colours)]

    return schemas.MapResponse(data=outdata,
                               metadata=schemas.MapMetadata(description="Test impact climatology map",
                                                            units="people affected",
                                                            legend=legend_values,
                                                            legend_colors=legend_colours))


@shared_task
@_api.post("/map/impact/event", tags=["map"], response=schemas.MapResponse,
           summary="Construct impact map data for one event")
def _api_map_impact_event(request, data: schemas.MapImpactEventRequest):
    imp_path = Path(SAMPLE_DIR, "map_imp_rp.csv")
    df = pd.read_csv(imp_path)
    colours, legend_values, legend_colours = values_to_colours(df['value'], PALETTE_IMPACT_COLORCET, reverse=True)

    outdata = [schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
               for lat, lon, v, c
               in zip(df['lat'], df['lon'], df['value'], colours)]

    return schemas.MapResponse(data=outdata,
                               metadata=schemas.MapMetadata(description="Test impact event map",
                                                            units="people affected",
                                                            legend=legend_values,
                                                            legend_colors=legend_colours))



@shared_task
@_api.post("/exceedance/hazard", tags=["exceedance"], response=schemas.ExceedanceResponse,
           summary="Construct hazard intensity exceedance curve data")
def _api_exceedance_hazard(request, data: schemas.ExceedanceHazardRequest):
    exceedance_path = Path(SAMPLE_DIR, "exceedance_haz.csv")
    df = pd.read_csv(exceedance_path)
    outdata = schemas.ExceedanceCurveData(return_period=list(df.return_period),
                                          intensity=list(df.intensity),
                                          return_period_units="years",
                                          intensity_units="m/s")
    return schemas.ExceedanceResponse(data=outdata,
                                      metadata={})


@shared_task
@_api.post("/exceedance/impact", tags=["exceedance"], response=schemas.ExceedanceResponse,
           summary="Construct impact exceedance curve data")
def _api_exceedance_impact(request, data: schemas.ExceedanceImpactRequest):
    exceedance_path = Path(SAMPLE_DIR, "exceedance_imp.csv")
    df = pd.read_csv(exceedance_path)
    outdata = schemas.ExceedanceCurveData(return_period=list(df.return_period),
                                          intensity=list(df.intensity),
                                          return_period_units="years",
                                          intensity_units="people affected")
    return schemas.ExceedanceResponse(data=outdata,
                                      metadata={})



@shared_task
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


@shared_task
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


@shared_task
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


@shared_task
@_api.get("/measures", tags=["adaptation measures"], summary="Not yet implemented")
def _api_get_adaptation_measures():
    return {}


@shared_task
@_api.post("/measures/add", tags=["adaptation measures"], summary="Not yet implemented")
def _api_get_adaptation_measures():
    return {}


@_api.get("/geocode/autocomplete", tags=["geocode"], response=schemas.GeocodeAutocompleteResponse,
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
