# Quick guide to the Vizzuality endpoints

In this document:
- Risk timeline
- Adaptation measures
- Cost-benefit
- Social vulnerability


## Risk Timeline

The `risk-timeline` endpoint returns all the information needed to construct a bar chart breaking down risk between 2020 and 2080 for the selected setup. The chart has a bar for each year of the timeline (2020, 2040, 2060, 2080) and each bar is broken down into components: the 2020 baseline risk, and changes due to population/economic growth and changes due to climate change.

Note that changes can be positive or negative depending on the hazard and location.

### Query structure

Queries are made to the `/rest/vizz/widgets/risk-timeline` POST endpoint available at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/risk-timeline.

Parameters are documented below and on the OpenAPI/Swagger docs at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_risk_timeline_submit.

*Note: the 'Used' column for tables in this document tells you whether the parameter is needed for the (expected) API widgets.*

#### Required parameters 

| Parameter | Type | Description | Notes |
| --------- | ---- | ----------- |------ |
| `location_name` |	string | Name of place of study | The list of precalculated locations are available through the `options` endpoint |
| `scenario_name` | string | Combined climate and growth scenario | One of `historical`, `rcp126`, `rcp245`, `rcp585` | 
| `scenario_year` | integer | Year to produce statistics for | One of `2020`, `2040`, `2060`, `2080` |
| `hazard_type` | string | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat`. Provided by the `options` endpoint. |
| `hazard_rp` | string | The return period to use for this analysis. | |
| `impact_type` | string | The impact to be calculated. | Depends on the hazard and exposure types. For tropical cyclones one of `assets_affected`, `economic_impact`, `people_affected`. For extreme heat `people_affected`. Provided by the `options` endpoint. |
| `units_hazard` | string | Units the hazard is measured in | One of `m/s`, `mph`, `km/h`, `knots`' (tropical cyclones) or `degC` `degF` (heat). Provided by the `options` endpoint |
| `units_exposure` | string | Units the exposure is measured in | One of `USD`, `EUR` (economic assets) or `people` (people) |
| `units_warming` |	string | Units the degree of warming is measured in. | One of `degC` `degF` |

#### Not required parameters

These are not needed for the current functioning of the API.

| Parameter | Type | Description | Notes |
| --------- | ---- | ----------- |------ |
| `location_scale` | string | Information on the type of location. Determined automatically if not provided | |
| `location_code` |	string | Internal location ID. Alternative to `location_name`. Determined automatically if not provided | |
| `location_poly` |	list of list of numbers | A polygon given in `[lat, lon]` pairs. If provided, the calculation is clipped to this region | |
| `geocoding` | GeocodePlace schema | For internal use: ignore! I'll remove it later. | |
| `exposure_type` | string | The exposure to be used. | Inferred from `impact_type`: no need to use. One of `economic_assets`, `people`. |
| `scenario_climate` | string | Climate scenario. Overrides `scenario_name` | |
| `scenario_growth` | string | Growth scenario. Overrides `scenario_name` | |
| `aggregation_scale` |	string | | For internal use: ignore! I'll remove it later
| `aggregation_method` | string | | For internal use: ignore! I'll remove it later


#### Example request

This is a request for a risk timeline showing the expected impacts from a 1-in-10 year tropical cyclone on economic assets in Havana in 2080 under the RCP 8.5 warming scenario and the SSP5 population growth scenario.

```
curl --location --request POST 'https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/risk-timeline' \
--header 'Content-Type: application/json' \
--data-raw '{
    "hazard_type": "tropical_cyclone",
    "hazard_rp": "10",
    "impact_type": "economic_impact",
    "scenario_name": "ssp585",
    "scenario_year": 2080,
    "location_name": "Havana, Cuba",
    "units_hazard": "m/s",
    "units_exposure": "dollars",
    "units_warming": "degC"
}'
```

### Response

The response is a `TimelineWidgetJobSchema` object, which you can see at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_widget_risk_timeline_poll.

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

Queries are made to the `/rest/vizz/widgets/default-measures` POST endpoint available at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/cost-benefit.

Parameters for the request are passed in the URL and are used to filter the returned adaptation measures. If no parameters are passed, all available measures are returned.

Parameters are documented below and on the OpenAPI/Swagger docs at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_default_measures.

Each parameter applies a filter to the queried measures. If no parameters are supplied, all available measures are returned.

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- | 
| `measure_ids` | integer | False |ID(s) of the measures you are requesting, if known |
| `slug` | string | False |The slugs of the measures you are requesting, if known |
| `hazard_type` | string | False | Filter to measures for a particular hazard. Currently one of `tropical_cyclone` or `extreme_heat` |
| `exposure_type` | string | False | Filter to measures for a particular type of exposures. Currently one of `economic_assets` or `people` |
| `units_hazard` | string | True | Units to return hazard information in. One of `m/s`, `mph`, `km/h`, `knots`' (tropical cyclones) or `degC` `degF` (heat). Provided by the `options` endpoint |
| `units_currency` | string | True | Units to return currency information in. One of `USD`, `EUR`. Provided by the `options` endpoint |
| `units_distance` | string | True | Units to return distance information in. One of `km`, `miles`. Provided by the `options` endpoint |

*Note: adaptation measures are currently defined independently of the exposure, so units are not required*

#### Example query

This is a request for pre-defined adaptation measures for tropical cyclones affecting economic assets.

```
curl --location --request GET 'https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/default-measures?hazard_type=tropical_cyclone&exposure_type=economic_assets&units_hazard=mph&units_currency=USD'
```

### Returned values

The response is a list of `MeasureSchema` objects, each containing the details of an adaptation measure matching the requested filters.

A `MeasureSchema` has the following properties. It was designed as a schema where the user would be able to provide their own custom measures, but for now we will only work with preset measures.

*Note: currently the cost is fixed, but I'd like the user to be able to be able to provide this when running a cost-benefit analysis. Maybe we add that as an additional parameter to the cost-benefit request.*

| Property | Type | Description | Notes |
| -------- | ---- | ----------- |------ |
| `id` | integer | Measure ID | |
| `name` | string | Measure name | |
| `slug` | string | A slug for the measure name | |
| `description`	| string | A text description of the measure | |
| `hazard_type` | string | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat` |
| `exposure_type` | string | The exposure type the measure applies to. | Currently one of `economic_assets` or `people` |
| `cost_type` | string | Information on how costs are described (e.g. whole project, by unit area, etc) | Currently only `whole_project` with no plans to expand: no need to display to user | 
| `cost` | number | Cost of the project | |
| `annual_upkeep` |	float | Currently ignored | Don't display to user. |
| `priority` | string | How the adaptation measure is implemented: one of `even_coverage`, `costbenefit`, `vulnerability` | |
| `percentage_coverage` | float | Percentage of the study area that the measure will affect. Spatial distribution is chosen according to the `priority` parameter. | |
| `percentage_effectiveness` | float | For population/assets in the coverage area, the percentage who experience the measure. e.g. a 70% adaptation rate for building codes, or 20% of the population using cooling spaces | 
| `is_coastal` | boolean | Does the measure only apply to coastal regions? | |
| `max_distance_from_coast` | float | If `is_coastal`, what distance inland benefits? | Minimum value of 7 |
| `hazard_cutoff` |	float | The measure prevents impacts from hazard intensity below this value |  Currently unused |
| `return_period_cutoff` | float | The measure prevents impacts from events with a return period below this value | Currently unused |
| `hazard_change_multiplier` | float | The measure scales the hazard intensity by this amount | (Currently it's 1 over this amount - I'll change that soon) |
| `hazard_change_constant` | float | The measure reduces the hazard intensity by this amount | |
| `cobenefits` | list of Cobenefits | A list of Cobenefit objects | Still being implemented |
| `units_currency` | string | Currency | |
| `units_hazard` | string | Units the hazard is measured in | |
| `units_distance` | string  | Units to measure distance | |
| `user_generated` | boolean | Flag for custom measures | Not enabled, always `false` |


