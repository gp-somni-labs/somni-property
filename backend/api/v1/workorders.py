"""
Work Orders API - Maintenance Request Management
Handles work orders, assignment workflow, and IoT-triggered maintenance
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import logging

from db.database import get_db
from db.models import WorkOrder, Unit, Building, Tenant, WorkOrderEvent, Contractor, WorkOrderTask, WorkOrderMaterial
from api.schemas import (
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderAssign,
    WorkOrderComplete,
    WorkOrderResponse,
    WorkOrderListResponse,
    WorkOrderEventCreate,
    WorkOrderEventResponse,
    WorkOrderTaskCreate,
    WorkOrderTaskUpdate,
    WorkOrderTaskResponse,
    WorkOrderMaterialCreate,
    WorkOrderMaterialUpdate,
    WorkOrderMaterialResponse
)
from core.auth import get_auth_user, require_manager, get_current_tenant, AuthUser, CurrentTenant
from core.security.rbac import require_permission, require_role, Role
from services.mqtt_client import mqtt_service
from services.websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# WORK ORDER CRUD OPERATIONS
# ============================================================================

@router.get("", response_model=WorkOrderListResponse)
@require_permission("work_orders", "read")
async def list_work_orders(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    unit_id: Optional[UUID] = None,
    building_id: Optional[UUID] = None,
    assigned_to: Optional[str] = None,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List work orders with optional filtering

    RBAC: Requires 'read' permission on 'work_orders' resource
    - **Admin/Operator/Technician**: Can see work orders based on role
    - **Read-only**: Can view work orders
    """
    query = select(WorkOrder)

    # Role-based filtering
    if not (auth_user.is_admin or auth_user.is_manager):
        # Tenants can only see their own work orders
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.auth_user_id == auth_user.username)
        )
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            return WorkOrderListResponse(items=[], total=0, skip=skip, limit=limit)

        query = query.where(WorkOrder.tenant_id == tenant.id)

    # Apply filters
    if status:
        query = query.where(WorkOrder.status == status)

    if priority:
        query = query.where(WorkOrder.priority == priority)

    if category:
        query = query.where(WorkOrder.category == category)

    if unit_id:
        query = query.where(WorkOrder.unit_id == unit_id)

    if building_id:
        query = query.where(WorkOrder.building_id == building_id)

    if assigned_to:
        query = query.where(WorkOrder.assigned_to == assigned_to)

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(WorkOrder.created_at.desc())
    result = await db.execute(query)
    work_orders = result.scalars().all()

    return WorkOrderListResponse(
        items=work_orders,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
async def get_work_order(
    work_order_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get work order by ID with tasks, materials, and events"""
    result = await db.execute(
        select(WorkOrder)
        .options(
            selectinload(WorkOrder.tasks),
            selectinload(WorkOrder.materials),
            selectinload(WorkOrder.events)
        )
        .where(WorkOrder.id == work_order_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Authorization check for tenants
    if not (auth_user.is_admin or auth_user.is_manager):
        tenant_result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id == work_order.tenant_id,
                    Tenant.auth_user_id == auth_user.username
                )
            )
        )
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this work order"
            )

    return work_order


@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
@require_permission("work_orders", "create")
async def create_work_order(
    work_order_data: WorkOrderCreate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new work order

    RBAC: Requires 'create' permission on 'work_orders' resource
    (Admin/Operator only)
    """
    # Validate unit/building exists if provided
    if work_order_data.unit_id:
        unit_result = await db.execute(
            select(Unit).where(Unit.id == work_order_data.unit_id)
        )
        if not unit_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )

    if work_order_data.building_id:
        building_result = await db.execute(
            select(Building).where(Building.id == work_order_data.building_id)
        )
        if not building_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Building not found"
            )

    # Create work order
    work_order = WorkOrder(
        unit_id=work_order_data.unit_id,
        building_id=work_order_data.building_id,
        tenant_id=work_order_data.tenant_id,
        title=work_order_data.title,
        description=work_order_data.description,
        category=work_order_data.category,
        priority=work_order_data.priority,
        estimated_cost=work_order_data.estimated_cost,
        status='open'
    )

    db.add(work_order)
    await db.commit()
    await db.refresh(work_order)

    logger.info(f"Created work order {work_order.id}: {work_order.title}")

    # Publish MQTT notification
    try:
        await mqtt_service.publish(
            f"somniproperty/workorder/created",
            {
                "work_order_id": str(work_order.id),
                "title": work_order.title,
                "priority": work_order.priority,
                "category": work_order.category
            }
        )
    except Exception as e:
        logger.warning(f"Failed to publish MQTT notification: {e}")

    return work_order


