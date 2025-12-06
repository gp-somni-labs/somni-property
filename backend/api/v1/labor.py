"""
Somni Property Manager - Labor Pricing API
Manage labor templates, calculate labor costs, and generate detailed labor breakdowns
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import joinedload
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

from db.database import get_db
from db.models_quotes import (
    LaborTemplate as LaborTemplateModel,
    QuoteLaborItem as QuoteLaborItemModel,
    LaborMaterial as LaborMaterialModel,
    Quote as QuoteModel
)
from api.schemas_quotes import (
    LaborTemplate, LaborTemplateCreate, LaborTemplateUpdate,
    QuoteLaborItem, QuoteLaborItemCreate, QuoteLaborItemUpdate,
    LaborMaterial, LaborMaterialCreate, LaborMaterialUpdate,
    LaborEstimationRequest, LaborEstimationResponse
)
from services.labor_calculator import LaborCalculator
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


# ============================================================================
# LABOR ESTIMATION (Public for quote calculator)
# ============================================================================

@router.post("/quotes/{quote_id}/labor/estimate", response_model=LaborEstimationResponse)
async def estimate_labor_for_quote(
    quote_id: UUID,
    request: LaborEstimationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Estimate labor costs based on selected products

    This endpoint analyzes the products selected in a quote and automatically
    calculates:
    - Installation labor (hours and cost)
    - Configuration and testing labor
    - Materials needed
    - Project duration

    Public endpoint (no auth) for quote calculator use.
    """
    calculator = LaborCalculator(db)

    try:
        estimation = await calculator.estimate_labor(
            quote_id=request.quote_id,
            product_selections=request.product_selections,
            include_materials=request.include_materials,
            labor_rate_override=None
        )

        return LaborEstimationResponse(**estimation)

    except Exception as e:
        logger.error(f"Failed to estimate labor for quote {quote_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Labor estimation failed: {str(e)}")


# ============================================================================
# LABOR TEMPLATES (Admin only)
# ============================================================================

@router.get("/labor/templates", response_model=List[LaborTemplate])
async def list_labor_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_manager)
):
    """
    List all labor templates

    Labor templates define standard labor tasks with pricing and materials.
    """
    query = select(LaborTemplateModel)

    if category:
        query = query.where(LaborTemplateModel.category == category)

    if active_only:
        query = query.where(LaborTemplateModel.active == True)

    query = query.offset(skip).limit(limit).order_by(LaborTemplateModel.category, LaborTemplateModel.template_name)

    result = await db.execute(query)
    templates = result.scalars().all()

    return [LaborTemplate.model_validate(t) for t in templates]