## Cost-benefit

The cost-benefit endpoint is probably the most awkward to use. This explains the structure of a query and how to interpret the response.

### Query structure

Queries are made to the `/rest/vizz/widgets/cost-benefit` POST endpoint available at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/cost-benefit.

A query is structured using the `CostBenefitRequest` schema, documented below and on the OpenAPI/Swagger docs at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_widget_costbenefit_submit

### Required parameters

| Parameter | Type | Description | Notes |
| --------- | ---- | ----------- |------ |
| `location_name` |	string | Name of place of study | The list of precalculated locations are available through the `options` endpoint |
| `scenario_name` | string | Combined climate and growth scenario | One of `historical`, `rcp126`, `rcp245`, `rcp585` | 
| `scenario_year` | integer | Year to produce statistics for | One of `2020`, `2040`, `2060`, `2080` |
| `hazard_type` | string | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat`. Provided by the `options` endpoint |
| `hazard_rp` | string | The return period to use for this analysis | |
| `impact_type` | string | The impact to be calculated. | Depends on the hazard and exposure types. For tropical cyclones one of `assets_affected`, `economic_impact`, `people_affected`. For extreme heat `people_affected`. Provided by the `options` endpoint |
| `measure_ids`	| list of integers | List of IDs of adaptation measures to be implemented. Measures are available through the `default_measures` endpoint (see above) | Currently either `2` or `4` |
| `units_hazard` | string | Units the hazard is measured in | One of `m/s`, `mph`, `km/h`, `knots`' (tropical cyclones) or `degC` `degF` (heat). Provided by the `options` endpoint |
| `units_exposure` | string | Units the exposure is measured in | One of `USD`, `EUR` (economic assets) or `people` (people) |
| `units_warming` |	string | Units the degree of warming is measured in | One of `degC`, `degF` |

### Not required parameters

| Parameter | Type | Default | Description | Notes |
| --------- | ---- | ------- | ----------- |------ |
| `location_scale` | string | | Information on the type of location. Determined automatically if not provided | |
| `location_code` |	string | | Internal location ID. Alternative to `location_name`. Determined automatically if not provided | |
| `location_poly` |	list of list of numbers | `[]` | A polygon given in `[lat, lon]` pairs. If provided, the calculation is clipped to this region | |
| `geocoding` | GeocodePlace schema | None | For internal use: ignore! I'll remove it later. | |
| `scenario_climate` | string | | Climate scenario. Overrides `scenario_name` | |
| `scenario_growth` | string | | Growth scenario. Overrides `scenario_name` | |
| `aggregation_scale` |	string | | | For internal use: ignore! I'll remove it later |
| `aggregation_method` | string | | | For internal use: ignore! I'll remove it later |


#### Example query

This is a request for a cost-benefit analysis for introducing mangroves in Jamaica, looking at the benefits out to 2080 under the RCP 8.5 climate and SSP 5 growth scenarios.

*Note: the measure IDs will occasionally change, so you'll need to query them each time.*

```
curl --location --request POST 'https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/cost-benefit' \
--header 'Content-Type: application/json' \
--data-raw '{
    "hazard_type": "tropical_cyclone",
    "hazard_rp": "10",
    "impact_type": "economic_impact",
    "scenario_name": "ssp585",
    "scenario_year": 2080,
    "location_name": "Jamaica",
    "measure_ids": [2],
    "units_hazard": "m/s",
    "units_exposure": "USD",
    "units_warming": "degC",
    "units_currency": "USD"
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

