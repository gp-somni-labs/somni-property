"""
Contractors API - Manage approved contractors and automated quote gathering
Handles contractor CRUD, quote requests, performance tracking
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from decimal import Decimal
import uuid

from db.database import get_db
from services.contractor_manager import ContractorManagerService
from services.quote_lookup_service import QuoteLookupService

router = APIRouter(prefix="/contractors", tags=["contractors"])


# ==========================================================================
# PYDANTIC SCHEMAS
# ==========================================================================

class ContractorCreate(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: str
    secondary_phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    business_type: Optional[str] = None
    license_number: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    insurance_expires_at: Optional[date] = None
    categories: List[str] = []
    specialty_services: List[str] = []
    pricing_model: str = 'hourly'
    hourly_rate: Optional[Decimal] = None
    emergency_rate: Optional[Decimal] = None
    minimum_charge: Optional[Decimal] = None
    travel_fee: Optional[Decimal] = None
    available_weekdays: bool = True
    available_weekends: bool = False
    available_24_7: bool = False
    service_area_radius_miles: Optional[int] = None
    approval_status: str = 'pending'


class ContractorUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    categories: Optional[List[str]] = None
    specialty_services: Optional[List[str]] = None
    hourly_rate: Optional[Decimal] = None
    emergency_rate: Optional[Decimal] = None
    available: Optional[bool] = None
    approval_status: Optional[str] = None
    insurance_expires_at: Optional[date] = None


class ContractorResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: str
    categories: List[str] = []
    specialty_services: List[str] = []
    hourly_rate: Optional[Decimal] = None
    emergency_rate: Optional[Decimal] = None
    approval_status: str
    available: bool
    average_rating: Optional[Decimal] = None
    total_jobs_completed: int = 0
    on_time_rate: Optional[Decimal] = None
    response_time_hours: Optional[int] = None
    insurance_expires_at: Optional[date] = None
    last_job_date: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class QuoteRequest(BaseModel):
    work_order_id: uuid.UUID
    job_title: str
    job_description: str
    job_category: str
    property_id: uuid.UUID
    urgency: str = 'normal'
    estimated_budget: Optional[Decimal] = None
    preferred_start_date: Optional[date] = None
    required_skills: List[str] = []


class QuoteResponse(BaseModel):
    id: uuid.UUID
    work_order_id: uuid.UUID
    contractor_id: Optional[uuid.UUID] = None
    contractor_name: str
    contractor_email: Optional[str] = None
    contractor_phone: Optional[str] = None
    quoted_amount: Optional[Decimal] = None
    quote_breakdown: Optional[Dict[str, Any]] = None
    availability_date: Optional[date] = None
    estimated_completion_date: Optional[date] = None
    status: str
    quote_method: str
    ai_recommendation: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================================================
# CONTRACTOR CRUD ENDPOINTS
# ==========================================================================

@router.post("", response_model=ContractorResponse)
async def create_contractor(
    contractor: ContractorCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new contractor to the approved vendor list
    """
    try:
        # Import contractor model here to avoid circular imports
        from db.models import Contractor as ContractorModel

        new_contractor = ContractorModel(
            company_name=contractor.company_name,
            contact_name=contractor.contact_name,
            email=contractor.email,
            phone=contractor.phone,
            secondary_phone=contractor.secondary_phone,
            website=contractor.website,
            address_line1=contractor.address_line1,
            city=contractor.city,
            state=contractor.state,
            zip_code=contractor.zip_code,
            business_type=contractor.business_type,
            license_number=contractor.license_number,
            insurance_provider=contractor.insurance_provider,
            insurance_policy_number=contractor.insurance_policy_number,
            insurance_expires_at=contractor.insurance_expires_at,
            categories=contractor.categories,
            specialty_services=contractor.specialty_services,
            pricing_model=contractor.pricing_model,
            hourly_rate=contractor.hourly_rate,
            emergency_rate=contractor.emergency_rate,
            minimum_charge=contractor.minimum_charge,
            travel_fee=contractor.travel_fee,
            available_weekdays=contractor.available_weekdays,
            available_weekends=contractor.available_weekends,
            available_24_7=contractor.available_24_7,
            service_area_radius_miles=contractor.service_area_radius_miles,
            approval_status=contractor.approval_status
        )

        db.add(new_contractor)
        await db.commit()
        await db.refresh(new_contractor)

        return new_contractor

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create contractor: {str(e)}")


