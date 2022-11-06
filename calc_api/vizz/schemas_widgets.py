from ninja import Schema
from typing import List, Union

import calc_api.vizz.schemas as schemas
from calc_api.vizz import enums
from calc_api.vizz.util import get_options
from calc_api.config import ClimadaCalcApiConfig


# Generated text
# ==============

class TextVariable(schemas.ResponseSchema):
    key: str
    value: Union[float, str]
    units: str = None

    def convert_units(self, units_dict):
        if self.units:
            schemas.ResponseSchema.convert_units(self, units_dict)


class GeneratedText(schemas.ResponseSchema):
    template: str
    values: List[TextVariable]


# Timeline / Impact over time
# ===========================

class TimelineWidgetRequest(schemas.ScenarioSchema):
    hazard_type: str
    hazard_rp: str
    impact_type: str
    exposure_type: str = None
    units_hazard: str = None
    units_exposure: str = None
    units_warming: str = None


class TimelineWidgetData(schemas.ResponseSchema):
    text: List[GeneratedText]
    chart: schemas.Timeline


class TimelineWidgetResponse(schemas.ResponseSchema):
    data: TimelineWidgetData
    metadata: schemas.TimelineMetadata


class TimelineWidgetJobSchema(schemas.JobSchema):
    response: TimelineWidgetResponse = None
    # response: dict = None  # Trying this because I can't serialise the TimelineWidgetResponse >:(


# CostBenefit
# ===========

class CostBenefitWidgetRequest(schemas.ScenarioSchema):
    hazard_type: str
    impact_type: str
    measure_ids: List[int] = None
    units_currency: str = None
    units_hazard: str = None
    units_exposure: str = None
    units_warming: str = None


class CostBenefitWidgetData(schemas.ResponseSchema):
    text: List[GeneratedText]
    chart: schemas.CostBenefit


class CostBenefitWidgetResponse(schemas.ResponseSchema):
    data: CostBenefitWidgetData
    metadata: schemas.CostBenefitMetadata


class CostBenefitWidgetJobSchema(schemas.JobSchema):
    response: CostBenefitWidgetResponse = None


# Biodiversity
# ============

class BiodiversityWidgetRequest(schemas.PlaceSchema):
    hazard_type: str


class BiodiversityWidgetData(schemas.ResponseSchema):
    text: List[GeneratedText]
    chart: schemas.ExposureBreakdown = None


class BiodiversityWidgetResponse(schemas.ResponseSchema):
    data: BiodiversityWidgetData
    metadata: dict


class BiodiversityWidgetJobSchema(schemas.JobSchema):
    response: BiodiversityWidgetResponse = None


# Population breakdown
# ====================

class SocialVulnerabilityWidgetRequest(schemas.PlaceSchema):
    hazard_type: str


class SocialVulnerabilityWidgetData(schemas.ResponseSchema):
    text: List[GeneratedText]
    chart: schemas.ExposureBreakdown = None


class SocialVulnerabilityWidgetResponse(schemas.ResponseSchema):
    data: SocialVulnerabilityWidgetData
    metadata: dict


class SocialVulnerabilityWidgetJobSchema(schemas.JobSchema):
    response: SocialVulnerabilityWidgetResponse = None