The response is a `CostBenefitJobSchema` object which you can see at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_widget_risk_timeline_poll.

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



## Social Vulnerability

The `social-vulnerabilty` endpoint gives information about the relative wealth of the population of interest. It returns all the information needed to construct a bar chart of the relative wealth distribution by decile.

### Query structure

Queries are made to the `/rest/vizz/widgets/social-vulnerability` POST endpoint available at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/social-vulnerability.

Parameters are documented below and on the OpenAPI/Swagger docs at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_social_vulnerability_submit.

*Note: social vulnerability data is only available for lower and middle-income countries. In this case there will be no numeric data and the automatically generated text will be very brief.*

#### Required parameters

| Parameter | Type | Default | Description | Notes |
| --------- | ---- |  ------- | ----------- |------ |
| `location_name` |	string |  | Name of place of study | The list of precalculated locations are available through the `options` endpoint |
| `hazard_type` | string | | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat`. Provided by the `options` endpoint. |


#### Not required parameters
| `location_scale` | string | | Information on the type of location. Determined automatically if not provided | No need to provide this |
| `location_code` |	string | | Internal location ID. Alternative to `location_name`. Determined automatically if not provided | No need to provide this |
| `location_poly` |	list of list of numbers | | A polygon given in `[lat, lon]` pairs. If provided, the calculation is clipped to this region | No need to use in the tool |
| `geocoding` | GeocodePlace schema | None | For internal use: ignore! I'll remove it later. | |


#### Example request

This is a request for social vulnerability information for Jamaica.

```
curl --location --request POST 'https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/social-vulnerability' \
--header 'Content-Type: application/json' \
--data-raw '{
    "hazard_type": "tropical_cyclone",
    "location_name": "Jamaica"
}'
```

### Response

The response is a `SocialVulnerabiltyWidgetJobSchema` object, which you can see at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_widget_social_vulnerability_poll.

The response is contained in its `response.data` properties, where the `text` property contains the generated text and the `chart` contains the data.

The chart gives legend information and a bar chart in its `items` property (note that there are two `items`: the first is data for the location of interest, the second for the country it is in). Each gives a breakdown for a bar chart with the `ExposureBreakdownBar` schema. The schema contains (up to) ten bars, giving the proportion of people living in each of the ten social vulnerability groups.

The `ExposureBreakdownBar` has this structure:

| Property | Type | Description | Notes |
| -------- | ---- | ----------- |------ |
| `label` | string | The chart title | | 
| `location_scale` | string | | Currently unused | 
| `category_labels`	| list of strings | Vulnerability deciles, always in the range '1' to '10' | Bars with no data are currently missed out |
| `values` | list of numbers | Each decile's proportional population in the area of interest (in the range 0 – 1) | |



## Biodiversity

The `biodiversity` endpoint gives information about landuse in the area of interest. It returns all the information needed to construct a bar or pie chart of land use types, plus descriptive text putting the information into an adaptation context.

### Query structure

Queries are made to the `/rest/vizz/widgets/biodiversity` POST endpoint available at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/biodiversity.

Parameters are documented below and on the OpenAPI/Swagger docs at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_biodiversity_submit.

#### Required parameters

| Parameter | Type | Default | Description | Notes |
| --------- | ---- |  ------- | ----------- |------ |
| `location_name` |	string |  | Name of place of study | The list of precalculated locations are available through the `options` endpoint |
| `hazard_type` | string | | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat`. Provided by the `options` endpoint. |


