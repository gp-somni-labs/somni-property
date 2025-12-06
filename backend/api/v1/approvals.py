"""
Approvals API - Manage human-in-the-middle approval workflow
Handles pending actions, approval policies, and decision tracking
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid

from db.database import get_db
from db.models_approval import (
    PendingAction, ApprovalAction, ApprovalPolicy, ApprovalNotification
)
from services.approval_workflow import ApprovalWorkflowEngine
from services.integration_orchestrator import get_integration_orchestrator

router = APIRouter(prefix="/approvals", tags=["approvals"])


# ==========================================================================
# PYDANTIC SCHEMAS
# ==========================================================================

class PendingActionCreate(BaseModel):
    action_type: str
    action_category: str
    action_title: str
    action_description: str
    action_data: Dict[str, Any]
    source_type: str = 'web'
    source_message_id: Optional[uuid.UUID] = None
    requester_type: str = 'tenant'
    tenant_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    property_id: Optional[uuid.UUID] = None
    requester_name: Optional[str] = None
    requester_contact: Optional[str] = None
    urgency: str = 'normal'
    estimated_cost: Optional[float] = None
    ai_intent: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_reasoning: Optional[str] = None


class PendingActionResponse(BaseModel):
    id: uuid.UUID
    action_type: str
    action_category: str
    action_title: str
    action_description: str
    action_data: Dict[str, Any]
    source_type: str
    requester_type: str
    requester_name: Optional[str] = None
    urgency: str
    priority: int
    estimated_cost: Optional[float] = None
    status: str
    can_auto_approve: bool
    auto_approve_reason: Optional[str] = None
    approval_count_required: int
    approval_count_current: int
    ai_intent: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_suggested_action: Optional[str] = None
    ai_risk_assessment: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalDecision(BaseModel):
    decision: str  # 'approve', 'reject', 'request_info', 'delegate'
    reason: Optional[str] = None
    conditions: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
    delegated_to: Optional[uuid.UUID] = None


class ApprovalPolicyCreate(BaseModel):
    policy_name: str
    policy_description: Optional[str] = None
    property_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    applies_to_all_properties: bool = False
    action_types: List[str]
    requester_types: Optional[List[str]] = None
    urgency_levels: Optional[List[str]] = None
    max_estimated_cost: Optional[float] = None
    auto_approve_enabled: bool = False
    auto_approve_conditions: Optional[Dict[str, Any]] = None
    requires_approval: bool = True
    requires_multi_approval: bool = False
    approval_count_required: int = 1
    approved_roles: Optional[List[str]] = None
    approval_timeout_hours: Optional[int] = None
    notify_on_creation: bool = True
    notify_on_approval: bool = True
    notify_on_rejection: bool = True


class ApprovalPolicyResponse(BaseModel):
    id: uuid.UUID
    policy_name: str
    policy_description: Optional[str] = None
    action_types: str
    auto_approve_enabled: bool
    requires_approval: bool
    approval_count_required: int
    is_active: bool
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================================================
# PENDING ACTIONS ENDPOINTS
# ==========================================================================

@router.post("/actions", response_model=PendingActionResponse)
async def create_pending_action(
    action: PendingActionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new pending action requiring approval
    """
    try:
        engine = ApprovalWorkflowEngine(db)

        action_id = await engine.create_pending_action(
            action_type=action.action_type,
            action_category=action.action_category,
            action_title=action.action_title,
            action_description=action.action_description,
            action_data=action.action_data,
            source_type=action.source_type,
            source_message_id=action.source_message_id,
            requester_type=action.requester_type,
            tenant_id=action.tenant_id,
            unit_id=action.unit_id,
            property_id=action.property_id,
            requester_name=action.requester_name,
            requester_contact=action.requester_contact,
            urgency=action.urgency,
            estimated_cost=action.estimated_cost,
            ai_intent=action.ai_intent,
            ai_confidence=action.ai_confidence,
            ai_reasoning=action.ai_reasoning
        )

        await db.commit()

        # Retrieve created action
        result = await db.execute(
            select(PendingAction).where(PendingAction.id == action_id)
        )
        created_action = result.scalar_one()

        return created_action

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create pending action: {str(e)}")


