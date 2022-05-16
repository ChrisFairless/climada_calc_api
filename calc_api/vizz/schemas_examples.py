from millify import millify
import datetime as dt
import uuid
from pathlib import Path
import pandas as pd

from climada_calc.settings import STATIC_ROOT
import climada.util.coordinates as u_coord

from calc_api.vizz import models
from calc_api.vizz import schemas, schemas_widgets
from calc_api.calc_methods.colourmaps import Legend
from calc_api.calc_methods.colourmaps import PALETTE_HAZARD_COLORCET, PALETTE_EXPOSURE_COLORCET, PALETTE_IMPACT_COLORCET

SAMPLE_DIR = Path(STATIC_ROOT, "sample_data")


def make_dummy_job(request_schema, location_root, job_id=None):
    job_id = uuid.uuid4() if not job_id else job_id
    return models.Job(
        job_id=job_id,
        location=location_root + str(job_id),
        status="submitted",
        request={} if not request_schema else request_schema.__dict__,
        response=None,
        submitted_at=dt.datetime(2020, 1, 1),
        expires_at=dt.datetime(2020, 1, 3)
    )


def make_dummy_mapjobschema(
        lat_array,
        lon_array,
        values,
        palette,
        title,
        description,
        units,
        location,
        example_value,
        raster_uri,
        job_id=None
):
    job_id = uuid.uuid4() if not job_id else job_id
    legend = Legend(values, palette, n_cols=12, reverse=True)

    outdata = schemas.Map(
        items=[
            schemas.MapEntry(lat=lat, lon=lon, value=v, color=c)
            for lat, lon, v, c
            in zip(lat_array, lon_array, legend.values, legend.colors)
        ],
        legend=schemas.ColorbarLegend(
            title=title,
            units=units,
            value=example_value,
            items=[
                schemas.ColorbarLegendItem(band_min=lo, band_max=hi, color=col)
                for lo, hi, col in zip(legend.intervals[:-1], legend.intervals[1:], legend.colorscale)
            ]
        )
    )

    lat_res, lon_res = u_coord.get_resolution(lat_array, lon_array)
    if abs(abs(lat_res) - abs(lon_res)) > 0.001:
        raise ValueError("Mismatch in x and y resolutions: " + str(lon_res) + " vs " + str(lat_res))
    bounds = u_coord.latlon_bounds(lat_array, lon_array, buffer=lon_res)

    metadata = schemas.MapMetadata(
        description=description,
        file_uri=raster_uri,
        units=units,
        custom_fields={},
        bounding_box=list(bounds),
    )

    response = schemas.MapResponse(data=outdata, metadata=metadata)

    return schemas.MapJobSchema(
        job_id=job_id,
        location=location,
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        expires_at=dt.datetime(2020, 1, 3),
        runtime=86400,
        response=response,
        response_uri=raster_uri
    )



def make_dummy_mapjobschema_hazard(request, job_id=None):
    haz_path = Path(SAMPLE_DIR, "map_haz_rp.csv")
    df = pd.read_csv(haz_path)
    raster_path = Path("/rest", "vtest", "img", "map_haz_rp.tif")
    raster_uri = request.build_absolute_uri(raster_path)
    location = "/map/hazard/climate/" + str(job_id)
    return make_dummy_mapjobschema(
        lat_array=df['lat'],
        lon_array=df['lon'],
        values=df['intensity'],
        palette=PALETTE_HAZARD_COLORCET,
        title="Dummy hazard dataset",
        description="Test hazard climatology map",
        units="m/s",
        location=location,
        example_value="18.1",
        raster_uri=raster_uri,
        job_id=job_id
    )


def make_dummy_mapjobschema_exposure(request, job_id=None):
    exp_path = Path(SAMPLE_DIR, "map_exp.csv")
    df = pd.read_csv(exp_path)
    raster_path = Path("/rest", "vtest", "img", "map_exp.tif")
    raster_uri = request.build_absolute_uri(raster_path)
    location="/map/exposure?job_id=" + str(job_id)
    return make_dummy_mapjobschema(
        lat_array=df['lat'],
        lon_array=df['lon'],
        values=df['value'],
        palette=PALETTE_EXPOSURE_COLORCET,
        title="Dummy exposure dataset",
        description="Test population exposure map",
        units="people",
        location=location,
        example_value="121 k",
        raster_uri=raster_uri,
        job_id=job_id
    )

