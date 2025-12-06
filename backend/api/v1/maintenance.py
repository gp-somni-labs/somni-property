"""
Maintenance Scheduling API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal

from db.database import get_db
from db.models_maintenance import (
    MaintenanceSchedule,
    MaintenanceTask,
    MaintenanceScheduleStatus,
    MaintenanceTaskStatus,
    MaintenanceFrequency
)
from api.schemas_maintenance import (
    MaintenanceScheduleCreate,
    MaintenanceScheduleUpdate,
    MaintenanceScheduleResponse,
    MaintenanceTaskCreate,
    MaintenanceTaskUpdate,
    MaintenanceTaskComplete,
    MaintenanceTaskResponse,
    MaintenanceDashboard,
    MaintenanceUpcoming,
    MaintenanceOverdue,
    MaintenanceScheduleFilters,
    MaintenanceTaskFilters
)

router = APIRouter()


# ============================================================================
# MAINTENANCE SCHEDULES
# ============================================================================

@router.get("/schedules", response_model=dict)
async def list_maintenance_schedules(
    property_id: Optional[UUID] = None,
    building_id: Optional[UUID] = None,
    unit_id: Optional[UUID] = None,
    contractor_id: Optional[UUID] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    frequency: Optional[str] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    List maintenance schedules with filtering and pagination
    """
    # Build query
    query = select(MaintenanceSchedule)

    # Apply filters
    if property_id:
        query = query.where(MaintenanceSchedule.property_id == property_id)
    if building_id:
        query = query.where(MaintenanceSchedule.building_id == building_id)
    if unit_id:
        query = query.where(MaintenanceSchedule.unit_id == unit_id)
    if contractor_id:
        query = query.where(MaintenanceSchedule.contractor_id == contractor_id)
    if category:
        query = query.where(MaintenanceSchedule.category == category)
    if priority:
        query = query.where(MaintenanceSchedule.priority == priority)
    if frequency:
        query = query.where(MaintenanceSchedule.frequency == frequency)
    if status:
        query = query.where(MaintenanceSchedule.status == status)
    if is_active is not None:
        query = query.where(MaintenanceSchedule.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(MaintenanceSchedule.next_due_date.asc())

    # Execute
    result = await db.execute(query)
    schedules = result.scalars().all()

    # Add task counts
    schedules_with_counts = []
    for schedule in schedules:
        schedule_dict = MaintenanceScheduleResponse.model_validate(schedule).model_dump()

        # Count tasks
        task_count_query = select(func.count()).where(MaintenanceTask.schedule_id == schedule.id)
        task_count_result = await db.execute(task_count_query)
        schedule_dict['total_tasks'] = task_count_result.scalar() or 0

        # Count completed tasks
        completed_count_query = select(func.count()).where(
            and_(
                MaintenanceTask.schedule_id == schedule.id,
                MaintenanceTask.status == MaintenanceTaskStatus.COMPLETED
            )
        )
        completed_count_result = await db.execute(completed_count_query)
        schedule_dict['completed_tasks'] = completed_count_result.scalar() or 0

        schedules_with_counts.append(schedule_dict)

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": schedules_with_counts
    }


