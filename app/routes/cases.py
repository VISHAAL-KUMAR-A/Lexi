"""Case search endpoints for different search criteria."""

import math
from typing import Union

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import (
    CaptchaError,
    CaseByComplainantAdvocateRequest,
    CaseByComplainantRequest,
    CaseByIndustryTypeRequest,
    CaseByJudgeRequest,
    CaseByNumberRequest,
    CaseByRespondentAdvocateRequest,
    CaseByRespondentRequest,
    CaseSearchResponse,
    ErrorDetail,
    ValidationError,
)
from app.services.jagriti_client import (
    JagritiAPIError,
    JagritiCaptchaError,
    JagritiTimeoutError,
    get_jagriti_client,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/cases",
    tags=["cases"],
    responses={
        400: {"model": ValidationError, "description": "Validation error"},
        500: {"model": ErrorDetail, "description": "Internal server error"},
        503: {"model": CaptchaError, "description": "Captcha required"},
    },
)


async def _search_cases_common(
    search_type: str,
    request_data: Union[
        CaseByNumberRequest,
        CaseByComplainantRequest,
        CaseByRespondentRequest,
        CaseByComplainantAdvocateRequest,
        CaseByRespondentAdvocateRequest,
        CaseByIndustryTypeRequest,
        CaseByJudgeRequest,
    ],
) -> CaseSearchResponse:
    """
    Common function to handle case searches with different criteria.

    Args:
        search_type: Type of search being performed
        request_data: The search request data

    Returns:
        CaseSearchResponse: Search results with pagination

    Raises:
        HTTPException: For various error conditions
    """
    try:
        logger.info(
            f"Searching cases: type={search_type}, state={request_data.state}, "
            f"commission={request_data.commission}, value={request_data.search_value}"
        )

        client = get_jagriti_client()

        # Perform the search
        cases, total_count = await client.search_cases(
            search_type=search_type,
            state_text=request_data.state,
            commission_text=request_data.commission,
            search_value=request_data.search_value,
            date_from=request_data.date_from,
            date_to=request_data.date_to,
            page=request_data.page,
            per_page=request_data.per_page,
        )

        # Calculate pagination info
        total_pages = math.ceil(
            total_count / request_data.per_page) if total_count > 0 else 0

        logger.info(
            f"Search completed: found {total_count} cases, returning {len(cases)} cases for page {request_data.page}"
        )

        return CaseSearchResponse(
            cases=cases,
            total_count=total_count,
            page=request_data.page,
            per_page=request_data.per_page,
            total_pages=total_pages,
        )

    except ValueError as e:
        logger.warning(f"Validation error in case search: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except JagritiCaptchaError:
        logger.warning(f"Captcha encountered during {search_type} search")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=CaptchaError().dict(),
        )

    except JagritiTimeoutError as e:
        logger.error(f"Timeout during {search_type} search: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to Jagriti timed out. Please try again later.",
        )

    except JagritiAPIError as e:
        logger.error(f"Jagriti API error during {search_type} search: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with Jagriti. Please try again later.",
        )

    except Exception as e:
        logger.error(f"Unexpected error during {search_type} search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )


def _validate_pagination(page: int, per_page: int) -> None:
    """Validate pagination parameters."""
    settings = get_settings()

    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1",
        )

    if per_page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Per page must be >= 1",
        )

    if per_page > settings.max_page_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Per page cannot exceed {settings.max_page_size}",
        )


@router.post(
    "/by-case-number",
    response_model=CaseSearchResponse,
    summary="Search cases by case number",
    description="Search for cases using case number as the search criteria.",
)
@router.get(
    "/by-case-number",
    response_model=CaseSearchResponse,
    summary="Search cases by case number",
    description="Search for cases using case number as the search criteria.",
)
async def search_by_case_number(
    # Query parameters for GET requests
    state: str = Query(None, description="State name"),
    commission: str = Query(None, description="Commission name"),
    search_value: str = Query(None, description="Case number to search for"),
    date_from: str = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, description="Page number"),
    per_page: int = Query(20, description="Items per page"),
    # Request body for POST requests
    request: CaseByNumberRequest = None,
):
    """Search for cases by case number."""
    # Handle both GET and POST requests
    if request is None:
        # GET request - validate required parameters
        if not all([state, commission, search_value]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="state, commission, and search_value are required",
            )

        _validate_pagination(page, per_page)

        request = CaseByNumberRequest(
            state=state,
            commission=commission,
            search_value=search_value,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )

    return await _search_cases_common("case_number", request)


@router.post(
    "/by-complainant",
    response_model=CaseSearchResponse,
    summary="Search cases by complainant",
    description="Search for cases using complainant name as the search criteria.",
)
@router.get(
    "/by-complainant",
    response_model=CaseSearchResponse,
    summary="Search cases by complainant",
    description="Search for cases using complainant name as the search criteria.",
)
async def search_by_complainant(
    # Query parameters for GET requests
    state: str = Query(None, description="State name"),
    commission: str = Query(None, description="Commission name"),
    search_value: str = Query(
        None, description="Complainant name to search for"),
    date_from: str = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, description="Page number"),
    per_page: int = Query(20, description="Items per page"),
    # Request body for POST requests
    request: CaseByComplainantRequest = None,
):
    """Search for cases by complainant name."""
    # Handle both GET and POST requests
    if request is None:
        # GET request - validate required parameters
        if not all([state, commission, search_value]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="state, commission, and search_value are required",
            )

        _validate_pagination(page, per_page)

        request = CaseByComplainantRequest(
            state=state,
            commission=commission,
            search_value=search_value,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )

    return await _search_cases_common("complainant", request)


