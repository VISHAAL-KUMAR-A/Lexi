"""Integration tests that use mocked Jagriti pages."""

import pytest
import respx
from httpx import Response

from app.core.cache import clear_all_cache


@pytest.mark.asyncio
async def test_full_case_search_workflow(
    client,
    sample_states_data,
    sample_commissions_data,
    sample_cases_data,
    mock_jagriti_html_states,
    mock_jagriti_html_commissions,
    mock_jagriti_html_cases,
):
    """Test the full workflow: get states -> get commissions -> search cases."""
    await clear_all_cache()

    # Mock the jagriti client methods to return sample data
    from app.services.jagriti_client import get_jagriti_client
    client_instance = get_jagriti_client()

    async def mock_fetch_states():
        return sample_states_data

    async def mock_fetch_commissions(state_id):
        return sample_commissions_data

    async def mock_search_cases(search_type, state_text, commission_text, search_value, **kwargs):
        return sample_cases_data, len(sample_cases_data)

    client_instance.fetch_states = mock_fetch_states
    client_instance.fetch_commissions = mock_fetch_commissions
    client_instance.search_cases = mock_search_cases

    # 1. Get states
    states_response = client.get("/states")
    assert states_response.status_code == 200
    states_data = states_response.json()
    assert len(states_data["states"]) == 3

    # 2. Get commissions for Karnataka
    commissions_response = client.get("/commissions/KA")
    assert commissions_response.status_code == 200
    commissions_data = commissions_response.json()
    assert len(commissions_data["commissions"]) == 2

    # 3. Search for cases
    search_request = {
        "state": "KARNATAKA",
        "commission": "Karnataka State Consumer Disputes Redressal Commission",
        "search_value": "CC/123/2023",
        "page": 1,
        "per_page": 20,
    }

    search_response = client.post("/cases/by-case-number", json=search_request)
    assert search_response.status_code == 200
    search_data = search_response.json()

    # Verify the exact response schema
    assert "cases" in search_data
    assert "total_count" in search_data
    assert "page" in search_data
    assert "per_page" in search_data
    assert "total_pages" in search_data

    cases = search_data["cases"]
    assert len(cases) == 2

    # Verify each case has the exact required fields
    for case in cases:
        required_fields = [
            "case_number",
            "case_stage",
            "filing_date",
            "complainant",
            "complainant_advocate",
            "respondent",
            "respondent_advocate",
            "document_link",
        ]

        for field in required_fields:
            assert field in case, f"Missing field: {field}"
            assert case[field] is not None, f"Field {field} is None"
            assert isinstance(
                case[field], str), f"Field {field} is not a string"

    # Verify specific data
    first_case = cases[0]
    assert first_case["case_number"] == "CC/123/2023"
    assert first_case["case_stage"] == "Pending"
    assert first_case["filing_date"] == "2023-01-15"
    assert first_case["complainant"] == "John Doe"
    assert first_case["complainant_advocate"] == "Advocate A"
    assert first_case["respondent"] == "XYZ Company"
    assert first_case["respondent_advocate"] == "Advocate B"
    assert first_case["document_link"] == "https://e-jagriti.gov.in/documents/123"


@pytest.mark.asyncio
async def test_captcha_handling_across_endpoints(client):
    """Test captcha handling across different endpoints."""
    await clear_all_cache()

    from app.services.jagriti_client import get_jagriti_client, JagritiCaptchaError
    client_instance = get_jagriti_client()

    async def mock_captcha_error(*args, **kwargs):
        raise JagritiCaptchaError("Captcha required")

    # Set all methods to raise captcha error
    client_instance.fetch_states = mock_captcha_error
    client_instance.fetch_commissions = mock_captcha_error
    client_instance.search_cases = mock_captcha_error

    # Test states endpoint
    states_response = client.get("/states")
    assert states_response.status_code == 503
    states_data = states_response.json()
    assert states_data["detail"] == "captcha_required"
    assert states_data["captcha"] is True

    # Test commissions endpoint
    commissions_response = client.get("/commissions/KA")
    assert commissions_response.status_code == 503
    commissions_data = commissions_response.json()
    assert commissions_data["detail"] == "captcha_required"

    # Test case search endpoint
    search_request = {
        "state": "KARNATAKA",
        "commission": "Karnataka State Commission",
        "search_value": "CC/123/2023",
    }

    search_response = client.post("/cases/by-case-number", json=search_request)
    assert search_response.status_code == 503
    search_data = search_response.json()
    assert search_data["detail"] == "captcha_required"


@pytest.mark.asyncio
async def test_health_and_root_endpoints(client):
    """Test health and root endpoints."""
    # Test health endpoint
    health_response = client.get("/health")
    assert health_response.status_code == 200
    health_data = health_response.json()
    assert health_data["status"] == "healthy"
    assert "version" in health_data
    assert "service" in health_data

    # Test root endpoint
    root_response = client.get("/")
    assert root_response.status_code == 200
    root_data = root_response.json()
    assert "message" in root_data
    assert "version" in root_data
    assert "endpoints" in root_data

    # Verify all expected endpoints are listed
    endpoints = root_data["endpoints"]
    assert "states" in endpoints
    assert "commissions" in endpoints
    assert "case_search" in endpoints

    case_search_endpoints = endpoints["case_search"]
    expected_case_endpoints = [
        "by_case_number",
        "by_complainant",
        "by_respondent",
        "by_complainant_advocate",
        "by_respondent_advocate",
        "by_industry_type",
        "by_judge",
    ]

    for endpoint in expected_case_endpoints:
        assert endpoint in case_search_endpoints
