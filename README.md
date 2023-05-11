# CLIMADA Calculations API

The code here is designed to provide a containerized climate risk and climate adaptation calculation service as a RESTful API.

In its current form you can launch the service with docker-compose and query four endpoints that were designed to serve risk calculations to a web tool, plus metadata and geocoding utilities. 

This branch is for running on your local machine and is not yet optimized for cloud deployment. Contact the authors for more information on this. It's a work in progress.

## Overview

The service allows the user to set up climate risk analyses choosing from
- two hazards (tropical cyclone, extreme heat)
- four risk metrics (tropical cyclone economic loss, tropical cyclone assets affected, tropical cyclone people affected and person-days of heat experienced)
- ten first-guess adaptation measures
- four climate change scenarios (historical, heavy mitigation, moderate mitigation, business as usual)
- five economic and population growth scenarios (SSPs 1-5)
- any return period, or average annual impact
- four future projection years (2020, 2040, 2060, 2080)

The tropical cyclone calculations can be performed for any place on earth (as long as it is recognised by the Maptiler geocoding service). The extreme heat calculations can be performed for ten pre-defined cities (and we are slowly expanding this). 

The currently available endpoints are:

### `rest/vizz/widgets/risk-timeline`

A timeline of climate risk until 2080.

For a chosen hazard, location, climate change scenario and return period, calculate the expected impacts between 2020 and 2080, and break them down into the 2020 baseline risk and components due to economic/population growth and climate change. Also generate text describing this risk.

In the back end this performs several risk calculations using an `impact` endpoint that is not yet exposed, and assembles them to give the risk-over-time information. The impact calculation uses CLIMADA data and functionality where available, plus a number of specially-written routines and extra datasets. For more details, see below.

### `rest/vizz/widgets/cost-benefit`

For a chosen hazard, location, climate change scenario, future year, and adaptation measure, calculate how a given adaptation measure changes the risk, and give the resulting cost-benefit for that adaptation measure, calculated as the ratio between the measure's cost and the expected total impacts the measure would prevent between 2020 and the future year of analysis. The endpoint also returns automatically generated text explaining the results.

In the back end this also performs several risk calculations using an `impact` endpoint that is not yet exposed. For more details see below.

### `rest/vizz/widgets/social-vulnerability`

