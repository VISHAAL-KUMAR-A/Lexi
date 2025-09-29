# Lexi Case Search API

A FastAPI backend that proxies and normalizes case-search results from Jagriti (https://e-jagriti.gov.in). This API provides a clean, standardized interface for searching legal cases across different states and commissions in India.

## Features

- **Multi-criteria case search**: Search by case number, complainant, respondent, advocates, industry type, or judge
- **State and commission management**: Retrieve available states and their corresponding commissions
- **Caching**: Intelligent caching for improved performance (24-hour TTL for metadata)
- **Error handling**: Comprehensive error handling including captcha detection
- **Async architecture**: Built with FastAPI and httpx for high performance
- **Type safety**: Full type hints and Pydantic models for request/response validation
- **Testing**: Comprehensive test suite with mocking for external services

## API Endpoints

### Deployed API
**Live API URL**: https://lexi-2zo3.onrender.com
**Interactive Documentation**: https://lexi-2zo3.onrender.com/docs

### Meta Endpoints
- `GET /states` - Get list of available states
- `GET /commissions/{state_id}` - Get commissions for a specific state

### Case Search Endpoints
All case search endpoints use POST method with JSON request body:

- `POST /cases/by-case-number` - Search by case number
- `POST /cases/by-complainant` - Search by complainant name
- `POST /cases/by-respondent` - Search by respondent name
- `POST /cases/by-complainant-advocate` - Search by complainant's advocate
- `POST /cases/by-respondent-advocate` - Search by respondent's advocate
- `POST /cases/by-industry-type` - Search by industry type
- `POST /cases/by-judge` - Search by judge name

### Utility Endpoints
- `GET /` - API information and endpoint listing
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)

## Installation and Setup

### Prerequisites
- Python 3.11+
- pip or poetry for package management

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lexi-case-search-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Install pre-commit hooks** (optional but recommended)
   ```bash
   pre-commit install
   ```

6. **Run the application**
   ```bash
   # Using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Or using the Python module
   python -m app.main
   ```

The API will be available at:
- **Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

For production deployment, see: https://lexi-2zo3.onrender.com

## Configuration

Environment variables can be set in a `.env` file or as system environment variables:

```bash
# Application settings
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Jagriti API settings
JAGRITI_BASE_URL=https://e-jagriti.gov.in
JAGRITI_TIMEOUT=30
JAGRITI_MAX_RETRIES=3

# Cache settings
CACHE_TTL_STATES=86400
CACHE_TTL_COMMISSIONS=86400

# API settings
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

## API Usage Examples

### 1. Get Available States

```bash
curl -X GET "https://lexi-2zo3.onrender.com/states" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "states": [
    {
      "state_text": "KARNATAKA",
      "state_id": "29"
    },
    {
      "state_text": "MAHARASHTRA", 
      "state_id": "27"
    },
    {
      "state_text": "DELHI",
      "state_id": "7"
    }
  ]
}
```

### 2. Get Commissions for a State

```bash
curl -X GET "https://lexi-2zo3.onrender.com/commissions/29" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "commissions": [
    {
      "commission_text": "District Consumer Disputes Redressal Commission",
      "commission_id": "29_1",
      "state_id": "29"
    },
    {
      "commission_text": "DCDRC",
      "commission_id": "29_2",
      "state_id": "29"
    },
    {
      "commission_text": "District Consumer Court",
      "commission_id": "29_3",
      "state_id": "29"
    }
  ],
  "state_id": "29"
}
```

### 3. Search Cases by Case Number

```bash
curl -X POST "https://lexi-2zo3.onrender.com/cases/by-case-number" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "KARNATAKA",
    "commission": "District Consumer Disputes Redressal Commission",
    "search_value": "CC/123/2023",
    "date_from": "2023-01-01",
    "date_to": "2023-12-31",
    "page": 1,
    "per_page": 20
  }'
```

### 4. Search Cases by Complainant

```bash
curl -X POST "https://lexi-2zo3.onrender.com/cases/by-complainant" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "KARNATAKA",
    "commission": "District Consumer Disputes Redressal Commission",
    "search_value": "John Doe",
    "page": 1,
    "per_page": 20
  }'
```

### 5. Search Cases by Respondent

```bash
curl -X POST "https://lexi-2zo3.onrender.com/cases/by-respondent" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "KARNATAKA",
    "commission": "District Consumer Disputes Redressal Commission",
    "search_value": "XYZ Corporation",
    "page": 1,
    "per_page": 10
  }'
```

### 6. Search Cases by Complainant Advocate

```bash
curl -X POST "https://lexi-2zo3.onrender.com/cases/by-complainant-advocate" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "KARNATAKA",
    "commission": "District Consumer Disputes Redressal Commission",
    "search_value": "Advocate Name",
    "page": 1,
    "per_page": 20
  }'
```

### 7. Search Cases by Industry Type

```bash
curl -X POST "https://lexi-2zo3.onrender.com/cases/by-industry-type" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "KARNATAKA",
    "commission": "District Consumer Disputes Redressal Commission",
    "search_value": "Banking",
    "page": 1,
    "per_page": 20
  }'
