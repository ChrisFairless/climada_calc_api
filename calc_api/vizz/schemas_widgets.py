from ninja import Schema
from typing import List
import calc_api.vizz.schemas as schemas


# Timeline / Impact over time
# ===========================


class TextVariable(Schema):
    key: str
    value: str
    unit: str = None


class GeneratedText(Schema):
    template: str
    values: List[TextVariable]


class TimelineWidgetRequest(Schema):
    hazard_type: str
    hazard_rp: int = None
    exposure_type: str = None
    scenario_name: str = None
    scenario_climate: str = None
    scenario_growth: str = None
    location_name: str = None
    location_id: str = None
    location_poly: str = None
    units_warming: str = None
    units_response: str = None


class TimelineWidgetData(Schema):
    text: List[GeneratedText]
    chart: schemas.Timeline


class TimelineWidgetResponse(Schema):
    data: TimelineWidgetData
    metadata: schemas.TimelineMetadata


class TimelineWidgetJobSchema(schemas.JobSchema):
    response: TimelineWidgetResponse = None


# Biodiversity
# ============

class BiodiversityWidgetRequest(Schema):
    location_name: str = None
    location_id: str = None
    location_poly: str = None
    area_units: str = None


class BiodiversityWidgetData(Schema):
    text: List[GeneratedText]


class BiodiversityWidgetResponse(Schema):
    data: BiodiversityWidgetData
    metadata: dict


class BiodiversityWidgetJobSchema(schemas.JobSchema):
    response: BiodiversityWidgetResponse = None


# Population breakdown
# ====================

class SocialVulnerabilityWidgetRequest(Schema):
    location_name: str = None
    location_id: str = None
    location_poly: str = None
    units_area: str = None


class SocialVulnerabilityWidgetData(Schema):
    text: List[GeneratedText]
    chart: schemas.ExposureBreakdown


class SocialVulnerabilityWidgetResponse(Schema):
    data: SocialVulnerabilityWidgetData
    metadata: dict


class SocialVulnerabilityWidgetJobSchema(schemas.JobSchema):
    response: SocialVulnerabilityWidgetResponse = None

