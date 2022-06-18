from string import Template
from millify import millify
import numpy as np

from calc_api.vizz.util import options_return_period_to_description, options_scenario_to_description
from calc_api.vizz import schemas_widgets


def generate_timeline_widget_text(
        hazard_type,
        location,
        location_type,
        scenario,
        impact_type,
        exposure_units,
        value_present,
        affected_present,
        affected_future,
        affected_future_exposure_change,
        affected_future_climate_change,
        future_year,
        return_period,
        frequency_change,
        intensity_change,
        new_10yr_return,
        new_100yr_return
):

    overview_text = _generate_timeline_widget_overview_text(
        hazard_type,
        location,
        location_type,
        exposure_units,
        value_present,
        affected_present,
        return_period
    )

    change_text = _generate_timeline_widget_change_text(
        hazard_type,
        scenario,
        impact_type,
        exposure_units,
        affected_present,
        affected_future,
        affected_future_exposure_change,
        affected_future_climate_change,
        future_year
    )

    hazard_overview_text = _generate_timeline_widget_hazard_overview_text(
        hazard_type
    )

    frequency_intensity_text = _generate_timeline_widget_frequency_intensity_text(
        hazard_type,
        location,
        future_year,
        frequency_change,
        intensity_change,
        new_10yr_return,
        new_100yr_return
    )

    return [overview_text, change_text, hazard_overview_text, frequency_intensity_text]


def _generate_timeline_widget_overview_text(
        hazard_type,
        location,
        location_type,
        exposure_units,
        value_present,
        affected_present,
        return_period
):
    text_overview = Template(
        "$location is a $location_type with approximately {{exposure_value}}. "
        "Under current climatic conditions (in 2020), $proportional_qualifier {{affected_present}} "
        "may be exposed to $event_description $return_period_description. "
    )

    proportional_qualifier = 'all' if affected_present == value_present else ''
    event_description = event_description_from_hazard_type(hazard_type)

    if return_period == 'aai':
        return_period_description = 'on average each year'
    else:
        return_period_description = f'every {return_period} years'

    final_text = text_overview.substitute(
        location=location.title(),
        location_type=location_type,
        proportional_qualifier=proportional_qualifier,
        event_description=event_description,
        return_period_description=return_period_description
    )

    text_numeric_values = [
        schemas_widgets.TextVariable(
            key='exposure_value',
            value=value_present,
            unit=exposure_units
        ),
        schemas_widgets.TextVariable(
            key='affected_present',
            value=affected_present,
            unit=exposure_units
        )
    ]

    return schemas_widgets.GeneratedText(
        template=final_text,
        values=text_numeric_values
    )


def _generate_timeline_widget_no_change_text(
        hazard_type,
        scenario
):
    text_no_components_change = Template(
        "Under the $scenario scenario this is not projected to change. "
    )
    final_text = text_no_components_change.substitute(
        scenario=options_scenario_to_description(scenario, hazard_type)
    )
    return schemas_widgets.GeneratedText(
        template=final_text,
        values=[]
    )


def _generate_timeline_widget_change_text(
        hazard_type,
        scenario,
        impact_type,
        exposure_units,
        affected_present,
        affected_future,
        affected_future_exposure_change,
        affected_future_climate_change,
        future_year,
):

    if affected_future_exposure_change == 0 and affected_future_climate_change == 0:
        return _generate_timeline_widget_no_change_text(
            hazard_type,
            scenario
        )
    else:
        return _generate_timeline_widget_with_change_text(
            hazard_type,
            scenario,
            impact_type,
            exposure_units,
            affected_present,
            affected_future,
            affected_future_exposure_change,
            affected_future_climate_change,
            future_year,
        )

