"""Pydantic models for request and response schemas."""

from datetime import date
from typing import List, Optional

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

    state: str = Field(..., description="State name or ID", min_length=1)
    commission: str = Field(...,
                            description="Commission name or ID", min_length=1)
    search_value: str = Field(..., description="Search term", min_length=1)
    date_from: Optional[date] = Field(
        None, description="Start date filter (YYYY-MM-DD)")
    date_to: Optional[date] = Field(
        None, description="End date filter (YYYY-MM-DD)")
    page: int = Field(default=1, description="Page number (1-based)", ge=1)
    per_page: int = Field(
        default=20, description="Items per page", ge=1, le=100)

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate that date_to is not before date_from."""
        if v and info.data.get("date_from"):
            if v < info.data["date_from"]:
                raise ValueError(
                    "date_to must be greater than or equal to date_from")
        return v


class CaseByNumberRequest(CaseSearchRequest):
    """Request model for searching cases by case number."""

    pass


class CaseByComplainantRequest(CaseSearchRequest):
    """Request model for searching cases by complainant."""

    pass


class CaseByRespondentRequest(CaseSearchRequest):
    """Request model for searching cases by respondent."""

    pass


class CaseByComplainantAdvocateRequest(CaseSearchRequest):
    """Request model for searching cases by complainant advocate."""

    pass


class CaseByRespondentAdvocateRequest(CaseSearchRequest):
    """Request model for searching cases by respondent advocate."""

    pass


class CaseByIndustryTypeRequest(CaseSearchRequest):
    """Request model for searching cases by industry type."""

    pass


class CaseByJudgeRequest(CaseSearchRequest):
    """Request model for searching cases by judge."""

    pass


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
    date_from: Optional[date] = Field(None, description="Start date")
    date_to: Optional[date] = Field(None, description="End date")
    page: int = Field(default=1, description="Page number")
    per_page: int = Field(default=20, description="Items per page")
