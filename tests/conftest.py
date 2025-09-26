"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_states_data():
    """Sample states data for testing."""
    return [
        {"state_text": "KARNATAKA", "state_id": "KA"},
        {"state_text": "MAHARASHTRA", "state_id": "MH"},
        {"state_text": "DELHI", "state_id": "DL"},
    ]


@pytest.fixture
def sample_commissions_data():
    """Sample commissions data for testing."""
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


@pytest.fixture
def sample_cases_data():
    """Sample cases data for testing."""
    return [
        {
            "case_number": "CC/123/2023",
            "case_stage": "Pending",
            "filing_date": "2023-01-15",
            "complainant": "John Doe",
            "complainant_advocate": "Advocate A",
            "respondent": "XYZ Company",
            "respondent_advocate": "Advocate B",
            "document_link": "https://e-jagriti.gov.in/documents/123",
        },
        {
            "case_number": "CC/124/2023",
            "case_stage": "Disposed",
            "filing_date": "2023-02-10",
            "complainant": "Jane Smith",
            "complainant_advocate": "Advocate C",
            "respondent": "ABC Corp",
            "respondent_advocate": "Advocate D",
            "document_link": "https://e-jagriti.gov.in/documents/124",
        },
    ]


@pytest.fixture
def mock_jagriti_html_states():
    """Mock HTML response for Jagriti states page."""
    return """
    <html>
    <body>
        <select id="states">
            <option value="KA">KARNATAKA</option>
            <option value="MH">MAHARASHTRA</option>
            <option value="DL">DELHI</option>
        </select>
    </body>
    </html>
    """


@pytest.fixture
def mock_jagriti_html_commissions():
    """Mock HTML response for Jagriti commissions page."""
    return """
    <html>
    <body>
        <select id="commissions">
            <option value="KA_STATE">Karnataka State Consumer Disputes Redressal Commission</option>
            <option value="KA_BANGALORE">Bangalore Urban District Consumer Disputes Redressal Forum</option>
        </select>
    </body>
    </html>
    """


@pytest.fixture
def mock_jagriti_html_cases():
    """Mock HTML response for Jagriti cases search results."""
    return """
    <html>
    <body>
        <table id="results">
            <tr>
                <td>CC/123/2023</td>
                <td>Pending</td>
                <td>2023-01-15</td>
                <td>John Doe</td>
                <td>Advocate A</td>
                <td>XYZ Company</td>
                <td>Advocate B</td>
                <td><a href="https://e-jagriti.gov.in/documents/123">View</a></td>
            </tr>
            <tr>
                <td>CC/124/2023</td>
                <td>Disposed</td>
                <td>2023-02-10</td>
                <td>Jane Smith</td>
                <td>Advocate C</td>
                <td>ABC Corp</td>
                <td>Advocate D</td>
                <td><a href="https://e-jagriti.gov.in/documents/124">View</a></td>
            </tr>
        </table>
        <div class="pagination">Total: 2 results</div>
    </body>
    </html>
    """


@pytest.fixture
def mock_jagriti_captcha_html():
    """Mock HTML response with captcha."""
    return """
    <html>
    <body>
        <div class="captcha">
            <h2>Security Check</h2>
            <p>Please verify you are human</p>
            <script src="https://www.google.com/recaptcha/api.js"></script>
        </div>
    </body>
    </html>
    """
