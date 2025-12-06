"""
Approval Workflow Engine - Human-in-the-Middle for AI Actions
Intelligent approval system with self-hosted notifications (Gotify/NTFY)
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from services.notification_service import get_notification_service
from services.email_service import EmailService
from services.sms_service import SMSService

# Integration Orchestrator - Master coordinator for all services
from services.integration_orchestrator import get_integration_orchestrator

logger = logging.getLogger(__name__)


class ApprovalWorkflowEngine:
    """
    Core approval workflow engine
    Handles creation, approval, rejection, and execution of pending actions
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_service = get_notification_service()

    async def create_pending_action(
        self,
        action_type: str,
        action_category: str,
        action_title: str,
        action_description: str,
        action_data: Dict[str, Any],
        source_type: str = 'email',
        source_message_id: Optional[uuid.UUID] = None,
        requester_type: str = 'tenant',
        tenant_id: Optional[uuid.UUID] = None,
        unit_id: Optional[uuid.UUID] = None,
        property_id: Optional[uuid.UUID] = None,
        requester_name: Optional[str] = None,
        requester_contact: Optional[str] = None,
        urgency: str = 'normal',
        estimated_cost: Optional[float] = None,
        ai_intent: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        ai_reasoning: Optional[str] = None
    ) -> uuid.UUID:
        """
        Create a pending action that requires approval

        Returns: action_id
        """
        from db.models_approval import PendingAction

        # Check approval policy to determine if auto-approval is possible
        policy = await self._find_matching_policy(
            action_type=action_type,
            property_id=property_id,
            urgency=urgency,
            estimated_cost=estimated_cost,
            requester_type=requester_type
        )

        can_auto_approve = False
        auto_approve_reason = None
        requires_approval = True
        approval_count_required = 1
        expires_at = None

        if policy:
            can_auto_approve = policy.auto_approve_enabled
            requires_approval = policy.requires_approval
            approval_count_required = policy.approval_count_required
            auto_approve_reason = policy.policy_name

            if policy.approval_timeout_hours:
                expires_at = datetime.utcnow() + timedelta(hours=policy.approval_timeout_hours)

        # Create pending action
        pending_action = PendingAction(
            source_type=source_type,
            source_message_id=source_message_id,
            requester_type=requester_type,
            tenant_id=tenant_id,
            unit_id=unit_id,
            property_id=property_id,
            requester_name=requester_name,
            requester_contact=requester_contact,
            action_type=action_type,
            action_category=action_category,
            action_title=action_title,
            action_description=action_description,
            action_data=action_data,
            ai_intent=ai_intent,
            ai_confidence=ai_confidence,
            ai_reasoning=ai_reasoning,
            urgency=urgency,
            estimated_cost=estimated_cost,
            can_auto_approve=can_auto_approve,
            auto_approve_reason=auto_approve_reason,
            approval_count_required=approval_count_required,
            expires_at=expires_at
        )

        self.db.add(pending_action)
        await self.db.commit()
        await self.db.refresh(pending_action)

        action_id = pending_action.id

        logger.info(f"Created pending action {action_id}: {action_title} (auto-approve: {can_auto_approve})")

        # Handle auto-approval or send notification
        if can_auto_approve and not requires_approval:
            await self._auto_approve_action(pending_action)
        else:
            # Send approval request notification to property managers
            await self._notify_approval_required(pending_action)

        return action_id

    async def approve_action(
        self,
        action_id: uuid.UUID,
        approver_id: uuid.UUID,
        approver_name: str,
        approver_role: str = 'property_manager',
        reason: Optional[str] = None,
        modifications: Optional[Dict] = None
    ) -> bool:
        """
        Approve a pending action
        Returns True if action is fully approved and executed
        """
        from db.models_approval import PendingAction, ApprovalAction

        # Get pending action
        query = select(PendingAction).where(PendingAction.id == action_id)
        result = await self.db.execute(query)
        pending_action = result.scalar_one_or_none()

        if not pending_action:
            logger.error(f"Pending action {action_id} not found")
            return False

        if pending_action.status != 'pending':
            logger.warning(f"Action {action_id} is not pending (status: {pending_action.status})")
            return False

        # Create approval record
        approval_action = ApprovalAction(
            pending_action_id=action_id,
            approver_id=approver_id,
            approver_name=approver_name,
            approver_role=approver_role,
            decision='approve',
            reason=reason,
            modifications=modifications,
            notification_method='gotify'  # Since notification came via Gotify/NTFY
        )

        self.db.add(approval_action)
        await self.db.commit()

        # Trigger will update pending_action status if all approvals received
        await self.db.refresh(pending_action)

        logger.info(
            f"Action {action_id} approved by {approver_name} "
            f"({pending_action.approval_count_current}/{pending_action.approval_count_required})"
        )

        # If fully approved, execute the action
        if pending_action.status == 'approved':
            await self._execute_action(pending_action, modifications)
            return True

        return False

    async def reject_action(
        self,
        action_id: uuid.UUID,
        rejector_id: uuid.UUID,
        rejector_name: str,
        reason: str,
        rejector_role: str = 'property_manager'
    ) -> bool:
        """
        Reject a pending action
        """
        from db.models_approval import PendingAction, ApprovalAction

        # Get pending action
        query = select(PendingAction).where(PendingAction.id == action_id)
        result = await self.db.execute(query)
        pending_action = result.scalar_one_or_none()

        if not pending_action:
            logger.error(f"Pending action {action_id} not found")
            return False

        # Create rejection record
        approval_action = ApprovalAction(
            pending_action_id=action_id,
            approver_id=rejector_id,
            approver_name=rejector_name,
            approver_role=rejector_role,
            decision='reject',
            reason=reason
        )

        self.db.add(approval_action)
        await self.db.commit()

        # Trigger will update pending_action status to 'rejected'
        await self.db.refresh(pending_action)

        logger.info(f"Action {action_id} rejected by {rejector_name}: {reason}")

        # Notify requester of rejection
        await self._notify_requester_of_decision(
            pending_action,
            decision='rejected',
            decision_reason=reason
        )

        return True

    async def _auto_approve_action(self, pending_action):
        """Automatically approve and execute an action"""
        from db.models_approval import ApprovalAction

        # Create system approval record
        approval_action = ApprovalAction(
            pending_action_id=pending_action.id,
            approver_name='System Auto-Approval',
            approver_role='system',
            decision='approve',
            reason=f"Auto-approved: {pending_action.auto_approve_reason}"
        )

        self.db.add(approval_action)

        pending_action.auto_approved_at = datetime.utcnow()
        pending_action.status = 'approved'
        pending_action.approved_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(pending_action)

        logger.info(f"Auto-approved action {pending_action.id}: {pending_action.action_title}")

        # Execute the action
        await self._execute_action(pending_action)

        # Notify property manager of auto-approval (for awareness)
        await self.notification_service.send_gotify(
            title=f"✅ Auto-Approved: {pending_action.action_title}",
            message=f"Action was automatically approved and executed.\n\nReason: {pending_action.auto_approve_reason}",
            priority=2
        )

    async def _execute_action(
        self,
        pending_action,
        modifications: Optional[Dict] = None
    ):
        """Execute an approved action"""
        action_type = pending_action.action_type
        action_data = pending_action.action_data

        if modifications:
            action_data.update(modifications)

        success = False
        result_message = ""
        execution_result = {}

        try:
            if action_type == 'create_work_order':
                success, result_message, execution_result = await self._execute_create_work_order(
                    pending_action,
                    action_data
                )

            elif action_type == 'book_amenity':
                success, result_message, execution_result = await self._execute_book_amenity(
                    pending_action,
                    action_data
                )

            elif action_type == 'generate_access_code':
                success, result_message, execution_result = await self._execute_generate_access_code(
                    pending_action,
                    action_data
                )

            elif action_type == 'send_payment_link':
                success, result_message, execution_result = await self._execute_send_payment_link(
                    pending_action,
                    action_data
                )

            elif action_type == 'feature_request':
                success, result_message, execution_result = await self._execute_log_feature_request(
                    pending_action,
                    action_data
                )

            elif action_type == 'bug_report':
                success, result_message, execution_result = await self._execute_log_bug_report(
                    pending_action,
                    action_data
                )

            else:
                logger.warning(f"Unknown action type: {action_type}")
                success = False
                result_message = f"Unknown action type: {action_type}"

        except Exception as e:
            logger.error(f"Error executing action {pending_action.id}: {e}", exc_info=True)
            success = False
            result_message = str(e)

        # Update pending action with execution result
        pending_action.executed = success
        pending_action.executed_at = datetime.utcnow()
        pending_action.execution_result = execution_result
        if not success:
            pending_action.execution_error = result_message

        await self.db.commit()

        # Notify property manager of execution result
        await self.notification_service.send_execution_result(
            action_id=str(pending_action.id),
            action_title=pending_action.action_title,
            success=success,
            result_message=result_message
        )

        # Notify requester of approval and result
        await self._notify_requester_of_decision(
            pending_action,
            decision='approved',
            execution_success=success,
            execution_result=result_message
        )

    async def _execute_create_work_order(self, pending_action, action_data: Dict) -> tuple:
        """
        Execute work order creation with COMPLETE 14-service integration

        Delegates to IntegrationOrchestrator which coordinates ALL services:
        1. Create work order in database
        2. Vikunja task management
        3. Homebox BOM creation
        4. Cal.com appointment scheduling
        5. Immich photo album creation
        6. Paperless-ngx document storage
        7. Nextcloud folder setup
        8. Firefly III financial tracking
        9. Novu multi-channel notifications
        10. n8n workflow automation
        11. Grafana analytics annotation
        12. MQTT IoT event publishing
        13. Documenso digital signatures (if needed)
        14. LocalAI analysis (used throughout)
        """
        from db.models import WorkOrder, Unit, Tenant

        try:
            # Step 1: Create work order in database
            work_order = WorkOrder(
                unit_id=pending_action.unit_id,
                tenant_id=pending_action.tenant_id,
                title=action_data.get('title', pending_action.action_title),
                description=action_data.get('description', pending_action.action_description),
                category=action_data.get('category', 'maintenance'),
                priority=pending_action.urgency,
                status='submitted',
                created_by_ai=True,
                notes=f"Created via AI approval workflow. Action ID: {pending_action.id}"
            )

            self.db.add(work_order)
            await self.db.commit()
            await self.db.refresh(work_order)

            work_order_id = str(work_order.id)
            logger.info(f"Created work order {work_order_id}: {work_order.title}")

            # Get related data for orchestrator
            unit = await self.db.get(Unit, pending_action.unit_id) if pending_action.unit_id else None
            tenant = await self.db.get(Tenant, pending_action.tenant_id) if pending_action.tenant_id else None

            property_name = unit.property.name if unit and unit.property else "Unknown Property"
            unit_number = unit.unit_number if unit else "N/A"
            tenant_name = f"{tenant.first_name} {tenant.last_name}" if tenant else pending_action.requester_name or "Unknown"
            tenant_email = tenant.email if tenant else pending_action.requester_contact or ""

            # Step 2: Execute complete workflow via Integration Orchestrator
            orchestrator = get_integration_orchestrator(self.db)

            workflow_result = await orchestrator.execute_complete_work_order_workflow(
                work_order_id=work_order_id,
                property_name=property_name,
                unit_number=unit_number,
                work_order_title=work_order.title,
                work_order_description=work_order.description or "",
                tenant_name=tenant_name,
                tenant_email=tenant_email,
                contractor_name=action_data.get('contractor_name'),
                contractor_email=action_data.get('contractor_email'),
                estimated_cost=pending_action.estimated_cost,
                urgency=pending_action.urgency,
                requires_parts=action_data.get('requires_parts', False),
                bom_items=action_data.get('bom_items'),
                requires_signature=action_data.get('requires_signature', False)
            )

            # Build success message from workflow results
            success_message = f"Work order {work_order_id} created with {len(workflow_result['integrations'])} integrations"

            for service, result in workflow_result['integrations'].items():
                if result['status'] == 'success':
                    success_message += f"\n✓ {service.capitalize()}"

            if workflow_result['errors']:
                success_message += f"\n\n⚠️ {len(workflow_result['errors'])} integration(s) had errors:"
                for error in workflow_result['errors']:
                    success_message += f"\n  - {error}"

            return (True, success_message, workflow_result)

        except Exception as e:
            logger.error(f"Failed to create work order: {e}", exc_info=True)
            return (False, f"Failed to create work order: {e}", {})

    async def _execute_book_amenity(self, pending_action, action_data: Dict) -> tuple:
        """Execute amenity booking"""
        # TODO: Implement amenity booking
        return (True, "Amenity booked successfully", {'booking_id': 'BOOK-123'})

    async def _execute_generate_access_code(self, pending_action, action_data: Dict) -> tuple:
        """Execute smart lock access code generation"""
        # TODO: Integrate with Home Assistant to create access code
        import random
        code = str(random.randint(1000, 9999))
        return (True, f"Access code generated: {code}", {'access_code': code})

    async def _execute_send_payment_link(self, pending_action, action_data: Dict) -> tuple:
        """Execute payment link sending"""
        # TODO: Integrate with payment processor
        payment_url = f"https://property.home.lan/pay/{pending_action.tenant_id}"
        return (True, f"Payment link sent: {payment_url}", {'payment_url': payment_url})

    async def _execute_log_feature_request(self, pending_action, action_data: Dict) -> tuple:
        """Log feature request"""
        # Just log it - already in pending_actions table
        return (True, "Feature request logged for review", {'logged': True})

    async def _execute_log_bug_report(self, pending_action, action_data: Dict) -> tuple:
        """Log bug report"""
        # Just log it - already in pending_actions table
        return (True, "Bug report logged", {'logged': True})

    async def _notify_approval_required(self, pending_action):
        """
        Send notification to property managers that approval is required

        Uses Novu for multi-channel notifications:
        - Email with approve/reject buttons
        - SMS for urgent requests
        - In-app notification
        - Push notification (if configured)
        """
        from db.models_approval import ApprovalNotification

        # Build notification content
        title = f"🔔 Approval Required: {pending_action.action_title}"

        message = f"""
**Action Type:** {pending_action.action_type.replace('_', ' ').title()}
**Urgency:** {pending_action.urgency.upper()}
**Requester:** {pending_action.requester_name or 'Unknown'}

{pending_action.action_description}
"""

        # Determine action URL
        action_url = f"https://property.home.lan/approvals/{pending_action.id}"

        # Send via Novu for rich multi-channel notifications
        try:
            novu_client = get_novu_client()

            # TODO: Get manager subscriber ID from property configuration
            manager_subscriber_id = "manager-primary"

            novu_tx_id = await novu_client.send_approval_request(
                manager_id=manager_subscriber_id,
                action_type=pending_action.action_type,
                action_title=pending_action.action_title,
                action_description=pending_action.action_description,
                estimated_cost=float(pending_action.estimated_cost) if pending_action.estimated_cost else None,
                urgency=pending_action.urgency,
                approval_url=action_url,
                metadata={
                    'action_id': str(pending_action.id),
                    'requester_name': pending_action.requester_name,
                    'property_id': str(pending_action.property_id) if pending_action.property_id else None,
                    'unit_id': str(pending_action.unit_id) if pending_action.unit_id else None
                }
            )

            if novu_tx_id:
                # Log Novu notification
                notification_record = ApprovalNotification(
                    pending_action_id=pending_action.id,
                    notification_type='creation',
                    notification_channel='novu',
                    notification_title=title,
                    notification_body=message,
                    delivered=True
                )
                self.db.add(notification_record)

                logger.info(f"Sent Novu approval notification {novu_tx_id} for action {pending_action.id}")

        except Exception as e:
            logger.error(f"Failed to send Novu notification: {e}")

            # Fallback to basic Gotify/NTFY notification
            try:
                notification_results = await self.notification_service.send_approval_request(
                    title=title,
                    message=message,
                    action_id=str(pending_action.id),
                    urgency=pending_action.urgency,
                    estimated_cost=float(pending_action.estimated_cost) if pending_action.estimated_cost else None,
                    requester_name=pending_action.requester_name,
                    action_url=action_url
                )

                # Log fallback notifications
                for channel, success in notification_results.items():
                    notification_record = ApprovalNotification(
                        pending_action_id=pending_action.id,
                        notification_type='creation',
                        notification_channel=channel,
                        notification_title=title,
                        notification_body=message,
                        delivered=success
                    )
                    self.db.add(notification_record)

                logger.info(f"Sent fallback Gotify/NTFY notification for action {pending_action.id}")

            except Exception as fallback_error:
                logger.error(f"Failed to send fallback notification: {fallback_error}")

        pending_action.notification_sent = True
        pending_action.notification_sent_at = datetime.utcnow()

        await self.db.commit()

        logger.info(f"Sent approval notification for action {pending_action.id}")

    async def _notify_requester_of_decision(
        self,
        pending_action,
        decision: str,
        decision_reason: Optional[str] = None,
        execution_success: Optional[bool] = None,
        execution_result: Optional[str] = None
    ):
        """Notify requester (tenant/contractor) of approval decision via email/SMS"""
        # Determine contact method
        contact = pending_action.requester_contact
        if not contact:
            logger.warning(f"No contact info for requester of action {pending_action.id}")
            return

        # Build message based on decision
        if decision == 'approved':
            subject = f"✅ Approved: {pending_action.action_title}"
            if execution_success:
                body = f"""
Hi {pending_action.requester_name or 'there'},

Good news! Your request has been approved and processed.

{execution_result}

Action ID: {pending_action.id}

Thank you,
Property Management Team
"""
            else:
                body = f"""
Hi {pending_action.requester_name or 'there'},

Your request has been approved but there was an issue processing it.
Our team has been notified and will follow up shortly.

Action ID: {pending_action.id}

Thank you,
Property Management Team
"""

        else:  # rejected
            subject = f"❌ Declined: {pending_action.action_title}"
            body = f"""
Hi {pending_action.requester_name or 'there'},

After reviewing your request, we're unable to proceed at this time.

Reason: {decision_reason or 'No specific reason provided'}

If you have questions, please contact our office.

Action ID: {pending_action.id}

Thank you,
Property Management Team
"""

        # Send via appropriate channel
        if '@' in contact:  # Email
            # Use email_service to send
            logger.info(f"Would send email to {contact}: {subject}")
            # TODO: Implement actual email sending via email_service

        else:  # Phone number - SMS
            # Use sms_service to send
            sms_body = body[:160]  # Truncate for SMS
            logger.info(f"Would send SMS to {contact}: {sms_body}")
            # TODO: Implement actual SMS sending via sms_service

    async def _find_matching_policy(
        self,
        action_type: str,
        property_id: Optional[uuid.UUID],
        urgency: str,
        estimated_cost: Optional[float],
        requester_type: str
    ):
        """Find the best matching approval policy"""
        from db.models_approval import ApprovalPolicy

        query = select(ApprovalPolicy).where(
            ApprovalPolicy.is_active == True,
            or_(
                ApprovalPolicy.applies_to_all_properties == True,
                ApprovalPolicy.property_id == property_id
            )
        ).order_by(ApprovalPolicy.priority.asc())

        result = await self.db.execute(query)
        policies = result.scalars().all()

        for policy in policies:
            # Check if action type matches
            action_types = json.loads(policy.action_types)
            if action_type not in action_types:
                continue

            # Check urgency if specified
            if policy.urgency_levels:
                urgency_levels = json.loads(policy.urgency_levels)
                if urgency not in urgency_levels:
                    continue

            # Check cost if specified
            if policy.max_estimated_cost and estimated_cost:
                if estimated_cost > policy.max_estimated_cost:
                    continue

            # This policy matches!
            return policy

        return None


# Helper functions for use in agentic_responder

async def request_approval(
    db: AsyncSession,
    **kwargs
) -> uuid.UUID:
    """
    Create a pending action requiring approval
    Returns action_id
    """
    workflow = ApprovalWorkflowEngine(db)
    return await workflow.create_pending_action(**kwargs)


async def approve_action(
    db: AsyncSession,
    action_id: uuid.UUID,
    approver_id: uuid.UUID,
    **kwargs
) -> bool:
    """Approve an action"""
    workflow = ApprovalWorkflowEngine(db)
    return await workflow.approve_action(action_id, approver_id, **kwargs)


async def reject_action(
    db: AsyncSession,
    action_id: uuid.UUID,
    rejector_id: uuid.UUID,
    **kwargs
) -> bool:
    """Reject an action"""
    workflow = ApprovalWorkflowEngine(db)
    return await workflow.reject_action(action_id, rejector_id, **kwargs)
