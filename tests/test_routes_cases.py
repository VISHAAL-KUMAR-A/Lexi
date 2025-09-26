"""Tests for case search routes."""

import pytest
from fastapi import status

from app.services.jagriti_client import get_jagriti_client, JagritiCaptchaError, JagritiTimeoutError


@pytest.mark.asyncio
async def test_search_by_case_number_post_success(client, sample_cases_data):
    """Test successful case search by case number using POST."""
    from app.services.jagriti_client import get_jagriti_client
    client_instance = get_jagriti_client()

    # Mock the search_cases method
    async def mock_search_cases(search_type, state_text, commission_text, search_value, **kwargs):
        return sample_cases_data, 2

    client_instance.search_cases = mock_search_cases

    request_data = {
        "state": "KARNATAKA",
        "commission": "Karnataka State Commission",
        "search_value": "CC/123/2023",
        "page": 1,
        "per_page": 20,
    }

    response = client.post("/cases/by-case-number", json=request_data)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "cases" in data
    assert "total_count" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    assert len(data["cases"]) == 2
    assert data["total_count"] == 2
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["total_pages"] == 1


@pytest.mark.asyncio
async def test_search_by_case_number_get_success(client, sample_cases_data):
    """Test successful case search by case number using GET."""
    from app.services.jagriti_client import get_jagriti_client
    client_instance = get_jagriti_client()

    # Mock the search_cases method
    async def mock_search_cases(search_type, state_text, commission_text, search_value, **kwargs):
        return sample_cases_data, 2

    client_instance.search_cases = mock_search_cases

    response = client.get(
        "/cases/by-case-number",
        params={
            "state": "KARNATAKA",
            "commission": "Karnataka State Commission",
            "search_value": "CC/123/2023",
            "page": 1,
            "per_page": 20,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["cases"]) == 2
    assert data["total_count"] == 2


@pytest.mark.asyncio
async def test_search_by_complainant_success(client, sample_cases_data):
    """Test successful case search by complainant."""
    from app.services.jagriti_client import get_jagriti_client
    client_instance = get_jagriti_client()

    # Mock the search_cases method
    async def mock_search_cases(search_type, state_text, commission_text, search_value, **kwargs):
        return sample_cases_data, 2

    client_instance.search_cases = mock_search_cases

    request_data = {
        "state": "KARNATAKA",
        "commission": "Karnataka State Commission",
        "search_value": "John Doe",
        "page": 1,
        "per_page": 20,
    }

    response = client.post("/cases/by-complainant", json=request_data)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["cases"]) == 2


@pytest.mark.asyncio
async def test_search_validation_error_missing_fields(client):
    """Test validation error when required fields are missing."""
    request_data = {
        "state": "KARNATAKA",
        # Missing commission and search_value
    }

    response = client.post("/cases/by-case-number", json=request_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_search_get_validation_error_missing_params(client):
    """Test validation error when required query params are missing."""
    response = client.get(
        "/cases/by-case-number",
        params={
            "state": "KARNATAKA",
            # Missing commission and search_value
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "required" in data["detail"]


@pytest.mark.asyncio
async def test_search_captcha_error(client):
    """Test case search with captcha error."""
    from app.services.jagriti_client import get_jagriti_client, JagritiCaptchaError
    client_instance = get_jagriti_client()

    # Mock the search_cases method to raise captcha error
    async def mock_search_cases(search_type, state_text, commission_text, search_value, **kwargs):
        raise JagritiCaptchaError("Captcha required")

    client_instance.search_cases = mock_search_cases

    request_data = {
        "state": "KARNATAKA",
        "commission": "Karnataka State Commission",
        "search_value": "CC/123/2023",
    }

    response = client.post("/cases/by-case-number", json=request_data)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert data["detail"] == "captcha_required"
    assert data["captcha"] is True


@pytest.mark.asyncio
async def test_search_timeout_error(client):
    """Test case search with timeout error."""
    from app.services.jagriti_client import get_jagriti_client, JagritiTimeoutError
    client_instance = get_jagriti_client()

    # Mock the search_cases method to raise timeout error
    async def mock_search_cases(search_type, state_text, commission_text, search_value, **kwargs):
        raise JagritiTimeoutError("Request timed out")

    client_instance.search_cases = mock_search_cases

    request_data = {
        "state": "KARNATAKA",
        "commission": "Karnataka State Commission",
        "search_value": "CC/123/2023",
    }

    response = client.post("/cases/by-case-number", json=request_data)

    assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT


@pytest.mark.asyncio
async def test_search_pagination_validation(client):
    """Test pagination validation."""
    # Test invalid page number
    response = client.get(
        "/cases/by-case-number",
        params={
            "state": "KARNATAKA",
            "commission": "Karnataka State Commission",
            "search_value": "CC/123/2023",
            "page": 0,  # Invalid page
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Test invalid per_page
    response = client.get(
        "/cases/by-case-number",
        params={
            "state": "KARNATAKA",
            "commission": "Karnataka State Commission",
            "search_value": "CC/123/2023",
            "per_page": 101,  # Exceeds max
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_all_case_search_endpoints(client, sample_cases_data):
    """Test all case search endpoints work."""
    from app.services.jagriti_client import get_jagriti_client
    client_instance = get_jagriti_client()

    # Mock the search_cases method
    async def mock_search_cases(search_type, state_text, commission_text, search_value, **kwargs):
        return sample_cases_data, 2

    client_instance.search_cases = mock_search_cases

    request_data = {
        "state": "KARNATAKA",
        "commission": "Karnataka State Commission",
        "search_value": "test_value",
    }

    endpoints = [
        "/cases/by-case-number",
        "/cases/by-complainant",
        "/cases/by-respondent",
        "/cases/by-complainant-advocate",
        "/cases/by-respondent-advocate",
        "/cases/by-industry-type",
        "/cases/by-judge",
    ]

    for endpoint in endpoints:
        response = client.post(endpoint, json=request_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["cases"]) == 2