def make_dummy_mapjobschema_impact(request, job_id=None):
    exp_path = Path(SAMPLE_DIR, "map_imp_rp.csv")
    df = pd.read_csv(exp_path)
    raster_path = Path("/rest", "vtest", "img", "map_imp_rp.tif")
    raster_uri = request.build_absolute_uri(raster_path)
    location = "/map/impact/climate?job_id=" + str(job_id)
    return make_dummy_mapjobschema(
        lat_array=df['lat'],
        lon_array=df['lon'],
        values=df['value'],
        palette=PALETTE_IMPACT_COLORCET,
        title="Dummy impact dataset",
        description="Test impact/risk climatology map",
        units="people affected",
        location=location,
        example_value="121 k",
        raster_uri=raster_uri,
        job_id=job_id
    )


def make_dummy_exceedance(
    exceedance_path,
    title,
    description,
    intensity_units,
    example_value,
    location,
    job_id=None
):
    job_id=uuid.uuid4() if not job_id else job_id
    df = pd.read_csv(exceedance_path)
    curves = [
        schemas.ExceedanceCurve(
            items=[
                schemas.ExceedanceCurvePoint(
                    return_period=row['return_period'],
                    intensity=row['intensity']
                )
                for _, row in df.iterrows()
            ],
            scenario_name='Example data',
            slug='example_data'
        )
    ]
    outdata = schemas.ExceedanceCurveSet(
        items=curves,
        return_period_units='years',
        intensity_units=intensity_units,
        legend=schemas.CategoricalLegend(
            title=title,
            units=intensity_units,
            items=[
                schemas.CategoricalLegendItem(
                    label="Example data",
                    slug="example_data",
                    value=example_value
                )
            ]
        )
    )
    outmetadata = schemas.ExceedanceCurveMetadata(
        description=description
    )
    response = schemas.ExceedanceResponse(data=outdata, metadata=outmetadata)
    return schemas.ExceedanceJobSchema(
        job_id=job_id,
        location=location,
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        expires_at=dt.datetime(2020, 1, 3),
        runtime=86400,
        response=response,
        response_uri=None
    )


def make_dummy_exceedance_hazard(job_id=None):
    exceedance_path = Path(SAMPLE_DIR, "exceedance_haz.csv")
    return make_dummy_exceedance(
        exceedance_path=exceedance_path,
        title="Example hazard exceedance curve",
        description='Dummy data for a hazard exceedance curve',
        intensity_units='m/s',
        example_value='22.2',
        location="/exceedance/hazard?job_id=" + str(job_id),
        job_id=job_id
    )


def make_dummy_exceedance_impact(job_id=None):
    exceedance_path = Path(SAMPLE_DIR, "exceedance_imp.csv")
    return make_dummy_exceedance(
        exceedance_path=exceedance_path,
        title="Example impact exceedance curve",
        description='Dummy data for a risk/impact exceedance curve',
        intensity_units='people affected',
        example_value='121 k',
        location="/exceedance/impact?job_id=" + str(job_id),
        job_id=job_id
    )


def make_dummy_exposure_breakdown(job_id=None):
    job_id = uuid.uuid4() if not job_id else job_id
    out_response = schemas.ExposureBreakdownResponse(
        data=schemas.ExposureBreakdown(
            items=[
                schemas.ExposureBreakdownBar(
                    label="Example breakdown",
                    category_labels=[str(i) for i in range(1, 11)],
                    values=[0.15, 0.2, 0.2, 0.15, 0.1, 0.5, 0.5, 0.5, 0.25, 0.25]
                )
            ],
            legend=schemas.CategoricalLegend(
                title="Vulnerability distributions compared to the national average",
                units="proportion",
                items=[schemas.CategoricalLegendItem(label=str(i), slug=str(i), value="0.25") for i in range(1, 11)]
            )
        ),
        metadata={
            'description': 'Sample exposure breakdown'
        }
    )
    return schemas.ExposureBreakdownJob(
        job_id=job_id,
        location="/breakdown/exposure?job_id=" + str(id),
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        expires_at=dt.datetime(2020, 1, 3),
        runtime=86400,
        response=out_response,
        response_uri=None
    )


