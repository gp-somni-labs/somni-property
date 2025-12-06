"""
Staff API - Manage in-house maintenance and property staff
Handles staff CRUD, scheduling, workload management, performance tracking
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from decimal import Decimal
import uuid

from db.database import get_db

router = APIRouter(prefix="/staff", tags=["staff"])


# ==========================================================================
# PYDANTIC SCHEMAS
# ==========================================================================

class StaffCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    position: str  # 'property_manager', 'maintenance_tech', 'leasing_agent', etc.
    department: Optional[str] = None  # 'maintenance', 'management', 'leasing', etc.
    employee_id: Optional[str] = None
    hire_date: Optional[date] = None
    employment_status: str = 'active'  # 'active', 'on_leave', 'terminated'
    skills: List[str] = []  # ['plumbing', 'electrical', 'hvac', 'carpentry']
    certifications: List[Dict[str, Any]] = []  # [{'name': 'EPA 608', 'expires': '2025-12-31'}]
    hourly_rate: Optional[Decimal] = None
    available: bool = True
    availability_schedule: Optional[Dict[str, Any]] = None  # Weekly schedule
    max_concurrent_jobs: int = 5
    assigned_properties: List[uuid.UUID] = []  # Which properties they cover


class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    employment_status: Optional[str] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    hourly_rate: Optional[Decimal] = None
    available: Optional[bool] = None
    availability_schedule: Optional[Dict[str, Any]] = None
    max_concurrent_jobs: Optional[int] = None
    assigned_properties: Optional[List[uuid.UUID]] = None


class StaffResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    position: str
    department: Optional[str] = None
    employee_id: Optional[str] = None
    hire_date: Optional[date] = None
    employment_status: str
    skills: List[str] = []
    certifications: List[Dict[str, Any]] = []
    hourly_rate: Optional[Decimal] = None
    available: bool
    availability_schedule: Optional[Dict[str, Any]] = None
    current_workload: int = 0
    max_concurrent_jobs: int = 5
    assigned_properties: List[str] = []
    total_jobs_completed: int = 0
    average_rating: Optional[Decimal] = None
    completion_time_avg_hours: Optional[Decimal] = None
    created_at: datetime
    last_active_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkloadAssignment(BaseModel):
    work_order_id: uuid.UUID
    assigned_date: date
    estimated_hours: Optional[float] = None


# ==========================================================================
# STAFF CRUD ENDPOINTS
# ==========================================================================

@router.post("", response_model=StaffResponse)
async def create_staff_member(
    staff: StaffCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new staff member
    """
    try:
        # Import staff model dynamically to avoid circular imports
        from db.models import Staff

        new_staff = Staff(
            first_name=staff.first_name,
            last_name=staff.last_name,
            email=staff.email,
            phone=staff.phone,
            position=staff.position,
            department=staff.department,
            employee_id=staff.employee_id,
            hire_date=staff.hire_date,
            employment_status=staff.employment_status,
            skills=staff.skills,
            certifications=staff.certifications,
            hourly_rate=staff.hourly_rate,
            available=staff.available,
            availability_schedule=staff.availability_schedule,
            max_concurrent_jobs=staff.max_concurrent_jobs,
            assigned_properties=staff.assigned_properties
        )

        db.add(new_staff)
        await db.commit()
        await db.refresh(new_staff)

        return new_staff

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create staff member: {str(e)}")