@router.post(
    "/by-respondent",
    response_model=CaseSearchResponse,
    summary="Search cases by respondent",
    description="Search for cases using respondent name as the search criteria.",
)
@router.get(
    "/by-respondent",
    response_model=CaseSearchResponse,
    summary="Search cases by respondent",
    description="Search for cases using respondent name as the search criteria.",
)
async def search_by_respondent(
    # Query parameters for GET requests
    state: str = Query(None, description="State name"),
    commission: str = Query(None, description="Commission name"),
    search_value: str = Query(
        None, description="Respondent name to search for"),
    date_from: str = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, description="Page number"),
    per_page: int = Query(20, description="Items per page"),
    # Request body for POST requests
    request: CaseByRespondentRequest = None,
):
    """Search for cases by respondent name."""
    # Handle both GET and POST requests
    if request is None:
        # GET request - validate required parameters
        if not all([state, commission, search_value]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="state, commission, and search_value are required",
            )

        _validate_pagination(page, per_page)

        request = CaseByRespondentRequest(
            state=state,
            commission=commission,
            search_value=search_value,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )

    return await _search_cases_common("respondent", request)


@router.post(
    "/by-complainant-advocate",
    response_model=CaseSearchResponse,
    summary="Search cases by complainant advocate",
    description="Search for cases using complainant advocate name as the search criteria.",
)
@router.get(
    "/by-complainant-advocate",
    response_model=CaseSearchResponse,
    summary="Search cases by complainant advocate",
    description="Search for cases using complainant advocate name as the search criteria.",
)
async def search_by_complainant_advocate(
    # Query parameters for GET requests
    state: str = Query(None, description="State name"),
    commission: str = Query(None, description="Commission name"),
    search_value: str = Query(
        None, description="Complainant advocate name to search for"),
    date_from: str = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, description="Page number"),
    per_page: int = Query(20, description="Items per page"),
    # Request body for POST requests
    request: CaseByComplainantAdvocateRequest = None,
):
    """Search for cases by complainant advocate name."""
    # Handle both GET and POST requests
    if request is None:
        # GET request - validate required parameters
        if not all([state, commission, search_value]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="state, commission, and search_value are required",
            )

        _validate_pagination(page, per_page)

        request = CaseByComplainantAdvocateRequest(
            state=state,
            commission=commission,
            search_value=search_value,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )

    return await _search_cases_common("complainant_advocate", request)


@router.post(
    "/by-respondent-advocate",
    response_model=CaseSearchResponse,
    summary="Search cases by respondent advocate",
    description="Search for cases using respondent advocate name as the search criteria.",
)
@router.get(
    "/by-respondent-advocate",
    response_model=CaseSearchResponse,
    summary="Search cases by respondent advocate",
    description="Search for cases using respondent advocate name as the search criteria.",
)
async def search_by_respondent_advocate(
    # Query parameters for GET requests
    state: str = Query(None, description="State name"),
    commission: str = Query(None, description="Commission name"),
    search_value: str = Query(
        None, description="Respondent advocate name to search for"),
    date_from: str = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, description="Page number"),
    per_page: int = Query(20, description="Items per page"),
    # Request body for POST requests
    request: CaseByRespondentAdvocateRequest = None,
):
    """Search for cases by respondent advocate name."""
    # Handle both GET and POST requests
    if request is None:
        # GET request - validate required parameters
        if not all([state, commission, search_value]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="state, commission, and search_value are required",
            )

        _validate_pagination(page, per_page)

        request = CaseByRespondentAdvocateRequest(
            state=state,
            commission=commission,
            search_value=search_value,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )

    return await _search_cases_common("respondent_advocate", request)


@router.post(
    "/by-industry-type",
    response_model=CaseSearchResponse,
    summary="Search cases by industry type",
    description="Search for cases using industry type as the search criteria.",
)
@router.get(
    "/by-industry-type",
    response_model=CaseSearchResponse,
    summary="Search cases by industry type",
    description="Search for cases using industry type as the search criteria.",
)
async def search_by_industry_type(
    # Query parameters for GET requests
    state: str = Query(None, description="State name"),
    commission: str = Query(None, description="Commission name"),
    search_value: str = Query(None, description="Industry type to search for"),
    date_from: str = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, description="Page number"),
    per_page: int = Query(20, description="Items per page"),
    # Request body for POST requests
    request: CaseByIndustryTypeRequest = None,
):
    """Search for cases by industry type."""
    # Handle both GET and POST requests
    if request is None:
        # GET request - validate required parameters
        if not all([state, commission, search_value]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="state, commission, and search_value are required",
            )

        _validate_pagination(page, per_page)

        request = CaseByIndustryTypeRequest(
            state=state,
            commission=commission,
            search_value=search_value,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )

    return await _search_cases_common("industry_type", request)


@router.post(
    "/by-judge",
    response_model=CaseSearchResponse,
    summary="Search cases by judge",
    description="Search for cases using judge name as the search criteria.",
)
@router.get(
    "/by-judge",
    response_model=CaseSearchResponse,
    summary="Search cases by judge",
    description="Search for cases using judge name as the search criteria.",
)
async def search_by_judge(
    # Query parameters for GET requests
    state: str = Query(None, description="State name"),
    commission: str = Query(None, description="Commission name"),
    search_value: str = Query(None, description="Judge name to search for"),
    date_from: str = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, description="Page number"),
    per_page: int = Query(20, description="Items per page"),
    # Request body for POST requests
    request: CaseByJudgeRequest = None,
):
    """Search for cases by judge name."""
    # Handle both GET and POST requests
    if request is None:
        # GET request - validate required parameters
        if not all([state, commission, search_value]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="state, commission, and search_value are required",
            )

        _validate_pagination(page, per_page)

        request = CaseByJudgeRequest(
            state=state,
            commission=commission,
            search_value=search_value,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
        )

    return await _search_cases_common("judge", request)
