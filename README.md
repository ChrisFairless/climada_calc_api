# Climada Calculations API

This is a work in progress.

Only a few endpoints are working right now, and depending on the state of refactoring, only a few of those are working.

You can use:
- the test endpoints, which return precalculated dummy data for each request
- the web tool's timeline widget endpoint, which returns all the information to describe risk over time in the web tool

This branch is for running on your local machine or deploying to Heroku. It's a work in progress.

## Install and run locally

### Quick start

**Note: these instructions are usually out of date - contact me if you're installing this locally**

You will need Docker installed on your machine and about 10 GB of space ... we will shrink the container sizes at a later date.

1. Clone this git repository to a local directory.

2. Run `cp env_template .env` to create an environment file. The default values here can be used to spin up a development server, but **do not use these in production**.

3. Run `docker-compose up --build` to launch the application. The first time this runs it will take a while. The application will (automatically)
    - download the relevant images. This is just over 4 GB because I've not shrunk down the containerised version of CLIMADA yet
    - create CLIMADA test files. This involves contacting the CLIMADA Data API, downloading files, and running a script to process the data
    - download and extract the OSMNames geocoding data (the small version, 8MB download, 300 MB when indexed)
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
The same container as `web` above, but running as a worker. It takes tasks from Celery's queue and executes them. The `redis` container acts as a broker for the tasks.

To scale the application, spin up more instances of this worker.