@router.get("", response_model=List[ContractorResponse])
async def list_contractors(
    approval_status: Optional[str] = None,
    category: Optional[str] = None,
    available: Optional[bool] = None,
    min_rating: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List contractors with optional filtering
    """
    try:
        from db.models import Contractor as ContractorModel

        query = select(ContractorModel)

        filters = []
        if approval_status:
            filters.append(ContractorModel.approval_status == approval_status)
        if category:
            filters.append(ContractorModel.categories.contains([category]))
        if available is not None:
            filters.append(ContractorModel.available == available)
        if min_rating is not None:
            filters.append(ContractorModel.average_rating >= min_rating)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(desc(ContractorModel.average_rating)).limit(limit).offset(offset)

        result = await db.execute(query)
        contractors = result.scalars().all()

        return contractors

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list contractors: {str(e)}")


@router.get("/{contractor_id}", response_model=ContractorResponse)
async def get_contractor(
    contractor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific contractor
    """
    try:
        from db.models import Contractor as ContractorModel

        result = await db.execute(
            select(ContractorModel).where(ContractorModel.id == contractor_id)
        )
        contractor = result.scalar_one_or_none()

        if not contractor:
            raise HTTPException(status_code=404, detail="Contractor not found")

        return contractor

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contractor: {str(e)}")


@router.put("/{contractor_id}", response_model=ContractorResponse)
async def update_contractor(
    contractor_id: uuid.UUID,
    contractor_update: ContractorUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update contractor information
    """
    try:
        from db.models import Contractor as ContractorModel

        result = await db.execute(
            select(ContractorModel).where(ContractorModel.id == contractor_id)
        )
        contractor = result.scalar_one_or_none()

        if not contractor:
            raise HTTPException(status_code=404, detail="Contractor not found")

        # Update fields
        update_data = contractor_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contractor, field, value)

        await db.commit()
        await db.refresh(contractor)

        return contractor

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update contractor: {str(e)}")


@router.delete("/{contractor_id}")
async def delete_contractor(
    contractor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (deactivate) a contractor
    """
    try:
        from db.models import Contractor as ContractorModel

        result = await db.execute(
            select(ContractorModel).where(ContractorModel.id == contractor_id)
        )
        contractor = result.scalar_one_or_none()

        if not contractor:
            raise HTTPException(status_code=404, detail="Contractor not found")

        contractor.approval_status = 'inactive'
        contractor.available = False
        await db.commit()

        return {"success": True, "message": "Contractor deactivated"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete contractor: {str(e)}")


# ==========================================================================
# QUOTE MANAGEMENT ENDPOINTS
# ==========================================================================

@router.post("/quotes/request")
async def request_quotes(
    quote_request: QuoteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Request quotes from contractors for a work order
    Triggers automated quote gathering if needed
    """
    try:
        contractor_manager = ContractorManagerService(db)

        # Find matching resources (staff + contractors)
        matches = await contractor_manager.find_matching_resources(
            job_category=quote_request.job_category,
            required_skills=quote_request.required_skills,
            property_id=quote_request.property_id,
            urgency=quote_request.urgency,
            estimated_budget=float(quote_request.estimated_budget) if quote_request.estimated_budget else None
        )

        # If no approved contractors available, trigger automated quote gathering
        if not matches.get("contractors"):
            quote_service = QuoteLookupService()

            # Trigger background quote gathering
            background_tasks.add_task(
                quote_service.gather_quotes_automated,
                work_order_id=quote_request.work_order_id,
                job_title=quote_request.job_title,
                job_description=quote_request.job_description,
                job_category=quote_request.job_category,
                property_id=quote_request.property_id
            )

            return {
                "success": True,
                "message": "No approved contractors available. Automated quote gathering initiated.",
                "quote_gathering_triggered": True,
                "staff_matches": len(matches.get("staff", [])),
                "contractor_matches": 0
            }

        # Send quote requests to approved contractors
        quotes_requested = []
        for contractor in matches.get("contractors", []):
            # Create quote request (would typically send email/API request here)
            quotes_requested.append({
                "contractor_id": contractor.id,
                "contractor_name": contractor.company_name,
                "status": "requested"
            })

        return {
            "success": True,
            "message": f"Quote requests sent to {len(quotes_requested)} contractors",
            "quote_gathering_triggered": False,
            "staff_matches": len(matches.get("staff", [])),
            "contractor_matches": len(quotes_requested),
            "quotes_requested": quotes_requested
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request quotes: {str(e)}")


@router.get("/quotes/work-order/{work_order_id}")
async def get_quotes_for_work_order(
    work_order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all quotes for a specific work order
    """
    try:
        from db.models import ContractorQuote

        result = await db.execute(
            select(ContractorQuote)
            .where(ContractorQuote.work_order_id == work_order_id)
            .order_by(desc(ContractorQuote.created_at))
        )
        quotes = result.scalars().all()

        return quotes

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quotes: {str(e)}")


# ==========================================================================
# CONTRACTOR PERFORMANCE & ANALYTICS
# ==========================================================================

@router.get("/{contractor_id}/performance")
async def get_contractor_performance(
    contractor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics for a contractor
    """
    try:
        from db.models import Contractor as ContractorModel, WorkOrder

        # Get contractor
        contractor_result = await db.execute(
            select(ContractorModel).where(ContractorModel.id == contractor_id)
        )
        contractor = contractor_result.scalar_one_or_none()

        if not contractor:
            raise HTTPException(status_code=404, detail="Contractor not found")

        # Get work orders for this contractor
        wo_result = await db.execute(
            select(WorkOrder).where(WorkOrder.contractor_id == contractor_id)
        )
        work_orders = wo_result.scalars().all()

        # Calculate metrics
        total_jobs = len(work_orders)
        completed_jobs = len([wo for wo in work_orders if wo.status == 'completed'])
        on_time_jobs = len([wo for wo in work_orders if wo.completed_on_time])

        return {
            "contractor_id": contractor_id,
            "company_name": contractor.company_name,
            "total_jobs_completed": completed_jobs,
            "total_jobs": total_jobs,
            "completion_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            "on_time_rate": contractor.on_time_rate,
            "average_rating": contractor.average_rating,
            "response_time_hours": contractor.response_time_hours,
            "categories": contractor.categories,
            "approval_status": contractor.approval_status
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/stats/overview")
async def get_contractor_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall contractor statistics
    """
    try:
        from db.models import Contractor as ContractorModel

        # Get all contractors
        result = await db.execute(select(ContractorModel))
        contractors = result.scalars().all()

        total_contractors = len(contractors)
        approved = len([c for c in contractors if c.approval_status == 'approved'])
        available = len([c for c in contractors if c.available])
        high_rated = len([c for c in contractors if c.average_rating and c.average_rating >= 4.0])

        # Calculate category distribution
        category_counts = {}
        for contractor in contractors:
            for category in contractor.categories or []:
                category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "total_contractors": total_contractors,
            "approved_contractors": approved,
            "available_contractors": available,
            "high_rated_contractors": high_rated,
            "category_distribution": category_counts,
            "avg_hourly_rate": sum([c.hourly_rate for c in contractors if c.hourly_rate]) / len([c for c in contractors if c.hourly_rate]) if any(c.hourly_rate for c in contractors) else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