#### Not required parameters
| `location_scale` | string | | Information on the type of location. Determined automatically if not provided | No need to provide this |
| `location_code` |	string | | Internal location ID. Alternative to `location_name`. Determined automatically if not provided | No need to provide this |
| `location_poly` |	list of list of numbers | | A polygon given in `[lat, lon]` pairs. If provided, the calculation is clipped to this region | No need to use in the tool |
| `geocoding` | GeocodePlace schema | None | For internal use: ignore! I'll remove it later. | |


#### Example request

This is a request for biodiversity data for Jamaica.

```
curl --location --request POST 'https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/biodiversity' \
--header 'Content-Type: application/json' \
--data-raw '{
    "hazard_type": "tropical_cyclone",
    "location_name": "Jamaica"
}'
```

### Response

The response is a `BiodiversityWidgetJobSchema` object, which you can see at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_widget_biodiversity_poll.

The response is contained in its `response.data` properties, where the `text` property contains the generated text and the `chart` contains the data.

The chart gives legend information and a bar/pie chart in its `items` property. Each is an `ExposureBreakdownBar` giving the fraction of (non-ocean) area taken up by each land-use type. It has this structure:

| Property | Type | Description | Notes |
| -------- | ---- | ----------- |------ |
| `label` | string | The chart title | | 
| `location_scale` | string | | Currently unused | 
| `category_labels`	| list of strings | Land use types | Non-ocean only |
| `values` | list of float | Each land-use types fractional contribution to the total area (in the range 0 – 1) | |

The automatically generated text gives an introduction and a sentence for each land-use type.