@router.get("/labor/templates/{template_id}", response_model=LaborTemplate)
async def get_labor_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_manager)
):
    """Get a specific labor template by ID"""
    query = select(LaborTemplateModel).where(LaborTemplateModel.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Labor template not found")

    return LaborTemplate.model_validate(template)


@router.post("/labor/templates", response_model=LaborTemplate, status_code=201)
async def create_labor_template(
    template: LaborTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Create a new labor template"""

    # Check for duplicate template code
    if template.template_code:
        query = select(LaborTemplateModel).where(LaborTemplateModel.template_code == template.template_code)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Labor template code already exists")

    new_template = LaborTemplateModel(**template.model_dump())
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)

    logger.info(f"Created labor template: {new_template.template_name} ({new_template.template_code})")

    return LaborTemplate.model_validate(new_template)


@router.put("/labor/templates/{template_id}", response_model=LaborTemplate)
async def update_labor_template(
    template_id: UUID,
    template: LaborTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Update an existing labor template"""
    query = select(LaborTemplateModel).where(LaborTemplateModel.id == template_id)
    result = await db.execute(query)
    existing_template = result.scalar_one_or_none()

    if not existing_template:
        raise HTTPException(status_code=404, detail="Labor template not found")

    # Update fields
    update_data = template.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_template, field, value)

    await db.commit()
    await db.refresh(existing_template)

    logger.info(f"Updated labor template: {existing_template.template_name}")

    return LaborTemplate.model_validate(existing_template)


@router.delete("/labor/templates/{template_id}", status_code=204)
async def delete_labor_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Delete a labor template"""
    query = select(LaborTemplateModel).where(LaborTemplateModel.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Labor template not found")

    await db.delete(template)
    await db.commit()

    logger.info(f"Deleted labor template: {template.template_name}")

    return None


# ============================================================================
# QUOTE LABOR ITEMS
# ============================================================================

@router.get("/quotes/{quote_id}/labor", response_model=List[QuoteLaborItem])
async def list_quote_labor_items(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all labor items for a quote

    No authentication required - allows customers to view labor breakdown
    """
    query = select(QuoteLaborItemModel).where(
        QuoteLaborItemModel.quote_id == quote_id
    ).order_by(QuoteLaborItemModel.display_order, QuoteLaborItemModel.line_number)

    result = await db.execute(query)
    labor_items = result.scalars().all()

    return [QuoteLaborItem.model_validate(item) for item in labor_items]


@router.post("/quotes/{quote_id}/labor", response_model=QuoteLaborItem, status_code=201)
async def add_labor_item_to_quote(
    quote_id: UUID,
    labor_item: QuoteLaborItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_manager)
):
    """Add a labor item to a quote"""

    # Verify quote exists
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    new_labor_item = QuoteLaborItemModel(**labor_item.model_dump())
    db.add(new_labor_item)
    await db.commit()
    await db.refresh(new_labor_item)

    logger.info(f"Added labor item to quote {quote_id}: {new_labor_item.task_name}")

    return QuoteLaborItem.model_validate(new_labor_item)


@router.put("/quotes/{quote_id}/labor/{labor_item_id}", response_model=QuoteLaborItem)
async def update_quote_labor_item(
    quote_id: UUID,
    labor_item_id: UUID,
    labor_item: QuoteLaborItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_manager)
):
    """Update a labor item in a quote"""
    query = select(QuoteLaborItemModel).where(
        QuoteLaborItemModel.id == labor_item_id,
        QuoteLaborItemModel.quote_id == quote_id
    )
    result = await db.execute(query)
    existing_item = result.scalar_one_or_none()

    if not existing_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Update fields
    update_data = labor_item.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_item, field, value)

    # Recalculate totals if pricing changed
    if "estimated_hours" in update_data or "hourly_rate" in update_data:
        existing_item.labor_subtotal = existing_item.estimated_hours * existing_item.hourly_rate
        existing_item.total_cost = existing_item.labor_subtotal + existing_item.materials_cost

    await db.commit()
    await db.refresh(existing_item)

    logger.info(f"Updated labor item {labor_item_id} in quote {quote_id}")

    return QuoteLaborItem.model_validate(existing_item)


@router.delete("/quotes/{quote_id}/labor/{labor_item_id}", status_code=204)
async def delete_quote_labor_item(
    quote_id: UUID,
    labor_item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_manager)
):
    """Delete a labor item from a quote"""
    query = select(QuoteLaborItemModel).where(
        QuoteLaborItemModel.id == labor_item_id,
        QuoteLaborItemModel.quote_id == quote_id
    )
    result = await db.execute(query)
    labor_item = result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    await db.delete(labor_item)
    await db.commit()

    logger.info(f"Deleted labor item {labor_item_id} from quote {quote_id}")

    return None


# ============================================================================
# LABOR MATERIALS
# ============================================================================

@router.get("/labor/materials", response_model=List[LaborMaterial])
async def list_labor_materials(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_manager)
):
    """List all labor materials"""
    query = select(LaborMaterialModel)

    if category:
        query = query.where(LaborMaterialModel.category == category)

    if active_only:
        query = query.where(LaborMaterialModel.active == True)

    query = query.offset(skip).limit(limit).order_by(LaborMaterialModel.category, LaborMaterialModel.material_name)

    result = await db.execute(query)
    materials = result.scalars().all()

    return [LaborMaterial.model_validate(m) for m in materials]