@router.put("/{work_order_id}", response_model=WorkOrderResponse)
async def update_work_order(
    work_order_id: UUID,
    work_order_data: WorkOrderUpdate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Update a work order (Admin/Manager only)"""
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Update fields
    update_data = work_order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(work_order, field, value)

    work_order.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(work_order)

    logger.info(f"Updated work order {work_order.id}")
    return work_order


@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_order(
    work_order_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Delete a work order (Admin/Manager only)"""
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    await db.delete(work_order)
    await db.commit()

    logger.info(f"Deleted work order {work_order_id}")


# ============================================================================
# WORK ORDER WORKFLOW
# ============================================================================

@router.post("/{work_order_id}/assign", response_model=WorkOrderResponse)
async def assign_work_order(
    work_order_id: UUID,
    assign_data: WorkOrderAssign,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Assign a work order to a contractor (Admin/Manager only)"""
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Verify contractor exists
    contractor_result = await db.execute(
        select(Contractor).where(Contractor.id == assign_data.assigned_to)
    )
    contractor = contractor_result.scalar_one_or_none()

    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contractor not found"
        )

    # Store old assignment for event
    old_assigned_to = work_order.assigned_to
    old_contractor_name = None
    if old_assigned_to:
        old_contractor_result = await db.execute(
            select(Contractor).where(Contractor.id == old_assigned_to)
        )
        old_contractor = old_contractor_result.scalar_one_or_none()
        if old_contractor:
            old_contractor_name = old_contractor.company_name

    # Update work order
    work_order.assigned_to = assign_data.assigned_to
    work_order.status = 'assigned'
    work_order.updated_at = datetime.utcnow()

    # Create event
    event = WorkOrderEvent(
        work_order_id=work_order_id,
        event_type='assignment' if not old_assigned_to else 'reassignment',
        old_value=old_contractor_name,
        new_value=contractor.company_name,
        created_by=auth_user.username,
        created_by_type='staff',
        notes=f"Work order assigned to {contractor.company_name}"
    )
    db.add(event)

    await db.commit()
    await db.refresh(work_order)

    logger.info(f"Assigned work order {work_order.id} to contractor {contractor.company_name}")

    # Publish MQTT notification
    try:
        await mqtt_service.publish(
            f"somniproperty/workorder/assigned",
            {
                "work_order_id": str(work_order.id),
                "assigned_to": str(assign_data.assigned_to),
                "contractor_name": contractor.company_name,
                "title": work_order.title
            }
        )
    except Exception as e:
        logger.warning(f"Failed to publish MQTT notification: {e}")

    # Send WebSocket notification
    try:
        room = f"property:{work_order.building_id}" if work_order.building_id else None
        await ws_manager.send_work_order_update(
            work_order_id=work_order.id,
            status='assigned',
            title=work_order.title,
            room=room
        )
    except Exception as e:
        logger.warning(f"Failed to send WebSocket notification: {e}")

    return work_order


@router.post("/{work_order_id}/start", response_model=WorkOrderResponse)
async def start_work_order(
    work_order_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Mark work order as in progress (Admin/Manager only)"""
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    if work_order.status not in ['open', 'assigned']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start work order with status: {work_order.status}"
        )

    work_order.status = 'in_progress'
    work_order.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(work_order)

    logger.info(f"Started work order {work_order.id}")
    return work_order


@router.post("/{work_order_id}/complete", response_model=WorkOrderResponse)
async def complete_work_order(
    work_order_id: UUID,
    complete_data: WorkOrderComplete,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Mark work order as completed (Admin/Manager only)"""
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    if work_order.status == 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work order is already completed"
        )

    work_order.status = 'completed'
    work_order.completed_date = datetime.utcnow()
    work_order.actual_cost = complete_data.actual_cost
    work_order.completion_notes = complete_data.completion_notes
    work_order.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(work_order)

    logger.info(f"Completed work order {work_order.id}")

    # Publish MQTT notification
    try:
        await mqtt_service.publish(
            f"somniproperty/workorder/completed",
            {
                "work_order_id": str(work_order.id),
                "title": work_order.title,
                "actual_cost": float(work_order.actual_cost) if work_order.actual_cost else None
            }
        )
    except Exception as e:
        logger.warning(f"Failed to publish MQTT notification: {e}")

    # Send WebSocket notification
    try:
        room = f"property:{work_order.building_id}" if work_order.building_id else None
        await ws_manager.send_work_order_update(
            work_order_id=work_order.id,
            status='completed',
            title=work_order.title,
            room=room
        )
    except Exception as e:
        logger.warning(f"Failed to send WebSocket notification: {e}")

    return work_order


@router.post("/{work_order_id}/cancel", response_model=WorkOrderResponse)
async def cancel_work_order(
    work_order_id: UUID,
    reason: Optional[str] = None,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a work order (Admin/Manager only)"""
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    if work_order.status in ['completed', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel work order with status: {work_order.status}"
        )

    work_order.status = 'cancelled'
    if reason:
        work_order.completion_notes = f"Cancelled: {reason}"
    work_order.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(work_order)

    logger.info(f"Cancelled work order {work_order.id}")
    return work_order


# ============================================================================
# TENANT WORK ORDER SUBMISSION
# ============================================================================

@router.post("/tenant/submit", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
async def submit_tenant_work_order(
    work_order_data: WorkOrderCreate,
    current_tenant: CurrentTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a maintenance request as a tenant

    Tenants can submit work orders for their own units
    """
    # Get tenant's current lease to determine unit
    from db.models import Lease
    lease_result = await db.execute(
        select(Lease).where(
            and_(
                Lease.tenant_id == current_tenant.tenant.id,
                Lease.status == 'active'
            )
        ).order_by(Lease.start_date.desc())
    )
    lease = lease_result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active lease found. Cannot submit work order."
        )

    # Create work order for tenant's unit
    work_order = WorkOrder(
        unit_id=lease.unit_id,
        tenant_id=current_tenant.tenant.id,
        title=work_order_data.title,
        description=work_order_data.description,
        category=work_order_data.category,
        priority=work_order_data.priority,
        status='open'
    )

    db.add(work_order)
    await db.commit()
    await db.refresh(work_order)

    logger.info(f"Tenant {current_tenant.tenant.id} submitted work order {work_order.id}")

    # Publish MQTT notification for property managers
    try:
        await mqtt_service.publish(
            f"somniproperty/workorder/tenant_submitted",
            {
                "work_order_id": str(work_order.id),
                "tenant_name": f"{current_tenant.tenant.first_name} {current_tenant.tenant.last_name}",
                "unit_id": str(lease.unit_id),
                "title": work_order.title,
                "priority": work_order.priority
            }
        )
    except Exception as e:
        logger.warning(f"Failed to publish MQTT notification: {e}")

    return work_order


# ============================================================================
# WORK ORDER TASKS
# ============================================================================

@router.get("/{work_order_id}/tasks", response_model=List[WorkOrderTaskResponse])
async def get_work_order_tasks(
    work_order_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all tasks for a work order"""
    # Verify work order exists and user has access
    wo_result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = wo_result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Get tasks
    result = await db.execute(
        select(WorkOrderTask)
        .where(WorkOrderTask.work_order_id == work_order_id)
        .order_by(WorkOrderTask.sequence)
    )
    tasks = result.scalars().all()

    return tasks


@router.post("/{work_order_id}/tasks", response_model=WorkOrderTaskResponse, status_code=status.HTTP_201_CREATED)
@require_permission("work_orders", "update")
async def create_work_order_task(
    work_order_id: UUID,
    task_data: WorkOrderTaskCreate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a task to a work order

    RBAC: Requires 'update' permission on 'work_orders' resource
    """
    # Verify work order exists
    wo_result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = wo_result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Create task
    task = WorkOrderTask(
        work_order_id=work_order_id,
        title=task_data.title,
        notes=task_data.notes,
        estimate_hours=task_data.estimate_hours,
        sequence=task_data.sequence,
        status=task_data.status
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"Created task {task.id} for work order {work_order_id}")
    return task


@router.patch("/{work_order_id}/tasks/{task_id}", response_model=WorkOrderTaskResponse)
@require_permission("work_orders", "update")
async def update_work_order_task(
    work_order_id: UUID,
    task_id: UUID,
    task_data: WorkOrderTaskUpdate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a work order task

    RBAC: Requires 'update' permission on 'work_orders' resource
    """
    # Verify task exists and belongs to work order
    result = await db.execute(
        select(WorkOrderTask).where(
            and_(
                WorkOrderTask.id == task_id,
                WorkOrderTask.work_order_id == work_order_id
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Update fields
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)

    logger.info(f"Updated task {task_id} for work order {work_order_id}")
    return task


@router.delete("/{work_order_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("work_orders", "update")
async def delete_work_order_task(
    work_order_id: UUID,
    task_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a work order task

    RBAC: Requires 'update' permission on 'work_orders' resource
    """
    # Verify task exists and belongs to work order
    result = await db.execute(
        select(WorkOrderTask).where(
            and_(
                WorkOrderTask.id == task_id,
                WorkOrderTask.work_order_id == work_order_id
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    await db.delete(task)
    await db.commit()

    logger.info(f"Deleted task {task_id} from work order {work_order_id}")


# ============================================================================
# WORK ORDER MATERIALS
# ============================================================================

@router.get("/{work_order_id}/materials", response_model=List[WorkOrderMaterialResponse])
async def get_work_order_materials(
    work_order_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all materials for a work order"""
    # Verify work order exists and user has access
    wo_result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = wo_result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Get materials
    result = await db.execute(
        select(WorkOrderMaterial)
        .where(WorkOrderMaterial.work_order_id == work_order_id)
        .order_by(WorkOrderMaterial.created_at)
    )
    materials = result.scalars().all()

    return materials


@router.post("/{work_order_id}/materials", response_model=WorkOrderMaterialResponse, status_code=status.HTTP_201_CREATED)
@require_permission("work_orders", "update")
async def create_work_order_material(
    work_order_id: UUID,
    material_data: WorkOrderMaterialCreate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a material to a work order

    RBAC: Requires 'update' permission on 'work_orders' resource
    """
    # Verify work order exists
    wo_result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = wo_result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Calculate extended cost
    extended_cost = material_data.qty * material_data.unit_cost

    # Create material
    material = WorkOrderMaterial(
        work_order_id=work_order_id,
        item=material_data.item,
        qty=material_data.qty,
        unit_cost=material_data.unit_cost,
        extended_cost=extended_cost,
        notes=material_data.notes
    )

    db.add(material)
    await db.commit()
    await db.refresh(material)

    logger.info(f"Created material {material.id} for work order {work_order_id}")
    return material


@router.patch("/{work_order_id}/materials/{material_id}", response_model=WorkOrderMaterialResponse)
@require_permission("work_orders", "update")
async def update_work_order_material(
    work_order_id: UUID,
    material_id: UUID,
    material_data: WorkOrderMaterialUpdate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a work order material

    RBAC: Requires 'update' permission on 'work_orders' resource
    """
    # Verify material exists and belongs to work order
    result = await db.execute(
        select(WorkOrderMaterial).where(
            and_(
                WorkOrderMaterial.id == material_id,
                WorkOrderMaterial.work_order_id == work_order_id
            )
        )
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )

    # Update fields
    update_data = material_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(material, field, value)

    # Recalculate extended cost if qty or unit_cost changed
    if 'qty' in update_data or 'unit_cost' in update_data:
        material.extended_cost = material.qty * material.unit_cost

    material.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(material)

    logger.info(f"Updated material {material_id} for work order {work_order_id}")
    return material


@router.delete("/{work_order_id}/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("work_orders", "update")
async def delete_work_order_material(
    work_order_id: UUID,
    material_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a work order material

    RBAC: Requires 'update' permission on 'work_orders' resource
    """
    # Verify material exists and belongs to work order
    result = await db.execute(
        select(WorkOrderMaterial).where(
            and_(
                WorkOrderMaterial.id == material_id,
                WorkOrderMaterial.work_order_id == work_order_id
            )
        )
    )
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )

    await db.delete(material)
    await db.commit()

    logger.info(f"Deleted material {material_id} from work order {work_order_id}")


# ============================================================================
# WORK ORDER STATISTICS
# ============================================================================

@router.get("/statistics/overview")
async def get_work_order_statistics(
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Get work order statistics (Admin/Manager only)

    Returns counts by status, priority, category, and average completion time
    """
    result = await db.execute(select(WorkOrder))
    work_orders = result.scalars().all()

    # Count by status
    status_counts = {}
    for wo in work_orders:
        status_counts[wo.status] = status_counts.get(wo.status, 0) + 1

    # Count by priority
    priority_counts = {}
    for wo in work_orders:
        priority_counts[wo.priority] = priority_counts.get(wo.priority, 0) + 1

    # Count by category
    category_counts = {}
    for wo in work_orders:
        category_counts[wo.category] = category_counts.get(wo.category, 0) + 1

    # Calculate average completion time
    completed_orders = [wo for wo in work_orders if wo.status == 'completed' and wo.completed_date]
    if completed_orders:
        total_days = sum((wo.completed_date - wo.created_at).days for wo in completed_orders)
        avg_completion_days = total_days / len(completed_orders)
    else:
        avg_completion_days = 0

    # Calculate total costs
    total_estimated = sum(wo.estimated_cost or 0 for wo in work_orders)
    total_actual = sum(wo.actual_cost or 0 for wo in work_orders if wo.status == 'completed')

    return {
        "total_work_orders": len(work_orders),
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "category_counts": category_counts,
        "average_completion_days": round(avg_completion_days, 1),
        "total_estimated_cost": float(total_estimated),
        "total_actual_cost": float(total_actual)
    }


# ============================================================================
# WORK ORDER EVENT TRACKING
# ============================================================================

@router.get("/{work_order_id}/events", response_model=List[WorkOrderEventResponse])
async def get_work_order_events(
    work_order_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get event history for a work order"""
    # Verify work order exists and user has access
    wo_result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = wo_result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Authorization check for tenants
    if not (auth_user.is_admin or auth_user.is_manager):
        tenant_result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id == work_order.tenant_id,
                    Tenant.auth_user_id == auth_user.username
                )
            )
        )
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this work order"
            )

    # Get events
    result = await db.execute(
        select(WorkOrderEvent)
        .where(WorkOrderEvent.work_order_id == work_order_id)
        .order_by(WorkOrderEvent.created_at.desc())
    )
    events = result.scalars().all()

    return events


@router.post("/{work_order_id}/events", response_model=WorkOrderEventResponse, status_code=status.HTTP_201_CREATED)
async def create_work_order_event(
    work_order_id: UUID,
    event_data: WorkOrderEventCreate,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an event (e.g., comment) for a work order"""
    # Verify work order exists
    wo_result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == work_order_id)
    )
    work_order = wo_result.scalar_one_or_none()

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work order not found"
        )

    # Create event
    event = WorkOrderEvent(
        work_order_id=work_order_id,
        event_type=event_data.event_type,
        old_value=event_data.old_value,
        new_value=event_data.new_value,
        created_by=event_data.created_by or auth_user.username,
        created_by_type=event_data.created_by_type,
        notes=event_data.notes,
        metadata=event_data.metadata
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.info(f"Created event for work order {work_order_id}: {event_data.event_type}")
    return event
