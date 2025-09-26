"""Meta endpoints for states and commissions data."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.cache import get_cached_commissions, get_cached_states, set_cached_commissions, set_cached_states
from app.core.logging import get_logger
from app.models.schemas import (
    CaptchaError,
    CommissionListResponse,
    ErrorDetail,
    StateListResponse,
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
    prefix="",
    tags=["meta"],
    responses={
        500: {"model": ErrorDetail, "description": "Internal server error"},
        503: {"model": CaptchaError, "description": "Captcha required"},
    },
)


@router.get(
    "/states",
    response_model=StateListResponse,
    summary="Get available states",
    description="Retrieve the list of available states from Jagriti. Results are cached for 24 hours.",
    responses={
        200: {"model": StateListResponse, "description": "List of available states"},
        503: {"model": CaptchaError, "description": "Captcha encountered"},
    },
)
async def get_states():
    """
    Get the list of available states from Jagriti.

    This endpoint fetches and caches the list of states available in the Jagriti system.
    The results are cached for 24 hours to improve performance.

    Returns:
        StateListResponse: List of states with their names and IDs
    """
    try:
        logger.info("Fetching states list")

        # Try to get from cache first
        cached_states = await get_cached_states()
        if cached_states is not None:
            logger.debug("Returning cached states")
            return StateListResponse(states=cached_states)

        # Fetch from Jagriti
        client = get_jagriti_client()
        states = await client.fetch_states()

        # Cache the results
        await set_cached_states(states)
        logger.info(f"Fetched and cached {len(states)} states")

        return StateListResponse(states=states)

    except JagritiCaptchaError:
        logger.warning("Captcha encountered while fetching states")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=CaptchaError().dict(),
        )

    except JagritiTimeoutError as e:
        logger.error(f"Timeout while fetching states: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to Jagriti timed out. Please try again later.",
        )

    except JagritiAPIError as e:
        logger.error(f"Jagriti API error while fetching states: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with Jagriti. Please try again later.",
        )

    except Exception as e:
        logger.error(f"Unexpected error while fetching states: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.get(
    "/commissions/{state_id}",
    response_model=CommissionListResponse,
    summary="Get commissions for a state",
    description="Retrieve the list of commissions for a specific state from Jagriti. Results are cached for 24 hours.",
    responses={
        200: {"model": CommissionListResponse, "description": "List of commissions for the state"},
        400: {"model": ValidationError, "description": "Invalid state ID"},
        404: {"model": ErrorDetail, "description": "State not found"},
        503: {"model": CaptchaError, "description": "Captcha encountered"},
    },
)
async def get_commissions(state_id: str):
    """
    Get the list of commissions for a specific state.

    This endpoint fetches and caches the list of commissions available for the specified state.
    The results are cached for 24 hours to improve performance.

    Args:
        state_id: The ID of the state to get commissions for

    Returns:
        CommissionListResponse: List of commissions for the state

    Raises:
        400: If the state_id is invalid or malformed
        404: If the state is not found
        503: If a captcha is encountered
    """
    try:
        logger.info(f"Fetching commissions for state_id: {state_id}")

        if not state_id or not state_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State ID cannot be empty",
            )

        # Try to get from cache first
        cached_commissions = await get_cached_commissions(state_id)
        if cached_commissions is not None:
            logger.debug(
                f"Returning cached commissions for state_id: {state_id}")
            return CommissionListResponse(
                commissions=cached_commissions, state_id=state_id
            )

        # Fetch from Jagriti
        client = get_jagriti_client()
        commissions = await client.fetch_commissions(state_id)

        if not commissions:
            logger.warning(f"No commissions found for state_id: {state_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No commissions found for state ID: {state_id}",
            )

        # Cache the results
        await set_cached_commissions(state_id, commissions)
        logger.info(
            f"Fetched and cached {len(commissions)} commissions for state_id: {state_id}")

        return CommissionListResponse(commissions=commissions, state_id=state_id)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except JagritiCaptchaError:
        logger.warning(
            f"Captcha encountered while fetching commissions for state_id: {state_id}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=CaptchaError().dict(),
        )

    except JagritiTimeoutError as e:
        logger.error(
            f"Timeout while fetching commissions for state_id {state_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to Jagriti timed out. Please try again later.",
        )

    except JagritiAPIError as e:
        logger.error(
            f"Jagriti API error while fetching commissions for state_id {state_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with Jagriti. Please try again later.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error while fetching commissions for state_id {state_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )
