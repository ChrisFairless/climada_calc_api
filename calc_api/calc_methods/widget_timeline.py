from celery import chain, chord, group, shared_task
from celery_singleton import Singleton
import numpy as np

from calc_api.vizz import schemas, schemas_widgets
from calc_api.vizz.text_timeline import generate_timeline_widget_text
from calc_api.calc_methods.calc_exposure import get_exposure
from calc_api.calc_methods.timeline import set_up_timeline_calculations, combine_impacts_to_timeline, combine_impacts_to_timeline_no_celery


def widget_timeline(data: schemas_widgets.TimelineWidgetRequest):
    data.standardise()
    all_rps = [data.hazard_rp, 10, 100]

    request = schemas.TimelineImpactRequest(
        hazard_type=data.hazard_type,
        hazard_rp=all_rps,
        exposure_type=data.exposure_type,
        impact_type=data.impact_type,
        scenario_name=data.scenario_name,
        scenario_climate=data.scenario_climate,
        scenario_growth=data.scenario_growth,
        location_name=data.location_name,
        location_scale=data.location_scale,
        location_code=data.location_code,
        location_poly=data.location_poly,
        aggregation_method=data.aggregation_method,
        units_warming=data.units_warming,
        units_exposure=data.units_exposure,
        geocoding=data.geocoding
    )

    exposure_total_signature = get_exposure.s(
        country=data.geocoding.country_id,
        exposure_type=request.exposure_type,
        impact_type=request.impact_type,
        scenario_name=request.scenario_name,
        scenario_growth=request.scenario_growth,
        scenario_year=data.scenario_year,
        location_poly=request.location_poly,
        aggregation_scale='all',
        aggregation_method='sum'
    )

    job_config_list, chord_header = set_up_timeline_calculations(request)

    chord_header.extend([exposure_total_signature])  # last job total exposure, all the rest impact calc
    # this is such an ugly way to parallelise all this but I am extremely tired

    callback_config = {
        'hazard_type': request.hazard_type,
        'location_name': request.location_name,
        'location_scale': request.location_scale,
        'scenario_name': request.scenario_name,
        'impact_type': request.impact_type,
        'units_exposure': request.units_exposure,
        'hazard_rp': all_rps
    }

    chord_callback = combine_impacts_to_timeline_widget.s(
        job_config_list=job_config_list,
        report_year=data.scenario_year,
        config=callback_config
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
    all_timelines = [tl.data for tl in combine_impacts_to_timeline_no_celery(impacts_list, job_config_list)]
    timeline, timeline_10yr, timeline_100yr = all_timelines
    future_analysis = [item for item in timeline.items if item.year_value == int(report_year)][0]
    present_impact = [
        imp
        for imp, job in zip(impacts_list, job_config_list)
        if job['haz_year'] == 2020 and job['exp_year'] == 2020][0][0]
    future_impact = [
        imp
        for imp, job in zip(impacts_list, job_config_list)
        if job['haz_year'] == int(report_year) and job['exp_year'] == int(report_year)][0][0]

    if present_impact['total_freq'] == 0:
        raise ValueError('Uh oh: trying to generate a widget with a total event set frequency of zero. Fix this.')
    frequency_change = (future_impact['total_freq'] - present_impact['total_freq']) / present_impact['total_freq']

    if present_impact['mean_imp'] == 0:
        raise ValueError('Uh oh: trying to generate a widget with a mean event set impact of zero. Fix this.')
    intensity_change = (future_impact['mean_imp'] - present_impact['mean_imp']) / present_impact['mean_imp']

    new_10yr_return = np.interp(
        present_impact['value'][1],
        future_impact['freq_curve']['impact'],
        future_impact['freq_curve']['return_per']
    )
    new_100yr_return = np.interp(
        present_impact['value'][2],
        future_impact['freq_curve']['impact'],
        future_impact['freq_curve']['return_per']
    )

    # TODO make this deal with differing economic and climate scenarios
    generated_text = generate_timeline_widget_text(
        hazard_type=config['hazard_type'],
        location=config['location_name'],
        location_type=config['location_scale'],
        scenario=config['scenario_name'],
        impact_type=config['impact_type'],
        exposure_units=config['units_exposure'],
        value_present=exposure_total[0]['value'],
        affected_present=future_analysis.current_climate,
        affected_future=future_analysis.future_climate,
        affected_future_exposure_change=future_analysis.growth_change,
        affected_future_climate_change=future_analysis.climate_change,
        future_year=report_year,
        return_period=config['hazard_rp'],
        frequency_change=frequency_change,
        intensity_change=intensity_change,
        new_10yr_return=new_10yr_return,
        new_100yr_return=new_100yr_return
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