For a chosen hazard and location, generate breakdowns of the social vulnerability at that location and (if different) the country, as scored by the [Relative Wealth Index](https://dataforgood.facebook.com/dfg/tools/relative-wealth-index). Also provides automatically generated text interpreting and putting the vulnerability in context.

### `rest/vizz/widgets/social-vulnerability`

For a chosen hazard and location, generate a breakdown of the land use at that location according to the [IUCN habitat classifications](https://www.nature.com/articles/s41597-020-00599-8). Also provides automatically generated text putting the land uses in context.

### `rest/vizz/widgets/geocode`

A family of lookup functions to help with geocoding of queries.

### `rest/vizz/options`

Detailed information on the available parameters in the tool.



## Install and run locally

### Quick start

You will need Docker installed on your machine and about 10 GB of space.

1. Clone this git repository to a local directory.

2. Run `cp env_template .env` to create an environment file. The default values here can be used to spin up a development server, but **do not use these in production**.

3. Set up geocoding. The tool's default setup uses the Maptiler Cloud service. To use this with your own machine, you'll to create an account with the [Maptiler Cloud API](https://docs.maptiler.com/cloud/api) and follow the instructions there for your free API key. Once you have it, edit the your `.env` environment file with the key. Note: if this doesn't work, there are other geocoding services implemented with the tool, including the OSMNames service. Contact me for setup instructions.

4. Run `docker-compose up --build` to launch the application. The first time this runs it will take a while. The application will (automatically)
    - download the relevant images. This is just over 4 GB because I've not shrunk down the containerised version of CLIMADA yet
    - create CLIMADA test files. This involves contacting the CLIMADA Data API, downloading files, and running a script to process the data
    - (only if using OSMNames geocoding:) download and extract the OSMNames geocoding data (the small version, 8MB download, 300 MB when indexed)
    - start the server

The API should now be running on port 8000.

You can test that it's responding by navigating to [http://0.0.0.0:8000/rest/vizz/map/debug/](http://0.0.0.0:8000/rest/vizz/map/debug/) or running 
```
curl -X 'GET' 'http://0.0.0.0:8000/rest/vizz/map/debug/' -H 'accept: */*'
```
The debug function waits three seconds and returns a JSON message of success. (It doesn't use any of the job management functionality.)

### Note:
The Django web server expects to mount a volume located on the host machine at `./static/sample_data/` (relative to the project root). The web container will download some files, calculate and store test datasets here. If you don't want these to persist after running, remove the volume from the `docker-compose.yml` file. If you want to mount a different directory instead, edit the `docker-compose.yml` file.


## Container structure

This current version of the project uses five containers:

#### web
A Django web tool running a RESTful API using Django Ninja. Mount a volume to `/climada_calc_api/static/sample_data` (by default this is set up as `./static/sample_data` on your local machine) to persist this data.

This is the component facing the outside world. It receives requests and processes them. Longer calculations are added to the Celery job queue and processed by workers.

#### celery
The same image as `web` above, but with the container running as a worker. It takes tasks from Celery's queue and executes them. The `redis` container acts as a broker for the tasks.

To scale the application, spin up more instances of this worker.

#### celery_flower
A job management interface for Celery. Access it on [0.0.0.0:5000](http://0.0.0.0:5000) to view the job queues and check things are working. You can drop this container from the docker-compose.yml file without affecting functionality.

#### db
A PostgreSQL database. Used for storing tabular data relevant to the tool, such as precalculated data, predefined measures, and for cacheing selected results.

#### redis
A redis database. This works as Celery's broker and results storage.


### Cloud structure: Digital Ocean

Deployment to the cloud on the Digital Ocean platform uses a very stripped-down version of this repository, available [here](https://github.com/ChrisFairless/reca-v1). The simpler version is designed only to handle a finite set of queries where all of the difficult calculations have already been cached in the PostgreSQL database.

The stripped-down version only runs the `web` container as a Digital Ocean Web App, and was created due to difficulties running longer jobs on the Digital Ocean platform, where small worker Functions aren't permitted to run for more than five seconds. In future this can be solved by simplifying and chaining the calculations, or by moving to another calculation service such as AWS Lambda.


### Cloud structure: Heroku (outdated)

Deployment to the cloud on the Heroku platform uses the same structure as the above. The `web` and `celery` components are initialised as Heroku dynos using the relevant Docker image, and the `redis` and `db` components are Heroku's provisioned Redis and PostegreSQL databases. The `celery_flower` container is currently excluded from this cloud deployment.


## Usage

This is an asynchronous calculations API. That means most endpoints need the user to make at least two calls. First to submit the job, and second to get the results a short time later.

Jobs are submitted via an endpoint's POST method, and the API returns a job ID, along with other metadata. The GET method will return information about the job's status until results are available, at which point the information will include the results. Users can keep polling the GET endpoint until the job is complete.

### Endpoints 

The API's endpoints are available through [0.0.0.0:8000/rest/vizz/](0.0.0.0:8000/rest/vizz/) (assuming you're running on your local machine).

Documentation is generated at [127.0.0.1:8000/rest/vizz/docs/](localhost:8000/rest/vizz/docs)
(assuming you're running on a local host). This is the best way to find out what's available to you and to test out the functionality! Note that not all of the endpoints are functional – the best information is on the [API documentation](https://github.com/ChrisFairless/climada_calc_api/blob/main/docs/endpoints_guide.md).

An endpoint's POST method takes multiple parameters in its body which together describe the data the user wants. See [API documentation](https://github.com/ChrisFairless/climada_calc_api/blob/main/docs/endpoints_guide.md) for the schema involved. The POST endpoint returns a job schema, including status information, as well as the URL to poll for results.

An endpoint's GET method only needs the job ID as a query parameter and returns information on the job's status. When the job is complete it also contains a `response` property, formatted according that endpoint's response schema.


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
curl --location --request GET 'https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/widgets/default-measures?hazard_type=tropical_cyclone&exposure_type=economic_assets&units_hazard=mph&units_currency=USD&units_distance='miles'
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
| `units_currency` | string | Units to return currency information in | One of `USD`, `EUR`. Provided by the `options` endpoint |
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
| Parameter | Type | Default | Description | Notes |
| --------- | ---- |  ------- | ----------- |------ |
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



## Geocoding

There are two geocoding endpoints, `rest/vizz/geocoding/autocomplete`, for querying locations by name, and `rest/vizz/geocoding/id/<id>` for querying locations when you already know the ID.

## Geocoding: autocomplete

The `geocoding/autocomplete` endpoint returns a list of the ten best matches for the queried location. Each list item contains metadata about the location, including the full name, id, bounding box and polygon.

Note: since version 1 of the tool limits your geographic queries to a finite selection of locations, you should already know the name of the location you are autocompleting, and autocomplete's first result should always be an exact match. Future versions may change this!


### Query structure

Queries are made with `/rest/vizz/geocoding/autocomplete?query=<query>` GET endpoint available at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/geocoding/autocomplete. The `query` parameter is provided in the URL as a query parameter.


#### Required parameters 

| Parameter | Type | Description | Notes |
| --------- | ---- | ----------- |------ |
| `query` |	string | Name of place to autocomplete | The list of precalculated locations are available through the `options` endpoint |


#### Example request

This is a request for Port-au-Prince, Haiti.

```
curl --location --request GET 'https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/geocode/autocomplete?query=Port-au-Prince,Haiti.' \
--header 'Content-Type: text/plain'
'
```

### Response

The response is an  `GeocodePlaceList` object, which you can see at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/geocode/calc_api_vizz_ninja__api_geocode_autocomplete.

The response is contained in its `data` property, wihch is a list of `GeocodePlace` objects. Each has the following properties:

| Property | Type | Description | Notes |
| -------- | ---- | ----------- |------ |
| `name` | string | Location name | | 
| `id` | string | An ID for the location, taken from OpenStreetMap | | 
| `scale`	| string | Geographic scale (e.g. city, province, country) | Currently unused |
| `country` | string | Country name | |
| `country_id` | string | 3-letter country ISO3 code | | 
| `admin1` | string | Admin 1 name | Currently unused | 
| `admin1_id` | string | Admin 1 code | Currently unused |
| `admin2` | string | Admin 1 name | Currently unused | 
| `admin2_id` | string | Admin 1 code | Currently unused |
| `poly` | List[ | Lat-lon coordinates with the form `[[lon1, lat1], [lon2, lat2], ... [lonN, latN]]` | | 
| `bbox` | string | Lat-lon coordinates of a bounding box for the location, with the form `[lon_min, lat_min, lon_max, lat_max]` | |


## Geocoding: id

The `geocoding/id` takes a known location ID as an input and returns data for that location.

### Query structure

Queries are made to `/rest/vizz/geocoding/autocomplete/id/<id>` GET endpoint available at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/geocoding/id.


#### Example request

This is a request for Port-au-Prince, Haiti, which has ID `level05.26390023`

```
curl --location --request GET 'https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/geocode/id/level05.26390023' \
--header 'Content-Type: text/plain'
'
```

### Response

The response is an  `GeocodePlace` object, which you can see at https://reca-v1-app-pfvsg.ondigitalocean.app/rest/vizz/docs#/geocode/calc_api_vizz_ninja__api_geocode_place.

The response has the following properties:

| Property | Type | Description | Notes |
| -------- | ---- | ----------- |------ |
| `name` | string | Location name | | 
| `id` | string | An ID for the location, taken from OpenStreetMap | | 
| `scale`	| string | Geographic scale (e.g. city, province, country) | Currently unused |
| `country` | string | Country name | |
| `country_id` | string | 3-letter country ISO3 code | | 
| `admin1` | string | Admin 1 name | Currently unused | 
| `admin1_id` | string | Admin 1 code | Currently unused |
| `admin2` | string | Admin 1 name | Currently unused | 
| `admin2_id` | string | Admin 1 code | Currently unused |
| `poly` | List[ | Lat-lon coordinates with the form `[[lon1, lat1], [lon2, lat2], ... [lonN, latN]]` | | 
| `bbox` | string | Lat-lon coordinates of a bounding box for the location, with the form `[lon_min, lat_min, lon_max, lat_max]` | |


## Working on the code

The repository is a bit of a mess. We started building the tool without a deep understanding of API design, or how to separate the calculations from the job management overhead. Some things we did ok, a lots need refactoring, some would benefit from a total rewrite by someone with more experience.

In this section I'll go over some of the details of the configuration and the structure of the codebase.

### Configuration

There are a few key configuration files that affect how the tool runs.

#### .env

The .env file in the project root sets variables relevant to the machine you are running on. A template for the file is in the file `env_template`.

The first time you run the container locally you will need to copy `env_template` to `.env`. After you provide a value to `MAPTILER_KEY` variable it should run with the other default settings.

Running on the cloud will require you to provide these values to the cloud platform (which varies by platform), and they will likely need modifying for the service you use.

- `SECRET_KEY`: The Django secret key. Part of the Django's security. This should never be published in a public location. It can be set to anything when running on your local machine, and should be a long string of random characters.
- `DEBUG`: Activate debug mode which gives helpful messages when things go wrong. It's a security risk, so turn this off before deployment.
- `ALLOWED_HOSTS`: IP addresses that are permitted to connect to the running Django app. The default value is 0.0.0.0, which allows anything to connect. This must be changed during cloud deployment using details from the platform you're deploying on.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`: These are parameters for connecting to the postgres database. No need to change them when running locally, but they will need to be set according to the cloud architecture when running in a hosted environment. Alternately provide a `POSTGRES_URL` environment variable with the full database connection string.
- `REDIS_URL`: Address of the Redis database to use as a job queue.
- `GEOCODE_URL`: If you're using a self-hosted geocoding container, such as OSMNames, its address.
- `MAPTILER_KEY`: If you're using the Maptiler geocoding service (recommended), your access key. Do not publish this. Set up an account and get your key from the [Maptiler Cloud API](https://docs.maptiler.com/cloud/api).
- `CELERY_BROKER_URL`: Address of the Celery Broker.
- `CELERY_RESULT_BACKEND`: Currently not used.

### climada_calc-config.yml

This file is a bit of a mess, and contains a lot of unused or half-implemented variables.

Some of the more important ones are:
- `geocoder`: one of 'maptiler', 'osmnames', 'nominatim_web'.
   - **maptiler**: this is the recommended option, and has been tested and works reliably. When chosen, geocoding queries are directed to the Maptiler API service, returning location data. To use this you need get a Maptiler key – see the setup instructions above – and set the `MAPTILER_KEY` environment variable. The Maptiler free tier limits you to 100k queries per month, which is more than enough for development purposes
   - **osmnames**: this uses the OpenStreetMap OSMNames geocoding service which is downloaded and hosted in a container locally. You will need to build the service from the docker-compose file at `docker_files/docker-compose-local_geocoding.yml`. From experience, the service is not always reliable at understanding the location you're looking for, which is why I implemented the Maptiler service. It has not been tested with the changes made to the repository in the last few months, so may fail unexpectedly.
   - **nomiatim_web**: this provides access to a web-hosted version of the OSMNames geocoding service. There is no need to host a geocoder locally, but it has the same accuracy issues as the osmnames service. It has not been tested with the changes made to the repository in the last few months, so may fail unexpectedly.
- `defaults`: sets a number of the default units and scenarios that the tool will use when nothing is provided. This isn't used much, because I've been writing most API methods to fail when they don't have this information.
- `database_mode`: one of 'off' 'read' 'create' 'update' 'fail_missing':
   - **off**: Don't use a results database at all. On receiving a request submit a Celery job and wait it to finish before returning. Currently not working.
   - **read**: Treat the results database as read-only. Results are not already stored in the database will set off a calculation but won't be saved. Designed for use with a database of precalculated results that will not be expanded.
   - **create**: If a result is already present in the database, use it. Otherwise set off a calculation to be added to the database on completion. Good for development use. Designed for use with a database that stores all its results and discards the least frequently used ones to save space (not yet implemented).
   - **update**: All requests set off a new calculation, regardless of whether results are in the database or not. Existing results are overwritten. Designed to allow administrators to recalculate parts of the database after updates to data or methods.
   - **fail_missing**: Treat the results database as read-only. Jobs will fail if results pre-calculated results are not already stored. Currently used in the cloud-hosted service on Digital Ocean.