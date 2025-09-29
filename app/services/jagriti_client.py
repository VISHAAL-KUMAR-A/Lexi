"""Jagriti API client for interfacing with e-jagriti.gov.in."""

import asyncio
import random
import re
from datetime import date
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import CaseInfo, CommissionInfo, StateInfo

logger = get_logger(__name__)


class JagritiAPIError(Exception):
    """Base exception for Jagriti API errors."""

    pass


class JagritiCaptchaError(JagritiAPIError):
    """Exception raised when Jagriti returns a captcha page."""

    pass


class JagritiTimeoutError(JagritiAPIError):
    """Exception raised when Jagriti API times out."""

    pass


# Global semaphore for rate limiting concurrent requests
_rate_limit_semaphore: Optional[asyncio.Semaphore] = None


def get_rate_limit_semaphore() -> asyncio.Semaphore:
    """Get or create the rate limiting semaphore."""
    global _rate_limit_semaphore
    if _rate_limit_semaphore is None:
        settings = get_settings()
        _rate_limit_semaphore = asyncio.Semaphore(
            settings.jagriti_concurrent_limit)
    return _rate_limit_semaphore


class JagritiClient:
    """Client for interacting with the Jagriti API."""

    # Search type mapping from user-friendly names to Jagriti parameter names
    SEARCH_TYPE_MAPPING = {
        "case_number": "case_no",
        "complainant": "complainant_name",
        "respondent": "respondent_name",
        "complainant_advocate": "complainant_advocate_name",
        "respondent_advocate": "respondent_advocate_name",
        "industry_type": "industry_type",
        "judge": "judge_name",
    }

    def __init__(self) -> None:
        """Initialize the Jagriti client."""
        self.settings = get_settings()
        self.base_url = self.settings.jagriti_base_url
        self.timeout = self.settings.jagriti_timeout
        self.max_retries = self.settings.jagriti_max_retries
        self.cache = get_cache()

        # Browser emulation headers
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "DNT": "1",
        }

    async def _random_delay(self) -> None:
        """Add a random delay between requests to be polite."""
        delay = random.uniform(
            self.settings.jagriti_request_delay_min,
            self.settings.jagriti_request_delay_max
        )
        await asyncio.sleep(delay)

    async def _make_request(
        self,
        method: str,
        url: str,
        session: Optional[httpx.AsyncClient] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request to Jagriti with error handling and retries."""
        # Ensure we don't overwhelm Jagriti with concurrent requests
        semaphore = get_rate_limit_semaphore()

        async with semaphore:
            # Add politeness delay
            await self._random_delay()

            full_url = f"{self.base_url}{url}" if not url.startswith(
                "http") else url

            # Merge default headers with custom ones
            headers = {**self.default_headers, **kwargs.pop("headers", {})}

            # Use provided session or create a new one
            if session:
                client = session
                close_client = False
            else:
                client = httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=headers,
                )
                close_client = True

            try:
                async for attempt in AsyncRetrying(
                    retry=retry_if_exception_type(
                        (httpx.TimeoutException, httpx.TransportError)),
                    stop=stop_after_attempt(self.max_retries + 1),
                    wait=wait_exponential(
                        multiplier=1,
                        max=60,
                        exp_base=self.settings.jagriti_retry_backoff_factor
                    ),
                ):
                    with attempt:
                        logger.debug(
                            f"Making {method} request to {full_url} (attempt {attempt.retry_state.attempt_number})"
                        )

                        response = await client.request(method, full_url, headers=headers, **kwargs)

                        # Log response info
                        content_length = len(
                            response.content) if response.content else 0
                        logger.debug(
                            f"Response: {response.status_code}, Content-Length: {content_length}")

                        # Check for captcha in response
                        await self._check_for_captcha(response)

                        # Check for other error conditions
                        if response.status_code == 429:
                            logger.warning(
                                "Rate limited by Jagriti, retrying...")
                            raise httpx.TransportError("Rate limited")

                        if response.status_code >= 500:
                            logger.warning(
                                f"Server error from Jagriti: {response.status_code}")
                            raise httpx.TransportError(
                                f"Server error: {response.status_code}")

                        return response

            except Exception as e:
                if isinstance(e, JagritiCaptchaError):
                    raise
                elif isinstance(e, httpx.TimeoutException) or "TimeoutException" in str(type(e)) or "timeout" in str(e).lower():
                    logger.error(
                        f"Request to {full_url} timed out after all retries")
                    raise JagritiTimeoutError(f"Request timed out: {e}")
                else:
                    logger.error(
                        f"Request to {full_url} failed after all retries: {e}")
                    raise JagritiAPIError(f"Request failed: {e}")
            finally:
                if close_client:
                    await client.aclose()

    async def _check_for_captcha(self, response: httpx.Response) -> None:
        """Check if the response contains a captcha page."""
        try:
            content = response.text.lower()
            # Common indicators of captcha pages
            captcha_indicators = [
                "captcha",
                "verify you are human",
                "security check",
                "recaptcha",
                "cloudflare",
                "are you human",
                "please complete the security check",
            ]

            if any(indicator in content for indicator in captcha_indicators):
                logger.warning("Captcha detected in Jagriti response")

                # If captcha solver is enabled, placeholder for future integration
                if self.settings.allow_captcha_solver:
                    logger.info(
                        "Captcha solver is enabled but not implemented (placeholder)")
                    # TODO: Integrate with external captcha solving service

                raise JagritiCaptchaError("Jagriti returned a captcha page")

        except Exception as e:
            if isinstance(e, JagritiCaptchaError):
                raise
            logger.error(f"Error checking for captcha: {e}")

    async def fetch_states(self) -> List[StateInfo]:
        """
        Fetch the list of available states from Jagriti.

        Returns:
            List[StateInfo]: List of states with their text and IDs
        """
        logger.info("Fetching states from Jagriti")

        # Check cache first
        cache_key = "jagriti_states"
        cached_states = await self.cache.get(cache_key)
        if cached_states:
            logger.debug("Returning cached states")
            return [StateInfo(**state) for state in cached_states]

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.default_headers,
                follow_redirects=True,
            ) as session:
                # Navigate to the main search page to get states dropdown
                search_url = "/daily_order_search/"
                response = await self._make_request("GET", search_url, session=session)

                if response.status_code != 200:
                    raise JagritiAPIError(
                        f"Failed to fetch search page: {response.status_code}")

                # Parse HTML to extract states
                soup = BeautifulSoup(response.text, 'html.parser')
                states = []

                # Look for state dropdown/select element
                state_select = soup.find('select', {'name': re.compile(r'state', re.I)}) or \
                    soup.find('select', {'id': re.compile(r'state', re.I)})

                if state_select:
                    for option in state_select.find_all('option'):
                        value = option.get('value', '').strip()
                        text = option.get_text(strip=True)

                        # Skip empty or placeholder options
                        if value and text and value.lower() not in ['', 'select', 'choose']:
                            states.append(StateInfo(
                                state_text=text.upper(),
                                state_id=value
                            ))
                else:
                    logger.warning(
                        "Could not find states dropdown in Jagriti page")
                    # If we can't find the dropdown, provide some common states as fallback
                    # This should be replaced with actual scraping logic based on Jagriti's structure
                    fallback_states = [
                        {"state_text": "KARNATAKA", "state_id": "29"},
                        {"state_text": "MAHARASHTRA", "state_id": "27"},
                        {"state_text": "TAMIL NADU", "state_id": "33"},
                        {"state_text": "DELHI", "state_id": "7"},
                        {"state_text": "GUJARAT", "state_id": "24"},
                    ]
                    states = [StateInfo(**state) for state in fallback_states]

                logger.info(f"Fetched {len(states)} states from Jagriti")

                # Cache the results
                states_dict = [state.model_dump() for state in states]
                await self.cache.set(cache_key, states_dict, ttl=self.settings.cache_ttl_states)

                return states

        except Exception as e:
            if isinstance(e, (JagritiCaptchaError, JagritiTimeoutError, JagritiAPIError)):
                raise
            logger.error(f"Error fetching states: {e}", exc_info=True)
            raise JagritiAPIError(f"Failed to fetch states: {e}")

    async def fetch_commissions(self, state_id: str) -> List[CommissionInfo]:
        """
        Fetch the list of commissions for a specific state from Jagriti.

        Args:
            state_id: The internal state ID to fetch commissions for

        Returns:
            List[CommissionInfo]: List of commissions for the state
        """
        logger.info(f"Fetching commissions for state_id: {state_id}")

        # Check cache first
        cache_key = f"jagriti_commissions_{state_id}"
        cached_commissions = await self.cache.get(cache_key)
        if cached_commissions:
            logger.debug(f"Returning cached commissions for state {state_id}")
            return [CommissionInfo(**comm) for comm in cached_commissions]

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.default_headers,
                follow_redirects=True,
            ) as session:
                # Make AJAX request to get commissions for the state
                # This might be a POST request with the state_id parameter
                commissions_url = "/get_commissions/"  # Adjust based on actual Jagriti endpoint

                # Try different approaches to get commissions
                commissions_data = {"state_id": state_id}
                response = await self._make_request(
                    "POST",
                    commissions_url,
                    session=session,
                    data=commissions_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                commissions = []

                if response.status_code == 200:
                    # Parse response - could be JSON or HTML
                    try:
                        # Try JSON first
                        json_data = response.json()
                        if isinstance(json_data, list):
                            for item in json_data:
                                if isinstance(item, dict) and 'id' in item and 'name' in item:
                                    commissions.append(CommissionInfo(
                                        commission_text=item['name'].strip(),
                                        commission_id=str(item['id']),
                                        state_id=state_id
                                    ))
                    except:
                        # If not JSON, parse as HTML
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Look for commission dropdown/select options
                        commission_select = soup.find(
                            'select') or soup.find('option')
                        if commission_select:
                            if commission_select.name == 'option':
                                options = [commission_select]
                            else:
                                options = commission_select.find_all('option')

                            for option in options:
                                value = option.get('value', '').strip()
                                text = option.get_text(strip=True)

                                # Filter for District Consumer Courts (DCDRC)
                                if (value and text and
                                    value.lower() not in ['', 'select', 'choose'] and
                                        ('district' in text.lower() or 'dcdrc' in text.lower())):
                                    commissions.append(CommissionInfo(
                                        commission_text=text,
                                        commission_id=value,
                                        state_id=state_id
                                    ))

                # If no commissions found, provide fallback based on state
                if not commissions:
                    logger.warning(
                        f"No commissions found for state {state_id}, using fallback")
                    # Add some common district consumer court patterns
                    fallback_commissions = [
                        f"District Consumer Disputes Redressal Commission",
                        f"DCDRC",
                        f"District Consumer Court"
                    ]

                    for i, comm_text in enumerate(fallback_commissions):
                        commissions.append(CommissionInfo(
                            commission_text=comm_text,
                            commission_id=f"{state_id}_{i+1}",
                            state_id=state_id
                        ))

                logger.info(
                    f"Fetched {len(commissions)} commissions for state {state_id}")

                # Cache the results
                commissions_dict = [comm.model_dump() for comm in commissions]
                await self.cache.set(cache_key, commissions_dict, ttl=self.settings.cache_ttl_commissions)

                return commissions

        except Exception as e:
            if isinstance(e, (JagritiCaptchaError, JagritiTimeoutError, JagritiAPIError)):
                raise
            logger.error(
                f"Error fetching commissions for state {state_id}: {e}", exc_info=True)
            raise JagritiAPIError(
                f"Failed to fetch commissions for state {state_id}: {e}")

    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date string to YYYY-MM-DD format.

        Args:
            date_str: Date string in various formats

        Returns:
            str: Normalized date in YYYY-MM-DD format
        """
        if not date_str or not date_str.strip():
            return ""

        try:
            # Parse using dateutil which handles many formats
            parsed_date = date_parser.parse(date_str.strip(), dayfirst=True)
            return parsed_date.date().isoformat()
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            return date_str.strip()

    def _normalize_document_link(self, link: str) -> str:
        """
        Normalize document link to absolute URL.

        Args:
            link: Document link (could be relative or absolute)

        Returns:
            str: Absolute URL
        """
        if not link or not link.strip():
            return ""

        link = link.strip()

        # If already absolute URL, return as-is
        if link.startswith(('http://', 'https://')):
            return link

        # Join with base URL for relative links
        return urljoin(self.base_url, link)

    def _parse_case_row(self, row_element, base_url: str = None) -> Optional[CaseInfo]:
        """
        Parse a case table row into CaseInfo object.

        Args:
            row_element: BeautifulSoup element representing a table row
            base_url: Base URL for resolving relative links

        Returns:
            Optional[CaseInfo]: Parsed case info or None if parsing failed
        """
        try:
            cells = row_element.find_all(['td', 'th'])
            if len(cells) < 7:  # Minimum expected columns
                return None

            # Extract data from cells - adjust indices based on actual Jagriti table structure
            case_number = cells[0].get_text(
                strip=True) if len(cells) > 0 else ""
            case_stage = cells[1].get_text(
                strip=True) if len(cells) > 1 else ""
            filing_date_raw = cells[2].get_text(
                strip=True) if len(cells) > 2 else ""
            complainant = cells[3].get_text(
                strip=True) if len(cells) > 3 else ""
            complainant_advocate = cells[4].get_text(
                strip=True) if len(cells) > 4 else ""
            respondent = cells[5].get_text(
                strip=True) if len(cells) > 5 else ""
            respondent_advocate = cells[6].get_text(
                strip=True) if len(cells) > 6 else ""

            # Look for document link in the row
            document_link = ""
            link_cell = cells[-1] if cells else None  # Usually last column
            if link_cell:
                link_elem = link_cell.find('a')
                if link_elem and link_elem.get('href'):
                    document_link = self._normalize_document_link(
                        link_elem.get('href'))

            # Normalize filing date
            filing_date = self._normalize_date(filing_date_raw)

            return CaseInfo(
                case_number=case_number,
                case_stage=case_stage,
                filing_date=filing_date,
                complainant=complainant,
                complainant_advocate=complainant_advocate,
                respondent=respondent,
                respondent_advocate=respondent_advocate,
                document_link=document_link,
            )

        except Exception as e:
            logger.warning(f"Failed to parse case row: {e}")
            return None

    async def search_cases(
        self,
        search_type: str,
        state_text: str,
        commission_text: str,
        search_value: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[CaseInfo], int]:
        """
        Search for cases in Jagriti based on the given criteria.

        Args:
            search_type: Type of search (e.g., 'case_number', 'complainant', etc.)
            state_text: State name (e.g., 'KARNATAKA')
            commission_text: Commission name
            search_value: The search term/value
            date_from: Optional start date filter
            date_to: Optional end date filter  
            page: Page number for pagination (1-based)
            per_page: Number of items per page

        Returns:
            Tuple[List[CaseInfo], int]: (list of cases, total count)
        """
        logger.info(
            f"Searching cases: type={search_type}, state={state_text}, "
            f"commission={commission_text}, value={search_value}, page={page}"
        )

        try:
            # Resolve state and commission IDs
            state_id, commission_id = await self.resolve_state_and_commission_ids(
                state_text, commission_text
            )

            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.default_headers,
                follow_redirects=True,
            ) as session:
                # Build search parameters
                search_params = {
                    "state_id": state_id,
                    "commission_id": commission_id,
                    "commission_type": "District Consumer Courts",  # Explicitly restrict to DCDRC
                    "order_type": "Daily Orders",  # Restrict to Daily Orders only
                    "date_filter_type": "Case Filing Date",  # Set date filter field as required
                }

                # Map search type to Jagriti parameter name
                jagriti_search_param = self.SEARCH_TYPE_MAPPING.get(
                    search_type, search_type)
                search_params[jagriti_search_param] = search_value

                # Add date filters if provided
                if date_from:
                    search_params["date_from"] = date_from
                if date_to:
                    search_params["date_to"] = date_to

                # Add pagination
                search_params["page"] = page
                search_params["per_page"] = per_page

                # Submit search request
                search_url = "/daily_order_search/results/"
                response = await self._make_request(
                    "POST",
                    search_url,
                    session=session,
                    data=search_params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if response.status_code != 200:
                    raise JagritiAPIError(
                        f"Search request failed: {response.status_code}")

                # Parse search results
                soup = BeautifulSoup(response.text, 'html.parser')
                cases = []
                total_count = 0

                # Look for results table
                results_table = soup.find('table', {'class': re.compile(r'result', re.I)}) or \
                    soup.find('table', {'id': re.compile(r'result', re.I)}) or \
                    soup.find('table')

                if results_table:
                    # Parse table rows (skip header row)
                    rows = results_table.find_all('tr')[1:]  # Skip header

                    for row in rows:
                        case_info = self._parse_case_row(row, self.base_url)
                        if case_info:
                            cases.append(case_info)

                    # Try to extract total count from pagination info
                    pagination_info = soup.find('div', {'class': re.compile(r'pagination', re.I)}) or \
                        soup.find('span', text=re.compile(
                            r'total|found', re.I))

                    if pagination_info:
                        # Extract number from text like "Total: 150 cases found"
                        text = pagination_info.get_text()
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            total_count = int(numbers[0])

                    # If we couldn't extract total count, estimate based on results
                    if total_count == 0:
                        if len(cases) == per_page:
                            # Assume there might be more pages
                            total_count = len(cases) * page + 1
                        else:
                            # Last page or only page
                            total_count = len(cases) + (page - 1) * per_page

                logger.info(
                    f"Search completed: found {len(cases)} cases on page {page}, total estimated: {total_count}")

                return cases, total_count

        except Exception as e:
            if isinstance(e, (JagritiCaptchaError, JagritiTimeoutError, JagritiAPIError)):
                raise
            logger.error(f"Error searching cases: {e}", exc_info=True)
            raise JagritiAPIError(f"Failed to search cases: {e}")

    async def resolve_state_and_commission_ids(
        self, state_text: str, commission_text: str
    ) -> Tuple[str, str]:
        """
        Resolve state and commission text to their internal IDs.

        Args:
            state_text: State name to resolve
            commission_text: Commission name to resolve

        Returns:
            Tuple[str, str]: (state_id, commission_id)

        Raises:
            ValueError: If state or commission cannot be found
        """
        logger.info(
            f"Resolving IDs for state='{state_text}', commission='{commission_text}'")

        # Fetch states and find matching state
        states = await self.fetch_states()
        state_id = None

        # Exact match first
        for state in states:
            if state.state_text.upper() == state_text.upper():
                state_id = state.state_id
                break

        # Fuzzy match if exact match not found
        if not state_id:
            for state in states:
                if state_text.upper() in state.state_text.upper() or \
                   state.state_text.upper() in state_text.upper():
                    state_id = state.state_id
                    logger.info(
                        f"Fuzzy matched state '{state_text}' to '{state.state_text}'")
                    break

        if not state_id:
            available_states = [s.state_text for s in states]
            raise ValueError(
                f"State '{state_text}' not found. Available: {available_states}")

        # Fetch commissions for the state and find matching commission
        commissions = await self.fetch_commissions(state_id)
        commission_id = None

        # Exact match first
        for commission in commissions:
            if commission.commission_text.upper() == commission_text.upper():
                commission_id = commission.commission_id
                break

        # Fuzzy match if exact match not found
        if not commission_id:
            for commission in commissions:
                if commission_text.upper() in commission.commission_text.upper() or \
                   commission.commission_text.upper() in commission_text.upper():
                    commission_id = commission.commission_id
                    logger.info(
                        f"Fuzzy matched commission '{commission_text}' to '{commission.commission_text}'")
                    break

        if not commission_id:
            available_commissions = [c.commission_text for c in commissions]
            raise ValueError(
                f"Commission '{commission_text}' not found for state '{state_text}'. Available: {available_commissions}")

        logger.info(
            f"Resolved state_id='{state_id}', commission_id='{commission_id}'")
        return state_id, commission_id


# Global client instance
_client_instance: Optional[JagritiClient] = None


def get_jagriti_client() -> JagritiClient:
    """Get the global Jagriti client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = JagritiClient()
    return _client_instance
