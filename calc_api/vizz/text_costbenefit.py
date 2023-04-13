from string import Template

from calc_api.vizz import schemas_widgets
from calc_api.vizz.enums import get_scenario_options, HAZARD_TO_NAME

def generate_costbenefit_widget_text(
        hazard_type,
        scenario,
        impact_type,
        measure_name,
        measure_description,
        measure_cost,
        units_exposure,
        units_currency,
        affected_present,
        affected_measure,
        affected_future,
        affected_future_measure,
        future_year
):

    costben_intro = _get_costben_intro(
        measure_name=measure_name
    )
    measure_description_text = _make_measure_description(
        measure_description=measure_description
    )
    measure_change_summary_pt1 = _get_measure_change_summary_pt1(
        measure_name=measure_name,
        hazard_type=hazard_type,
        impact_type=impact_type,
        units_exposure=units_exposure,
        affected_present=affected_present,
        affected_measure=affected_measure,
    )
    measure_change_summary_pt2 = _get_measure_change_summary_pt2(
        hazard_type=hazard_type,
        measure_cost=measure_cost,
        impact_type=impact_type,
        scenario=scenario,
        units_exposure=units_exposure,
        future_year=future_year,
        affected_present=affected_present,
        affected_future=affected_future,
        affected_measure=affected_measure,
        affected_future_measure=affected_future_measure
    )
    measure_change_summary_pt3 = _get_measure_change_summary_pt3(
        measure_name=measure_name,
        measure_cost=measure_cost,
        units_currency=units_currency,
        impact_type=impact_type,
        units_exposure=units_exposure,
        future_year=future_year,
        affected_present=affected_present,
        affected_future=affected_future,
        affected_measure=affected_measure,
        affected_future_measure=affected_future_measure
    )
    costben_conclusion = _get_costben_conclusion()

    return [
        costben_intro,
        measure_description_text,
        measure_change_summary_pt1,
        measure_change_summary_pt2,
        measure_change_summary_pt3,
        costben_conclusion
    ]


def _get_costben_intro(measure_name):
    intro_text = Template("""\
Climate adaptation measures can either reduce the intensity of hazards or the impacts that hazards have. \
While it's hard to model the adaptation measures at single locations without dedicated feasibility \
studies, we can give first-guess, indicative numbers for the effectiveness of $measure_name.\
    """)

    intro_text = intro_text.substitute(measure_name=measure_name.lower())

    return schemas_widgets.GeneratedText(
        template=intro_text,
        values=[]
    )


def _make_measure_description(
        measure_description
    ):

    return schemas_widgets.GeneratedText(
        template=measure_description,
        values=[]
    )


def _get_measure_change_summary_pt1(
        measure_name,
        hazard_type,
        impact_type,
        units_exposure,
        affected_present,
        affected_measure,
):
    template = Template('''\
By adapting with $measure_name there is an average estimated decrease of {{measure_benefit}} \
$affected_description the impacts of $hazard_type each year, using a 2020 baseline.'''
                        )

    measure_benefit = affected_present - affected_measure

    # TODO put all of these lookups into a big dictionary somewhere so it's easy to add new types
    if impact_type == 'people_affected':
        affected_description = 'affected by'
    elif impact_type == 'economic_impact':
        affected_description = 'loss from'
    elif impact_type == 'assets_affected':
        affected_description = 'assets affected by'
    else:
        raise ValueError(f'{impact_type} is not in my list of pre-prepared impact types for text generation')

    hazard_name = HAZARD_TO_NAME[hazard_type]
    if hazard_name == "tropical cyclone":
        hazard_name = "tropical cyclones"

    template = template.substitute(
        measure_name=measure_name.lower(),
        affected_description=affected_description,
        hazard_type=hazard_name
    )

    text_values = [
        schemas_widgets.TextVariable(
            key='measure_benefit',
            value=measure_benefit,
            units=units_exposure
        )
    ]

    return schemas_widgets.GeneratedText(
        template=template,
        values=text_values
    )

