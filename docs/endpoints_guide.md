# Quick guide to the Vizzuality endpoints

## Adaptation measures

The RECA tool provides data on a number of out-of-the-box adaptation measures for illustration purposes.

The measures should be used to populate the web tool's selection of available adaptation measures, and a measure ID is needed when making a request to the `cost-benefit` endpoint.

### Query structure

*Note: the pre-populated database currently only has data for the measure with ID 12 (Mangroves, for tropical cyclones and economic assets)* 

Queries are made to the `/rest/vizz/widgets/default-measures` POST endpoint available at https://reca-api.herokuapp.com/rest/vizz/widgets/cost-benefit.

Parameters for the request are passed in the URL and are used to filter the returned adaptation measures. If no parameters are passed, all available measures are returned.

Parameters are documented below and on the OpenAPI/Swagger docs at https://reca-api.herokuapp.com/rest/vizz/docs#/widget/calc_api_vizz_ninja__api_default_measures.


| Parameter | Type | Description |
| --------- | ---- | ------- |
| `measure_ids` | integer | ID(s) of the measures you are requesting, if known |
| `hazard_type` | string | Filter to measures for a particular hazard. Currently one of `tropical_cyclone` or `extreme_heat` |
| `exposure_type` | string | Filter to measures for a particular type of exposures. Currently one of `economic_assets` or `people` |

*Note: I think we will need to add units information to this request*


### Returned values

The response is a list of `MeasureSchema` objects, each containing the details of an adaptation measure matching the requested filters.

A `MeasureSchema` has the following properties. It was designed as a schema where the user would be able to set provide their own custom measures, but for now we will only work with preset measures.

*Note: currently the cost is fixed, but I'd like the user to be able to be able to provide this when running a cost-benefit analysis. Maybe we add that as an additional parameter to the cost-benefit request.*

| Property | Type | Default | Description | Notes |
| -------- | ---- | ------- | ----------- |------ |
| `id` | integer | | Measure ID | Looks like this isn't currently returned - I'll update that today!! Use 12 for testing. |
| `name` | string | | Measure name | |
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


| Parameter | Type | Default | Description | Notes |
| --------- | ---- | ------- | ----------- |------ |
| `location_name` |	string | | Name of place of study | The list of precalculated locations are available through the `options` endpoint |
| `location_scale` | string | | Information on the type of location. Determined automatically if not provided | No need to provide this |
| `location_code` |	string | | Internal location ID. Alternative to `location_name`. Determined automatically if not provided | No need to provide this |
| `location_poly` |	list of list of numbers | `[]` | A polygon given in `[lat, lon]` pairs. If provided, the calculation is clipped to this region | No need to use in the tool |
| `geocoding` | GeocodePlace schema | None | For internal use: ignore! I'll remove it later. | |
| `scenario_name` | string | | Combined climate and growth scenario | One of `historical`, `rcp126`, `rcp245`, `rcp585` | 
| `scenario_climate` | string | | Climate scenario. Overrides `scenario_name` | Currently unused |
| `scenario_growth` | string | | Growth scenario. Overrides `scenario_name` | Currently unused |
| `scenario_year` | integer | | Year to produce statistics for | One of `2020`, `2040`, `2060`, `2080` |
| `aggregation_scale` |	string | | | For internal use: ignore! I'll remove it later
| `aggregation_method` | string | | | For internal use: ignore! I'll remove it later
| `hazard_type` | string | | The hazard type the measure applies to. | Currently one of `tropical_cyclone` or `extreme_heat`. Provided by the `options` endpoint. |
| `exposure_type` | string | | The exposure type the measure applies to. | Currently one of `economic_assets` or `people`. Provided by the `options` endpoint. |
| `impact_type` | string | | The impact to be calculated. | Depends on the hazard and exposure types. For tropical cyclones one of `assets_affected`, `economic_impact`, `people_affected`. For extreme heat `people_affected`. Provided by the `options` endpoint. |
| `units_hazard` | string | | Units the hazard is measured in | Currently one of `ms` (tropical cyclones) or `celsius` (heat). To be expanded |
| `units_exposure` | string | | Units the exposure is measured in | Currently one of `dollars` (economic assets) or `people` (people). To be expanded |
| `units_warming` |	string | | Units the degree of warming is measured in | Currently `celsius`. To be expanded |
| `measure_ids`	| list of integers | `[]` | IDs of adaptation measures to be implemented (see above). |