@router.get("/actions", response_model=List[PendingActionResponse])
async def list_pending_actions(
    status: Optional[str] = None,
    action_type: Optional[str] = None,
    urgency: Optional[str] = None,
    property_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List pending actions with optional filtering
    """
    try:
        query = select(PendingAction)

        filters = []
        if status:
            filters.append(PendingAction.status == status)
        if action_type:
            filters.append(PendingAction.action_type == action_type)
        if urgency:
            filters.append(PendingAction.urgency == urgency)
        if property_id:
            filters.append(PendingAction.property_id == property_id)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(desc(PendingAction.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        actions = result.scalars().all()

        return actions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pending actions: {str(e)}")


@router.get("/actions/{action_id}", response_model=PendingActionResponse)
async def get_pending_action(
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific pending action
    """
    try:
        result = await db.execute(
            select(PendingAction).where(PendingAction.id == action_id)
        )
        action = result.scalar_one_or_none()

        if not action:
            raise HTTPException(status_code=404, detail="Pending action not found")

        return action

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pending action: {str(e)}")


@router.post("/actions/{action_id}/decide")
async def make_approval_decision(
    action_id: uuid.UUID,
    decision: ApprovalDecision,
    approver_id: uuid.UUID,  # TODO: Get from auth token
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Make an approval decision (approve, reject, request_info, delegate)
    """
    try:
        engine = ApprovalWorkflowEngine(db)

        if decision.decision == 'approve':
            result = await engine.approve_action(
                action_id=action_id,
                approver_id=approver_id,
                reason=decision.reason,
                conditions=decision.conditions
            )
        elif decision.decision == 'reject':
            result = await engine.reject_action(
                action_id=action_id,
                rejector_id=approver_id,
                reason=decision.reason or "No reason provided"
            )
        elif decision.decision == 'delegate':
            if not decision.delegated_to:
                raise HTTPException(status_code=400, detail="delegated_to is required for delegation")
            result = await engine.delegate_action(
                action_id=action_id,
                delegator_id=approver_id,
                delegatee_id=decision.delegated_to,
                reason=decision.reason
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid decision: {decision.decision}")

        await db.commit()

        return {
            "success": True,
            "action_id": action_id,
            "decision": decision.decision,
            "status": result.get("status"),
            "executed": result.get("executed", False)
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process decision: {str(e)}")


@router.delete("/actions/{action_id}")
async def cancel_pending_action(
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a pending action
    """
    try:
        result = await db.execute(
            select(PendingAction).where(PendingAction.id == action_id)
        )
        action = result.scalar_one_or_none()

        if not action:
            raise HTTPException(status_code=404, detail="Pending action not found")

        if action.status != 'pending':
            raise HTTPException(status_code=400, detail="Can only cancel pending actions")

        action.status = 'cancelled'
        await db.commit()

        return {"success": True, "message": "Action cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel action: {str(e)}")


# ==========================================================================
# APPROVAL POLICIES ENDPOINTS
# ==========================================================================

@router.post("/policies", response_model=ApprovalPolicyResponse)
async def create_approval_policy(
    policy: ApprovalPolicyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new approval policy
    """
    try:
        new_policy = ApprovalPolicy(
            policy_name=policy.policy_name,
            policy_description=policy.policy_description,
            property_id=policy.property_id,
            building_id=policy.building_id,
            applies_to_all_properties=policy.applies_to_all_properties,
            action_types=str(policy.action_types),
            requester_types=str(policy.requester_types) if policy.requester_types else None,
            urgency_levels=str(policy.urgency_levels) if policy.urgency_levels else None,
            max_estimated_cost=policy.max_estimated_cost,
            auto_approve_enabled=policy.auto_approve_enabled,
            auto_approve_conditions=policy.auto_approve_conditions,
            requires_approval=policy.requires_approval,
            requires_multi_approval=policy.requires_multi_approval,
            approval_count_required=policy.approval_count_required,
            approved_roles=str(policy.approved_roles) if policy.approved_roles else None,
            approval_timeout_hours=policy.approval_timeout_hours,
            notify_on_creation=policy.notify_on_creation,
            notify_on_approval=policy.notify_on_approval,
            notify_on_rejection=policy.notify_on_rejection
        )

        db.add(new_policy)
        await db.commit()
        await db.refresh(new_policy)

        return new_policy

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create approval policy: {str(e)}")


@router.get("/policies", response_model=List[ApprovalPolicyResponse])
async def list_approval_policies(
    is_active: Optional[bool] = None,
    property_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List approval policies
    """
    try:
        query = select(ApprovalPolicy).order_by(ApprovalPolicy.priority)

        filters = []
        if is_active is not None:
            filters.append(ApprovalPolicy.is_active == is_active)
        if property_id:
            filters.append(
                or_(
                    ApprovalPolicy.property_id == property_id,
                    ApprovalPolicy.applies_to_all_properties == True
                )
            )

        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(query)
        policies = result.scalars().all()

        return policies

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list policies: {str(e)}")


@router.get("/policies/{policy_id}", response_model=ApprovalPolicyResponse)
async def get_approval_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific approval policy
    """
    try:
        result = await db.execute(
            select(ApprovalPolicy).where(ApprovalPolicy.id == policy_id)
        )
        policy = result.scalar_one_or_none()

        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        return policy

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get policy: {str(e)}")


@router.put("/policies/{policy_id}")
async def update_approval_policy(
    policy_id: uuid.UUID,
    policy: ApprovalPolicyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an approval policy
    """
    try:
        result = await db.execute(
            select(ApprovalPolicy).where(ApprovalPolicy.id == policy_id)
        )
        existing_policy = result.scalar_one_or_none()

        if not existing_policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        # Update fields
        existing_policy.policy_name = policy.policy_name
        existing_policy.policy_description = policy.policy_description
        existing_policy.action_types = str(policy.action_types)
        existing_policy.auto_approve_enabled = policy.auto_approve_enabled
        existing_policy.requires_approval = policy.requires_approval
        existing_policy.approval_count_required = policy.approval_count_required
        # ... update other fields as needed

        await db.commit()
        await db.refresh(existing_policy)

        return existing_policy

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {str(e)}")


@router.delete("/policies/{policy_id}")
async def delete_approval_policy(
    policy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (deactivate) an approval policy
    """
    try:
        result = await db.execute(
            select(ApprovalPolicy).where(ApprovalPolicy.id == policy_id)
        )
        policy = result.scalar_one_or_none()

        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        policy.is_active = False
        await db.commit()

        return {"success": True, "message": "Policy deactivated"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete policy: {str(e)}")


# ==========================================================================
# STATISTICS & ANALYTICS
# ==========================================================================

@router.get("/stats")
async def get_approval_statistics(
    property_id: Optional[uuid.UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get approval workflow statistics
    """
    try:
        query = select(PendingAction)

        filters = []
        if property_id:
            filters.append(PendingAction.property_id == property_id)
        if start_date:
            filters.append(PendingAction.created_at >= start_date)
        if end_date:
            filters.append(PendingAction.created_at <= end_date)

        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(query)
        actions = result.scalars().all()

        # Calculate statistics
        total_actions = len(actions)
        pending = len([a for a in actions if a.status == 'pending'])
        approved = len([a for a in actions if a.status == 'approved'])
        rejected = len([a for a in actions if a.status == 'rejected'])
        auto_approved = len([a for a in actions if a.can_auto_approve and a.status == 'approved'])

        avg_approval_time = None
        if approved > 0:
            approval_times = [
                (a.approved_at - a.created_at).total_seconds() / 3600
                for a in actions
                if a.approved_at and a.created_at
            ]
            if approval_times:
                avg_approval_time = sum(approval_times) / len(approval_times)

        return {
            "total_actions": total_actions,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "auto_approved": auto_approved,
            "approval_rate": (approved / total_actions * 100) if total_actions > 0 else 0,
            "avg_approval_time_hours": avg_approval_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
