"""
Tests for Property Management database models
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import date, timedelta

from db.models import (
    Building,
    Unit,
    Tenant,
    Lease,
    Payment,
    WorkOrder
)


class TestBuildingModel:
    """Test Building model relationships and constraints"""

    @pytest.mark.asyncio
    async def test_create_building(self, db_session: AsyncSession):
        """Test creating a building"""
        building = Building(
            name="Test Building",
            address="123 Test St",
            city="Test City",
            state="CA",
            zip_code="12345",
            building_type="residential",
            total_units=10
        )
        
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        
        assert building.id is not None
        assert building.name == "Test Building"
        assert building.total_units == 10

    @pytest.mark.asyncio
    async def test_building_units_relationship(self, db_session: AsyncSession):
        """Test Building -> Units relationship"""
        # Create building
        building = Building(
            name="Building with Units",
            address="456 Test Ave",
            city="Test City",
            state="NY",
            zip_code="54321",
            building_type="residential",
            total_units=5
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        
        # Create units for this building
        for i in range(3):
            unit = Unit(
                building_id=building.id,
                unit_number=f"{i+1}01",
                floor=i + 1,
                bedrooms=2,
                bathrooms=1,
                square_feet=850,
                monthly_rent=1500.00,
                status="available"
            )
            db_session.add(unit)
        
        await db_session.commit()
        
        # Verify relationship
        result = await db_session.execute(
            select(Building).where(Building.id == building.id)
        )
        fetched_building = result.scalar_one()
        
        assert len(fetched_building.units) == 3


class TestUnitModel:
    """Test Unit model relationships and constraints"""

    @pytest.mark.asyncio
    async def test_create_unit(self, db_session: AsyncSession):
        """Test creating a unit"""
        # Create building first
        building = Building(
            name="Unit Test Building",
            address="789 Unit St",
            city="Unit City",
            state="TX",
            zip_code="78901",
            building_type="residential",
            total_units=5
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        
        # Create unit
        unit = Unit(
            building_id=building.id,
            unit_number="101",
            floor=1,
            bedrooms=2,
            bathrooms=1,
            square_feet=850,
            monthly_rent=1500.00,
            status="available"
        )
        
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)
        
        assert unit.id is not None
        assert unit.unit_number == "101"
        assert unit.building_id == building.id

    @pytest.mark.asyncio
    async def test_unit_building_relationship(self, db_session: AsyncSession):
        """Test Unit -> Building relationship"""
        # Create building and unit
        building = Building(
            name="Relationship Test Building",
            address="111 Relation St",
            city="Relation City",
            state="WA",
            zip_code="11111",
            building_type="residential",
            total_units=1
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        
        unit = Unit(
            building_id=building.id,
            unit_number="202",
            floor=2,
            bedrooms=1,
            bathrooms=1,
            square_feet=650,
            monthly_rent=1200.00,
            status="available"
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)
        
        # Verify relationship
        result = await db_session.execute(
            select(Unit).where(Unit.id == unit.id)
        )
        fetched_unit = result.scalar_one()
        
        assert fetched_unit.building.id == building.id
        assert fetched_unit.building.name == "Relationship Test Building"


class TestLeaseModel:
    """Test Lease model relationships and business logic"""

    @pytest.mark.asyncio
    async def test_create_lease(self, db_session: AsyncSession):
        """Test creating a lease with tenant and unit"""
        # Create building
        building = Building(
            name="Lease Test Building",
            address="222 Lease Ave",
            city="Lease City",
            state="FL",
            zip_code="22222",
            building_type="residential",
            total_units=3
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        
        # Create unit
        unit = Unit(
            building_id=building.id,
            unit_number="303",
            floor=3,
            bedrooms=2,
            bathrooms=2,
            square_feet=1000,
            monthly_rent=1800.00,
            status="available"
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)
        
        # Create tenant
        tenant = Tenant(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="555-1234"
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        
        # Create lease
        start_date = date.today()
        end_date = start_date + timedelta(days=365)
        
        lease = Lease(
            unit_id=unit.id,
            tenant_id=tenant.id,
            start_date=start_date,
            end_date=end_date,
            monthly_rent=1800.00,
            security_deposit=1800.00,
            status="active"
        )
        
        db_session.add(lease)
        await db_session.commit()
        await db_session.refresh(lease)
        
        assert lease.id is not None
        assert lease.unit_id == unit.id
        assert lease.tenant_id == tenant.id
        assert lease.status == "active"

    @pytest.mark.asyncio
    async def test_lease_relationships(self, db_session: AsyncSession):
        """Test Lease relationships to Unit and Tenant"""
        # Create full hierarchy
        building = Building(
            name="Full Hierarchy Building",
            address="333 Full St",
            city="Full City",
            state="OR",
            zip_code="33333",
            building_type="residential",
            total_units=1
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        
        unit = Unit(
            building_id=building.id,
            unit_number="404",
            floor=4,
            bedrooms=3,
            bathrooms=2,
            square_feet=1400,
            monthly_rent=2200.00,
            status="available"
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)
        
        tenant = Tenant(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone="555-5678"
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        
        lease = Lease(
            unit_id=unit.id,
            tenant_id=tenant.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            monthly_rent=2200.00,
            security_deposit=2200.00,
            status="active"
        )
        db_session.add(lease)
        await db_session.commit()
        await db_session.refresh(lease)
        
        # Verify relationships
        result = await db_session.execute(
            select(Lease).where(Lease.id == lease.id)
        )
        fetched_lease = result.scalar_one()
        
        assert fetched_lease.unit.unit_number == "404"
        assert fetched_lease.tenant.email == "jane.smith@example.com"
        assert fetched_lease.unit.building.name == "Full Hierarchy Building"


class TestPaymentModel:
    """Test Payment model and financial tracking"""

    @pytest.mark.asyncio
    async def test_create_payment(self, db_session: AsyncSession):
        """Test creating a payment record"""
        # Create tenant
        tenant = Tenant(
            first_name="Payment",
            last_name="Tester",
            email="payment.tester@example.com",
            phone="555-9999"
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        
        # Create payment
        payment = Payment(
            tenant_id=tenant.id,
            amount=1500.00,
            payment_date=date.today(),
            payment_for_month=date.today().strftime("%Y-%m"),
            payment_method="credit_card",
            status="completed"
        )
        
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)
        
        assert payment.id is not None
        assert payment.amount == 1500.00
        assert payment.status == "completed"

    @pytest.mark.asyncio
    async def test_payment_tenant_relationship(self, db_session: AsyncSession):
        """Test Payment -> Tenant relationship"""
        tenant = Tenant(
            first_name="Relationship",
            last_name="Payment",
            email="rel.payment@example.com",
            phone="555-7777"
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        
        payment = Payment(
            tenant_id=tenant.id,
            amount=1200.00,
            payment_date=date.today(),
            payment_for_month=date.today().strftime("%Y-%m"),
            payment_method="bank_transfer",
            status="completed"
        )
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)
        
        # Verify relationship
        result = await db_session.execute(
            select(Payment).where(Payment.id == payment.id)
        )
        fetched_payment = result.scalar_one()
        
        assert fetched_payment.tenant.email == "rel.payment@example.com"


class TestWorkOrderModel:
    """Test Work Order model and maintenance tracking"""

    @pytest.mark.asyncio
    async def test_create_work_order(self, db_session: AsyncSession):
        """Test creating a work order"""
        # Create building and unit
        building = Building(
            name="WO Test Building",
            address="444 WO St",
            city="WO City",
            state="CO",
            zip_code="44444",
            building_type="residential",
            total_units=2
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        
        unit = Unit(
            building_id=building.id,
            unit_number="505",
            floor=5,
            bedrooms=1,
            bathrooms=1,
            square_feet=600,
            monthly_rent=1100.00,
            status="occupied"
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)
        
        # Create work order
        work_order = WorkOrder(
            unit_id=unit.id,
            title="Leaky Faucet",
            description="Kitchen faucet is dripping",
            priority="medium",
            status="open",
            category="plumbing"
        )
        
        db_session.add(work_order)
        await db_session.commit()
        await db_session.refresh(work_order)
        
        assert work_order.id is not None
        assert work_order.title == "Leaky Faucet"
        assert work_order.priority == "medium"

    @pytest.mark.asyncio
    async def test_work_order_unit_relationship(self, db_session: AsyncSession):
        """Test Work Order -> Unit relationship"""
        building = Building(
            name="WO Relationship Building",
            address="555 Relation Ave",
            city="Relation City",
            state="NV",
            zip_code="55555",
            building_type="residential",
            total_units=1
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        
        unit = Unit(
            building_id=building.id,
            unit_number="606",
            floor=6,
            bedrooms=2,
            bathrooms=1,
            square_feet=900,
            monthly_rent=1600.00,
            status="occupied"
        )
        db_session.add(unit)
        await db_session.commit()
        await db_session.refresh(unit)
        
        work_order = WorkOrder(
            unit_id=unit.id,
            title="AC Repair",
            description="Air conditioning not working",
            priority="high",
            status="in_progress",
            category="hvac"
        )
        db_session.add(work_order)
        await db_session.commit()
        await db_session.refresh(work_order)
        
        # Verify relationship
        result = await db_session.execute(
            select(WorkOrder).where(WorkOrder.id == work_order.id)
        )
        fetched_wo = result.scalar_one()
        
        assert fetched_wo.unit.unit_number == "606"
        assert fetched_wo.unit.building.name == "WO Relationship Building"
