from celery import chord, shared_task
from celery_singleton import Singleton

from calc_api.vizz.schemas import schemas
from calc_api.vizz.schemas import schemas_widgets
from calc_api.vizz.texts import generate_timeline_widget_text
from calc_api.vizz.endpoints.get_exposure import get_exposure
from calc_api.calc_methods.timeline import set_up_timeline_calculations, combine_impacts_to_timeline_no_celery
from calc_api.calc_methods.geocode import standardise_location

def widget_timeline(data: schemas_widgets.TimelineWidgetRequest):
    location = standardise_location(location_name=data.location_name, location_code=data.location_id)
    request = schemas.TimelineImpactRequest(
        hazard_type=data.hazard_type,
        hazard_rp=data.hazard_rp,
        exposure_type=data.exposure_type,
        impact_type=data.impact_type,
        scenario_name=data.scenario_name,
        scenario_climate=data.scenario_climate,
        scenario_growth=data.scenario_growth,
        location_name=location.name,
        location_scale=location.scale,
        location_code=location.id,
        location_poly=location.poly,
        aggregation_method='sum',
        units_warming=data.units_warming,
        units_response=data.units_response
    )

    exp_request = schemas.MapExposureRequest(
        country=location.id,
        exposure_type=request.exposure_type,
        impact_type=request.impact_type,
        scenario_name=request.scenario_name,
        scenario_growth=request.scenario_growth,
        scenario_year=data.scenario_year,
        location_poly=request.location_poly,
        aggregation_scale=location.scale,
        aggregation_method=request.aggregation_method,
        units=None
    )

    job_config_list, chord_header = set_up_timeline_calculations(request)
    exposure_total_signature = get_exposure.s(exp_request)
    chord_header.extend([exposure_total_signature])  # last job total exposure, all the rest impact calc
    # this is such an ugly way to parallise all this but I am extremely tired

    callback_config = {
        'hazard_type': request.hazard_type,
        'location_name': request.location_name,
        'location_scale': request.location_scale,
        'scenario_name':request.scenario_name,
        'impact_type': request.impact_type,
        'units_response': request.units_response,
        'hazard_rp': request.hazard_rp
    }

    chord_callback = combine_impacts_to_timeline_widget.s(
        job_config_list,
        data.scenario_year,
        callback_config
    )

    # with transaction.atomic():
    res = chord(chord_header)(chord_callback)
    out = res.id
    return out


@shared_task(base=Singleton)
def combine_impacts_to_timeline_widget(impacts_widget_data,
                                       job_config_list,
                                       report_year,
                                       config):   # Yes this is horrible: fix it
    exposure_total, impacts_list = impacts_widget_data[-1], impacts_widget_data[:-1]
    timeline = combine_impacts_to_timeline_no_celery(impacts_list, job_config_list).data

    future_analysis = [item for item in timeline.items if item.year_value == int(report_year)][0]
    # TODO make this deal with differing economic and climate scenarios
    generated_text = generate_timeline_widget_text(
        config['hazard_type'],
        config['location_name'],
        config['location_scale'],
        config['scenario_name'],
        config['impact_type'],
        config['units_response'],
        0.0,
        future_analysis.current_climate,
        future_analysis.future_climate,
        future_analysis.population_change,
        future_analysis.climate_change,
        report_year,
        config['hazard_rp']
    )
    timeline_data = schemas_widgets.TimelineWidgetData(
        text=generated_text,
        chart=timeline
    )
    timeline_metadata = schemas.TimelineMetadata(
        description='Timeline' #TODO flesh out!!!
    )
    return schemas_widgets.TimelineWidgetResponse(
        data=timeline_data,
        metadata=timeline_metadata
    )



def widget_social_vulnerability(data: schemas_widgets.SocialVulnerabilityWidgetRequest):
    return {}


def widget_biodiversity(data: schemas_widgets.BiodiversityWidgetRequest):
    return {}