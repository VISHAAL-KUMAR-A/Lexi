"""Tests for the Jagriti client."""

import pytest
import respx
from httpx import Response

from app.services.jagriti_client import (
    JagritiAPIError,
    JagritiCaptchaError,
    JagritiClient,
    JagritiTimeoutError,
)


@pytest.mark.asyncio
async def test_jagriti_client_captcha_detection():
    """Test captcha detection in responses."""
    client = JagritiClient()

    # Mock response with captcha content
    captcha_html = """
    <html>
        <body>
            <div>Please complete the captcha below</div>
            <script src="https://www.google.com/recaptcha/api.js"></script>
        </body>
    </html>
    """

    response = Response(200, text=captcha_html)

    with pytest.raises(JagritiCaptchaError):
        await client._check_for_captcha(response)


@pytest.mark.asyncio
async def test_jagriti_client_normal_response():
    """Test normal response without captcha."""
    client = JagritiClient()

    normal_html = """
    <html>
        <body>
            <div>Normal content</div>
            <table>
                <tr><td>Some data</td></tr>
            </table>
        </body>
    </html>
    """

    response = Response(200, text=normal_html)

    # Should not raise an exception
    await client._check_for_captcha(response)


@pytest.mark.asyncio
async def test_make_request_success():
    """Test successful HTTP request."""
    client = JagritiClient()

    with respx.mock:
        respx.get("https://e-jagriti.gov.in/test").mock(
            return_value=Response(200, text="Success")
        )

        response = await client._make_request("GET", "/test")
        assert response.status_code == 200
        assert response.text == "Success"


@pytest.mark.asyncio
async def test_make_request_with_captcha():
    """Test HTTP request that returns captcha."""
    client = JagritiClient()

    with respx.mock:
        respx.get("https://e-jagriti.gov.in/test").mock(
            return_value=Response(
                200, text="Please verify you are human with this captcha")
        )

        with pytest.raises(JagritiCaptchaError):
            await client._make_request("GET", "/test")


@pytest.mark.asyncio
async def test_make_request_timeout():
    """Test HTTP request timeout."""
    client = JagritiClient()
    client.max_retries = 0  # Disable retries for faster test

    import httpx

    with respx.mock:
        respx.get("https://e-jagriti.gov.in/test").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        with pytest.raises(JagritiTimeoutError):
            await client._make_request("GET", "/test")


@pytest.mark.asyncio
async def test_fetch_states_not_implemented():
    """Test that fetch_states raises NotImplementedError."""
    client = JagritiClient()

    with pytest.raises(NotImplementedError):
        await client.fetch_states()


@pytest.mark.asyncio
async def test_fetch_commissions_not_implemented():
    """Test that fetch_commissions raises NotImplementedError."""
    client = JagritiClient()

    with pytest.raises(NotImplementedError):
        await client.fetch_commissions("KA")


@pytest.mark.asyncio
async def test_search_cases_not_implemented():
    """Test that search_cases raises NotImplementedError."""
    client = JagritiClient()

    with pytest.raises(NotImplementedError):
        await client.search_cases(
            search_type="case_number",
            state_text="KARNATAKA",
            commission_text="State Commission",
            search_value="CC/123/2023",
        )


@pytest.mark.asyncio
async def test_resolve_state_and_commission_ids_not_implemented():
    """Test that resolve_state_and_commission_ids raises NotImplementedError."""
    client = JagritiClient()

    with pytest.raises(NotImplementedError):
        await client.resolve_state_and_commission_ids("KARNATAKA", "State Commission")