@router.post("/schedules", response_model=MaintenanceScheduleResponse, status_code=201)
async def create_maintenance_schedule(
    schedule: MaintenanceScheduleCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new maintenance schedule
    """
    # Validate at least one location is provided
    if not any([schedule.property_id, schedule.building_id, schedule.unit_id]):
        raise HTTPException(
            status_code=400,
            detail="At least one location (property_id, building_id, or unit_id) must be provided"
        )

    # Calculate next due date based on frequency
    next_due_date = calculate_next_due_date(schedule.start_date, schedule.frequency, schedule.interval_days)

    # Create schedule
    db_schedule = MaintenanceSchedule(
        **schedule.model_dump(exclude={'next_due_date'}),
        next_due_date=next_due_date,
        status=MaintenanceScheduleStatus.ACTIVE,
        is_active=True
    )

    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)

    response = MaintenanceScheduleResponse.model_validate(db_schedule)
    return response


@router.get("/schedules/{schedule_id}", response_model=MaintenanceScheduleResponse)
async def get_maintenance_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get maintenance schedule by ID
    """
    result = await db.execute(
        select(MaintenanceSchedule).where(MaintenanceSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")

    # Add task counts
    schedule_dict = MaintenanceScheduleResponse.model_validate(schedule).model_dump()

    task_count_query = select(func.count()).where(MaintenanceTask.schedule_id == schedule.id)
    task_count_result = await db.execute(task_count_query)
    schedule_dict['total_tasks'] = task_count_result.scalar() or 0

    completed_count_query = select(func.count()).where(
        and_(
            MaintenanceTask.schedule_id == schedule.id,
            MaintenanceTask.status == MaintenanceTaskStatus.COMPLETED
        )
    )
    completed_count_result = await db.execute(completed_count_query)
    schedule_dict['completed_tasks'] = completed_count_result.scalar() or 0

    return schedule_dict


@router.put("/schedules/{schedule_id}", response_model=MaintenanceScheduleResponse)
async def update_maintenance_schedule(
    schedule_id: UUID,
    schedule_update: MaintenanceScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update maintenance schedule
    """
    result = await db.execute(
        select(MaintenanceSchedule).where(MaintenanceSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")

    # Update fields
    update_data = schedule_update.model_dump(exclude_unset=True)

    # Recalculate next_due_date if frequency or interval changed
    if 'frequency' in update_data or 'interval_days' in update_data:
        new_frequency = update_data.get('frequency', schedule.frequency)
        new_interval = update_data.get('interval_days', schedule.interval_days)
        start_date = update_data.get('start_date', schedule.start_date)
        update_data['next_due_date'] = calculate_next_due_date(start_date, new_frequency, new_interval)

    for field, value in update_data.items():
        setattr(schedule, field, value)

    schedule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(schedule)

    return MaintenanceScheduleResponse.model_validate(schedule)


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_maintenance_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete maintenance schedule (cascades to tasks)
    """
    result = await db.execute(
        select(MaintenanceSchedule).where(MaintenanceSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")

    await db.delete(schedule)
    await db.commit()


@router.post("/schedules/{schedule_id}/pause", response_model=MaintenanceScheduleResponse)
async def pause_maintenance_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Pause maintenance schedule
    """
    result = await db.execute(
        select(MaintenanceSchedule).where(MaintenanceSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")

    schedule.status = MaintenanceScheduleStatus.PAUSED
    schedule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(schedule)

    return MaintenanceScheduleResponse.model_validate(schedule)


@router.post("/schedules/{schedule_id}/resume", response_model=MaintenanceScheduleResponse)
async def resume_maintenance_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Resume paused maintenance schedule
    """
    result = await db.execute(
        select(MaintenanceSchedule).where(MaintenanceSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")

    schedule.status = MaintenanceScheduleStatus.ACTIVE
    schedule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(schedule)

    return MaintenanceScheduleResponse.model_validate(schedule)


# ============================================================================
# MAINTENANCE TASKS
# ============================================================================

@router.get("/tasks", response_model=dict)
async def list_maintenance_tasks(
    schedule_id: Optional[UUID] = None,
    property_id: Optional[UUID] = None,
    building_id: Optional[UUID] = None,
    unit_id: Optional[UUID] = None,
    contractor_id: Optional[UUID] = None,
    work_order_id: Optional[UUID] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    is_overdue: Optional[bool] = None,
    assigned_to: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    List maintenance tasks with filtering and pagination
    """
    # Build query
    query = select(MaintenanceTask)

    # Apply filters
    if schedule_id:
        query = query.where(MaintenanceTask.schedule_id == schedule_id)
    if property_id:
        query = query.where(MaintenanceTask.property_id == property_id)
    if building_id:
        query = query.where(MaintenanceTask.building_id == building_id)
    if unit_id:
        query = query.where(MaintenanceTask.unit_id == unit_id)
    if contractor_id:
        query = query.where(MaintenanceTask.contractor_id == contractor_id)
    if work_order_id:
        query = query.where(MaintenanceTask.work_order_id == work_order_id)
    if category:
        query = query.where(MaintenanceTask.category == category)
    if priority:
        query = query.where(MaintenanceTask.priority == priority)
    if status:
        query = query.where(MaintenanceTask.status == status)
    if is_overdue is not None:
        query = query.where(MaintenanceTask.is_overdue == is_overdue)
    if assigned_to:
        query = query.where(MaintenanceTask.assigned_to == assigned_to)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(MaintenanceTask.scheduled_date.asc())

    # Execute
    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [MaintenanceTaskResponse.model_validate(task) for task in tasks]
    }


@router.post("/tasks", response_model=MaintenanceTaskResponse, status_code=201)
async def create_maintenance_task(
    task: MaintenanceTaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new maintenance task (ad-hoc or from schedule)
    """
    # Validate at least one location is provided
    if not any([task.property_id, task.building_id, task.unit_id]):
        raise HTTPException(
            status_code=400,
            detail="At least one location (property_id, building_id, or unit_id) must be provided"
        )

    # Create task
    db_task = MaintenanceTask(
        **task.model_dump(),
        status=MaintenanceTaskStatus.SCHEDULED,
        is_overdue=False
    )

    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)

    return MaintenanceTaskResponse.model_validate(db_task)


@router.get("/tasks/{task_id}", response_model=MaintenanceTaskResponse)
async def get_maintenance_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get maintenance task by ID
    """
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    return MaintenanceTaskResponse.model_validate(task)


@router.put("/tasks/{task_id}", response_model=MaintenanceTaskResponse)
async def update_maintenance_task(
    task_id: UUID,
    task_update: MaintenanceTaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update maintenance task
    """
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    # Update fields
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return MaintenanceTaskResponse.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_maintenance_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete maintenance task
    """
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    await db.delete(task)
    await db.commit()


@router.post("/tasks/{task_id}/start", response_model=MaintenanceTaskResponse)
async def start_maintenance_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Start maintenance task (mark as in_progress)
    """
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    task.status = MaintenanceTaskStatus.IN_PROGRESS
    task.started_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return MaintenanceTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/complete", response_model=MaintenanceTaskResponse)
async def complete_maintenance_task(
    task_id: UUID,
    completion: MaintenanceTaskComplete,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete maintenance task
    """
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    # Update task
    task.status = MaintenanceTaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    task.completion_notes = completion.completion_notes
    task.completion_photos = completion.completion_photos
    task.actual_duration_hours = completion.actual_duration_hours
    task.actual_cost = completion.actual_cost

    if completion.checklist:
        task.checklist = completion.checklist

    task.updated_at = datetime.utcnow()

    # If task is from a schedule, update schedule's last_completed_date and calculate next_due_date
    if task.schedule_id:
        schedule_result = await db.execute(
            select(MaintenanceSchedule).where(MaintenanceSchedule.id == task.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if schedule:
            schedule.last_completed_date = task.completed_at
            schedule.next_due_date = calculate_next_due_date(
                task.completed_at,
                schedule.frequency,
                schedule.interval_days
            )
            schedule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return MaintenanceTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/cancel", response_model=MaintenanceTaskResponse)
async def cancel_maintenance_task(
    task_id: UUID,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel maintenance task
    """
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    task.status = MaintenanceTaskStatus.CANCELLED
    if reason:
        task.notes = f"{task.notes}\nCancellation reason: {reason}" if task.notes else f"Cancellation reason: {reason}"
    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return MaintenanceTaskResponse.model_validate(task)


# ============================================================================
# DASHBOARD & REPORTING
# ============================================================================

@router.get("/dashboard", response_model=MaintenanceDashboard)
async def get_maintenance_dashboard(
    property_id: Optional[UUID] = None,
    building_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get maintenance dashboard statistics
    """
    now = datetime.utcnow()

    # Base query with optional filters
    base_query = select(MaintenanceTask)
    if property_id:
        base_query = base_query.where(MaintenanceTask.property_id == property_id)
    if building_id:
        base_query = base_query.where(MaintenanceTask.building_id == building_id)

    # Upcoming tasks (7 and 30 days)
    upcoming_7_query = base_query.where(
        and_(
            MaintenanceTask.scheduled_date >= now,
            MaintenanceTask.scheduled_date <= now + timedelta(days=7),
            MaintenanceTask.status == MaintenanceTaskStatus.SCHEDULED
        )
    )
    upcoming_7_result = await db.execute(select(func.count()).select_from(upcoming_7_query.subquery()))
    upcoming_7_days = upcoming_7_result.scalar() or 0

    upcoming_30_query = base_query.where(
        and_(
            MaintenanceTask.scheduled_date >= now,
            MaintenanceTask.scheduled_date <= now + timedelta(days=30),
            MaintenanceTask.status == MaintenanceTaskStatus.SCHEDULED
        )
    )
    upcoming_30_result = await db.execute(select(func.count()).select_from(upcoming_30_query.subquery()))
    upcoming_30_days = upcoming_30_result.scalar() or 0

    # Overdue tasks
    overdue_query = base_query.where(MaintenanceTask.is_overdue == True)
    overdue_result = await db.execute(select(func.count()).select_from(overdue_query.subquery()))
    overdue_count = overdue_result.scalar() or 0

    overdue_critical_query = base_query.where(
        and_(
            MaintenanceTask.is_overdue == True,
            MaintenanceTask.priority == 'critical'
        )
    )
    overdue_critical_result = await db.execute(select(func.count()).select_from(overdue_critical_query.subquery()))
    overdue_critical = overdue_critical_result.scalar() or 0

    # This month stats
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    completed_this_month_query = base_query.where(
        and_(
            MaintenanceTask.completed_at >= month_start,
            MaintenanceTask.status == MaintenanceTaskStatus.COMPLETED
        )
    )
    completed_result = await db.execute(select(func.count()).select_from(completed_this_month_query.subquery()))
    completed_this_month = completed_result.scalar() or 0

    # Total cost this month
    cost_query = select(func.sum(MaintenanceTask.actual_cost)).where(
        and_(
            MaintenanceTask.completed_at >= month_start,
            MaintenanceTask.status == MaintenanceTaskStatus.COMPLETED
        )
    )
    if property_id:
        cost_query = cost_query.where(MaintenanceTask.property_id == property_id)
    if building_id:
        cost_query = cost_query.where(MaintenanceTask.building_id == building_id)

    cost_result = await db.execute(cost_query)
    total_cost_this_month = cost_result.scalar() or Decimal('0.00')

    # Active schedules
    schedule_query = select(MaintenanceSchedule)
    if property_id:
        schedule_query = schedule_query.where(MaintenanceSchedule.property_id == property_id)
    if building_id:
        schedule_query = schedule_query.where(MaintenanceSchedule.building_id == building_id)

    active_schedules_result = await db.execute(
        select(func.count()).select_from(
            schedule_query.where(MaintenanceSchedule.status == MaintenanceScheduleStatus.ACTIVE).subquery()
        )
    )
    active_schedules = active_schedules_result.scalar() or 0

    paused_schedules_result = await db.execute(
        select(func.count()).select_from(
            schedule_query.where(MaintenanceSchedule.status == MaintenanceScheduleStatus.PAUSED).subquery()
        )
    )
    paused_schedules = paused_schedules_result.scalar() or 0

    # Tasks by category (all active/scheduled tasks)
    category_query = select(
        MaintenanceTask.category,
        func.count(MaintenanceTask.id).label('count')
    ).where(
        MaintenanceTask.status.in_([MaintenanceTaskStatus.SCHEDULED, MaintenanceTaskStatus.IN_PROGRESS])
    )
    if property_id:
        category_query = category_query.where(MaintenanceTask.property_id == property_id)
    if building_id:
        category_query = category_query.where(MaintenanceTask.building_id == building_id)

    category_query = category_query.group_by(MaintenanceTask.category).order_by(func.count(MaintenanceTask.id).desc()).limit(5)
    category_result = await db.execute(category_query)
    tasks_by_category = {row[0]: row[1] for row in category_result.all()}

    # Tasks by status
    status_query = select(
        MaintenanceTask.status,
        func.count(MaintenanceTask.id).label('count')
    )
    if property_id:
        status_query = status_query.where(MaintenanceTask.property_id == property_id)
    if building_id:
        status_query = status_query.where(MaintenanceTask.building_id == building_id)

    status_query = status_query.group_by(MaintenanceTask.status)
    status_result = await db.execute(status_query)
    tasks_by_status = {row[0]: row[1] for row in status_result.all()}

    return MaintenanceDashboard(
        upcoming_7_days=upcoming_7_days,
        upcoming_30_days=upcoming_30_days,
        overdue_count=overdue_count,
        overdue_critical=overdue_critical,
        completed_this_month=completed_this_month,
        total_cost_this_month=total_cost_this_month,
        active_schedules=active_schedules,
        paused_schedules=paused_schedules,
        tasks_by_category=tasks_by_category,
        tasks_by_status=tasks_by_status
    )


@router.get("/upcoming", response_model=MaintenanceUpcoming)
async def get_upcoming_maintenance(
    days: int = Query(30, ge=1, le=365),
    property_id: Optional[UUID] = None,
    building_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get upcoming maintenance tasks
    """
    now = datetime.utcnow()
    end_date = now + timedelta(days=days)

    query = select(MaintenanceTask).where(
        and_(
            MaintenanceTask.scheduled_date >= now,
            MaintenanceTask.scheduled_date <= end_date,
            MaintenanceTask.status == MaintenanceTaskStatus.SCHEDULED
        )
    )

    if property_id:
        query = query.where(MaintenanceTask.property_id == property_id)
    if building_id:
        query = query.where(MaintenanceTask.building_id == building_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get tasks
    query = query.offset(skip).limit(limit).order_by(MaintenanceTask.scheduled_date.asc())
    result = await db.execute(query)
    tasks = result.scalars().all()

    return MaintenanceUpcoming(
        tasks=[MaintenanceTaskResponse.model_validate(task) for task in tasks],
        total=total
    )


@router.get("/overdue", response_model=MaintenanceOverdue)
async def get_overdue_maintenance(
    property_id: Optional[UUID] = None,
    building_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overdue maintenance tasks
    """
    query = select(MaintenanceTask).where(MaintenanceTask.is_overdue == True)

    if property_id:
        query = query.where(MaintenanceTask.property_id == property_id)
    if building_id:
        query = query.where(MaintenanceTask.building_id == building_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Count critical
    critical_query = select(func.count()).where(
        and_(
            MaintenanceTask.is_overdue == True,
            MaintenanceTask.priority == 'critical'
        )
    )
    if property_id:
        critical_query = critical_query.where(MaintenanceTask.property_id == property_id)
    if building_id:
        critical_query = critical_query.where(MaintenanceTask.building_id == building_id)

    critical_result = await db.execute(critical_query)
    total_critical = critical_result.scalar()

    # Get tasks
    query = query.offset(skip).limit(limit).order_by(MaintenanceTask.due_date.asc())
    result = await db.execute(query)
    tasks = result.scalars().all()

    return MaintenanceOverdue(
        tasks=[MaintenanceTaskResponse.model_validate(task) for task in tasks],
        total=total,
        total_critical=total_critical
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_next_due_date(start_date: datetime, frequency: str, interval_days: Optional[int] = None) -> datetime:
    """
    Calculate next due date based on frequency
    """
    if frequency == MaintenanceFrequency.DAILY:
        return start_date + timedelta(days=1)
    elif frequency == MaintenanceFrequency.WEEKLY:
        return start_date + timedelta(days=7)
    elif frequency == MaintenanceFrequency.BIWEEKLY:
        return start_date + timedelta(days=14)
    elif frequency == MaintenanceFrequency.MONTHLY:
        return start_date + timedelta(days=30)
    elif frequency == MaintenanceFrequency.QUARTERLY:
        return start_date + timedelta(days=90)
    elif frequency == MaintenanceFrequency.SEMIANNUAL:
        return start_date + timedelta(days=180)
    elif frequency == MaintenanceFrequency.ANNUAL:
        return start_date + timedelta(days=365)
    elif frequency == MaintenanceFrequency.CUSTOM and interval_days:
        return start_date + timedelta(days=interval_days)
    else:
        # Default to monthly
        return start_date + timedelta(days=30)