def _generate_timeline_widget_with_change_text(
        hazard_type,
        scenario,
        impact_type,
        exposure_units,
        affected_present,
        affected_future,
        affected_future_exposure_change,
        affected_future_climate_change,
        future_year,
):

    text_change_description = Template(
        "The $affected_description is projected to "
        "$growth_description by $future_year under the $scenario scenario. "
        "This change is $cause_description. "
    )

    if impact_type == 'people_affected':
        exposure_description = 'population'
        affected_description = 'number of people affected'
    elif impact_type == 'economic_impact':
        exposure_description = 'economic assets'
        affected_description = 'loss'
    else:
        raise ValueError(f'{impact_type} is not in my list of pre-prepared impact types for text generation')

    growth_text, growth_values = growth_description(affected_present, affected_future, exposure_units)
    sign_climate_change = np.sign(affected_future_climate_change)
    sign_exposure_change = np.sign(affected_future_exposure_change)

     # Case: no climate change
    if affected_future_climate_change == 0:
        if impact_type == 'people_affected':
            cause_description = 'entirely due to population change'
        elif impact_type == 'economic_impact':
            if affected_future_exposure_change < 0:
                cause_description = 'entirely due to a shrinking economy'
            else:
                cause_description = 'entirely due to economic growth'
        else:
            raise ValueError(f'{impact_type} is not in my list of pre-prepared impact types for text generation')

    # Case: no exposure change
    elif affected_future_exposure_change == 0:
        affected_description = 'entirely due to a changing climate'

    # Case: opposing signs
    elif sign_climate_change == -1 and sign_exposure_change == 1:
        if affected_future_exposure_change < 0:
            cause_description = f'due to the decrease in climate risk exceeding the increase in {exposure_description}'
        else:
            cause_description = f'due to the increase in {exposure_description} exceeding the decrease in climate risk'

    elif sign_exposure_change == -1 and sign_climate_change == 1:
        if affected_future_climate_change < 0:
            cause_description = f'due to the decrease in {exposure_description} exceeding the increase in climate risk'
        else:
            cause_description = f'due to the increase in climate risk exceeding the decrease in {exposure_description}'

    else:
        if sign_climate_change != sign_exposure_change:
            raise ValueError("Something went wrong with the logic processing changes in impacts")
        ratio = affected_future_climate_change/affected_future_exposure_change
        if ratio > 10:
            cause_description = 'almost entirely due to changes in climate'
        elif ratio > 2:
            cause_description = 'mostly due to changes in climate'
        elif ratio > 0.5:
            cause_description = f'due to a combination of changes to climate risk and {exposure_description}'
        elif ratio > 0.1:
            cause_description = f'mostly due to changes in {affected_description}'
        else:
            cause_description = f'almost entirely due to changes in {affected_description}'

    if not cause_description:
        raise ValueError("Something went wrong with the logic processing changes in impacts")

    final_text = text_change_description.substitute(
        growth_description=growth_text,
        future_year=future_year,
        scenario=options_scenario_to_description(scenario, hazard_type),
        cause_description=cause_description
    )

    return schemas_widgets.GeneratedText(
        template=final_text,
        values=growth_values
    )


def _generate_timeline_widget_hazard_overview_text(hazard_type):
    if hazard_type == 'tropical_cyclone':
        text = 'Tropical storms cause can damage from high winds, flooding and coastal storm surges, with the strongest storms devastating whole communities, causing severe financial losses, injuries and deaths.'
    elif hazard_type == 'extreme_heat':
        text = 'Heatwaves are one of the deadliest natural disasters globally. Heat stress causes illness and death and slows economic activity.'
    else:
        raise ValueError('Hazard must be one of tropical_cyclone or extreme_heat')
    return schemas_widgets.GeneratedText(
        template=text,
        values=[]
    )

