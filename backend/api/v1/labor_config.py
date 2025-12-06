"""
Labor Configuration API
CRUD endpoints for managing labor rates, installation times, and materials
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List
from decimal import Decimal
from pydantic import BaseModel, Field
import uuid

from db.database import get_db
from db.models_labor_config import LaborRate, InstallationTime, DeviceMaterial, ContractorLaborRate

router = APIRouter(prefix="/labor-config", tags=["Labor Configuration"])


# ============================================================================
# Pydantic Models
# ============================================================================

class LaborRateCreate(BaseModel):
    category: str = Field(..., max_length=50)
    rate_per_hour: Decimal = Field(..., ge=0)
    description: str | None = None
    is_active: bool = True

class LaborRateUpdate(BaseModel):
    rate_per_hour: Decimal | None = Field(None, ge=0)
    description: str | None = None
    is_active: bool | None = None

class LaborRateResponse(BaseModel):
    id: uuid.UUID
    category: str
    rate_per_hour: Decimal
    description: str | None
    is_active: bool
    updated_by: str | None

    class Config:
        from_attributes = True


class InstallationTimeCreate(BaseModel):
    device_category: str = Field(..., max_length=50)
    vendor: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    complexity_type: str | None = Field(None, max_length=50)
    complexity_multiplier: Decimal = Field(default=Decimal("1.00"), ge=0, le=9.99)
    first_unit_hours: Decimal = Field(..., ge=0)
    additional_unit_hours: Decimal = Field(..., ge=0)
    labor_category: str = Field(default="installation", max_length=50)
    description: str | None = None
    notes: str | None = None
    is_active: bool = True

class InstallationTimeUpdate(BaseModel):
    vendor: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    complexity_type: str | None = Field(None, max_length=50)
    complexity_multiplier: Decimal | None = Field(None, ge=0, le=9.99)
    first_unit_hours: Decimal | None = Field(None, ge=0)
    additional_unit_hours: Decimal | None = Field(None, ge=0)
    labor_category: str | None = None
    description: str | None = None
    notes: str | None = None
    is_active: bool | None = None

class InstallationTimeResponse(BaseModel):
    id: uuid.UUID
    device_category: str
    vendor: str | None
    model: str | None
    complexity_type: str | None
    complexity_multiplier: Decimal
    first_unit_hours: Decimal
    additional_unit_hours: Decimal
    labor_category: str
    description: str | None
    notes: str | None
    is_active: bool
    updated_by: str | None

    class Config:
        from_attributes = True


class DeviceMaterialCreate(BaseModel):
    device_category: str = Field(..., max_length=50)
    material_name: str = Field(..., max_length=100)
    unit: str = Field(..., max_length=20)
    quantity_per_device: Decimal = Field(..., ge=0)
    cost_per_unit: Decimal = Field(..., ge=0)
    is_active: bool = True

class DeviceMaterialUpdate(BaseModel):
    material_name: str | None = None
    unit: str | None = None
    quantity_per_device: Decimal | None = Field(None, ge=0)
    cost_per_unit: Decimal | None = Field(None, ge=0)
    is_active: bool | None = None

class DeviceMaterialResponse(BaseModel):
    id: uuid.UUID
    device_category: str
    material_name: str
    unit: str
    quantity_per_device: Decimal
    cost_per_unit: Decimal
    is_active: bool
    updated_by: str | None

    class Config:
        from_attributes = True


class ContractorLaborRateCreate(BaseModel):
    contractor_id: uuid.UUID
    labor_category: str = Field(..., max_length=50)
    rate_per_hour: Decimal = Field(..., ge=0)
    notes: str | None = None
    is_active: bool = True

class ContractorLaborRateUpdate(BaseModel):
    rate_per_hour: Decimal | None = Field(None, ge=0)
    notes: str | None = None
    is_active: bool | None = None

class ContractorLaborRateResponse(BaseModel):
    id: uuid.UUID
    contractor_id: uuid.UUID
    labor_category: str
    rate_per_hour: Decimal
    effective_date: str
    notes: str | None
    is_active: bool
    updated_by: str | None

    class Config:
        from_attributes = True


# ============================================================================
# Labor Rates Endpoints
# ============================================================================

@router.get("/rates", response_model=List[LaborRateResponse])
async def get_labor_rates(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get all labor rate categories"""
    query = select(LaborRate)
    if not include_inactive:
        query = query.where(LaborRate.is_active == True)
    query = query.order_by(LaborRate.category)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/rates/{rate_id}", response_model=LaborRateResponse)
