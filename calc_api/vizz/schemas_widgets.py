from ninja import Schema
from typing import List
import calc_api.vizz.schemas as schemas


# Timeline / Impact over time
# ===========================

class TimelineWidgetRequest(Schema):
    hazard_type: str
    exposure_type: str = None
    scenario_name: str = None
    scenario_rp: int = None
    location_name: str = None
    location_id: str = None
    location_poly: str = None
    units_warming: str = None
    units_response: str = None


class TimelineWidgetData(Schema):
    text: List[schemas.GeneratedText]
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
    text: List[schemas.GeneratedText]


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
    area_units: str = None


class SocialVulnerabilityWidgetData(Schema):
    text: List[schemas.GeneratedText]
    chart: schemas.ExposureBreakdown


class SocialVulnerabilityWidgetResponse(Schema):
    data: SocialVulnerabilityWidgetData
    metadata: dict


class SocialVulnerabilityWidgetJobSchema(schemas.JobSchema):
    response: SocialVulnerabilityWidgetResponse = None