@router.post("/labor/materials", response_model=LaborMaterial, status_code=201)
async def create_labor_material(
    material: LaborMaterialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Create a new labor material"""

    # Check for duplicate material code
    if material.material_code:
        query = select(LaborMaterialModel).where(LaborMaterialModel.material_code == material.material_code)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Material code already exists")

    new_material = LaborMaterialModel(**material.model_dump())
    db.add(new_material)
    await db.commit()
    await db.refresh(new_material)

    logger.info(f"Created labor material: {new_material.material_name}")

    return LaborMaterial.model_validate(new_material)


@router.put("/labor/materials/{material_id}", response_model=LaborMaterial)
async def update_labor_material(
    material_id: UUID,
    material: LaborMaterialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Update a labor material"""
    query = select(LaborMaterialModel).where(LaborMaterialModel.id == material_id)
    result = await db.execute(query)
    existing_material = result.scalar_one_or_none()

    if not existing_material:
        raise HTTPException(status_code=404, detail="Labor material not found")

    # Update fields
    update_data = material.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_material, field, value)

    await db.commit()
    await db.refresh(existing_material)

    logger.info(f"Updated labor material: {existing_material.material_name}")

    return LaborMaterial.model_validate(existing_material)


@router.delete("/labor/materials/{material_id}", status_code=204)
async def delete_labor_material(
    material_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Delete a labor material"""
    query = select(LaborMaterialModel).where(LaborMaterialModel.id == material_id)
    result = await db.execute(query)
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(status_code=404, detail="Labor material not found")

    await db.delete(material)
    await db.commit()

    logger.info(f"Deleted labor material: {material.material_name}")

    return None


# ============================================================================
# LABOR SUMMARY & STATISTICS
# ============================================================================

class LaborSummaryResponse(BaseModel):
    """Summary of labor costs for a quote"""
    quote_id: UUID
    total_labor_hours: float
    total_labor_cost: float
    total_materials_cost: float
    total_cost: float
    labor_items_count: int
    categories: Dict[str, Dict[str, float]]  # Category breakdown


@router.get("/quotes/{quote_id}/labor/summary", response_model=LaborSummaryResponse)
async def get_quote_labor_summary(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get labor cost summary for a quote

    Returns totals and breakdown by category.
    No authentication required - for customer view.
    """
    query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.quote_id == quote_id)
    result = await db.execute(query)
    labor_items = result.scalars().all()

    if not labor_items:
        return LaborSummaryResponse(
            quote_id=quote_id,
            total_labor_hours=0,
            total_labor_cost=0,
            total_materials_cost=0,
            total_cost=0,
            labor_items_count=0,
            categories={}
        )

    total_labor_hours = sum(float(item.estimated_hours) for item in labor_items)
    total_labor_cost = sum(float(item.labor_subtotal) for item in labor_items)
    total_materials_cost = sum(float(item.materials_cost) for item in labor_items)
    total_cost = sum(float(item.total_cost) for item in labor_items)

    # Category breakdown
    categories = {}
    for item in labor_items:
        category = item.category
        if category not in categories:
            categories[category] = {
                "hours": 0,
                "labor_cost": 0,
                "materials_cost": 0,
                "total_cost": 0
            }
        categories[category]["hours"] += float(item.estimated_hours)
        categories[category]["labor_cost"] += float(item.labor_subtotal)
        categories[category]["materials_cost"] += float(item.materials_cost)
        categories[category]["total_cost"] += float(item.total_cost)

    return LaborSummaryResponse(
        quote_id=quote_id,
        total_labor_hours=total_labor_hours,
        total_labor_cost=total_labor_cost,
        total_materials_cost=total_materials_cost,
        total_cost=total_cost,
        labor_items_count=len(labor_items),
        categories=categories
    )
