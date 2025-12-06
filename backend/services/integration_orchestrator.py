"""
Integration Orchestrator - Master Conductor for All SomniCluster Services

Coordinates complex multi-service workflows across 14 integrated services:
- Novu (notifications)
- Vikunja (task management)
- Cal.com (scheduling)
- Homebox (inventory/BOM)
- Paperless-ngx (document management)
- Invoice Ninja (invoicing)
- Documenso (digital signatures)
- Immich (photo management)
- n8n (workflow automation)
- LocalAI (AI inference)
- Nextcloud (file storage)
- Firefly III (financial tracking)
- MQTT (IoT integration)
- Grafana (analytics)

Provides unified high-level workflows for property management operations.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from services.novu_client import get_novu_client
from services.vikunja_client import get_vikunja_client, TaskPriority
from services.calcom_client import get_calcom_client
from services.homebox_client import get_homebox_client
from services.paperless_client import get_paperless_client
from services.invoiceninja_client import get_invoiceninja_client
from services.documenso_client import get_documenso_client
from services.immich_client import get_immich_client
from services.n8n_client import get_n8n_client
from services.localai_client import get_localai_client
from services.nextcloud_client import get_nextcloud_client
from services.fireflyiii_client import get_fireflyiii_client
from services.mqtt_client import get_mqtt_client
from services.grafana_client import get_grafana_client
from services.contractor_manager import get_contractor_manager
from services.quote_lookup_service import get_quote_lookup_service

logger = logging.getLogger(__name__)


class IntegrationOrchestrator:
    """
    Master orchestrator for complex multi-service workflows

    Provides high-level methods that coordinate multiple services
    to accomplish complete business workflows.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # Initialize all service clients (lazy loaded)
        self._novu = None
        self._vikunja = None
        self._calcom = None
        self._homebox = None
        self._paperless = None
        self._invoiceninja = None
        self._documenso = None
        self._immich = None
        self._n8n = None
        self._localai = None
        self._nextcloud = None
        self._fireflyiii = None
        self._mqtt = None
        self._grafana = None
        self._contractor_manager = None
        self._quote_lookup = None

    # ========================================
    # Property Initialization
    # ========================================

    @property
    def novu(self):
        if self._novu is None:
            self._novu = get_novu_client()
        return self._novu

    @property
    def vikunja(self):
        if self._vikunja is None:
            self._vikunja = get_vikunja_client()
        return self._vikunja

    @property
    def calcom(self):
        if self._calcom is None:
            self._calcom = get_calcom_client()
        return self._calcom

    @property
    def homebox(self):
        if self._homebox is None:
            self._homebox = get_homebox_client()
        return self._homebox

    @property
    def paperless(self):
        if self._paperless is None:
            self._paperless = get_paperless_client()
        return self._paperless

    @property
    def invoiceninja(self):
        if self._invoiceninja is None:
            self._invoiceninja = get_invoiceninja_client()
        return self._invoiceninja

    @property
    def documenso(self):
        if self._documenso is None:
            self._documenso = get_documenso_client()
        return self._documenso

    @property
    def immich(self):
        if self._immich is None:
            self._immich = get_immich_client()
        return self._immich

    @property
    def n8n(self):
        if self._n8n is None:
            self._n8n = get_n8n_client()
        return self._n8n

    @property
    def localai(self):
        if self._localai is None:
            self._localai = get_localai_client()
        return self._localai

    @property
    def nextcloud(self):
        if self._nextcloud is None:
            self._nextcloud = get_nextcloud_client()
        return self._nextcloud

    @property
    def fireflyiii(self):
        if self._fireflyiii is None:
            self._fireflyiii = get_fireflyiii_client()
        return self._fireflyiii

    @property
    def mqtt(self):
        if self._mqtt is None:
            self._mqtt = get_mqtt_client()
        return self._mqtt

    @property
    def grafana(self):
        if self._grafana is None:
            self._grafana = get_grafana_client()
        return self._grafana

    @property
    def contractor_manager(self):
        if self._contractor_manager is None:
            self._contractor_manager = get_contractor_manager(self.db)
        return self._contractor_manager

    @property
    def quote_lookup(self):
        if self._quote_lookup is None:
            self._quote_lookup = get_quote_lookup_service(self.db)
        return self._quote_lookup

    # ========================================
    # Intelligent Contractor/Staff Assignment
    # ========================================

    async def find_and_assign_contractor(
        self,
        work_order_id: uuid.UUID,
        service_category: str,
        property_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        urgency: str = 'normal',
        estimated_hours: Optional[Decimal] = None,
        estimated_cost: Optional[Decimal] = None,
        service_description: str = '',
        assigned_by: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Intelligent 3-tier contractor/staff assignment:

        1. Try in-house staff first
        2. Try approved contractors second
        3. Trigger automated quote gathering if neither available

        Returns:
        {
            'assignment_type': 'staff'|'contractor'|'quotes_pending',
            'assignment_id': UUID (if assigned),
            'resource_name': str (if assigned),
            'quote_campaign_id': UUID (if quotes gathering),
            'estimated_cost': Decimal,
            'status': 'assigned'|'quotes_pending'|'failed'
        }
        """
        result = {
            'assignment_type': None,
            'assignment_id': None,
            'resource_name': None,
            'quote_campaign_id': None,
            'estimated_cost': estimated_cost,
            'status': 'pending',
            'errors': []
        }

        logger.info(f"Finding resource for work order {work_order_id}, category: {service_category}")

        try:
            # Step 1: Try to find best available resource (staff or contractor)
            best_match = await self.contractor_manager.find_best_resource(
                service_category=service_category,
                property_id=property_id,
                urgency=urgency,
                estimated_hours=estimated_hours,
                max_budget=estimated_cost
            )

            if best_match:
                # Found someone! Assign them
                logger.info(
                    f"Found resource: {best_match.resource_type} '{best_match.resource_name}' "
                    f"(match score: {best_match.match_score:.2f})"
                )

                assignment_id = await self.contractor_manager.assign_work_order(
                    work_order_id=work_order_id,
                    resource_type=best_match.resource_type,
                    resource_id=best_match.resource_id,
                    assigned_by=assigned_by or uuid.uuid4(),  # System assignment
                    estimated_hours=estimated_hours,
                    estimated_cost=best_match.estimated_cost or estimated_cost,
                    assignment_method='auto_assigned'
                )

                result['assignment_type'] = best_match.resource_type
                result['assignment_id'] = assignment_id
                result['resource_name'] = best_match.resource_name
                result['estimated_cost'] = best_match.estimated_cost or estimated_cost
                result['status'] = 'assigned'

                logger.info(f"Work order {work_order_id} assigned to {best_match.resource_name}")

            else:
                # No one available - trigger automated quote gathering
                logger.warning(
                    f"No available resources for work order {work_order_id} - "
                    f"triggering automated quote gathering"
                )

                campaign_id = await self.contractor_manager.request_quotes(
                    work_order_id=work_order_id,
                    service_category=service_category,
                    service_description=service_description,
                    property_id=property_id,
                    unit_id=unit_id,
                    urgency=urgency,
                    target_quote_count=3,
                    deadline_hours=48 if urgency != 'emergency' else 24
                )

                result['assignment_type'] = 'quotes_pending'
                result['quote_campaign_id'] = campaign_id
                result['status'] = 'quotes_pending'

                logger.info(
                    f"Quote gathering campaign {campaign_id} started for work order {work_order_id}"
                )

                # Send notification to manager
                await self.novu.send_notification(
                    subscriber_id='manager-primary',
                    workflow_id='quote-gathering-started',
                    payload={
                        'work_order_id': str(work_order_id),
                        'service_category': service_category,
                        'campaign_id': str(campaign_id),
                        'urgency': urgency
                    }
                )

        except Exception as e:
            logger.error(f"Failed to assign contractor for work order {work_order_id}: {e}", exc_info=True)
            result['status'] = 'failed'
            result['errors'].append(str(e))

        return result

    # ========================================
    # Complete Workflow: Work Order Full Lifecycle
    # ========================================

    async def execute_complete_work_order_workflow(
        self,
        work_order_id: str,
        property_name: str,
        unit_number: str,
        work_order_title: str,
        work_order_description: str,
        tenant_name: str,
        tenant_email: str,
        contractor_name: Optional[str] = None,
        contractor_email: Optional[str] = None,
        estimated_cost: Optional[Decimal] = None,
        urgency: str = "normal",
        requires_parts: bool = False,
        bom_items: Optional[List[Dict]] = None,
        requires_signature: bool = False
    ) -> Dict[str, Any]:
        """
        Execute complete work order workflow across ALL services

        Workflow Steps:
        1. Create Vikunja task with subtasks
        2. Create Homebox BOM if parts needed
        3. Schedule Cal.com appointment if contractor provided
        4. Create Immich photo album for documentation
        5. Store work order in Paperless-ngx
        6. Set up Nextcloud folder for files
        7. Record in Firefly III for financial tracking
        8. Send Novu multi-channel notifications
        9. Trigger n8n workflow for additional automation
        10. Update Grafana with annotation
        11. Publish MQTT event for IoT integration
        12. Create digital signature request if needed

        Returns:
            Dict with all integration IDs and status
        """
        results = {
            "work_order_id": work_order_id,
            "status": "in_progress",
            "integrations": {},
            "errors": []
        }

        logger.info(f"Starting complete workflow for work order {work_order_id}")

        # Step 1: Create Vikunja Task
        try:
            task_priority_map = {
                'low': TaskPriority.LOW,
                'normal': TaskPriority.MEDIUM,
                'high': TaskPriority.HIGH,
                'urgent': TaskPriority.URGENT
            }
            priority = task_priority_map.get(urgency, TaskPriority.MEDIUM)

            # TODO: Get project_id from property configuration
            project_id = 1

            vikunja_task = await self.vikunja.create_work_order_task(
                project_id=project_id,
                work_order_id=work_order_id,
                work_order_title=work_order_title,
                work_order_description=work_order_description,
                priority=priority
            )

            if vikunja_task:
                results["integrations"]["vikunja"] = {
                    "status": "success",
                    "task_id": vikunja_task.id
                }
                logger.info(f"Created Vikunja task {vikunja_task.id}")
        except Exception as e:
            logger.error(f"Failed to create Vikunja task: {e}")
            results["errors"].append(f"Vikunja: {str(e)}")

        # Step 2: Create Homebox BOM
        if requires_parts and bom_items:
            try:
                bom = await self.homebox.create_bom_for_work_order(
                    work_order_id=work_order_id,
                    work_order_description=work_order_description,
                    items=bom_items
                )

                if bom:
                    results["integrations"]["homebox"] = {
                        "status": "success",
                        "bom_id": bom.work_order_id,
                        "total_cost": float(bom.total_estimated_cost)
                    }
                    logger.info(f"Created BOM for work order: ${bom.total_estimated_cost}")
            except Exception as e:
                logger.error(f"Failed to create Homebox BOM: {e}")
                results["errors"].append(f"Homebox: {str(e)}")

        # Step 3: Schedule Cal.com Appointment
        if contractor_email and contractor_name:
            try:
                property_address = f"{property_name}, Unit {unit_number}"

                booking = await self.calcom.schedule_work_order(
                    work_order_id=work_order_id,
                    work_order_title=work_order_title,
                    work_order_description=work_order_description,
                    contractor_email=contractor_email,
                    contractor_name=contractor_name,
                    property_address=property_address
                )

                if booking:
                    results["integrations"]["calcom"] = {
                        "status": "success",
                        "booking_id": booking.id,
                        "appointment_time": booking.start_time.isoformat()
                    }
                    logger.info(f"Scheduled appointment {booking.id} at {booking.start_time}")
            except Exception as e:
                logger.error(f"Failed to schedule Cal.com appointment: {e}")
                results["errors"].append(f"Cal.com: {str(e)}")

        # Step 4: Create Immich Photo Album
        try:
            album_name = f"WO-{work_order_id}: {work_order_title}"
            album_description = f"Photos for work order {work_order_id} at {property_name} Unit {unit_number}"

            album = await self.immich.create_album(
                name=album_name,
                description=album_description
            )

            if album:
                results["integrations"]["immich"] = {
                    "status": "success",
                    "album_id": album.id
                }
                logger.info(f"Created Immich album {album.id}")
        except Exception as e:
            logger.error(f"Failed to create Immich album: {e}")
            results["errors"].append(f"Immich: {str(e)}")

        # Step 5: Store in Paperless-ngx
        try:
            # Create work order document
            wo_doc_content = f"""
Work Order #{work_order_id}

Property: {property_name}
Unit: {unit_number}
Tenant: {tenant_name}

Title: {work_order_title}

Description:
{work_order_description}

Estimated Cost: ${estimated_cost or 0}
Urgency: {urgency.upper()}

Created: {datetime.now().isoformat()}
"""

            doc_id = await self.paperless.upload_work_order_document(
                work_order_id=work_order_id,
                property_name=property_name,
                unit_number=unit_number,
                document_content=wo_doc_content.encode('utf-8'),
                document_name=f"Work_Order_{work_order_id}.txt"
            )

            if doc_id:
                results["integrations"]["paperless"] = {
                    "status": "success",
                    "document_id": doc_id
                }
                logger.info(f"Stored document in Paperless-ngx: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to store in Paperless-ngx: {e}")
            results["errors"].append(f"Paperless-ngx: {str(e)}")

        # Step 6: Set up Nextcloud Folder
        try:
            folder_path = await self.nextcloud.setup_property_structure(
                property_name=property_name,
                unit_number=unit_number
            )

            results["integrations"]["nextcloud"] = {
                "status": "success",
                "folder_path": folder_path
            }
            logger.info(f"Created Nextcloud folder: {folder_path}")
        except Exception as e:
            logger.error(f"Failed to set up Nextcloud folder: {e}")
            results["errors"].append(f"Nextcloud: {str(e)}")

        # Step 7: Record in Firefly III
        try:
            if estimated_cost and estimated_cost > 0:
                transaction = await self.fireflyiii.record_work_order_expense(
                    work_order_id=work_order_id,
                    description=work_order_title,
                    amount=estimated_cost,
                    property_name=property_name,
                    unit_number=unit_number,
                    category="Maintenance"
                )

                if transaction:
                    results["integrations"]["fireflyiii"] = {
                        "status": "success",
                        "transaction_id": transaction.id
                    }
                    logger.info(f"Recorded expense in Firefly III: ${estimated_cost}")
        except Exception as e:
            logger.error(f"Failed to record in Firefly III: {e}")
            results["errors"].append(f"Firefly III: {str(e)}")

        # Step 8: Send Novu Notifications
        try:
            novu_tx = await self.novu.send_work_order_update(
                tenant_id=f"tenant-{tenant_email}",
                work_order_id=work_order_id,
                work_order_title=work_order_title,
                status="created",
                message=f"Your work order has been approved and scheduled.",
                metadata={
                    "property": property_name,
                    "unit": unit_number,
                    "urgency": urgency
                }
            )

            if novu_tx:
                results["integrations"]["novu"] = {
                    "status": "success",
                    "transaction_id": novu_tx
                }
                logger.info(f"Sent Novu notification: {novu_tx}")
        except Exception as e:
            logger.error(f"Failed to send Novu notification: {e}")
            results["errors"].append(f"Novu: {str(e)}")

        # Step 9: Trigger n8n Workflow
        try:
            workflow_result = await self.n8n.trigger_maintenance_scheduling(
                work_order_id=work_order_id,
                property_name=property_name,
                contractor_email=contractor_email or "",
                urgency=urgency
            )

            if workflow_result:
                results["integrations"]["n8n"] = {
                    "status": "success",
                    "workflow_result": workflow_result
                }
                logger.info(f"Triggered n8n workflow")
        except Exception as e:
            logger.error(f"Failed to trigger n8n workflow: {e}")
            results["errors"].append(f"n8n: {str(e)}")

        # Step 10: Update Grafana
        try:
            annotation = await self.grafana.create_work_order_annotation(
                work_order_id=work_order_id,
                work_order_title=work_order_title,
                property_name=property_name,
                tags=["work-order", urgency]
            )

            if annotation:
                results["integrations"]["grafana"] = {
                    "status": "success",
                    "annotation_id": annotation
                }
                logger.info(f"Created Grafana annotation")
        except Exception as e:
            logger.error(f"Failed to create Grafana annotation: {e}")
            results["errors"].append(f"Grafana: {str(e)}")

        # Step 11: Publish MQTT Event
        try:
            event_published = await self.mqtt.publish_event(
                event_type="work_order_created",
                property_id=property_name,
                unit_id=unit_number,
                data={
                    "work_order_id": work_order_id,
                    "title": work_order_title,
                    "urgency": urgency,
                    "contractor": contractor_name
                }
            )

            if event_published:
                results["integrations"]["mqtt"] = {
                    "status": "success"
                }
                logger.info(f"Published MQTT event")
        except Exception as e:
            logger.error(f"Failed to publish MQTT event: {e}")
            results["errors"].append(f"MQTT: {str(e)}")

        # Step 12: Create Digital Signature Request
        if requires_signature:
            try:
                # TODO: Generate work order completion PDF
                pdf_bytes = b"PDF content placeholder"

                doc_id = await self.documenso.create_work_order_completion(
                    work_order_id=work_order_id,
                    work_order_title=work_order_title,
                    pdf_content=pdf_bytes,
                    tenant_email=tenant_email,
                    tenant_name=tenant_name,
                    contractor_email=contractor_email or "",
                    contractor_name=contractor_name or ""
                )

                if doc_id:
                    results["integrations"]["documenso"] = {
                        "status": "success",
                        "document_id": doc_id
                    }
                    logger.info(f"Created Documenso signature request: {doc_id}")
            except Exception as e:
                logger.error(f"Failed to create Documenso signature request: {e}")
                results["errors"].append(f"Documenso: {str(e)}")

        # Final status
        results["status"] = "completed" if not results["errors"] else "completed_with_errors"
        results["completed_at"] = datetime.now().isoformat()

        logger.info(
            f"Completed workflow for {work_order_id}: "
            f"{len(results['integrations'])} integrations, "
            f"{len(results['errors'])} errors"
        )

        return results

    # ========================================
    # Complete Workflow: Lease Signing
    # ========================================

    async def execute_lease_signing_workflow(
        self,
        lease_id: str,
        property_name: str,
        unit_number: str,
        tenant_name: str,
        tenant_email: str,
        monthly_rent: Decimal,
        lease_start_date: date,
        lease_end_date: date,
        lease_pdf_content: bytes
    ) -> Dict[str, Any]:
        """
        Execute complete lease signing workflow

        Steps:
        1. Upload lease to Paperless-ngx
        2. Create Documenso signature workflow
        3. Set up Invoice Ninja recurring billing
        4. Create Nextcloud folder for tenant
        5. Set up Firefly III budget tracking
        6. Send Novu welcome notification
        7. Create Grafana annotation for lease start

        Returns:
            Dict with all integration IDs
        """
        results = {
            "lease_id": lease_id,
            "status": "in_progress",
            "integrations": {},
            "errors": []
        }

        logger.info(f"Starting lease signing workflow for lease {lease_id}")

        # Step 1: Upload to Paperless-ngx
        try:
            doc_id = await self.paperless.upload_document(
                document_content=lease_pdf_content,
                title=f"Lease Agreement - {property_name} Unit {unit_number}",
                tags=["lease", "signed", property_name, unit_number]
            )

            if doc_id:
                results["integrations"]["paperless"] = {
                    "status": "success",
                    "document_id": doc_id
                }
                logger.info(f"Uploaded lease to Paperless-ngx: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to upload to Paperless-ngx: {e}")
            results["errors"].append(f"Paperless-ngx: {str(e)}")

        # Step 2: Create Documenso Signature Workflow
        try:
            doc_id = await self.documenso.create_lease_signing(
                lease_id=lease_id,
                lease_pdf=lease_pdf_content,
                tenant_email=tenant_email,
                tenant_name=tenant_name,
                landlord_email="landlord@property.com",  # TODO: From config
                landlord_name="Property Manager"
            )

            if doc_id:
                results["integrations"]["documenso"] = {
                    "status": "success",
                    "document_id": doc_id
                }
                logger.info(f"Created Documenso signature workflow: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to create Documenso workflow: {e}")
            results["errors"].append(f"Documenso: {str(e)}")

        # Step 3: Set up Invoice Ninja Recurring Billing
        try:
            # Create client
            client = await self.invoiceninja.create_client(
                name=tenant_name,
                email=tenant_email
            )

            if client:
                # Set up recurring rent invoice
                recurring = await self.invoiceninja.setup_monthly_rent_billing(
                    tenant_name=tenant_name,
                    property_name=property_name,
                    unit_number=unit_number,
                    monthly_rent=monthly_rent,
                    lease_start_date=lease_start_date,
                    lease_end_date=lease_end_date,
                    client_id=client.id
                )

                if recurring:
                    results["integrations"]["invoiceninja"] = {
                        "status": "success",
                        "client_id": client.id,
                        "recurring_invoice_id": recurring.id
                    }
                    logger.info(f"Set up recurring billing: ${monthly_rent}/month")
        except Exception as e:
            logger.error(f"Failed to set up Invoice Ninja billing: {e}")
            results["errors"].append(f"Invoice Ninja: {str(e)}")

        # Step 4: Create Nextcloud Tenant Folder
        try:
            folder_path = await self.nextcloud.setup_property_structure(
                property_name=property_name,
                unit_number=unit_number
            )

            # Share folder with tenant
            share = await self.nextcloud.share_file(
                path=folder_path,
                share_type="email",
                share_with=tenant_email,
                permissions="read"
            )

            results["integrations"]["nextcloud"] = {
                "status": "success",
                "folder_path": folder_path,
                "share_id": share.id if share else None
            }
            logger.info(f"Created and shared Nextcloud folder")
        except Exception as e:
            logger.error(f"Failed to set up Nextcloud: {e}")
            results["errors"].append(f"Nextcloud: {str(e)}")

        # Step 5: Set up Firefly III Budget Tracking
        try:
            # Record lease as recurring revenue
            transaction = await self.fireflyiii.record_rent_payment(
                tenant_name=tenant_name,
                property_name=property_name,
                unit_number=unit_number,
                amount=monthly_rent,
                payment_date=lease_start_date,
                destination_account_id="1"  # TODO: From config
            )

            if transaction:
                results["integrations"]["fireflyiii"] = {
                    "status": "success",
                    "transaction_id": transaction.id
                }
                logger.info(f"Set up Firefly III tracking")
        except Exception as e:
            logger.error(f"Failed to set up Firefly III: {e}")
            results["errors"].append(f"Firefly III: {str(e)}")

        # Step 6: Send Welcome Notification
        try:
            novu_tx = await self.novu.trigger(
                event_name="tenant-welcome",
                subscriber_id=f"tenant-{tenant_email}",
                payload={
                    "tenant_name": tenant_name,
                    "property_name": property_name,
                    "unit_number": unit_number,
                    "lease_start": lease_start_date.isoformat(),
                    "monthly_rent": float(monthly_rent)
                }
            )

            if novu_tx:
                results["integrations"]["novu"] = {
                    "status": "success",
                    "transaction_id": novu_tx
                }
                logger.info(f"Sent welcome notification")
        except Exception as e:
            logger.error(f"Failed to send Novu notification: {e}")
            results["errors"].append(f"Novu: {str(e)}")

        # Step 7: Create Grafana Annotation
        try:
            annotation = await self.grafana.create_annotation(
                text=f"Lease Started: {tenant_name} - {property_name} Unit {unit_number}",
                tags=["lease", "move-in", property_name]
            )

            if annotation:
                results["integrations"]["grafana"] = {
                    "status": "success",
                    "annotation_id": annotation
                }
                logger.info(f"Created Grafana annotation")
        except Exception as e:
            logger.error(f"Failed to create Grafana annotation: {e}")
            results["errors"].append(f"Grafana: {str(e)}")

        results["status"] = "completed" if not results["errors"] else "completed_with_errors"
        results["completed_at"] = datetime.now().isoformat()

        return results


# ========================================
# Singleton instance management
# ========================================

_orchestrator_instance: Optional[IntegrationOrchestrator] = None


def get_integration_orchestrator(db: AsyncSession) -> IntegrationOrchestrator:
    """Get or create integration orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None or _orchestrator_instance.db != db:
        _orchestrator_instance = IntegrationOrchestrator(db)
    return _orchestrator_instance
