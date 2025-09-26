"""Tests for meta routes (states and commissions)."""

import pytest
import respx
from fastapi import status
from httpx import Response

from app.core.cache import clear_all_cache


@pytest.mark.asyncio
async def test_get_states_success(client, sample_states_data, mock_jagriti_html_states):
    """Test successful states retrieval."""
    # Clear cache to ensure fresh test
    await clear_all_cache()

    with respx.mock:
        # Mock the Jagriti states endpoint
        respx.get("https://e-jagriti.gov.in/search").mock(
            return_value=Response(200, text=mock_jagriti_html_states)
        )

        # Mock the jagriti client to return sample data
        from app.services.jagriti_client import get_jagriti_client
        client_instance = get_jagriti_client()

        # Mock the fetch_states method
        async def mock_fetch_states():
            return [
                {"state_text": "KARNATAKA", "state_id": "KA"},
                {"state_text": "MAHARASHTRA", "state_id": "MH"},
                {"state_text": "DELHI", "state_id": "DL"},
            ]

        client_instance.fetch_states = mock_fetch_states

        response = client.get("/states")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "states" in data
        assert len(data["states"]) == 3
        assert data["states"][0]["state_text"] == "KARNATAKA"
        assert data["states"][0]["state_id"] == "KA"


@pytest.mark.asyncio
async def test_get_states_captcha_error(client, mock_jagriti_captcha_html):
    """Test states retrieval with captcha error."""
    await clear_all_cache()

    from app.services.jagriti_client import get_jagriti_client, JagritiCaptchaError
    client_instance = get_jagriti_client()

    # Mock the fetch_states method to raise captcha error
    async def mock_fetch_states():
        raise JagritiCaptchaError("Captcha required")

    client_instance.fetch_states = mock_fetch_states

    response = client.get("/states")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert data["detail"] == "captcha_required"
    assert data["captcha"] is True


@pytest.mark.asyncio
async def test_get_commissions_success(client, sample_commissions_data):
    """Test successful commissions retrieval."""
    await clear_all_cache()

    from app.services.jagriti_client import get_jagriti_client
    client_instance = get_jagriti_client()

    # Mock the fetch_commissions method
    async def mock_fetch_commissions(state_id):
        return [
            {
                "commission_text": "Karnataka State Consumer Disputes Redressal Commission",
                "commission_id": "KA_STATE",
                "state_id": "KA",
            },
            {
                "commission_text": "Bangalore Urban District Consumer Disputes Redressal Forum",
                "commission_id": "KA_BANGALORE",
                "state_id": "KA",
            },
        ]

    client_instance.fetch_commissions = mock_fetch_commissions

    response = client.get("/commissions/KA")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "commissions" in data
    assert "state_id" in data
    assert data["state_id"] == "KA"
    assert len(data["commissions"]) == 2


@pytest.mark.asyncio
async def test_get_commissions_empty_state_id(client):
    """Test commissions retrieval with empty state ID."""
    response = client.get("/commissions/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_commissions_not_found(client):
    """Test commissions retrieval for non-existent state."""
    from app.services.jagriti_client import get_jagriti_client
    client_instance = get_jagriti_client()

    # Mock the fetch_commissions method to return empty list
    async def mock_fetch_commissions(state_id):
        return []

    client_instance.fetch_commissions = mock_fetch_commissions

    response = client.get("/commissions/INVALID")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "No commissions found" in data["detail"]


@pytest.mark.asyncio
async def test_get_commissions_captcha_error(client):
    """Test commissions retrieval with captcha error."""
    from app.services.jagriti_client import get_jagriti_client, JagritiCaptchaError
    client_instance = get_jagriti_client()

    # Mock the fetch_commissions method to raise captcha error
    async def mock_fetch_commissions(state_id):
        raise JagritiCaptchaError("Captcha required")

    client_instance.fetch_commissions = mock_fetch_commissions

    response = client.get("/commissions/KA")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert data["detail"] == "captcha_required"
    assert data["captcha"] is True
