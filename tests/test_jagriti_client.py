"""Tests for the Jagriti client service."""

import pytest
import respx
from httpx import Response
from pathlib import Path

from app.core.cache import get_cache
from app.core.config import get_settings
from app.services.jagriti_client import (
    JagritiClient,
    JagritiAPIError,
    JagritiCaptchaError,
    JagritiTimeoutError,
    get_jagriti_client,
)
from app.models.schemas import StateInfo, CommissionInfo, CaseInfo


# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "html"


def load_fixture(filename: str) -> str:
    """Load HTML fixture from file."""
    fixture_path = FIXTURES_DIR / filename
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def client():
    """Create a fresh Jagriti client for testing."""
    return JagritiClient()


@pytest.fixture
def mock_jagriti_base():
    """Mock base Jagriti responses."""
    settings = get_settings()
    with respx.mock:
        # Mock main search page
        respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
            return_value=Response(
                200,
                content=load_fixture("jagriti_search_page.html"),
                headers={"content-type": "text/html"}
            )
        )
        yield


@pytest.mark.asyncio
class TestJagritiClient:
    """Test cases for JagritiClient class."""

    async def test_fetch_states_returns_correct_mapping(self, client, mock_jagriti_base):
        """Test that fetch_states returns the correct state mapping."""
        states = await client.fetch_states()

        assert len(states) == 5
        assert all(isinstance(state, StateInfo) for state in states)

        # Check specific states
        state_texts = [state.state_text for state in states]
        state_ids = [state.state_id for state in states]

        assert "KARNATAKA" in state_texts
        assert "MAHARASHTRA" in state_texts
        assert "TAMIL NADU" in state_texts
        assert "DELHI" in state_texts
        assert "GUJARAT" in state_texts

        # Check that state IDs are properly mapped
        karnataka_state = next(
            s for s in states if s.state_text == "KARNATAKA")
        assert karnataka_state.state_id == "29"

    async def test_fetch_states_caches_results(self, client, mock_jagriti_base):
        """Test that fetch_states caches results properly."""
        # First call
        states1 = await client.fetch_states()

        # Second call should use cache (no additional HTTP request)
        states2 = await client.fetch_states()

        assert states1 == states2
        assert len(states1) == 5

    async def test_fetch_commissions_returns_commission_list(self, client):
        """Test that fetch_commissions returns commission list for a state."""
        settings = get_settings()

        with respx.mock:
            # Mock commissions endpoint
            respx.post(f"{settings.jagriti_base_url}/get_commissions/").mock(
                return_value=Response(
                    200,
                    content=load_fixture("jagriti_commissions_karnataka.html"),
                    headers={"content-type": "text/html"}
                )
            )

            commissions = await client.fetch_commissions("29")

            assert len(commissions) == 6
            assert all(isinstance(comm, CommissionInfo)
                       for comm in commissions)

            # Check specific commissions
            commission_texts = [comm.commission_text for comm in commissions]
            assert any("Bangalore Urban" in text for text in commission_texts)
            assert any("Mysore" in text for text in commission_texts)

            # Check that all commissions belong to the correct state
            assert all(comm.state_id == "29" for comm in commissions)

    async def test_fetch_commissions_caches_per_state(self, client):
        """Test that fetch_commissions caches results per state."""
        settings = get_settings()

        with respx.mock:
            respx.post(f"{settings.jagriti_base_url}/get_commissions/").mock(
                return_value=Response(
                    200,
                    content=load_fixture("jagriti_commissions_karnataka.html"),
                    headers={"content-type": "text/html"}
                )
            )

            # First call
            commissions1 = await client.fetch_commissions("29")

            # Second call should use cache
            commissions2 = await client.fetch_commissions("29")

            assert commissions1 == commissions2

    async def test_search_cases_parses_html_rows_and_normalizes_fields(self, client):
        """Test that search_cases parses HTML rows and normalizes fields correctly."""
        settings = get_settings()

        with respx.mock:
            # Mock states page
            respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
                return_value=Response(
                    200,
                    content=load_fixture("jagriti_search_page.html"),
                    headers={"content-type": "text/html"}
                )
            )

            # Mock commissions endpoint
            respx.post(f"{settings.jagriti_base_url}/get_commissions/").mock(
                return_value=Response(
                    200,
                    content=load_fixture("jagriti_commissions_karnataka.html"),
                    headers={"content-type": "text/html"}
                )
            )

            # Mock search results
            respx.post(f"{settings.jagriti_base_url}/daily_order_search/results/").mock(
                return_value=Response(
                    200,
                    content=load_fixture("jagriti_search_results.html"),
                    headers={"content-type": "text/html"}
                )
            )

            cases, total_count = await client.search_cases(
                search_type="case_number",
                state_text="KARNATAKA",
                commission_text="Bangalore Urban",
                search_value="CC/123/2023",
                page=1,
                per_page=20
            )

            assert len(cases) == 5
            assert total_count == 150
            assert all(isinstance(case, CaseInfo) for case in cases)

            # Check first case details
            first_case = cases[0]
            assert first_case.case_number == "CC/123/2023"
            assert first_case.case_stage == "Under Hearing"
            assert first_case.filing_date == "2023-03-15"  # Normalized date format
            assert first_case.complainant == "John Doe"
            assert first_case.complainant_advocate == "Advocate A. Kumar"
            assert first_case.respondent == "XYZ Corporation Ltd"
            assert first_case.respondent_advocate == "Advocate B. Sharma"
            assert first_case.document_link.endswith(
                "/documents/cc_123_2023.pdf")

    async def test_search_cases_handles_pagination(self, client):
        """Test that search_cases handles pagination correctly."""
        settings = get_settings()

        with respx.mock:
            # Mock all required endpoints
            respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
                return_value=Response(
                    200, content=load_fixture("jagriti_search_page.html"))
            )
            respx.post(f"{settings.jagriti_base_url}/get_commissions/").mock(
                return_value=Response(200, content=load_fixture(
                    "jagriti_commissions_karnataka.html"))
            )
            respx.post(f"{settings.jagriti_base_url}/daily_order_search/results/").mock(
                return_value=Response(200, content=load_fixture(
                    "jagriti_search_results.html"))
            )

            # Test different page parameters
            cases_page1, total_count1 = await client.search_cases(
                search_type="complainant",
                state_text="KARNATAKA",
                commission_text="Bangalore Urban",
                search_value="John Doe",
                page=1,
                per_page=10
            )

            cases_page2, total_count2 = await client.search_cases(
                search_type="complainant",
                state_text="KARNATAKA",
                commission_text="Bangalore Urban",
                search_value="John Doe",
                page=2,
                per_page=10
            )

            # Both calls should return results (mocked to same page)
            assert len(cases_page1) > 0
            assert len(cases_page2) > 0
            assert total_count1 == total_count2  # Same total count

    async def test_search_cases_detects_captcha_and_raises(self, client):
        """Test that search_cases detects captcha and raises appropriate exception."""
        settings = get_settings()

        with respx.mock:
            # Mock states and commissions pages normally
            respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
                return_value=Response(
                    200, content=load_fixture("jagriti_search_page.html"))
            )
            respx.post(f"{settings.jagriti_base_url}/get_commissions/").mock(
                return_value=Response(200, content=load_fixture(
                    "jagriti_commissions_karnataka.html"))
            )

            # Mock search results to return captcha page
            respx.post(f"{settings.jagriti_base_url}/daily_order_search/results/").mock(
                return_value=Response(
                    200,
                    content=load_fixture("jagriti_captcha_page.html"),
                    headers={"content-type": "text/html"}
                )
            )

            with pytest.raises(JagritiCaptchaError) as exc_info:
                await client.search_cases(
                    search_type="case_number",
                    state_text="KARNATAKA",
                    commission_text="Bangalore Urban",
                    search_value="CC/123/2023"
                )

            assert "captcha" in str(exc_info.value).lower()

    async def test_resolve_state_and_commission_ids_exact_match(self, client):
        """Test exact matching of state and commission names."""
        settings = get_settings()

        with respx.mock:
            respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
                return_value=Response(
                    200, content=load_fixture("jagriti_search_page.html"))
            )
            respx.post(f"{settings.jagriti_base_url}/get_commissions/").mock(
                return_value=Response(200, content=load_fixture(
                    "jagriti_commissions_karnataka.html"))
            )

            state_id, commission_id = await client.resolve_state_and_commission_ids(
                "KARNATAKA",
                "District Consumer Disputes Redressal Commission, Bangalore Urban"
            )

            assert state_id == "29"
            assert commission_id == "29_1"

    async def test_resolve_state_and_commission_ids_fuzzy_match(self, client):
        """Test fuzzy matching of state and commission names."""
        settings = get_settings()

        with respx.mock:
            respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
                return_value=Response(
                    200, content=load_fixture("jagriti_search_page.html"))
            )
            respx.post(f"{settings.jagriti_base_url}/get_commissions/").mock(
                return_value=Response(200, content=load_fixture(
                    "jagriti_commissions_karnataka.html"))
            )

            # Test partial state name
            state_id, commission_id = await client.resolve_state_and_commission_ids(
                "Karnataka",  # Different case
                "Bangalore Urban"  # Partial commission name
            )

            assert state_id == "29"
            assert commission_id == "29_1"

    async def test_resolve_state_and_commission_ids_not_found(self, client):
        """Test error handling when state or commission is not found."""
        settings = get_settings()

        with respx.mock:
            respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
                return_value=Response(
                    200, content=load_fixture("jagriti_search_page.html"))
            )

            # Test with non-existent state
            with pytest.raises(ValueError) as exc_info:
                await client.resolve_state_and_commission_ids(
                    "NONEXISTENT_STATE",
                    "Some Commission"
                )

            assert "not found" in str(exc_info.value)
            assert "Available:" in str(exc_info.value)

    async def test_date_normalization(self, client):
        """Test date normalization functionality."""
        # Test various date formats
        assert client._normalize_date("15/03/2023") == "2023-03-15"
        assert client._normalize_date("15-03-2023") == "2023-03-15"
        assert client._normalize_date("2023-03-15") == "2023-03-15"
        assert client._normalize_date("Mar 15, 2023") == "2023-03-15"
        assert client._normalize_date("") == ""
        assert client._normalize_date("   ") == ""

    async def test_document_link_normalization(self, client):
        """Test document link normalization functionality."""
        base_url = "https://e-jagriti.gov.in"
        client.base_url = base_url

        # Test relative URL
        assert client._normalize_document_link(
            "/documents/case123.pdf") == f"{base_url}/documents/case123.pdf"

        # Test absolute URL
        assert client._normalize_document_link(
            "https://example.com/doc.pdf") == "https://example.com/doc.pdf"

        # Test empty link
        assert client._normalize_document_link("") == ""
        assert client._normalize_document_link("   ") == ""

    async def test_search_type_mapping(self, client):
        """Test that search types are correctly mapped to Jagriti parameters."""
        expected_mappings = {
            "case_number": "case_no",
            "complainant": "complainant_name",
            "respondent": "respondent_name",
            "complainant_advocate": "complainant_advocate_name",
            "respondent_advocate": "respondent_advocate_name",
            "industry_type": "industry_type",
            "judge": "judge_name",
        }

        assert client.SEARCH_TYPE_MAPPING == expected_mappings

    async def test_concurrent_request_limiting(self, client):
        """Test that concurrent requests are properly limited."""
        settings = get_settings()

        # This test verifies that the semaphore is created with correct limit
        from app.services.jagriti_client import get_rate_limit_semaphore

        semaphore = get_rate_limit_semaphore()
        assert semaphore._value == settings.jagriti_concurrent_limit

    async def test_api_error_handling(self, client):
        """Test proper handling of various API errors."""
        settings = get_settings()

        with respx.mock:
            # Mock 500 error that gets retried but keeps failing
            respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
                return_value=Response(500, content="Internal Server Error")
            )

            # The client will fallback to default states, so we expect it to succeed
            # but will log errors during the process
            states = await client.fetch_states()
            # Should return fallback states
            assert len(states) > 0
            assert all(isinstance(state, StateInfo) for state in states)

    async def test_timeout_error_handling(self, client):
        """Test proper handling of timeout errors."""
        import httpx
        settings = get_settings()

        with respx.mock:
            # Mock timeout exception that gets retried
            respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
                side_effect=httpx.TimeoutException("Request timed out")
            )

            # The client will fallback to default states when network errors occur
            # This tests the resilience of the system
            states = await client.fetch_states()
            # Should return fallback states
            assert len(states) > 0
            assert all(isinstance(state, StateInfo) for state in states)


@pytest.mark.asyncio
async def test_get_jagriti_client_singleton():
    """Test that get_jagriti_client returns the same instance."""
    client1 = get_jagriti_client()
    client2 = get_jagriti_client()

    assert client1 is client2
    assert isinstance(client1, JagritiClient)


@pytest.mark.asyncio
async def test_rate_limiting_with_multiple_requests():
    """Test rate limiting behavior with multiple concurrent requests."""
    settings = get_settings()
    client = JagritiClient()

    with respx.mock:
        respx.get(f"{settings.jagriti_base_url}/daily_order_search/").mock(
            return_value=Response(
                200, content=load_fixture("jagriti_search_page.html"))
        )

        # Make multiple concurrent requests
        import asyncio
        tasks = [client.fetch_states() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed (though some may be cached)
        assert all(not isinstance(r, Exception) for r in results)


@pytest.mark.asyncio
async def test_browser_emulation_headers():
    """Test that proper browser emulation headers are used."""
    client = JagritiClient()

    headers = client.default_headers
    assert "User-Agent" in headers
    assert "Mozilla" in headers["User-Agent"]
    assert "Accept" in headers
    assert "Accept-Language" in headers
    assert headers["DNT"] == "1"  # Do Not Track