def _generate_timeline_widget_frequency_intensity_text(
        hazard_type,
        location_name,
        future_year,
        frequency_change,
        intensity_change,
        new_10yr_return,
        new_100yr_return
):

    text_freq_intense_change = Template(
        '$event_description in $location $frequency_change_desc $intensity_change_desc by {{future_year}}. $rp_text'
    )
    values = [schemas_widgets.TextVariable(
        key='frequency_change',
        value=100 * frequency_change,
        units='%'
        )]

    if frequency_change > 0.15:
        frequency_change_desc = "are projected to become much more ({{frequency_change}}) frequent"
    elif frequency_change > 0.05:
        frequency_change_desc = "are projected to become more ({{frequency_change}}) frequent"
    elif frequency_change > 0.01:
        frequency_change_desc = "are projected to become slightly more ({{frequency_change}}) frequent"
    elif frequency_change > -0.01:
        frequency_change_desc = "are not projected to change much in frequency"
        _ = values.pop()  # Drop the frequency change, we don't need it
    elif frequency_change > -0.05:
        frequency_change_desc = "are projected to become slightly less ({{frequency_change}}) frequent"
    elif frequency_change > -0.1:
        frequency_change_desc = "are projected to become less ({{frequency_change}}) frequent"
    elif frequency_change <= -0.15:
        frequency_change_desc = "are projected to become much less ({{frequency_change}}) frequent"
    else:
        raise ValueError(f'Could not process change in frequency: {frequency_change}')

    # TODO think about whether to decscribe changing intensity rather than changing impacts
    values.extend([
        schemas_widgets.TextVariable(
            key='intensity_change',
            value=100 * intensity_change,
            units='%'
        )
    ])
    if intensity_change > 0.15:
        intensity_change_desc = "and are projected to become much more ({{intensity_change}}) damaging on average"
    elif intensity_change > 0.05:
        intensity_change_desc = "and are projected to become more ({{intensity_change}}) damaging on average"
    elif intensity_change > 0.01:
        intensity_change_desc = "and are projected to become slightly more ({{intensity_change}}) damaging on average"
    elif intensity_change > -0.01:
        intensity_change_desc = "and are not projected to change much in average impact"
        _ = values.pop()  # Drop the intensity change since we won't display it
    elif intensity_change > -0.05:
        intensity_change_desc = "and are projected to become slightly less ({{intensity_change}}) damaging on average"
    elif intensity_change > -0.1:
        intensity_change_desc = "and are projected to become less ({{intensity_change}}) damaging on average"
    elif intensity_change <= -0.1:
        intensity_change_desc = "and are projected to become much less ({{intensity_change}}) damaging on average"
    else:
        raise ValueError(f'Could not process change in intensity: {intensity_change}')

    event_description = event_description_from_hazard_type(hazard_type)
    is_new_rp_10yr = new_10yr_return <= 9.5 or new_10yr_return >= 10.5
    is_new_rp_100yr = new_100yr_return <= 95 or new_100yr_return >= 105

    value_new_10yr = [schemas_widgets.TextVariable(
        key='new_10yr_return',
        value=new_10yr_return,
        units='years'
    )]
    value_new_100yr = [schemas_widgets.TextVariable(
        key='new_100yr_return',
        value=new_100yr_return,
        units='years'
    )]

    if not is_new_rp_100yr and not is_new_rp_10yr:
        rp_text = ''
    elif not is_new_rp_100yr:
        rp_text = f'The impacts of a {event_description} that would be expected once in 10 years are projected to happen once in {{new_10yr_return}} years instead, but the impacts of 1-in-100-year events are not projected to change much by {{year}}.'
        values.extend(value_new_10yr)
    elif not is_new_rp_10yr:
        rp_text = f'The impacts of 1-in-10-year events are not projected to change much, but the impacts of a {event_description} that would be expected once in 100 years are projected to happen once in {{new_100yr_return}} years instead.'
        values.extend(value_new_100yr)
    else:
        rp_text = f'The impacts of a {event_description} that would be expected once in 10 years are projected to happen once in {{new_10yr_return}} years instead, and impacts that would be expected once in 100 years are projected to happen once in {{new_100yr_return}} years instead.'
        values.extend(value_new_10yr)
        values.extend(value_new_100yr)

    final_text = text_freq_intense_change.substitute(
        event_description=event_description,
        location=location_name,
        future_year=future_year,
        frequency_change_desc=frequency_change_desc,
        intensity_change_desc=intensity_change_desc,
        rp_text=rp_text
    )

    return schemas_widgets.GeneratedText(
        template=final_text,
        values=values
    )


def prettify_exposure(value, units):
    if units == 'people':
        return f"{millify(value, precision=2)} people"
    elif units == 'dollars':
        return f"$ {millify(value, precision=2)}"
    else:
        raise ValueError(f'Need to cater for more units: {units}')


def growth_description(current, future, units):
    ratio = np.nan if current == 0 else future/current
    if current == 0 or future/current > 100:
        text = f'grow to {{future_value}}'
        values = [
            schemas_widgets.TextVariable(
                key='future_value',
                value=future,
                units=units
            )
        ]
        return text, values

    if ratio < 1.001 and ratio > 0.999:
        return 'hardly change', []

    if ratio > 1:
        growth_pct = 100*(ratio-1)
        text = f'grow by {{future_percent}} to {{future_value}}', ['future_percent', 'future_value']
        values = [
            schemas_widgets.TextVariable(
                key='future_percent',
                value=growth_pct,
                units='%'
            ),
            schemas_widgets.TextVariable(
                key='future_value',
                value=future,
                units=units
            )
        ]
        return text, values

    if ratio < 1:
        shrink_pct = 100*(1-ratio)
        text = f'shrink by {{future_percent}} to {{future_value}}', ['future_percent', 'future_value']
        values = [
            schemas_widgets.TextVariable(
                key='future_percent',
                value=shrink_pct,
                units='%'
            ),
            schemas_widgets.TextVariable(
                key='future_value',
                value=future,
                units=units
            )
        ]
        return text, values

    raise ValueError("Somehow we didn't work out a growth description")


def event_description_from_hazard_type(hazard_type):
    if hazard_type == 'tropical_cyclone':
        return 'tropical cyclones'
    if hazard_type == 'extreme_heat':
        return 'extreme heat events'
    raise ValueError(f'{hazard_type} is not in my list of pre-prepared hazards for text generation')