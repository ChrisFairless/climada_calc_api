# Quick guide to the Vizzuality endpoints

## Risk Timelines

The `risk-timeline` endpoint returns all the information needed to construct a bar chart breaking down risk between 2020 and 2080 for the selected setup. The chart has a bar for each year of the timeline (2020, 2040, 2060, 2080) and each bar is broken down into components: the 2020 baseline risk, and changes due to population/economic growth and changes due to climate change.

Note that changes can be positive or negative depending on the hazard and location.

### Query structure

Queries are made to the `/rest/vizz/widgets/risk-timeline` POST endpoint available at https://reca-api.herokuapp.com/rest/vizz/widgets/risk-timeline.

Parameters are documented below and on the OpenAPI/Swagger docs at https://reca-api.herokuapp.com/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_risk_timeline_submit.

*Note: the 'Used' column for tables in this document tells you whether the parameter is needed for the (expected) API widgets.*

| Parameter | Type | Used | Default | Description | Notes |
| --------- | ---- | ---- | ------- | ----------- |------ |
| `location_name` |	string | Y | | Name of place of study | The list of precalculated locations are available through the `options` endpoint |
| `location_scale` | string | N | | Information on the type of location. Determined automatically if not provided | No need to provide this |
| `location_code` |	string | N | | Internal location ID. Alternative to `location_name`. Determined automatically if not provided | No need to provide this |
| `location_poly` |	list of list of numbers | N | `[]` | A polygon given in `[lat, lon]` pairs. If provided, the calculation is clipped to this region | No need to use in the tool |
| `geocoding` | GeocodePlace schema | N | None | For internal use: ignore! I'll remove it later. | |
| `scenario_name` | string | Y | | Combined climate and growth scenario | One of `historical`, `rcp126`, `rcp245`, `rcp585` | 
| `scenario_climate` | string | N | | Climate scenario. Overrides `scenario_name` | Currently unused |
| `scenario_growth` | string | N | | Growth scenario. Overrides `scenario_name` | Currently unused |
| `scenario_year` | integer | Y | | Year to produce statistics for | One of `2020`, `2040`, `2060`, `2080` |
| `aggregation_scale` |	string | N | | | For internal use: ignore! I'll remove it later
| `aggregation_method` | string | N | | | For internal use: ignore! I'll remove it later
| `hazard_type` | string | Y | | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat`. Provided by the `options` endpoint. |
| `hazard_rp` | string | Y | | The return period to use for this analysis. | This will be retired soon, replacing all calculations with average annual impact instead |
| `exposure_type` | string | Y | | The exposure type the measure applies to. | Currently one of `economic_assets` or `people`. Provided by the `options` endpoint. |
| `impact_type` | string | Y | | The impact to be calculated. | Depends on the hazard and exposure types. For tropical cyclones one of `assets_affected`, `economic_impact`, `people_affected`. For extreme heat `people_affected`. Provided by the `options` endpoint. |
| `units_hazard` | string | Y | | Units the hazard is measured in | Currently one of `ms` (tropical cyclones) or `celsius` (heat). To be expanded |
| `units_exposure` | string | Y | | Units the exposure is measured in | Currently one of `dollars` (economic assets) or `people` (people). To be expanded |
| `units_warming` |	string | Y | | Units the degree of warming is measured in | Currently `celsius`. To be expanded |

#### Example request

This is a request for a risk timeline showing the expected impacts from a 1-in-10 year tropical cyclone on economic assets in Havana in 2080 under the RCP 8.5 warming scenario and the SSP5 population growth scenario.

```
curl --location --request POST 'https://reca-api.herokuapp.com/rest/vizz/widgets/risk-timeline' \
--header 'Content-Type: application/json' \
--data-raw '{
    "hazard_type": "tropical_cyclone",
    "hazard_rp": "10",
    "exposure_type": "economic_assets",
    "impact_type": "economic_impact",
    "scenario_name": "ssp585",
    "scenario_year": 2080,
    "location_name": "Havana, Cuba",
    "units_hazard": "ms",
    "units_exposure": "dollars",
    "units_warming": "celsius"
}'
```

### Response

The response is a `TimelineWidgetJobSchema` object, which you can see at https://reca-api.herokuapp.com/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_widget_risk_timeline_poll.

The response is contained in its `response.data` properties, where the `text` property has the generated text and the `chart` contains the data.

The chart gives legend information and a series of bars, contained in the chart's `items` property. Each is a `BreakdownBar` schema with the following properties:

*Note: the BreakdownBar class has other properties, but they are not used in this response*

| Property | Type | Description | Notes |
| -------- | ---- | ----------- |------ |
| `year_label` | string | The year the analysis is valid for | | 
| `year_value` | integer | The year the analysis is valid for | | 
| `temperature`	| number | Currently unused | |
| `current_climate` | number | The calculated baseline impacts in the present day (2020) climate | |
| `growth_change` |	number | The change in impacts from the baseline to the year of analysis due to economic/population growth | | 
| `climate_change` | number | The change in impacts from the baseline to the year of analysis due to climate change (includes compounding effects of growth) | | 
| `future_climate` | number | The calculated impacts for the year of analysis. Equal to the sum of the previous three properties | |


## Adaptation measures

The RECA tool provides data on a number of out-of-the-box adaptation measures for illustration purposes.

The measures should be used to populate the web tool's selection of available adaptation measures, and a measure ID is needed when making a request to the `cost-benefit` endpoint.

### Query structure

*Note: the pre-populated database currently only has data for the measure with ID 12 (Mangroves, for tropical cyclones and economic assets)* 

Queries are made to the `/rest/vizz/widgets/default-measures` POST endpoint available at https://reca-api.herokuapp.com/rest/vizz/widgets/cost-benefit.

Parameters for the request are passed in the URL and are used to filter the returned adaptation measures. If no parameters are passed, all available measures are returned.

Parameters are documented below and on the OpenAPI/Swagger docs at https://reca-api.herokuapp.com/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_default_measures.

| Parameter | Type | Used | Description |
| --------- | ---- | ---- | ----------- | 
| `measure_ids` | integer | Y | ID(s) of the measures you are requesting, if known |
| `slug` | string | Y | The sligs of the measures you are requesting, if known |
| `hazard_type` | string | Y | Filter to measures for a particular hazard. Currently one of `tropical_cyclone` or `extreme_heat` |
| `exposure_type` | string | Y | Filter to measures for a particular type of exposures. Currently one of `economic_assets` or `people` |

*Note: I think we will need to add units information to this request*

#### Example query

This is a request for pre-defined adaptation measures for tropical cyclones affecting economic assets.

```
curl --location --request GET 'https://reca-api.herokuapp.com/rest/vizz/widgets/default-measures?hazard_type=tropical_cyclone&exposure_type=economic_assets'
```

### Returned values

The response is a list of `MeasureSchema` objects, each containing the details of an adaptation measure matching the requested filters.

A `MeasureSchema` has the following properties. It was designed as a schema where the user would be able to set provide their own custom measures, but for now we will only work with preset measures.

*Note: currently the cost is fixed, but I'd like the user to be able to be able to provide this when running a cost-benefit analysis. Maybe we add that as an additional parameter to the cost-benefit request.*

| Property | Type | Default | Description | Notes |
| -------- | ---- | ------- | ----------- |------ |
| `id` | integer | | Measure ID | Looks like this isn't currently returned - I'll update that today!! Use 12 for testing. |
| `name` | string | | Measure name | |
| `slug` | string | | A slug for the measure name | |
| `description`	| string | | A text description of the measure | |
| `hazard_type` | string | | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat` |
| `exposure_type` | string | | The exposure type the measure applies to. | Currently one of `economic_assets` or `people` |
| `cost_type` | string | `whole_project` | Information on how costs are described (e.g. whole project, by unit area, etc) | Currently only `whole_project` with no plans to expand: no need to display to user | 
| `cost` | number | | Cost of the project | |
| `annual_upkeep` |	number | 0 | Currently ignored. Don't display to user. |
| `priority` | string | `even_coverage` | How the adaptation measure is implemented: one of `even_coverage`, `costbenefit`, `vulnerability` |
| `percentage_coverage` | number | 100 | Percentage of the study area that the measure will affect. Spatial distribution is chosen according to the `priority` parameter. | |
| `percentage_effectiveness` | number | 100 | For population/assets in the coverage area, the percentage who experience the measure. e.g. a 70% adaptation rate for building codes, or 20% of the population using cooling spaces | 
| `is_coastal` | boolean | `false` | Does the measure only apply to coastal regions? | |
| `max_distance_from_coast` | number | 7 | If `is_coastal`, what distance inland benefits? | Minimum value of 7 |
| `hazard_cutoff` |	number | 0 | The measure prevents impacts from hazard intensity below this value |  Currently unused |
| `return_period_cutoff` | number | 0 | The measure prevents impacts from events with a return period below this value | Currently unused |
| `hazard_change_multiplier` | number | 1 | The measure scales the hazard intensity by this amount | (Currently it's 1 over this amount - I'll change that soon) |
| `hazard_change_constant` | number | 0 | The measure reduces the hazard intensity by this amount | |
| `cobenefits` | list of Cobenefits | `[]` | A list of Cobenefit objects. | Still being implemented |
| `units_currency` | string | `dollars` | Currency | Currently always dollars
| `units_hazard` | string | | Units the hazard is measured in | Currently one of `ms` (tropical cyclones) or `celsius` (heat). To be expanded |
| `units_distance` | string | `kilometres` | Units to measure distance | Currently `kilometres`. To be expanded. |
| user_generated |	boolean | `false` | Flag for custom measures | Not enabled: always `false` |