def make_dummy_timeline(
        response_units,
        scale,
        units_temperature='degrees Fahrenheit',
        units_response='people affected',
        description="Dummy data from tests API",
        location_root="/timeline/impact?job_id=",
        job_id=None
    ):
    job_id = uuid.uuid4() if not job_id else job_id
    timeline = schemas.Timeline(
        items=[
            schemas.TimelineBar(
                yearLabel=str(2020 + 20 * i),
                yearValue=2020 + 20 * i,
                temperature=1 + 0.25 * i,
                current_climate=scale,
                population_growth=scale/5 * i,
                climate_change=scale/10 * i
            )
            for i in range(5)
        ],
        legend=schemas.CategoricalLegend(
            title=response_units + " (example data)",
            units=response_units,
            items=[
                schemas.CategoricalLegendItem(
                    label="Current climate",
                    slug="current_climate",
                    value=millify(scale, precision=1)),
                schemas.CategoricalLegendItem(
                    label="Population change",
                    slug="population_change",
                    value=millify(scale, precision=1)),
                schemas.CategoricalLegendItem(
                    label="Climate change",
                    slug="climate_change",
                    value=millify(scale, precision=1))
            ],
        ),
        units_temperature=units_temperature,
        units_response=units_response
    )

    metadata = schemas.TimelineMetadata(
        description=description
    )

    out_response = schemas.TimelineResponse(data=timeline, metadata=metadata)

    return schemas.TimelineJobSchema(
        job_id=job_id,
        location=location_root + str(job_id),
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        expires_at=dt.datetime(2020, 1, 3),
        runtime=86400,
        response=out_response,
        response_uri=None
    )


def make_dummy_timelinewidget_risk(job_id=None):
    # Set variables, in case we want to generalise this later
    job_id = uuid.uuid4() if not job_id else job_id
    description = "Dummy timeline data for tests API"
    location_root = "/timeline/impact?job_id="
    response_units = "people"
    scale = 1000000
    text_template = "London is a city with about {{current_population}}. In the current climate, {{affected_qualifier}} {{current_affected}} may be exposed to extreme heat events each year. The number of people affected is projected to grow by about {{affected_growth}} to {{future_affected}} by {{future_year}} under the {{scenario_name}} scenario. This change is {{reason}}."
    values = [
        schemas_widgets.TextVariable(key="current_population", value=8, unit="million people"),
        schemas_widgets.TextVariable(key="affected_qualifier", value="all", unit=None),
        schemas_widgets.TextVariable(key="current_affected", value=8, unit="million people"),
        schemas_widgets.TextVariable(key="affected_growth", value=12, unit="%"),
        schemas_widgets.TextVariable(key="future_affected", value=8.8, unit="million"),
        schemas_widgets.TextVariable(key="future_year", value=2080, unit=None),
        schemas_widgets.TextVariable(key="scenario_name", value="moderate_action", unit=None),
        schemas_widgets.TextVariable(key="reason", value="entirely due to population growth", unit=None)
    ]
    timeline_job = make_dummy_timeline(
        response_units=response_units,
        scale=scale,
        units_temperature='degrees Fahrenheit',
        units_response='people affected',
        description='Dummy data for timeline widget',
        location_root="/timeline/impact?job_id="
    )
    timeline = timeline_job.response.data
    widget = schemas_widgets.TimelineWidgetData(
        text=[schemas_widgets.GeneratedText(template=text_template, values=values)],
        chart=timeline
    )
    metadata = schemas.TimelineMetadata(
        description=description
    )

    out_response = schemas_widgets.TimelineWidgetResponse(data=widget, metadata=metadata)
    return schemas_widgets.TimelineWidgetJobSchema(
        job_id=job_id,
        location=location_root + str(id),
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        expires_at=dt.datetime(2020, 1, 3),
        runtime=86400,
        response=out_response,
        response_uri=None
    )