@router.get("", response_model=List[StaffResponse])
async def list_staff(
    employment_status: Optional[str] = None,
    position: Optional[str] = None,
    department: Optional[str] = None,
    available: Optional[bool] = None,
    skill: Optional[str] = None,
    property_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List staff members with optional filtering
    """
    try:
        from db.models import Staff

        query = select(Staff)

        filters = []
        if employment_status:
            filters.append(Staff.employment_status == employment_status)
        if position:
            filters.append(Staff.position == position)
        if department:
            filters.append(Staff.department == department)
        if available is not None:
            filters.append(Staff.available == available)
        if skill:
            filters.append(Staff.skills.contains([skill]))
        if property_id:
            filters.append(Staff.assigned_properties.contains([str(property_id)]))

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(Staff.last_name, Staff.first_name).limit(limit).offset(offset)

        result = await db.execute(query)
        staff_members = result.scalars().all()

        return staff_members

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list staff: {str(e)}")


@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff_member(
    staff_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific staff member
    """
    try:
        from db.models import Staff

        result = await db.execute(
            select(Staff).where(Staff.id == staff_id)
        )
        staff_member = result.scalar_one_or_none()

        if not staff_member:
            raise HTTPException(status_code=404, detail="Staff member not found")

        return staff_member

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get staff member: {str(e)}")


@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff_member(
    staff_id: uuid.UUID,
    staff_update: StaffUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update staff member information
    """
    try:
        from db.models import Staff

        result = await db.execute(
            select(Staff).where(Staff.id == staff_id)
        )
        staff_member = result.scalar_one_or_none()

        if not staff_member:
            raise HTTPException(status_code=404, detail="Staff member not found")

        # Update fields
        update_data = staff_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(staff_member, field, value)

        staff_member.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(staff_member)

        return staff_member

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update staff member: {str(e)}")


@router.delete("/{staff_id}")
async def delete_staff_member(
    staff_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (deactivate) a staff member
    """
    try:
        from db.models import Staff

        result = await db.execute(
            select(Staff).where(Staff.id == staff_id)
        )
        staff_member = result.scalar_one_or_none()

        if not staff_member:
            raise HTTPException(status_code=404, detail="Staff member not found")

        staff_member.employment_status = 'terminated'
        staff_member.available = False
        await db.commit()

        return {"success": True, "message": "Staff member deactivated"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete staff member: {str(e)}")


# ==========================================================================
# AVAILABILITY & SCHEDULING
# ==========================================================================

@router.get("/available/now")
async def get_available_staff(
    skill: Optional[str] = None,
    property_id: Optional[uuid.UUID] = None,
    max_workload: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get currently available staff members
    """
    try:
        from db.models import Staff

        query = select(Staff).where(
            and_(
                Staff.available == True,
                Staff.employment_status == 'active'
            )
        )

        filters = []
        if skill:
            filters.append(Staff.skills.contains([skill]))
        if property_id:
            filters.append(Staff.assigned_properties.contains([str(property_id)]))
        if max_workload is not None:
            filters.append(Staff.current_workload <= max_workload)

        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(query)
        available_staff = result.scalars().all()

        return [
            {
                "id": staff.id,
                "name": f"{staff.first_name} {staff.last_name}",
                "position": staff.position,
                "skills": staff.skills,
                "current_workload": staff.current_workload,
                "max_concurrent_jobs": staff.max_concurrent_jobs,
                "availability_percentage": ((staff.max_concurrent_jobs - staff.current_workload) / staff.max_concurrent_jobs * 100) if staff.max_concurrent_jobs > 0 else 0
            }
            for staff in available_staff
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available staff: {str(e)}")


@router.post("/{staff_id}/assign-workorder")
async def assign_work_order(
    staff_id: uuid.UUID,
    assignment: WorkloadAssignment,
    db: AsyncSession = Depends(get_db)
):
    """
    Assign a work order to a staff member
    """
    try:
        from db.models import Staff, WorkOrder

        # Get staff member
        staff_result = await db.execute(
            select(Staff).where(Staff.id == staff_id)
        )
        staff_member = staff_result.scalar_one_or_none()

        if not staff_member:
            raise HTTPException(status_code=404, detail="Staff member not found")

        if not staff_member.available:
            raise HTTPException(status_code=400, detail="Staff member is not available")

        if staff_member.current_workload >= staff_member.max_concurrent_jobs:
            raise HTTPException(status_code=400, detail="Staff member is at maximum workload")

        # Get work order
        wo_result = await db.execute(
            select(WorkOrder).where(WorkOrder.id == assignment.work_order_id)
        )
        work_order = wo_result.scalar_one_or_none()

        if not work_order:
            raise HTTPException(status_code=404, detail="Work order not found")

        # Assign work order
        work_order.assigned_staff_id = staff_id
        work_order.assigned_date = assignment.assigned_date
        work_order.estimated_hours = assignment.estimated_hours

        # Update staff workload
        staff_member.current_workload += 1
        staff_member.last_active_at = datetime.utcnow()

        await db.commit()

        return {
            "success": True,
            "message": "Work order assigned successfully",
            "staff_id": staff_id,
            "work_order_id": assignment.work_order_id,
            "new_workload": staff_member.current_workload
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to assign work order: {str(e)}")


# ==========================================================================
# PERFORMANCE & ANALYTICS
# ==========================================================================

@router.get("/{staff_id}/performance")
async def get_staff_performance(
    staff_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics for a staff member
    """
    try:
        from db.models import Staff, WorkOrder

        # Get staff member
        staff_result = await db.execute(
            select(Staff).where(Staff.id == staff_id)
        )
        staff_member = staff_result.scalar_one_or_none()

        if not staff_member:
            raise HTTPException(status_code=404, detail="Staff member not found")

        # Get work orders for this staff member
        wo_result = await db.execute(
            select(WorkOrder).where(WorkOrder.assigned_staff_id == staff_id)
        )
        work_orders = wo_result.scalars().all()

        # Calculate metrics
        total_jobs = len(work_orders)
        completed_jobs = len([wo for wo in work_orders if wo.status == 'completed'])
        on_time_jobs = len([wo for wo in work_orders if wo.completed_on_time])

        return {
            "staff_id": staff_id,
            "name": f"{staff_member.first_name} {staff_member.last_name}",
            "position": staff_member.position,
            "department": staff_member.department,
            "total_jobs_completed": staff_member.total_jobs_completed,
            "total_jobs": total_jobs,
            "completion_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            "on_time_rate": (on_time_jobs / completed_jobs * 100) if completed_jobs > 0 else 0,
            "average_rating": staff_member.average_rating,
            "completion_time_avg_hours": staff_member.completion_time_avg_hours,
            "current_workload": staff_member.current_workload,
            "skills": staff_member.skills,
            "certifications": staff_member.certifications
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/stats/overview")
async def get_staff_statistics(
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall staff statistics
    """
    try:
        from db.models import Staff

        # Get all staff
        result = await db.execute(select(Staff))
        staff_members = result.scalars().all()

        total_staff = len(staff_members)
        active = len([s for s in staff_members if s.employment_status == 'active'])
        available = len([s for s in staff_members if s.available])
        at_capacity = len([s for s in staff_members if s.current_workload >= s.max_concurrent_jobs])

        # Calculate department distribution
        dept_counts = {}
        for staff in staff_members:
            dept = staff.department or 'unassigned'
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

        # Calculate position distribution
        position_counts = {}
        for staff in staff_members:
            position_counts[staff.position] = position_counts.get(staff.position, 0) + 1

        # Calculate total capacity
        total_capacity = sum([s.max_concurrent_jobs for s in staff_members if s.available])
        current_utilization = sum([s.current_workload for s in staff_members if s.available])

        return {
            "total_staff": total_staff,
            "active_staff": active,
            "available_staff": available,
            "at_capacity_staff": at_capacity,
            "department_distribution": dept_counts,
            "position_distribution": position_counts,
            "total_capacity": total_capacity,
            "current_utilization": current_utilization,
            "utilization_percentage": (current_utilization / total_capacity * 100) if total_capacity > 0 else 0,
            "avg_rating": sum([s.average_rating for s in staff_members if s.average_rating]) / len([s for s in staff_members if s.average_rating]) if any(s.average_rating for s in staff_members) else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# ==========================================================================
# SKILLS & CERTIFICATIONS
# ==========================================================================

@router.post("/{staff_id}/skills")
async def add_skill(
    staff_id: uuid.UUID,
    skill: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a skill to a staff member
    """
    try:
        from db.models import Staff

        result = await db.execute(
            select(Staff).where(Staff.id == staff_id)
        )
        staff_member = result.scalar_one_or_none()

        if not staff_member:
            raise HTTPException(status_code=404, detail="Staff member not found")

        if skill not in staff_member.skills:
            staff_member.skills = staff_member.skills + [skill]
            await db.commit()

        return {"success": True, "skills": staff_member.skills}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add skill: {str(e)}")


@router.post("/{staff_id}/certifications")
async def add_certification(
    staff_id: uuid.UUID,
    certification: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Add a certification to a staff member
    """
    try:
        from db.models import Staff

        result = await db.execute(
            select(Staff).where(Staff.id == staff_id)
        )
        staff_member = result.scalar_one_or_none()

        if not staff_member:
            raise HTTPException(status_code=404, detail="Staff member not found")

        staff_member.certifications = staff_member.certifications + [certification]
        await db.commit()

        return {"success": True, "certifications": staff_member.certifications}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add certification: {str(e)}")
