"""
Labor Configuration Models
Database models for configurable labor rates, installation times, and materials
"""
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from db.models import Base


class LaborRate(Base):
    """Labor rates by category (installation, configuration, etc.)"""
    __tablename__ = "labor_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(50), nullable=False, unique=True)
    rate_per_hour = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)


class InstallationTime(Base):
    """Installation times by device category with vendor-specific and complexity variations"""
    __tablename__ = "installation_times"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_category = Column(String(50), nullable=False)
    vendor = Column(String(100), nullable=True)  # e.g., "Yale", "Schlage", "Ecobee"
    model = Column(String(100), nullable=True)   # e.g., "Assure Lock 2", "Encode Plus"
    complexity_type = Column(String(50), nullable=True)  # e.g., "neutral_wire_present", "no_neutral_wire"
    complexity_multiplier = Column(Numeric(3, 2), nullable=False, default=1.00)
    first_unit_hours = Column(Numeric(10, 2), nullable=False)
    additional_unit_hours = Column(Numeric(10, 2), nullable=False)
    labor_category = Column(String(50), nullable=False, default="installation")
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)


class DeviceMaterial(Base):
    """Materials needed per device category"""
    __tablename__ = "device_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_category = Column(String(50), nullable=False)
    material_name = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=False)
    quantity_per_device = Column(Numeric(10, 2), nullable=False)
    cost_per_unit = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)


class ContractorLaborRate(Base):
    """Contractor-specific labor rates (overrides default rates)"""
    __tablename__ = "contractor_labor_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contractor_id = Column(UUID(as_uuid=True), nullable=False)  # References contractors table
    labor_category = Column(String(50), nullable=False)
    rate_per_hour = Column(Numeric(10, 2), nullable=False)
    effective_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)