#### celery_flower
A job management interface for Celery. Access it on [0.0.0.0:5000](http://0.0.0.0:5000) to view the job queues and check things are working. You can drop this container without affecting functionality.

#### db
A PostgreSQL database. Used for storing any tabular information relevant to the tool and for cacheing selected results.

#### redis
A redis database. This works as Celery's broker and results storage.


### Cloud structure

Deployment to the cloud (currently: Heroku) uses the same structure as the above. The `web` and `celery` components are initialised as Heroku dynos using the relevant Docker image, and the `redis` and `db` components are Heroku's provisioned Redis and PostegreSQL databases. The `celery_flower` container is currently excluded from cloud deployment.

## Usage

This is an asynchronous calculations API. That means most endpoints need the user to make at least two calls. First to submit the job, and second to get the results a short time later.

Jobs are submitted via an endpoint's POST method, and the API returns a job ID, along with other metadata. The GET method will return information about the job's status until results are available, at which point the information will include the results. Users can keep polling the GET endpoint until the job is complete.

### Test endpoints 

The API's 'test' endpoints provide pre-calculated results. They're designed to give the user information about query structure and examples of the API's responses. Each test endpoint always gives the same response (usually tropical cyclone data from Haiti) regardless of the query.

The test endpoints are available through [0.0.0.0:8000/rest/vtest/](0.0.0.0:8000/rest/vtest/) (assuming you're running on your local machine).

Documentation is generated at [127.0.0.1:8000/rest/vtest/docs/](localhost:8000/rest/vtest/docs)
(assuming you're running on a local host). This is the best way to find out what's available to you and to test out the functionality!

An endpoint's POST method takes multiple parameters in its body which together describe the data the user wants. See the above documentation for the schema involved. The POST endpoint returns a job schema, including status information, as well as the URL to poll for results.

An endpoint's GET method only needs the job ID as a query parameter and returns information on the job's status. When the job is complete it also contains a `response` propert, formatted according the that endpoint's response schema. Often this will include a URL to download relevant images or files.

### Example request:

To 'submit' a tropical cyclone hazard map job for Haiti (the response to all hazard map requests!) you can run the following on the command line (note the dummy data in the request) or use the interactive 'Try it out' features in the documentation at [127.0.0.1:8000/rest/vtest/docs/](localhost:8000/rest/vtest/docs).

```
curl -X 'POST' \
  'http://0.0.0.0:8000/rest/vtest/map/hazard/climate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "scenario_name": "string",
  "scenario_climate": "string",
  "scenario_growth": "string",
  "scenario_year": 0,
  "location_name": "string",
  "location_scale": "string",
  "location_code": "string",
  "location_poly": [
    0
  ],
  "aggregation_scale": "string",
  "aggregation_method": "string",
  "hazard_type": "tropical_cyclone",
  "hazard_rp": "string",
  "format": "tif",
  "units": "string"
}'
```

Then to view the result of a 'successful' job mapping hazard for Haiti, run the following, or give the 'Try it out' feature a valid UUID as a job ID (the previous request should have returned one, or you can copy the example from following):

```
curl -X 'GET' \
  'http://0.0.0.0:8000/rest/vtest/map/hazard/climate?job_id=3fa85f64-5717-4562-b3fc-2c963f66afa6' \
  -H 'accept: application/json'
```
The response should contain job information, the data you need to generate a hazard map, and the location of a hazard map in the `response_uri` parameter, namely [http://0.0.0.0:8000/rest/vtest/img/map_haz_rp.tif](http://0.0.0.0:8000/rest/vtest/img/map_haz_rp.tif).

### Notes:
- The GET methods on the test endpoints are in a slightly different format to the other endpoints, which now take the job ID in the URL rather than the request body.
- The `/rest/vtest/map/hazard/climate`, `/rest/vtest/map/exposure`, `/rest/vtest/map/impact/climate` POST endpoints will return sample job submission data for mapping different elements of risk (always for Haiti - change the country by editing the file `scripts/generate_sample_data.py` in the repository and deleting any existing outputs in the mounted volume). The GET endpoints will return sample completed job information, including a URL to access the generated image. 
- The `rest/vtest/geocoding/autocomplete` endpoint returns location suggestions for a user-entered string.


## Vizz endpoints

The endpoints used by the forthcoming RECA app are available at [0.0.0.0:8000/rest/vizz/](0.0.0.0:8000/rest/vizz/).

On this branch only a couple are working, and then not always reliably.

These endpoints use the full job queuing functionality, and work (right now) for any country. Some bits of functionality don't work very well, and the accepted parameters aren't documented yet, so for now let's just show it in action with a demonstration.

This is a request to submit a job to construct a bar chart breaking down future climate risk from tropical cyclones on economic assets in Haiti.

If you're using the Swagger documentation, here is an example body you can POST:
```
{
    "hazard_type": "tropical_cyclone",
    "hazard_rp": "50",
    "exposure_type": "economic_assets",
    "impact_type": "economic_impact",
    "scenario_name": "ssp585",
    "scenario_year": 2080,
    "location_name": "Haiti",
    "location_scale": "country",
    "units_response": "dollars",
    "units_warming": "celsius"
}
```
and here it is as a Curl request:
```
curl --location --request POST 'http://0.0.0.0:8000/rest/vizz/widgets/risk-timeline' \
--header 'Content-Type: application/json' \
--data-raw '{
    "hazard_type": "tropical_cyclone",
    "hazard_rp": "50",
    "exposure_type": "economic_assets",
    "impact_type": "economic_impact",
    "scenario_name": "ssp585",
    "scenario_year": 2080,
    "location_name": "Haiti",
    "location_scale": "country",
    "units_response": "dollars",
    "units_warming": "celsius"
}'
```
This should return information including a job ID and the URL to poll for results.

The setup isn't parallelised yet, so it takes much longer than it should (how to do this depends on the platform it's deployed on, sadly).

Given your job ID, you can poll the results by navigating to the URL provided in the response, something like,
```
rest/vizz/widgets/risk-timeline/2d81de97-6ef9-41c5-84cc-e0df0bbaf6a6
```
or with Curl (replace the UUID in this example with the one provided when you submitted the job:
```
curl -X 'GET' \
  'http://0.0.0.0:8000/rest/vizz/widgets/risk-timeline/2d81de97-6ef9-41c5-84cc-e0df0bbaf6a6' \
  -H 'accept: application/json'
```
or by using the Swagger documentation 'Try it out' for the POST method with the job ID.

