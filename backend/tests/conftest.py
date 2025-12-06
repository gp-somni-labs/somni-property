"""
Pytest Configuration and Fixtures
Provides reusable test fixtures for database, API client, and authentication
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from main import app
from db.database import get_db
from db.models import Base
from core.config import settings

# Test database URL (use in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ============================================================================
# ASYNCIO EVENT LOOP
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the entire test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
async def test_engine():
    """Create a test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(test_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing FastAPI endpoints

    This client automatically uses the test database session
    """
    # Override the get_db dependency to use test session
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # Create async client
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # Clear overrides after test
    app.dependency_overrides.clear()


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def admin_headers() -> dict:
    """Headers for admin user (bypassing Authelia)"""
    return {
        "X-Forwarded-User": "admin",
        "X-Forwarded-Email": "admin@property.local",
        "X-Forwarded-Name": "Admin User",
        "X-Forwarded-Groups": "admins,property-managers"
    }


@pytest.fixture
def manager_headers() -> dict:
    """Headers for manager user"""
    return {
        "X-Forwarded-User": "manager",
        "X-Forwarded-Email": "manager@property.local",
        "X-Forwarded-Name": "Property Manager",
        "X-Forwarded-Groups": "managers,property-managers"
    }


@pytest.fixture
def tenant_headers() -> dict:
    """Headers for tenant user"""
    return {
        "X-Forwarded-User": "tenant1",
        "X-Forwarded-Email": "tenant1@example.com",
        "X-Forwarded-Name": "John Doe",
        "X-Forwarded-Groups": "tenants"
    }


@pytest.fixture
def no_auth_headers() -> dict:
    """Headers with no authentication (should fail)"""
    return {}


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
async def sample_property(test_session):
    """Create a sample property for testing"""
    from db.models import Property
    from uuid import uuid4

    property = Property(
        id=uuid4(),
        name="Oak Street Apartments",
        address_line1="123 Oak Street",
        city="Portland",
        state="OR",
        zip_code="97201",
        property_type="residential"
    )

    test_session.add(property)
    await test_session.commit()
    await test_session.refresh(property)

    return property


@pytest.fixture
async def sample_building(test_session, sample_property):
    """Create a sample building for testing"""
    from db.models import Building

    building = Building(
        property_id=sample_property.id,
        name="Building A",
        floors=3,
        total_units=12
    )

    test_session.add(building)
    await test_session.commit()
    await test_session.refresh(building)

    return building


@pytest.fixture
async def sample_unit(test_session, sample_building):
    """Create a sample unit for testing"""
    from db.models import Unit
    from decimal import Decimal

    unit = Unit(
        building_id=sample_building.id,
        unit_number="101",
        floor=1,
        bedrooms=Decimal("2.0"),
        bathrooms=Decimal("1.0"),
        monthly_rent=Decimal("1500.00"),
        status="vacant"
    )

    test_session.add(unit)
    await test_session.commit()
    await test_session.refresh(unit)

    return unit


@pytest.fixture
async def sample_tenant(test_session):
    """Create a sample tenant for testing"""
    from db.models import Tenant

    tenant = Tenant(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="503-555-0123",
        status="active",
        portal_enabled=True,
        auth_user_id="tenant1"
    )

    test_session.add(tenant)
    await test_session.commit()
    await test_session.refresh(tenant)

    return tenant


@pytest.fixture
async def sample_lease(test_session, sample_unit, sample_tenant):
    """Create a sample lease for testing"""
    from db.models import Lease
    from datetime import date, timedelta
    from decimal import Decimal

    lease = Lease(
        unit_id=sample_unit.id,
        tenant_id=sample_tenant.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        monthly_rent=Decimal("1500.00"),
        security_deposit=Decimal("1500.00"),
        status="active"
    )

    test_session.add(lease)
    await test_session.commit()
    await test_session.refresh(lease)

    return lease