def make_dummy_biodiversitywidget(job_id=None):
    job_id = uuid.uuid4() if not job_id else job_id
    out_data = schemas_widgets.BiodiversityWidgetData(
        text=[
            schemas_widgets.GeneratedText(
                template="As a city, {{location}} is densely populated. Its green spaces are hugely important to its biodiversity and community wellbeing. {{prop_protected_land}} of the land and {{prop_protected_green}} of the area classified as 'green' is protected in some way.",
                values=[
                    schemas_widgets.TextVariable(key="location", value="Cancún", unit=None),
                    schemas_widgets.TextVariable(key="prop_protected_land", value="1", unit="%"),
                    schemas_widgets.TextVariable(key="prop_protected_green", value="15", unit="%"),
                ]
            ),
            schemas_widgets.GeneratedText(
                template="{{location}} is also home to endangered species with very limited habitats, including {{endangered_species_1}} {{endangered_species_2}} (click here for the full list), and has {{biodiverse_area}} of land classified as 'highly biodiverse'.",
                values=[
                    schemas_widgets.TextVariable(key="location", value="Cancún", unit=None),
                    schemas_widgets.TextVariable(key="endangered_species_1", value="XXX", unit=None),
                    schemas_widgets.TextVariable(key="endangered_species_1", value="and YYY", unit=None),
                    schemas_widgets.TextVariable(key="biodiverse_area", value="ZZZ", unit="km2"),
                ]
            ),
            schemas_widgets.GeneratedText(
                template="The low amounts of green space mean that it's critical to preserve and expand them to support local species, mitigate heat and boost community wellbeing. {{location}}’s coastline has {{coastline_feature_1}} {{coastline_feature_2}}, {{coastline_conjunction}} rich biodiversity and protect the area from coastal hazards.",
                values=[
                    schemas_widgets.TextVariable(key="location", value="Cancún", unit=None),
                    schemas_widgets.TextVariable(key="coastline_feature_1", value="mangroves", unit=None),
                    schemas_widgets.TextVariable(key="coastline_feature_1", value="and coral reefs", unit=None),
                    schemas_widgets.TextVariable(key="coastline_conjunction", value="both of which have", unit=None),
                ]
            )
        ]
    )

    out_response = schemas_widgets.BiodiversityWidgetResponse(
        data=out_data,
        metadata={
            'description': 'Dummy biodiversity text'
        }
    )

    return schemas_widgets.BiodiversityWidgetJobSchema(
        job_id=job_id,
        location="/widgets/biodiversity?job_id=" + str(id),
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        expires_at=dt.datetime(2020, 1, 3),
        runtime=86400,
        response=out_response,
        response_uri=None
    )


def make_dummy_socialvulnerability_widget(job_id=None):
    job_id = uuid.uuid4() if not job_id else job_id
    out_data = schemas_widgets.SocialVulnerabilityWidgetData(
        text=[
            schemas_widgets.GeneratedText(
                template="Not everyone experiences the effects of climate change equally. Societies are structured giving some groups disproportionate access to resources which in turn affects their vulnerability to extreme events and ability to adapt.",
                values=[]
            ),
            schemas_widgets.GeneratedText(
                template="Extreme heat has disproportionate effects on the elderly, the disabled, people under the age of 5, outdoor labourers, people in uncooled workplaces, and people unable to cool their homes. Adaptation measures should be targeted accordingly.",
                values=[]
            ),
            schemas_widgets.GeneratedText(
                template="The population of {{location}} is projected to grow larger and older by {{future_year}}, both of which enhance the risks it faces. Today about {{current_elderly_percentage}} of London is aged over 70, and this is projected to grow to {{future_elderly_percentage}} by 2080 in the moderate action scenario.",
                values=[
                    schemas_widgets.TextVariable(key="location", value="London", unit=None),
                    schemas_widgets.TextVariable(key="future_year", value="2080", unit=None),
                    schemas_widgets.TextVariable(key="current_elderly_percentage", value="7", unit="%"),
                    schemas_widgets.TextVariable(key="future_elderly_percentage", value="13", unit="%"),
                ]
            ),
            schemas_widgets.GeneratedText(
                template="Communities in {{location}} are on average more wealthy than the whole of {{country}}. {{location}} has more particularly rich communities than other regions but also more particularly poor communities than other regions of Great Britain, meaning that adaptation measures must be targeted carefully in order to maximise their benefits.",
                values=[
                    schemas_widgets.TextVariable(key="location", value="London", unit=None),
                    schemas_widgets.TextVariable(key="country", value="Great Britain", unit=None),
                ]
            )
        ],
        chart=make_dummy_exposure_breakdown().response.data
    )

    out_response = schemas_widgets.SocialVulnerabilityWidgetResponse(
        data=out_data,
        metadata={
            'description': 'Dummy social vulnerability widget data'
        }
    )

    return schemas_widgets.SocialVulnerabilityWidgetJobSchema(
        job_id=job_id,
        location="/widgets/social-vulnerabilityy?job_id=" + str(id),
        status="completed",
        request={},
        submitted_at=dt.datetime(2020, 1, 1),
        completed_at=dt.datetime(2020, 1, 2),
        expires_at=dt.datetime(2020, 1, 3),
        runtime=86400,
        response=out_response,
        response_uri=None
    )