async def get_labor_rate(
    rate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific labor rate by ID"""
    result = await db.execute(select(LaborRate).where(LaborRate.id == rate_id))
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Labor rate not found")
    return rate


@router.post("/rates", response_model=LaborRateResponse, status_code=201)
async def create_labor_rate(
    rate: LaborRateCreate,
    updated_by: str = "admin",  # TODO: Get from auth context
    db: AsyncSession = Depends(get_db)
):
    """Create new labor rate category"""
    # Check if category already exists
    result = await db.execute(select(LaborRate).where(LaborRate.category == rate.category))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Labor rate for category '{rate.category}' already exists")

    db_rate = LaborRate(
        **rate.model_dump(),
        updated_by=updated_by
    )
    db.add(db_rate)
    await db.commit()
    await db.refresh(db_rate)
    return db_rate


@router.put("/rates/{rate_id}", response_model=LaborRateResponse)
async def update_labor_rate(
    rate_id: uuid.UUID,
    rate: LaborRateUpdate,
    updated_by: str = "admin",  # TODO: Get from auth context
    db: AsyncSession = Depends(get_db)
):
    """Update existing labor rate"""
    result = await db.execute(select(LaborRate).where(LaborRate.id == rate_id))
    db_rate = result.scalar_one_or_none()
    if not db_rate:
        raise HTTPException(status_code=404, detail="Labor rate not found")

    update_data = rate.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_rate, field, value)

    db_rate.updated_by = updated_by
    await db.commit()
    await db.refresh(db_rate)
    return db_rate


@router.delete("/rates/{rate_id}", status_code=204)
async def deactivate_labor_rate(
    rate_id: uuid.UUID,
    updated_by: str = "admin",  # TODO: Get from auth context
    db: AsyncSession = Depends(get_db)
):
    """Deactivate labor rate (soft delete)"""
    result = await db.execute(select(LaborRate).where(LaborRate.id == rate_id))
    db_rate = result.scalar_one_or_none()
    if not db_rate:
        raise HTTPException(status_code=404, detail="Labor rate not found")

    db_rate.is_active = False
    db_rate.updated_by = updated_by
    await db.commit()


# ============================================================================
# Installation Times Endpoints
# ============================================================================

@router.get("/installation-times", response_model=List[InstallationTimeResponse])
async def get_installation_times(
    device_category: str | None = None,
    vendor: str | None = None,
    model: str | None = None,
    complexity_type: str | None = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get installation time configurations with optional filtering by device/vendor/model/complexity"""
    query = select(InstallationTime)

    if device_category:
        query = query.where(InstallationTime.device_category == device_category)
    if vendor:
        query = query.where(InstallationTime.vendor == vendor)
    if model:
        query = query.where(InstallationTime.model == model)
    if complexity_type:
        query = query.where(InstallationTime.complexity_type == complexity_type)
    if not include_inactive:
        query = query.where(InstallationTime.is_active == True)

    query = query.order_by(
        InstallationTime.device_category,
        InstallationTime.vendor,
        InstallationTime.model,
        InstallationTime.complexity_type
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/installation-times/{time_id}", response_model=InstallationTimeResponse)
async def get_installation_time(
    time_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific installation time by ID"""
    result = await db.execute(select(InstallationTime).where(InstallationTime.id == time_id))
    time_config = result.scalar_one_or_none()
    if not time_config:
        raise HTTPException(status_code=404, detail="Installation time not found")
    return time_config


@router.post("/installation-times", response_model=InstallationTimeResponse, status_code=201)
async def create_installation_time(
    time_config: InstallationTimeCreate,
    updated_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """Create new installation time configuration"""
    result = await db.execute(select(InstallationTime).where(
        InstallationTime.device_category == time_config.device_category
    ))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Installation time for '{time_config.device_category}' already exists"
        )

    db_time = InstallationTime(
        **time_config.model_dump(),
        updated_by=updated_by
    )
    db.add(db_time)
    await db.commit()
    await db.refresh(db_time)
    return db_time


@router.put("/installation-times/{time_id}", response_model=InstallationTimeResponse)
async def update_installation_time(
    time_id: uuid.UUID,
    time_config: InstallationTimeUpdate,
    updated_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """Update installation time configuration"""
    result = await db.execute(select(InstallationTime).where(InstallationTime.id == time_id))
    db_time = result.scalar_one_or_none()
    if not db_time:
        raise HTTPException(status_code=404, detail="Installation time not found")

    update_data = time_config.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_time, field, value)

    db_time.updated_by = updated_by
    await db.commit()
    await db.refresh(db_time)
    return db_time


@router.delete("/installation-times/{time_id}", status_code=204)
async def deactivate_installation_time(
    time_id: uuid.UUID,
    updated_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """Deactivate installation time (soft delete)"""
    result = await db.execute(select(InstallationTime).where(InstallationTime.id == time_id))
    db_time = result.scalar_one_or_none()
    if not db_time:
        raise HTTPException(status_code=404, detail="Installation time not found")

    db_time.is_active = False
    db_time.updated_by = updated_by
    await db.commit()


# ============================================================================
# Device Materials Endpoints
# ============================================================================

@router.get("/materials", response_model=List[DeviceMaterialResponse])
async def get_device_materials(
    device_category: str | None = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get device materials, optionally filtered by device category"""
    query = select(DeviceMaterial)
    if device_category:
        query = query.where(DeviceMaterial.device_category == device_category)
    if not include_inactive:
        query = query.where(DeviceMaterial.is_active == True)
    query = query.order_by(DeviceMaterial.device_category, DeviceMaterial.material_name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/materials/{material_id}", response_model=DeviceMaterialResponse)
async def get_device_material(
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific device material by ID"""
    result = await db.execute(select(DeviceMaterial).where(DeviceMaterial.id == material_id))
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Device material not found")
    return material


@router.post("/materials", response_model=DeviceMaterialResponse, status_code=201)
async def create_device_material(
    material: DeviceMaterialCreate,
    updated_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """Create new device material configuration"""
    db_material = DeviceMaterial(
        **material.model_dump(),
        updated_by=updated_by
    )
    db.add(db_material)
    await db.commit()
    await db.refresh(db_material)
    return db_material


@router.put("/materials/{material_id}", response_model=DeviceMaterialResponse)
async def update_device_material(
    material_id: uuid.UUID,
    material: DeviceMaterialUpdate,
    updated_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """Update device material configuration"""
    result = await db.execute(select(DeviceMaterial).where(DeviceMaterial.id == material_id))
    db_material = result.scalar_one_or_none()
    if not db_material:
        raise HTTPException(status_code=404, detail="Device material not found")

    update_data = material.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_material, field, value)

    db_material.updated_by = updated_by
    await db.commit()
    await db.refresh(db_material)
    return db_material


@router.delete("/materials/{material_id}", status_code=204)
async def delete_device_material(
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete device material (hard delete)"""
    result = await db.execute(select(DeviceMaterial).where(DeviceMaterial.id == material_id))
    db_material = result.scalar_one_or_none()
    if not db_material:
        raise HTTPException(status_code=404, detail="Device material not found")

    db.delete(db_material)
    await db.commit()


# ============================================================================
# Contractor Labor Rates Endpoints
# ============================================================================

@router.get("/contractor-rates", response_model=List[ContractorLaborRateResponse])
async def get_contractor_labor_rates(
    contractor_id: uuid.UUID | None = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get contractor-specific labor rates, optionally filtered by contractor"""
    query = select(ContractorLaborRate)
    if contractor_id:
        query = query.where(ContractorLaborRate.contractor_id == contractor_id)
    if not include_inactive:
        query = query.where(ContractorLaborRate.is_active == True)
    query = query.order_by(ContractorLaborRate.contractor_id, ContractorLaborRate.labor_category)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/contractor-rates/{rate_id}", response_model=ContractorLaborRateResponse)
async def get_contractor_labor_rate(
    rate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific contractor labor rate by ID"""
    result = await db.execute(select(ContractorLaborRate).where(ContractorLaborRate.id == rate_id))
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Contractor labor rate not found")
    return rate


@router.post("/contractor-rates", response_model=ContractorLaborRateResponse, status_code=201)
async def create_contractor_labor_rate(
    rate: ContractorLaborRateCreate,
    updated_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """Create contractor-specific labor rate"""
    # Check if rate already exists for this contractor/category
    result = await db.execute(select(ContractorLaborRate).where(
        ContractorLaborRate.contractor_id == rate.contractor_id,
        ContractorLaborRate.labor_category == rate.labor_category
    ))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Contractor rate for category '{rate.labor_category}' already exists"
        )

    db_rate = ContractorLaborRate(
        **rate.model_dump(),
        updated_by=updated_by
    )
    db.add(db_rate)
    await db.commit()
    await db.refresh(db_rate)
    return db_rate


@router.put("/contractor-rates/{rate_id}", response_model=ContractorLaborRateResponse)
async def update_contractor_labor_rate(
    rate_id: uuid.UUID,
    rate: ContractorLaborRateUpdate,
    updated_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """Update contractor labor rate"""
    result = await db.execute(select(ContractorLaborRate).where(ContractorLaborRate.id == rate_id))
    db_rate = result.scalar_one_or_none()
    if not db_rate:
        raise HTTPException(status_code=404, detail="Contractor labor rate not found")

    update_data = rate.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_rate, field, value)

    db_rate.updated_by = updated_by
    await db.commit()
    await db.refresh(db_rate)
    return db_rate


@router.delete("/contractor-rates/{rate_id}", status_code=204)
async def delete_contractor_labor_rate(
    rate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete contractor labor rate (hard delete)"""
    result = await db.execute(select(ContractorLaborRate).where(ContractorLaborRate.id == rate_id))
    db_rate = result.scalar_one_or_none()
    if not db_rate:
        raise HTTPException(status_code=404, detail="Contractor labor rate not found")

    db.delete(db_rate)
    await db.commit()
