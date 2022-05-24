from string import Template
from millify import millify
import numpy as np

from calc_api.vizz.util import options_scenario_to_description
from calc_api.vizz.schemas import schemas_widgets


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

    if affected_future_exposure_change == 0 and affected_future_climate_change == 0:
        change_text = _generate_timeline_widget_no_change_text(
            hazard_type,
            scenario
        )
    else:
        change_text = _generate_timeline_widget_change_text(
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

    return [overview_text, change_text]


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
    if hazard_type == 'tropical_cyclone':
        event_description = 'tropical cyclones'
    elif hazard_type == 'extreme_heat':
        event_description = 'extreme heat events'
    else:
        raise ValueError(f'{hazard_type} is not in my list of pre-prepared hazards for text generation')

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