```

### 8. Search Cases by Judge

```bash
curl -X POST "https://lexi-2zo3.onrender.com/cases/by-judge" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "KARNATAKA",
    "commission": "District Consumer Disputes Redressal Commission",
    "search_value": "Judge Name",
    "page": 1,
    "per_page": 20
  }'
```

**Expected Response for Case Searches:**
```json
{
  "cases": [
    {
      "case_number": "CC/123/2023",
      "case_stage": "Pending",
      "filing_date": "2023-01-15",
      "complainant": "John Doe",
      "complainant_advocate": "Advocate A",
      "respondent": "XYZ Company",
      "respondent_advocate": "Advocate B",
      "document_link": "https://e-jagriti.gov.in/documents/123"
    }
  ],
  "total_count": 1,
  "page": 1,
  "per_page": 20,
  "total_pages": 1
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

### Captcha Error (503)
```json
{
  "detail": "captcha_required",
  "captcha": true,
  "message": "Jagriti returned a captcha; request cannot be completed automatically."
}
```

### Validation Error (400)
```json
{
  "detail": "state, commission, and search_value are required"
}
```

### Not Found Error (404)
```json
{
  "detail": "No commissions found for state ID: INVALID"
}
```

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_routes_cases.py

# Run tests with verbose output
pytest -v
```

### Test Structure
- `tests/test_routes_meta.py` - Tests for states and commissions endpoints
- `tests/test_routes_cases.py` - Tests for case search endpoints
- `tests/test_jagriti_client.py` - Tests for Jagriti client functionality
- `tests/test_integration.py` - Integration tests with mocked responses

## Development

### Code Quality
The project uses several tools for code quality:

- **Ruff**: Fast Python linter and formatter
- **Black**: Code formatting
- **isort**: Import sorting
- **MyPy**: Static type checking
- **Pre-commit**: Git hooks for code quality

### Run Linting
```bash
# Run ruff
ruff check .
ruff format .

# Run mypy
mypy app/

# Run all pre-commit hooks
pre-commit run --all-files
```

## Deployment

### Environment Variables for Production
Set these environment variables for production deployment:

```bash
DEBUG=false
LOG_LEVEL=WARNING
JAGRITI_TIMEOUT=60
CACHE_TTL_STATES=86400
CACHE_TTL_COMMISSIONS=86400
```

### Deployment on Render

**Live Deployment**: https://lexi-2zo3.onrender.com

The application is successfully deployed on Render with the following configuration:
1. Build command: `pip install -r requirements.txt`
2. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Environment variables configured for production
4. Auto-deployment on push to main branch

### Alternative Deployment Options

#### Railway
1. Connect your GitHub repository to Railway
2. Railway will auto-detect the Python app
3. Add environment variables in the Railway dashboard
4. Deploy automatically on push to main branch

## Submission Checklist

- [x] **Complete FastAPI application** with all required endpoints
- [x] **Pydantic models** for request/response validation
- [x] **Async architecture** with httpx client
- [x] **Comprehensive error handling** including captcha detection
- [x] **Caching mechanism** for states and commissions
- [x] **Type hints** throughout the codebase
- [x] **Comprehensive test suite** with respx mocking
- [x] **Pre-commit hooks** for code quality
- [x] **Documentation** with API examples
- [x] **Hosted URL**: https://lexi-2zo3.onrender.com
- [x] **Interactive API Documentation**: https://lexi-2zo3.onrender.com/docs
- [x] **README with run instructions** and comprehensive API documentation

## API Schema

The API follows a consistent schema for all requests and responses:

### Case Search Request Schema
All case search endpoints (`/cases/by-*`) accept the following JSON request body:

```json
{
  "state": "string",                    // Required: State name (e.g., "KARNATAKA")
  "commission": "string",               // Required: Commission name
  "search_value": "string",             // Required: Search term specific to endpoint
  "date_from": "YYYY-MM-DD",           // Optional: Start date filter
  "date_to": "YYYY-MM-DD",             // Optional: End date filter
  "page": 1,                           // Optional: Page number (default: 1)
  "per_page": 20                       // Optional: Results per page (default: 20, max: 100)
}
```

### Case Search Response Schema
```json
{
  "cases": [
    {
      "case_number": "string",
      "case_stage": "string", 
      "filing_date": "YYYY-MM-DD",
      "complainant": "string",
      "complainant_advocate": "string",
      "respondent": "string",
      "respondent_advocate": "string",
      "document_link": "https://..."
    }
  ],
  "total_count": 1,
  "page": 1,
  "per_page": 20,
  "total_pages": 1
}
```

### State Response Schema
```json
{
  "states": [
    {
      "state_text": "string",
      "state_id": "string"
    }
  ]
}
```

### Commission Response Schema
```json
{
  "commissions": [
    {
      "commission_text": "string",
      "commission_id": "string",
      "state_id": "string"
    }
  ],
  "state_id": "string"
}
```

## Support

For issues or questions:
1. **Live API Documentation**: https://lexi-2zo3.onrender.com/docs - Interactive API testing
2. **API Base URL**: https://lexi-2zo3.onrender.com - Production endpoint
3. Review the test files for usage examples (`tests/` directory)
4. Check the logs for detailed error information

### Quick Test
Try the health check endpoint:
```bash
curl https://lexi-2zo3.onrender.com/health
```

## License

This project is licensed under the MIT License.
