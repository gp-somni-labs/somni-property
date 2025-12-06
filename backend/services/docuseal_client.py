"""
DocuSeal API Client
Digital document signing and workflow management
"""

import httpx
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from uuid import UUID

from core.config import settings

logger = logging.getLogger(__name__)


class DocuSealClient:
    """
    DocuSeal API client for document signing

    Integrates with DocuSeal for:
    - Lease signing
    - Move-in/Move-out forms
    - Work order completion signatures
    - General document signing workflows
    """

    def __init__(self):
        """Initialize DocuSeal client"""
        self.base_url = settings.DOCUSEAL_URL
        self.api_key = settings.DOCUSEAL_API_KEY

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                'X-Auth-Token': self.api_key,
                'Content-Type': 'application/json'
            } if self.api_key else {},
            timeout=30.0
        )

        logger.info(f"DocuSeal client initialized: {self.base_url}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def create_submission(
        self,
        template_id: int,
        signers: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
        send_email: bool = True,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new document submission from a template

        Args:
            template_id: DocuSeal template ID
            signers: List of signers with email and name
                Example: [{"email": "tenant@example.com", "name": "John Doe"}]
            metadata: Additional metadata to attach
            send_email: Whether to send email notification
            message: Custom message for signers

        Returns:
            Submission details including ID and signing URLs
        """
        try:
            payload = {
                "template_id": template_id,
                "send_email": send_email,
                "submitters": [
                    {
                        "email": signer["email"],
                        "name": signer.get("name", signer["email"])
                    }
                    for signer in signers
                ]
            }

            if message:
                payload["message"] = message

            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post("/api/submissions", json=payload)
            response.raise_for_status()

            submission = response.json()
            logger.info(f"Created DocuSeal submission: {submission.get('id')}")

            return submission

        except httpx.HTTPError as e:
            logger.error(f"Failed to create DocuSeal submission: {e}")
            return {}

    async def get_submission(self, submission_id: int) -> Optional[Dict[str, Any]]:
        """
        Get submission details

        Args:
            submission_id: DocuSeal submission ID

        Returns:
            Submission details or None
        """
        try:
            response = await self.client.get(f"/api/submissions/{submission_id}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get DocuSeal submission {submission_id}: {e}")
            return None

    async def list_submissions(
        self,
        template_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List submissions with optional filtering

        Args:
            template_id: Filter by template
            status: Filter by status (pending, completed, etc.)
            limit: Maximum number of results

        Returns:
            List of submissions
        """
        try:
            params = {"limit": limit}
            if template_id:
                params["template_id"] = template_id
            if status:
                params["status"] = status

            response = await self.client.get("/api/submissions", params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to list DocuSeal submissions: {e}")
            return []

    async def cancel_submission(self, submission_id: int) -> bool:
        """
        Cancel a pending submission

        Args:
            submission_id: DocuSeal submission ID

        Returns:
            True if successful
        """
        try:
            response = await self.client.delete(f"/api/submissions/{submission_id}")
            response.raise_for_status()
            logger.info(f"Cancelled DocuSeal submission: {submission_id}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to cancel DocuSeal submission {submission_id}: {e}")
            return False

    async def resend_email(self, submission_id: int) -> bool:
        """
        Resend signing email to pending signers

        Args:
            submission_id: DocuSeal submission ID

        Returns:
            True if successful
        """
        try:
            response = await self.client.post(
                f"/api/submissions/{submission_id}/resend"
            )
            response.raise_for_status()
            logger.info(f"Resent DocuSeal email for submission: {submission_id}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to resend email for submission {submission_id}: {e}")
            return False

    async def download_documents(self, submission_id: int) -> Optional[bytes]:
        """
        Download completed and signed documents

        Args:
            submission_id: DocuSeal submission ID

        Returns:
            PDF bytes or None
        """
        try:
            response = await self.client.get(
                f"/api/submissions/{submission_id}/download"
            )
            response.raise_for_status()
            logger.info(f"Downloaded documents for submission: {submission_id}")
            return response.content

        except httpx.HTTPError as e:
            logger.error(f"Failed to download documents for submission {submission_id}: {e}")
            return None

    async def create_lease_signing(
        self,
        lease_id: UUID,
        tenant_email: str,
        tenant_name: str,
        landlord_email: str,
        landlord_name: str,
        lease_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a lease signing workflow

        Args:
            lease_id: Lease UUID
            tenant_email: Tenant's email
            tenant_name: Tenant's name
            landlord_email: Landlord's email
            landlord_name: Landlord's name
            lease_data: Lease details (rent, dates, unit, etc.)

        Returns:
            Submission details with signing URLs
        """
        # TODO: Get lease template ID from settings
        # For now, assume template ID 1 is the lease template
        template_id = settings.DOCUSEAL_LEASE_TEMPLATE_ID or 1

        signers = [
            {"email": tenant_email, "name": tenant_name},
            {"email": landlord_email, "name": landlord_name}
        ]

        metadata = {
            "lease_id": str(lease_id),
            "type": "lease_agreement",
            **lease_data
        }

        message = (
            f"Please review and sign the lease agreement for {lease_data.get('unit_address', 'your unit')}. "
            f"Lease term: {lease_data.get('start_date')} to {lease_data.get('end_date')}"
        )

        return await self.create_submission(
            template_id=template_id,
            signers=signers,
            metadata=metadata,
            send_email=True,
            message=message
        )

    async def create_work_order_completion(
        self,
        work_order_id: UUID,
        tenant_email: str,
        tenant_name: str,
        work_order_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a work order completion signature request

        Args:
            work_order_id: Work order UUID
            tenant_email: Tenant's email
            tenant_name: Tenant's name
            work_order_details: Work order details

        Returns:
            Submission details
        """
        # TODO: Get work order completion template ID from settings
        template_id = settings.DOCUSEAL_WORK_ORDER_TEMPLATE_ID or 2

        signers = [{"email": tenant_email, "name": tenant_name}]

        metadata = {
            "work_order_id": str(work_order_id),
            "type": "work_order_completion",
            **work_order_details
        }

        message = (
            f"Please review and sign to confirm completion of work order: {work_order_details.get('title', '')}"
        )

        return await self.create_submission(
            template_id=template_id,
            signers=signers,
            metadata=metadata,
            send_email=True,
            message=message
        )

    async def webhook_handler(self, event_data: Dict[str, Any]) -> bool:
        """
        Handle DocuSeal webhooks

        Args:
            event_data: Webhook payload

        Returns:
            True if handled successfully
        """
        event_type = event_data.get("event_type")
        submission = event_data.get("data", {})
        submission_id = submission.get("id")

        logger.info(f"Received DocuSeal webhook: {event_type} for submission {submission_id}")

        # TODO: Handle different event types
        # - submission.completed: All signatures collected
        # - submission.viewed: Document viewed by signer
        # - submission.signed: Individual signature added

        return True


# Global DocuSeal client instance
docuseal_client = DocuSealClient()


async def get_docuseal_client() -> DocuSealClient:
    """Dependency to get DocuSeal client instance"""
    return docuseal_client
