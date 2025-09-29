"""Pydantic models for request and response schemas."""

from typing import List, Optional
import re

from pydantic import BaseModel, Field, field_validator


# Base models for common data structures
class StateInfo(BaseModel):
    """State information model."""

    state_text: str = Field(..., description="State name (e.g., 'KARNATAKA')")
    state_id: str = Field(..., description="Internal state ID")


class CommissionInfo(BaseModel):
    """Commission information model."""

    commission_text: str = Field(..., description="Commission name")
    commission_id: str = Field(..., description="Internal commission ID")
    state_id: str = Field(..., description="Parent state ID")


# Request models
class CaseSearchRequest(BaseModel):
    """Base model for case search requests."""

    state: str = Field(..., description="State name",
                       min_length=1, examples=["KARNATAKA"])
    commission: str = Field(..., description="Commission name", min_length=1,
                            examples=["District Consumer Disputes Redressal Commission"])
    search_value: str = Field(..., description="Search term", min_length=1,
                              examples=["CC/123/2023"])
    date_from: Optional[str] = Field(
        None, description="Start date filter in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2023-01-01"])
    date_to: Optional[str] = Field(
        None, description="End date filter in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2023-12-31"])
    page: int = Field(
        default=1, description="Page number (1-based)", ge=1, examples=[1])
    per_page: int = Field(
        default=20, description="Items per page", ge=1, le=100, examples=[20])

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format."""
        if v is not None:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate that date_to is not before date_from."""
        if v and info.data.get("date_from"):
            # Simple string comparison works for YYYY-MM-DD format
            if v < info.data["date_from"]:
                raise ValueError(
                    "date_to must be greater than or equal to date_from")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "state": "KARNATAKA",
                "commission": "District Consumer Disputes Redressal Commission",
                "search_value": "CC/123/2023",
                "date_from": "2023-01-01",
                "date_to": "2023-12-31",
                "page": 1,
                "per_page": 20
            }
        }


class CaseByNumberRequest(CaseSearchRequest):
    """Request model for searching cases by case number."""

    class Config:
        json_schema_extra = {
            "example": {
                "state": "KARNATAKA",
                "commission": "District Consumer Disputes Redressal Commission",
                "search_value": "CC/123/2023",
                "date_from": "2023-01-01",
                "date_to": "2023-12-31",
                "page": 1,
                "per_page": 20
            }
        }


class CaseByComplainantRequest(CaseSearchRequest):
    """Request model for searching cases by complainant."""

    class Config:
        json_schema_extra = {
            "example": {
                "state": "KARNATAKA",
                "commission": "District Consumer Disputes Redressal Commission",
                "search_value": "John Doe",
                "date_from": "2023-01-01",
                "date_to": "2023-12-31",
                "page": 1,
                "per_page": 20
            }
        }


class CaseByRespondentRequest(CaseSearchRequest):
    """Request model for searching cases by respondent."""

    class Config:
        json_schema_extra = {
            "example": {
                "state": "KARNATAKA",
                "commission": "District Consumer Disputes Redressal Commission",
                "search_value": "XYZ Corporation",
                "date_from": "2023-01-01",
                "date_to": "2023-12-31",
                "page": 1,
                "per_page": 20
            }
        }


class CaseByComplainantAdvocateRequest(CaseSearchRequest):
    """Request model for searching cases by complainant advocate."""

    class Config:
        json_schema_extra = {
            "example": {
                "state": "KARNATAKA",
                "commission": "District Consumer Disputes Redressal Commission",
                "search_value": "Advocate Smith",
                "date_from": "2023-01-01",
                "date_to": "2023-12-31",
                "page": 1,
                "per_page": 20
            }
        }


class CaseByRespondentAdvocateRequest(CaseSearchRequest):
    """Request model for searching cases by respondent advocate."""

    class Config:
        json_schema_extra = {
            "example": {
                "state": "KARNATAKA",
                "commission": "District Consumer Disputes Redressal Commission",
                "search_value": "Advocate Johnson",
                "date_from": "2023-01-01",
                "date_to": "2023-12-31",
                "page": 1,
                "per_page": 20
            }
        }


class CaseByIndustryTypeRequest(CaseSearchRequest):
    """Request model for searching cases by industry type."""

    class Config:
        json_schema_extra = {
            "example": {
                "state": "KARNATAKA",
                "commission": "District Consumer Disputes Redressal Commission",
                "search_value": "Banking",
                "date_from": "2023-01-01",
                "date_to": "2023-12-31",
                "page": 1,
                "per_page": 20
            }
        }


class CaseByJudgeRequest(CaseSearchRequest):
    """Request model for searching cases by judge."""

    class Config:
        json_schema_extra = {
            "example": {
                "state": "KARNATAKA",
                "commission": "District Consumer Disputes Redressal Commission",
                "search_value": "Justice Sharma",
                "date_from": "2023-01-01",
                "date_to": "2023-12-31",
                "page": 1,
                "per_page": 20
            }
        }


# Response models
class CaseInfo(BaseModel):
    """Case information model with exact fields as specified."""

    case_number: str = Field(..., description="Case number")
    case_stage: str = Field(..., description="Current stage of the case")
    filing_date: str = Field(...,
                             description="Filing date in YYYY-MM-DD format")
    complainant: str = Field(..., description="Complainant name")
    complainant_advocate: str = Field(...,
                                      description="Complainant's advocate")
    respondent: str = Field(..., description="Respondent name")
    respondent_advocate: str = Field(..., description="Respondent's advocate")
    document_link: str = Field(..., description="Link to case documents")


class CaseSearchResponse(BaseModel):
    """Response model for case search endpoints."""

    cases: List[CaseInfo] = Field(...,
                                  description="List of cases matching the search")
    total_count: int = Field(..., description="Total number of cases found")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class StateListResponse(BaseModel):
    """Response model for states endpoint."""

    states: List[StateInfo] = Field(...,
                                    description="List of available states")


class CommissionListResponse(BaseModel):
    """Response model for commissions endpoint."""

    commissions: List[CommissionInfo] = Field(
        ..., description="List of commissions for the state")
    state_id: str = Field(...,
                          description="State ID these commissions belong to")


# Error models
class ErrorDetail(BaseModel):
    """Error detail model."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")


class CaptchaError(BaseModel):
    """Captcha error model for when Jagriti returns a captcha."""

    detail: str = Field(default="captcha_required", description="Error type")
    captcha: bool = Field(
        default=True, description="Indicates captcha is required")
    message: str = Field(
        default="Jagriti returned a captcha; request cannot be completed automatically.",
        description="Human-readable error message",
    )


class ValidationError(BaseModel):
    """Validation error model."""

    detail: str = Field(..., description="Validation error message")
    field: Optional[str] = Field(
        None, description="Field that failed validation")
    suggestions: Optional[List[str]] = Field(
        None, description="Suggested corrections")


# Internal models for Jagriti client
class JagritiSearchParams(BaseModel):
    """Internal model for Jagriti search parameters."""

    search_type: str = Field(...,
                             description="Type of search (case_number, complainant, etc.)")
    state_text: str = Field(..., description="State name")
    commission_text: str = Field(..., description="Commission name")
    search_value: str = Field(..., description="Search term")
    date_from: Optional[str] = Field(
        None, description="Start date in YYYY-MM-DD format")
    date_to: Optional[str] = Field(
        None, description="End date in YYYY-MM-DD format")
    page: int = Field(default=1, description="Page number")
    per_page: int = Field(default=20, description="Items per page")
