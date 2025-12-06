# SomniProperty Backend Tests

## Overview

Comprehensive test suite for the SomniProperty Manager backend API, database models, and integration workflows.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and test configuration
├── api/                     # API endpoint tests
│   ├── __init__.py
│   ├── test_dashboard.py    # Dashboard & NOC endpoints
│   ├── test_buildings.py    # Building CRUD operations
│   ├── test_units.py        # Unit CRUD operations
│   ├── test_tenants.py      # Tenant CRUD operations
│   ├── test_leases.py       # Lease CRUD operations
│   ├── test_payments.py     # Payment CRUD operations
│   ├── test_work_orders.py  # Work Order CRUD operations
│   ├── test_alerts.py       # Alert CRUD operations
│   └── test_hubs.py         # Hub (PropertyEdgeNode) CRUD operations
├── models/                  # Database model tests
│   ├── __init__.py
│   ├── test_property_models.py  # Property management models
│   └── test_hub_models.py       # Hub and alert models
└── integration/             # End-to-end workflow tests
    ├── __init__.py
    ├── test_lease_workflow.py        # Complete lease lifecycle
    ├── test_maintenance_workflow.py  # Work order workflows
    └── test_alert_workflow.py        # Alert management workflows
```

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure database is running
# Tests use conftest.py fixtures for database setup
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Suites

```bash
# API tests only
pytest tests/api/ -v

# Model tests only
pytest tests/models/ -v

# Integration tests only
pytest tests/integration/ -v
```

### Run Specific Test Files

```bash
# Dashboard tests
pytest tests/api/test_dashboard.py -v

# Building tests
pytest tests/api/test_buildings.py -v

# Lease workflow
pytest tests/integration/test_lease_workflow.py -v
```

### Run Specific Test Cases

```bash
# Single test method
pytest tests/api/test_dashboard.py::TestPropertyDashboard::test_get_dashboard_stats -v

# All tests in a class
pytest tests/api/test_buildings.py::TestBuildingsAPI -v
```

## Test Fixtures

### From `conftest.py`

- **`db_session`**: Async database session for model tests
- **`client`**: Async HTTP client for API tests
- **`admin_headers`**: Authentication headers for admin user
- **`sample_building`**: Pre-created building for testing
- **`sample_unit`**: Pre-created unit for testing
- **`sample_tenant`**: Pre-created tenant for testing

### Example Usage

```python
@pytest.mark.asyncio
async def test_create_building(client: AsyncClient, admin_headers):
    response = await client.post(
        "/api/v1/buildings",
        headers=admin_headers,
        json={"name": "Test Building", ...}
    )
    assert response.status_code == 201
```

## Test Coverage

### API Endpoints (~90 tests)
- ✅ All CRUD operations (Create, Read, Update, Delete)
- ✅ Filtering and pagination
- ✅ Authentication requirements
- ✅ Error handling (404, 401, validation errors)
- ✅ Dashboard metrics and summaries

### Database Models (~18 tests)
- ✅ Model creation and validation
- ✅ Relationship integrity (Foreign keys)
- ✅ Cascade behaviors
- ✅ Data constraints

### Integration Workflows (~11 tests)
- ✅ Complete lease workflow (Building → Unit → Tenant → Lease → Payment)
- ✅ Work order lifecycle (Creation → In Progress → Completed)
- ✅ Alert management (Creation → Acknowledgment → Resolution)
- ✅ Hub status changes and monitoring

## Writing New Tests

### API Test Template

```python
import pytest
from httpx import AsyncClient

class TestMyAPI:
    @pytest.mark.asyncio
    async def test_list_items(self, client: AsyncClient, admin_headers):
        """Test GET /api/v1/items returns list"""
        response = await client.get("/api/v1/items", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_item(self, client: AsyncClient, admin_headers):
        """Test POST /api/v1/items creates new item"""
        item_data = {"name": "Test Item"}
        
        response = await client.post(
            "/api/v1/items",
            headers=admin_headers,
            json=item_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == item_data["name"]
        assert "id" in data
```

### Model Test Template

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import MyModel

class TestMyModel:
    @pytest.mark.asyncio
    async def test_create_model(self, db_session: AsyncSession):
        """Test creating a model instance"""
        instance = MyModel(name="Test", value=123)
        
        db_session.add(instance)
        await db_session.commit()
        await db_session.refresh(instance)
        
        assert instance.id is not None
        assert instance.name == "Test"
```

### Integration Test Template

```python
import pytest
from httpx import AsyncClient

class TestMyWorkflow:
    @pytest.mark.asyncio
    async def test_complete_workflow(self, client: AsyncClient, admin_headers):
        """Test complete end-to-end workflow"""
        # Step 1: Create resource A
        response_a = await client.post(
            "/api/v1/resource-a",
            headers=admin_headers,
            json={"name": "A"}
        )
        resource_a_id = response_a.json()["id"]
        
        # Step 2: Create resource B linked to A
        response_b = await client.post(
            "/api/v1/resource-b",
            headers=admin_headers,
            json={"resource_a_id": resource_a_id, "name": "B"}
        )
        
        # Step 3: Verify relationship
        verify_response = await client.get(
            f"/api/v1/resource-a/{resource_a_id}",
            headers=admin_headers
        )
        assert verify_response.status_code == 200
```

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on other tests
2. **Async/Await**: Always use `@pytest.mark.asyncio` for async tests
3. **Descriptive Names**: Use clear, descriptive test names that explain what is being tested
4. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
5. **Clean Up**: Use fixtures for setup/teardown to keep tests clean
6. **Error Cases**: Test both success and failure scenarios
7. **Authentication**: Always include authentication tests for protected endpoints

## Continuous Integration

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Debugging Tests

### Run with verbose output
```bash
pytest -vv
```

### Show print statements
```bash
pytest -s
```

### Stop on first failure
```bash
pytest -x
```

### Run only failed tests from last run
```bash
pytest --lf
```

### Debug with pdb
```bash
pytest --pdb
```

## Common Issues

### Database Connection Errors
- Ensure PostgreSQL is running
- Check `DATABASE_URL` environment variable
- Verify database credentials in `.env`

### Async Warnings
- Make sure all async functions use `@pytest.mark.asyncio`
- Check `pytest.ini` has `asyncio_mode = auto`

### Import Errors
- Run tests from the backend directory: `cd backend && pytest`
- Check `PYTHONPATH` includes the backend directory

## Coverage Reports

### Generate coverage report
```bash
pytest --cov=. --cov-report=html
```

### View coverage
```bash
open htmlcov/index.html
```

---

**Last Updated**: 2025-11-19  
**Test Count**: ~119 backend tests
