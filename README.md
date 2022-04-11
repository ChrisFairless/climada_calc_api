# Climada Calculations API

This is a work in progress. This first version only has the 'test' endpoints which provide precalculated dummy data in response to every request.

This is the Heroku test version. It's a mess still.

## Install and run

You will need Docker installed on your machine and about 3 GB of space - right now the project is big.

Clone this git repository to a local directory.

Then run `docker-compose up --build` to launch the application. The first time this runs it will take a while. The application will (automatically)
- download the relevant images. This is just over 4 GB because I've not worked to shrink down the containerised version of CLIMADA yet
- create CLIMADA test files. This involves contacting the CLIMADA Data API, downloading files, and running a script to process the data
- download and extract the OpenStreetMap places data

The Django web server expects to mount a volume located on the host machine at `./static/sample_data/`. The first time the web container is run it will download some, calculate and store test datasets here. If you don't want these to persist after running, remove the volume from the `docker-compose.yml` file. If you want to mount a different directory, edit the `docker-compose.yml` file.


## Usage

All endpoints are available through [localhost:8000/rest/vtest/](localhost:8000/rest/vtest/) (assuming you're running on your local machine). At the moment only these test endpoints are functioning (and even then, not all of them). They all return the same sample datasets for Haiti, regardless of the query or job details submitted.

Documentation is generated at [127.0.0.1:8000/rest/vtest/docs/](localhost:8000/rest/vtest/docs)
(assuming you're running on a local host). This is the best way to find out what's available to you!

The API is asynchronous, meaning that endpoints that get climate data have POST methods to submit a job, and GET methods to access the job status and results.

See the documentation for details about the relevant schema. An endpoint's POST method will take multiple parameters in its body that define a piece of desired data. The endpoint returns a job schema, including status information, as well as the URL to poll for results. The GET method, along with the job ID as a query parameter, will return the job's status. When the job is complete, it will also contain a response parameter, formatted according the that endpoint's response schema. Often this will include a URL that will be used to download relevant images or files.

In particular
- the `/rest/vtest/map/hazard/climate`, `/rest/vtest/map/exposure`, `/rest/vtest/map/impact/climate` POST endpoints will return sample job submission data for mapping different elements of risk (always for Haiti - change the country by editing the file `scripts/generate_sample_data.py` in the repository and deleting any existing outputs in the mounted volume). The GET endpoints will return sample completed job information, including a URL to access the generated image. 
- the `rest/vtest/geocoding/autocomplete` endpoint returns location suggestions for a user-entered string.

Note: since this is a test endpoint, it will ignore all the parameters you pass to it. That is, it requires them to be set, but makes no difference to the returned values.


## Structure

This test version of the project uses four containers:
- **web:** A Django web tool running a RESTful API using ninja. On startup it checks for the existence of test data and downloads and creates it when it doesn't exist. Mount a volume to `/climada_calc_api/static/sample_data` (by default this is set up as `./static/sample_data` on your local machine) to persist this data.
- **celery:** A containerised task/queue manager to manage requests. The test requests don't actually use it.
- **redis:** A redis database. This handles all the storage, cacheing and works as Celery's broker. In future these jobs will be split amongst other services.
- **geocoding_api:** A containerised version of the [OSMNames geocoder](https://hub.docker.com/r/klokantech/osmnames-sphinxsearch). It uses the defaults settings which keep the container small(ish) and limited to 100k places.