def _get_measure_change_summary_pt2(
        hazard_type,
        measure_cost,
        impact_type,
        scenario,
        units_exposure,
        future_year,
        affected_present,
        affected_future,
        affected_measure,
        affected_future_measure
):
    template = Template('''\
Projecting forward with climate change and growth, the effect $change_direction_description by \
{{future_measure_percentage_change}}: in $future_year the measure gives a decrease of {{measure_future_benefit}} \
$affected_description in an average year under the $scenario scenario.'''
                        )

    measure_benefit = affected_present - affected_measure
    measure_future_benefit = affected_future - affected_future_measure
    future_measure_percentage_change = 100 * (measure_future_benefit/measure_benefit - 1)
    # TODO use the actual costbenefit module for this

    if measure_benefit < 0 or measure_future_benefit < 0:
        raise ValueError('Costbenefit text generation is not yet ready to deal with negative benefits')

    scenario_name = get_scenario_options(hazard_type=hazard_type, parameters={"value": scenario}, get_value="name")[0]
    scenario_description = get_scenario_options(hazard_type=hazard_type, parameters={"value": scenario}, get_value="description")[0]
    scenario_description = scenario_description.lower()
    scenario_full = scenario_name + " (" + scenario_description + ")"

    # TODO deal with affected_present == 0
    if future_measure_percentage_change > 0:
        if future_measure_percentage_change > 5:
            change_direction_description = "increases the effect"
        else:
            change_direction_description = "increases the effect slightly"
    elif future_measure_percentage_change < 0:
        if future_measure_percentage_change < -5:
            change_direction_description = "decreases the effect"
        else:
            change_direction_description = "decreases the effect slightly"
    else:
        # TODO
        raise ValueError("We didn't prepare for the case of no future change yet")

    # TODO put all of these lookups into a big dictionary somewhere so it's easy to add new types
    if impact_type == 'people_affected':
        affected_description = 'affected'
    elif impact_type == 'economic_impact':
        affected_description = 'loss'
    elif impact_type == 'assets_affected':
        affected_description = 'assets affected'
    else:
        raise ValueError(f'{impact_type} is not in my list of pre-prepared impact types for text generation')

    template = template.substitute(
        affected_description=affected_description,
        change_direction_description=change_direction_description,
        future_year=future_year,
        scenario=scenario_full
    )

    text_values = [
        schemas_widgets.TextVariable(
            key='future_measure_percentage_change',
            value=abs(future_measure_percentage_change),
            units='%'
        ),
        schemas_widgets.TextVariable(
            key='measure_future_benefit',
            value=measure_future_benefit,
            units=units_exposure
        )
    ]

    return schemas_widgets.GeneratedText(
        template=template,
        values=text_values
    )


def _get_measure_change_summary_pt3(
            measure_name,
            measure_cost,
            units_currency,
            impact_type,
            units_exposure,
            future_year,
            affected_present,
            affected_future,
            affected_measure,
            affected_future_measure
    ):
    template = Template('''\
This means that, over {{n_years_of_analysis}} until $future_year, and at a cost of {{measure_cost}}, \
implementing $measure_name saves (very roughly) {{saved_per_unit_currency}} $affected_description for each \
$units_currency spent.'''
                        )

    # TODO use the actual costbenefit module for this
    # TODO And create a class to store this info, we've done this calculation twice
    measure_benefit = affected_present - affected_measure
    measure_future_benefit = affected_future - affected_future_measure
    n_years = max(future_year - 2020, 1)
    total_benefit = 0.5 * (measure_future_benefit + measure_benefit) * n_years
    saved_per_unit_currency = total_benefit / measure_cost

    # TODO put all of these lookups into a big dictionary somewhere so it's easy to add new types
    if impact_type == 'people_affected':
        affected_description = 'affected'
    elif impact_type == 'economic_impact':
        affected_description = 'loss'
    elif impact_type == 'assets_affected':
        affected_description = 'assets affected'
    else:
        raise ValueError(f'{impact_type} is not in my list of pre-prepared impact types for text generation')

    template = template.substitute(
        measure_name=measure_name.lower(),
        affected_description=affected_description,
        future_year=future_year,
        units_currency=units_currency
    )

    text_values = [
        schemas_widgets.TextVariable(
            key='n_years_of_analysis',
            value=int(n_years),
            units='years'
        ),
        schemas_widgets.TextVariable(
            key='measure_cost',
            value=measure_cost,
            units=units_currency
        ),
        schemas_widgets.TextVariable(
            key='saved_per_unit_currency',
            value=abs(saved_per_unit_currency),
            units=units_exposure
        )
    ]

    return schemas_widgets.GeneratedText(
        template=template,
        values=text_values
    )

def _get_costben_conclusion():
    text = '''\
Remember: these numbers are intended as guidance only - they are based on global climate models and global impact \
models. Inevitably the situations in individual places will be different from the global assumptions that go into \
these models. They're not a substitute for local feasibility studies, which should be the next step.\
'''
    return schemas_widgets.GeneratedText(
        template=text,
        values=[]
    )