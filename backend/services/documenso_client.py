"""
Documenso Integration Client for SomniProperty

Integrates with self-hosted Documenso (open-source document signing) for:
- Digital lease signing
- Work order completion signatures
- Move-in/Move-out inspection forms
- Contractor agreements
- Tenant consent forms
- Document templates with field mapping
- Multi-party signing workflows
- Audit trail and compliance tracking

Documenso Service: documenso.utilities.svc.cluster.local
Documentation: https://docs.documenso.com
API Docs: https://docs.documenso.com/developers/api
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from io import BytesIO
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DocumentStatus(Enum):
    """Documenso document status"""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    SIGNED = "SIGNED"


class RecipientRole(Enum):
    """Document recipient roles"""
    SIGNER = "SIGNER"
    VIEWER = "VIEWER"
    APPROVER = "APPROVER"
    CC = "CC"


class FieldType(Enum):
    """Document field types"""
    SIGNATURE = "SIGNATURE"
    EMAIL = "EMAIL"
    NAME = "NAME"
    DATE = "DATE"
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    CHECKBOX = "CHECKBOX"


class DocumensoDocument(BaseModel):
    """Documenso document model"""
    id: Optional[str] = None
    title: str
    status: str = DocumentStatus.DRAFT.value
    document_data_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DocumentRecipient(BaseModel):
    """Document recipient/signer"""
    id: Optional[str] = None
    name: str
    email: str
    role: str = RecipientRole.SIGNER.value
    signing_order: int = 1
    signed_at: Optional[datetime] = None


class DocumentField(BaseModel):
    """Document form field"""
    id: Optional[str] = None
    recipient_id: str
    type: str
    page: int
    position_x: float
    position_y: float
    width: float
    height: float
    required: bool = True
    inserted: Optional[bool] = False


class DocumensoClient:
    """Client for interacting with Documenso API"""

    def __init__(
        self,
        base_url: str = "http://documenso.utilities.svc.cluster.local:3000",
        api_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Documenso client

        Args:
            base_url: Documenso service URL
            api_token: Documenso API token (from Settings → API Tokens)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    # ========================================
    # Document Management
    # ========================================

    async def create_document(
        self,
        file_data: bytes,
        filename: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[DocumensoDocument]:
        """
        Upload a document to Documenso

        Use for:
        - Lease agreements
        - Work order completion forms
        - Move-in/move-out checklists
        - Contractor service agreements
        - Tenant consent forms

        Args:
            file_data: PDF document bytes
            filename: Original filename
            title: Document title
            metadata: Additional metadata (e.g., lease_id, work_order_id)

        Returns:
            Created document or None on failure
        """
        try:
            # Upload document file
            files = {
                'file': (filename, BytesIO(file_data), 'application/pdf')
            }

            # Prepare form data
            data = {
                'title': title
            }

            # Remove Content-Type for multipart upload
            headers = {k: v for k, v in self._headers().items() if k != "Content-Type"}

            response = await self.client.post(
                f"{self.base_url}/api/v1/documents",
                headers=headers,
                files=files,
                data=data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Created Documenso document: {title}")
                return DocumensoDocument(
                    id=result.get('id'),
                    title=result.get('title'),
                    status=result.get('status', DocumentStatus.DRAFT.value),
                    document_data_id=result.get('documentDataId'),
                    created_at=datetime.fromisoformat(result['createdAt']) if result.get('createdAt') else None
                )
            else:
                logger.error(f"Failed to create document: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating Documenso document: {e}")
            return None

    async def get_document(self, document_id: str) -> Optional[DocumensoDocument]:
        """
        Get document details

        Args:
            document_id: Documenso document ID

        Returns:
            Document details or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/documents/{document_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return DocumensoDocument(
                    id=data.get('id'),
                    title=data.get('title'),
                    status=data.get('status'),
                    document_data_id=data.get('documentDataId'),
                    created_at=datetime.fromisoformat(data['createdAt']) if data.get('createdAt') else None,
                    completed_at=datetime.fromisoformat(data['completedAt']) if data.get('completedAt') else None
                )
            return None

        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None

    async def list_documents(
        self,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        List documents with filtering

        Args:
            status: Filter by status (DRAFT, PENDING, COMPLETED)
            page: Page number
            per_page: Results per page

        Returns:
            Documents list with pagination
        """
        try:
            params = {
                'page': page,
                'perPage': per_page
            }
            if status:
                params['status'] = status

            response = await self.client.get(
                f"{self.base_url}/api/v1/documents",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to list documents: {response.status_code} - {response.text}")
                return {"documents": [], "totalPages": 0}

        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return {"documents": [], "totalPages": 0}

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document

        Args:
            document_id: Documenso document ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/documents/{document_id}",
                headers=self._headers()
            )

            if response.status_code in [200, 204]:
                logger.info(f"Deleted Documenso document: {document_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False

    # ========================================
    # Recipient Management
    # ========================================

    async def add_signer(
        self,
        document_id: str,
        name: str,
        email: str,
        role: str = RecipientRole.SIGNER.value,
        signing_order: int = 1,
        message: Optional[str] = None
    ) -> Optional[DocumentRecipient]:
        """
        Add a signer to a document

        Use for:
        - Tenant signing lease
        - Contractor signing work order
        - Multiple parties signing agreement
        - Property manager approving document

        Args:
            document_id: Documenso document ID
            name: Signer name
            email: Signer email
            role: Recipient role (SIGNER, VIEWER, APPROVER, CC)
            signing_order: Order in signing workflow (1-based)
            message: Custom message for signer

        Returns:
            Created recipient or None on failure
        """
        try:
            payload = {
                "name": name,
                "email": email,
                "role": role,
                "signingOrder": signing_order
            }

            if message:
                payload["message"] = message

            response = await self.client.post(
                f"{self.base_url}/api/v1/documents/{document_id}/recipients",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Added signer to document {document_id}: {name}")
                return DocumentRecipient(
                    id=data.get('id'),
                    name=name,
                    email=email,
                    role=role,
                    signing_order=signing_order
                )
            else:
                logger.error(f"Failed to add signer: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error adding signer: {e}")
            return None

    async def get_recipients(self, document_id: str) -> List[DocumentRecipient]:
        """
        Get all recipients for a document

        Args:
            document_id: Documenso document ID

        Returns:
            List of recipients
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/documents/{document_id}/recipients",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    DocumentRecipient(
                        id=recipient.get('id'),
                        name=recipient.get('name'),
                        email=recipient.get('email'),
                        role=recipient.get('role'),
                        signing_order=recipient.get('signingOrder', 1),
                        signed_at=datetime.fromisoformat(recipient['signedAt']) if recipient.get('signedAt') else None
                    )
                    for recipient in data.get('recipients', [])
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting recipients: {e}")
            return []

    # ========================================
    # Field Management
    # ========================================

    async def add_field(
        self,
        document_id: str,
        recipient_id: str,
        field_type: str,
        page: int,
        position_x: float,
        position_y: float,
        width: float = 200.0,
        height: float = 50.0,
        required: bool = True,
        placeholder: Optional[str] = None
    ) -> Optional[DocumentField]:
        """
        Add a form field to a document

        Use for:
        - Signature fields
        - Date fields (lease start/end)
        - Text fields (initials, names)
        - Checkboxes (agreement terms)

        Args:
            document_id: Documenso document ID
            recipient_id: Recipient ID (who fills this field)
            field_type: Field type (SIGNATURE, DATE, TEXT, etc.)
            page: PDF page number (1-indexed)
            position_x: X coordinate on page
            position_y: Y coordinate on page
            width: Field width in pixels
            height: Field height in pixels
            required: Whether field is required
            placeholder: Placeholder text

        Returns:
            Created field or None on failure
        """
        try:
            payload = {
                "recipientId": recipient_id,
                "type": field_type,
                "pageNumber": page,
                "positionX": position_x,
                "positionY": position_y,
                "width": width,
                "height": height,
                "required": required
            }

            if placeholder:
                payload["placeholder"] = placeholder

            response = await self.client.post(
                f"{self.base_url}/api/v1/documents/{document_id}/fields",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"Added field to document {document_id}: {field_type}")
                return DocumentField(
                    id=data.get('id'),
                    recipient_id=recipient_id,
                    type=field_type,
                    page=page,
                    position_x=position_x,
                    position_y=position_y,
                    width=width,
                    height=height,
                    required=required
                )
            else:
                logger.error(f"Failed to add field: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error adding field: {e}")
            return None

    async def get_fields(self, document_id: str) -> List[DocumentField]:
        """
        Get all fields for a document

        Args:
            document_id: Documenso document ID

        Returns:
            List of fields
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/documents/{document_id}/fields",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    DocumentField(
                        id=field.get('id'),
                        recipient_id=field.get('recipientId'),
                        type=field.get('type'),
                        page=field.get('pageNumber', 1),
                        position_x=field.get('positionX', 0),
                        position_y=field.get('positionY', 0),
                        width=field.get('width', 200),
                        height=field.get('height', 50),
                        required=field.get('required', True),
                        inserted=field.get('inserted', False)
                    )
                    for field in data.get('fields', [])
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting fields: {e}")
            return []

    # ========================================
    # Document Workflow
    # ========================================

    async def send_document(
        self,
        document_id: str,
        subject: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """
        Send document for signing

        Triggers email notifications to all recipients based on signing order

        Args:
            document_id: Documenso document ID
            subject: Email subject (optional)
            message: Email message (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {}
            if subject:
                payload["subject"] = subject
            if message:
                payload["message"] = message

            response = await self.client.post(
                f"{self.base_url}/api/v1/documents/{document_id}/send",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 204]:
                logger.info(f"Sent document for signing: {document_id}")
                return True
            else:
                logger.error(f"Failed to send document: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return False

    async def get_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed signing status of a document

        Returns:
        - Document status
        - Recipient signing status
        - Completed fields
        - Signing timeline

        Args:
            document_id: Documenso document ID

        Returns:
            Status details or None on failure
        """
        try:
            doc = await self.get_document(document_id)
            if not doc:
                return None

            recipients = await self.get_recipients(document_id)
            fields = await self.get_fields(document_id)

            return {
                "document_id": document_id,
                "title": doc.title,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
                "recipients": [
                    {
                        "name": r.name,
                        "email": r.email,
                        "role": r.role,
                        "signed": r.signed_at is not None,
                        "signed_at": r.signed_at.isoformat() if r.signed_at else None
                    }
                    for r in recipients
                ],
                "fields_completed": sum(1 for f in fields if f.inserted),
                "fields_total": len(fields)
            }

        except Exception as e:
            logger.error(f"Error getting document status: {e}")
            return None

    async def download_document(self, document_id: str) -> Optional[bytes]:
        """
        Download completed and signed document

        Args:
            document_id: Documenso document ID

        Returns:
            PDF bytes or None on failure
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/documents/{document_id}/download",
                headers=self._headers()
            )

            if response.status_code == 200:
                logger.info(f"Downloaded signed document: {document_id}")
                return response.content
            return None

        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            return None

    async def download_certificate(self, document_id: str) -> Optional[bytes]:
        """
        Download certificate of completion (audit trail)

        Args:
            document_id: Documenso document ID

        Returns:
            Certificate PDF bytes or None on failure
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/documents/{document_id}/certificate",
                headers=self._headers()
            )

            if response.status_code == 200:
                logger.info(f"Downloaded certificate for document: {document_id}")
                return response.content
            return None

        except Exception as e:
            logger.error(f"Error downloading certificate: {e}")
            return None

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def create_lease_signing(
        self,
        lease_pdf: bytes,
        tenant_name: str,
        tenant_email: str,
        landlord_name: str,
        landlord_email: str,
        lease_id: str,
        unit_address: str
    ) -> Optional[str]:
        """
        Create a complete lease signing workflow

        Args:
            lease_pdf: Lease agreement PDF bytes
            tenant_name: Tenant name
            tenant_email: Tenant email
            landlord_name: Landlord/manager name
            landlord_email: Landlord/manager email
            lease_id: Lease ID for tracking
            unit_address: Unit address

        Returns:
            Document ID or None on failure
        """
        try:
            # 1. Upload lease document
            doc = await self.create_document(
                file_data=lease_pdf,
                filename=f"lease_{lease_id}.pdf",
                title=f"Lease Agreement - {unit_address}",
                metadata={"lease_id": lease_id, "unit_address": unit_address}
            )

            if not doc or not doc.id:
                return None

            # 2. Add tenant as first signer
            tenant_recipient = await self.add_signer(
                document_id=doc.id,
                name=tenant_name,
                email=tenant_email,
                role=RecipientRole.SIGNER.value,
                signing_order=1,
                message=f"Please review and sign the lease agreement for {unit_address}"
            )

            if not tenant_recipient or not tenant_recipient.id:
                await self.delete_document(doc.id)
                return None

            # 3. Add landlord as second signer
            landlord_recipient = await self.add_signer(
                document_id=doc.id,
                name=landlord_name,
                email=landlord_email,
                role=RecipientRole.SIGNER.value,
                signing_order=2,
                message="Please countersign the lease agreement"
            )

            if not landlord_recipient or not landlord_recipient.id:
                await self.delete_document(doc.id)
                return None

            # 4. Add signature fields (assuming standard positions)
            # Tenant signature (bottom of last page)
            await self.add_field(
                document_id=doc.id,
                recipient_id=tenant_recipient.id,
                field_type=FieldType.SIGNATURE.value,
                page=1,  # Adjust based on your lease template
                position_x=100,
                position_y=650,
                width=200,
                height=50
            )

            # Landlord signature
            await self.add_field(
                document_id=doc.id,
                recipient_id=landlord_recipient.id,
                field_type=FieldType.SIGNATURE.value,
                page=1,
                position_x=350,
                position_y=650,
                width=200,
                height=50
            )

            # 5. Send for signing
            success = await self.send_document(
                document_id=doc.id,
                subject=f"Lease Agreement for {unit_address}",
                message=f"Please review and sign the attached lease agreement for {unit_address}. "
                        f"Lease ID: {lease_id}"
            )

            if success:
                logger.info(f"Created lease signing workflow: {lease_id}")
                return doc.id
            else:
                await self.delete_document(doc.id)
                return None

        except Exception as e:
            logger.error(f"Error creating lease signing workflow: {e}")
            return None

    async def create_work_order_completion(
        self,
        completion_form_pdf: bytes,
        tenant_name: str,
        tenant_email: str,
        work_order_id: str,
        work_order_title: str
    ) -> Optional[str]:
        """
        Create a work order completion signature workflow

        Args:
            completion_form_pdf: Work order completion form PDF
            tenant_name: Tenant name
            tenant_email: Tenant email
            work_order_id: Work order ID
            work_order_title: Work order title

        Returns:
            Document ID or None on failure
        """
        try:
            # 1. Upload completion form
            doc = await self.create_document(
                file_data=completion_form_pdf,
                filename=f"work_order_{work_order_id}_completion.pdf",
                title=f"Work Order Completion - {work_order_title}",
                metadata={"work_order_id": work_order_id}
            )

            if not doc or not doc.id:
                return None

            # 2. Add tenant as signer
            tenant_recipient = await self.add_signer(
                document_id=doc.id,
                name=tenant_name,
                email=tenant_email,
                role=RecipientRole.SIGNER.value,
                signing_order=1,
                message=f"Please confirm completion of work order: {work_order_title}"
            )

            if not tenant_recipient or not tenant_recipient.id:
                await self.delete_document(doc.id)
                return None

            # 3. Add signature field
            await self.add_field(
                document_id=doc.id,
                recipient_id=tenant_recipient.id,
                field_type=FieldType.SIGNATURE.value,
                page=1,
                position_x=100,
                position_y=650,
                width=200,
                height=50
            )

            # 4. Add date field
            await self.add_field(
                document_id=doc.id,
                recipient_id=tenant_recipient.id,
                field_type=FieldType.DATE.value,
                page=1,
                position_x=350,
                position_y=650,
                width=150,
                height=30
            )

            # 5. Send for signing
            success = await self.send_document(
                document_id=doc.id,
                subject=f"Work Order Completion - {work_order_title}",
                message=f"Please review and sign to confirm completion of work order {work_order_id}"
            )

            if success:
                logger.info(f"Created work order completion workflow: {work_order_id}")
                return doc.id
            else:
                await self.delete_document(doc.id)
                return None

        except Exception as e:
            logger.error(f"Error creating work order completion workflow: {e}")
            return None


# ========================================
# Singleton instance management
# ========================================

_documenso_client: Optional[DocumensoClient] = None


def get_documenso_client(
    base_url: str = "http://documenso.utilities.svc.cluster.local:3000",
    api_token: Optional[str] = None
) -> DocumensoClient:
    """Get singleton Documenso client instance"""
    global _documenso_client
    if _documenso_client is None:
        _documenso_client = DocumensoClient(base_url=base_url, api_token=api_token)
    return _documenso_client


async def close_documenso_client():
    """Close singleton Documenso client"""
    global _documenso_client
    if _documenso_client:
        await _documenso_client.close()
        _documenso_client = None