## Cost-benefit

The cost-benefit endpoint is probably the most awkward to use. This explains the structure of a query and how to interpret the response.

### Query structure

Queries are made to the `/rest/vizz/widgets/cost-benefit` POST endpoint available at https://reca-api.herokuapp.com/rest/vizz/widgets/cost-benefit.

A query is structured using the `CostBenefitRequest` schema, documented below and on the OpenAPI/Swagger docs at https://reca-api.herokuapp.com/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_widget_costbenefit_submit


| Parameter | Type | Used | Default | Description | Notes |
| --------- | ---- | ---- | ------- | ----------- |------ |
| `location_name` |	string | Y | | Name of place of study | The list of precalculated locations are available through the `options` endpoint |
| `location_scale` | string | N | | Information on the type of location. Determined automatically if not provided | No need to provide this |
| `location_code` |	string | N | | Internal location ID. Alternative to `location_name`. Determined automatically if not provided | No need to provide this |
| `location_poly` |	list of list of numbers | N | `[]` | A polygon given in `[lat, lon]` pairs. If provided, the calculation is clipped to this region | No need to use in the tool |
| `geocoding` | GeocodePlace schema | N | None | For internal use: ignore! I'll remove it later. | |
| `scenario_name` | string | Y | | Combined climate and growth scenario | One of `historical`, `rcp126`, `rcp245`, `rcp585` | 
| `scenario_climate` | string | N | | Climate scenario. Overrides `scenario_name` | Currently unused |
| `scenario_growth` | string | N | | Growth scenario. Overrides `scenario_name` | Currently unused |
| `scenario_year` | integer | Y | | Year to produce statistics for | One of `2020`, `2040`, `2060`, `2080` |
| `aggregation_scale` |	string | N | | | For internal use: ignore! I'll remove it later
| `aggregation_method` | string | N | | | For internal use: ignore! I'll remove it later
| `hazard_type` | string | Y | | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat`. Provided by the `options` endpoint. |
| `hazard_rp` | string | Y | | The return period to use for this analysis. | |
| `exposure_type` | string | Y | | The exposure type the measure applies to. | Currently one of `economic_assets` or `people`. Provided by the `options` endpoint. |
| `impact_type` | string | Y | | The impact to be calculated. | Depends on the hazard and exposure types. For tropical cyclones one of `assets_affected`, `economic_impact`, `people_affected`. For extreme heat `people_affected`. Provided by the `options` endpoint. |
| `units_hazard` | string | Y | | Units the hazard is measured in | Currently one of `ms` (tropical cyclones) or `celsius` (heat). To be expanded |
| `units_exposure` | string | Y | | Units the exposure is measured in | Currently one of `dollars` (economic assets) or `people` (people). To be expanded |
| `units_warming` |	string | Y | | Units the degree of warming is measured in | Currently `celsius`. To be expanded |
| `measure_ids`	| list of integers | Y | `[]` | IDs of adaptation measures to be implemented (see above). |

#### Example query

This is a request for a cost-benefit analysis for introducing mangroves in Jamaica, looking at the benefits out to 2080 under the RCP 8.5 climate and SSP 5 growth scenarios.

*Note: the measure IDs will keep changing (at the moment), so you'll need to query them each time.*

```
curl --location --request POST 'https://reca-api.herokuapp.com/rest/vizz/widgets/cost-benefit' \
--header 'Content-Type: application/json' \
--data-raw '{
    "hazard_type": "tropical_cyclone",
    "hazard_rp": "10",
    "exposure_type": "economic_assets",
    "impact_type": "economic_impact",
    "scenario_name": "ssp585",
    "scenario_year": 2080,
    "location_name": "Jamaica",
    "measure_ids": [74],
    "units_hazard": "ms",
    "units_exposure": "dollars",
    "units_warming": "celsius"
}'
```

### Returned values

A CostBenefit is communicated as several components.
- `current_climate`: The baseline (2020) climate impacts
- `growth_change`: The change in impacts from the baseline year to the analysis year due to economic or population growth
- `climate_change`: The change in impacts from the baseline year to the analysis year due to climate change
- `future_climate`: The climate impacts in the analysis year. Equal to the sum of the previous three values.
- `measure_change`: The change in impacts in the analysis year from introducing the selected adaptation measure.
- `measure_climate`: The climate impacts in the analysis year with the adaptation measure applied. Equal to the sum of the previous two values.

The response is a `CostBenefitJobSchema` object which you can see at https://reca-api.herokuapp.com/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_widget_risk_timeline_poll.

The response is contained in its `response.data` properties, where the `text` property has the generated text and the `chart` contains the data.

The above components are contained in the chart's `items` property. Each is a `BreakdownBar` schema with the following properties:

| Property | Type | Description | Notes |
| -------- | ---- | ----------- |------ |
| `year_label` | string | The year the analysis is valid for | | 
| `year_value` | integer | The year the analysis is valid for | | 
| `temperature`	| number | Currently unused | |
| `current_climate` | number | The calculated baseline impacts in the present day (2020) climate | |
| `growth_change` |	number | The change in impacts from the baseline to the year of analysis due to economic/population growth | | 
| `climate_change` | number | The change in impacts from the baseline to the year of analysis due to climate change (includes compounding effects of growth) | | 
| `future_climate` | number | The calculated impacts for the year of analysis. Equal to the sum of the previous three properties | |
| `measure_names` | list of strings | The names of the measures applied | Currently limited to one measure |
| `measure_change` | list of numbers | The change in impacts for the analysis year when each adaptation measure is applied | Currently limited to one measure | 
| `measure_climate` | list of numbers | The calculated impact for the analysis year when each adaptation measure is applied. Equal to the sum of the previous two properties. | Currently limited to one measure |
| `combined_measure_change` | number | The change in impacts for the analysis year when all adaptation measures are applied | Not in use | 
| `combined_measure_climate` | number | The calculated impact for the analysis year when all adaptation measures are applied | Not in use |