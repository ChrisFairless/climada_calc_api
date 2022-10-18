from ninja import Schema
from typing import List
import calc_api.vizz.schemas as schemas
from calc_api.vizz import enums


# Generated text
# ==============

class TextVariable(Schema):
    key: str
    value: str
    units: str = None


class GeneratedText(Schema):
    template: str
    values: List[TextVariable]


# Timeline / Impact over time
# ===========================

class TimelineWidgetRequest(schemas.AnalysisSchema):
    hazard_type: str
    hazard_rp: str
    impact_type: str
    exposure_type: str = None
    units_hazard: str = None
    units_exposure: str = None
    units_warming: str = None


class TimelineWidgetData(Schema):
    text: List[GeneratedText]
    chart: schemas.Timeline


class TimelineWidgetResponse(Schema):
    data: TimelineWidgetData
    metadata: schemas.TimelineMetadata


class TimelineWidgetJobSchema(schemas.JobSchema):
    response: TimelineWidgetResponse = None
    # response: dict = None  # Trying this because I can't serialise the TimelineWidgetResponse >:(


# CostBenefit
# ===========

class CostBenefitWidgetRequest(schemas.AnalysisSchema):
    hazard_type: str
    impact_type: str
    measure_ids: List[int] = None
    units_currency: str = None
    units_hazard: str = None
    units_exposure: str = None
    units_warming: str = None


class CostBenefitWidgetData(Schema):
    text: List[GeneratedText]
    chart: schemas.CostBenefit


class CostBenefitWidgetResponse(Schema):
    data: CostBenefitWidgetData
    metadata: schemas.CostBenefitMetadata


class CostBenefitWidgetJobSchema(schemas.JobSchema):
    response: CostBenefitWidgetResponse = None


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
    hazard_type: str


class SocialVulnerabilityWidgetData(Schema):
    text: List[GeneratedText]
    chart: schemas.ExposureBreakdown = None


class SocialVulnerabilityWidgetResponse(Schema):
    data: SocialVulnerabilityWidgetData
    metadata: dict


class SocialVulnerabilityWidgetJobSchema(schemas.JobSchema):
    response: SocialVulnerabilityWidgetResponse = None
