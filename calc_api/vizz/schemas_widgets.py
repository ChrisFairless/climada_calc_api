from ninja import Schema
from typing import List
import calc_api.vizz.schemas as schemas
from calc_api.vizz import enums


# Timeline / Impact over time
# ===========================


class TextVariable(Schema):
    key: str
    value: str
    units: str = None


class GeneratedText(Schema):
    template: str
    values: List[TextVariable]


# TODO add polygon functionality?
class TimelineWidgetRequest(schemas.AnalysisSchema):
    hazard_type: str
    hazard_rp: int
    exposure_type: str
    impact_type: str
    units_hazard: str = None
    units_exposure: str = None
    units_warming: str = None

    def standardise(self):
        super().standardise()
        if not self.exposure_type:
            self.exposure_type = enums.exposure_type_from_impact_type(self.impact_type)


class TimelineWidgetData(Schema):
    text: List[GeneratedText]
    chart: schemas.Timeline


class TimelineWidgetResponse(Schema):
    data: TimelineWidgetData
    metadata: schemas.TimelineMetadata


class TimelineWidgetJobSchema(schemas.JobSchema):
    response: TimelineWidgetResponse = None
    # response: dict = None  # Trying this because I can't serialise the TimelineWidgetResponse >:(

# Biodiversity
# ============

class BiodiversityWidgetRequest(schemas.PlaceSchema):
    units_area: str = None


class BiodiversityWidgetData(Schema):
    text: List[GeneratedText]


class BiodiversityWidgetResponse(Schema):
    data: BiodiversityWidgetData
    metadata: dict


class BiodiversityWidgetJobSchema(schemas.JobSchema):
    response: BiodiversityWidgetResponse = None


# Population breakdown
# ====================

class SocialVulnerabilityWidgetRequest(schemas.PlaceSchema):
    units_area: str = None


class SocialVulnerabilityWidgetData(Schema):
    text: List[GeneratedText]
    chart: schemas.ExposureBreakdown


class SocialVulnerabilityWidgetResponse(Schema):
    data: SocialVulnerabilityWidgetData
    metadata: dict


class SocialVulnerabilityWidgetJobSchema(schemas.JobSchema):
    response: SocialVulnerabilityWidgetResponse = None

