"""
Paperless-ngx Integration Client for SomniProperty

Integrates with self-hosted Paperless-ngx (document management with OCR) for:
- Document scanning and OCR processing
- Intelligent document search and retrieval
- Tag-based organization
- Correspondent management (tenants, contractors, vendors)
- Document linking to work orders and leases
- Automated document archival
- Full-text search across all documents

Paperless Service: paperless.storage.svc.cluster.local
Documentation: https://docs.paperless-ngx.com
API Docs: https://docs.paperless-ngx.com/api/
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from io import BytesIO
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Common document types for property management"""
    LEASE = "lease"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    WORK_ORDER = "work_order"
    INSPECTION = "inspection"
    CORRESPONDENCE = "correspondence"
    CONTRACT = "contract"
    INSURANCE = "insurance"
    TAX_DOCUMENT = "tax_document"
    UTILITY_BILL = "utility_bill"


class PaperlessDocument(BaseModel):
    """Paperless-ngx document model"""
    id: Optional[int] = None
    title: str
    content: Optional[str] = None
    correspondent: Optional[int] = None
    document_type: Optional[int] = None
    tags: Optional[List[int]] = []
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    added: Optional[datetime] = None
    archive_serial_number: Optional[str] = None
    original_file_name: Optional[str] = None
    archived_file_name: Optional[str] = None


class PaperlessCorrespondent(BaseModel):
    """Paperless-ngx correspondent (person/organization)"""
    id: Optional[int] = None
    name: str
    match: Optional[str] = None
    matching_algorithm: int = 1  # 1=any, 2=all, 3=literal, 4=regex


class PaperlessTag(BaseModel):
    """Paperless-ngx tag"""
    id: Optional[int] = None
    name: str
    color: str = "#a6cee3"
    match: Optional[str] = None
    matching_algorithm: int = 1


class PaperlessClient:
    """Client for interacting with Paperless-ngx API"""

    def __init__(
        self,
        base_url: str = "http://paperless.storage.svc.cluster.local:8000",
        api_token: Optional[str] = None,
        timeout: int = 60
    ):
        """
        Initialize Paperless-ngx client

        Args:
            base_url: Paperless-ngx service URL
            api_token: Paperless-ngx API token (from Settings → API Tokens)
            timeout: Request timeout in seconds (60s for OCR processing)
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
            headers["Authorization"] = f"Token {self.api_token}"
        return headers

    # ========================================
    # Document Management
    # ========================================

    async def upload_document(
        self,
        file_data: bytes,
        filename: str,
        title: Optional[str] = None,
        correspondent_id: Optional[int] = None,
        document_type_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        created_date: Optional[datetime] = None,
        archive_serial_number: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[PaperlessDocument]:
        """
        Upload a document to Paperless-ngx for OCR and indexing

        Use for:
        - Lease agreements (link to lease via archive_serial_number)
        - Invoices and receipts
        - Work order documentation (before/after photos, completion forms)
        - Inspection reports
        - Tenant correspondence

        Args:
            file_data: Document bytes (PDF, image, etc.)
            filename: Original filename
            title: Document title (auto-generated if not provided)
            correspondent_id: Paperless correspondent ID
            document_type_id: Paperless document type ID
            tag_ids: List of tag IDs to apply
            created_date: Document creation date
            archive_serial_number: Custom ID for linking (e.g., work order ID)
            metadata: Additional metadata

        Returns:
            Created document or None on failure
        """
        try:
            # Prepare multipart form data
            files = {
                'document': (filename, BytesIO(file_data))
            }

            data = {}
            if title:
                data['title'] = title
            if correspondent_id:
                data['correspondent'] = correspondent_id
            if document_type_id:
                data['document_type'] = document_type_id
            if tag_ids:
                data['tags'] = ','.join(str(tag_id) for tag_id in tag_ids)
            if created_date:
                data['created'] = created_date.strftime('%Y-%m-%d')
            if archive_serial_number:
                data['archive_serial_number'] = archive_serial_number

            # Remove Content-Type header for multipart upload
            headers = {k: v for k, v in self._headers().items() if k != "Content-Type"}

            response = await self.client.post(
                f"{self.base_url}/api/documents/post_document/",
                headers=headers,
                files=files,
                data=data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Uploaded document to Paperless: {filename}")
                return PaperlessDocument(
                    id=result.get('id'),
                    title=result.get('title', title or filename),
                    archive_serial_number=archive_serial_number
                )
            else:
                logger.error(f"Failed to upload document: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error uploading document to Paperless: {e}")
            return None

    async def get_document(self, document_id: int) -> Optional[PaperlessDocument]:
        """
        Get document details from Paperless-ngx

        Args:
            document_id: Paperless document ID

        Returns:
            Document details or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/documents/{document_id}/",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return PaperlessDocument(
                    id=data.get('id'),
                    title=data.get('title'),
                    content=data.get('content'),
                    correspondent=data.get('correspondent'),
                    document_type=data.get('document_type'),
                    tags=data.get('tags', []),
                    archive_serial_number=data.get('archive_serial_number'),
                    original_file_name=data.get('original_file_name'),
                    archived_file_name=data.get('archived_file_name')
                )
            return None

        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None

    async def search_documents(
        self,
        query: Optional[str] = None,
        tag_ids: Optional[List[int]] = None,
        document_type_id: Optional[int] = None,
        correspondent_id: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        archive_serial_number: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
        ordering: str = "-created"
    ) -> Dict[str, Any]:
        """
        Search documents in Paperless-ngx

        Full-text search across all OCR'd documents with advanced filtering

        Args:
            query: Full-text search query (searches content, title, tags, etc.)
            tag_ids: Filter by tag IDs
            document_type_id: Filter by document type ID
            correspondent_id: Filter by correspondent ID
            created_after: Filter by creation date (after)
            created_before: Filter by creation date (before)
            archive_serial_number: Search by archive serial number (e.g., work order ID)
            page: Page number
            page_size: Results per page
            ordering: Sort field (prefix with - for descending)

        Returns:
            Search results with pagination info
        """
        try:
            params = {
                'page': page,
                'page_size': page_size,
                'ordering': ordering
            }

            if query:
                params['query'] = query
            if tag_ids:
                params['tags__id__in'] = ','.join(str(tag_id) for tag_id in tag_ids)
            if document_type_id:
                params['document_type__id'] = document_type_id
            if correspondent_id:
                params['correspondent__id'] = correspondent_id
            if created_after:
                params['created__date__gt'] = created_after.strftime('%Y-%m-%d')
            if created_before:
                params['created__date__lt'] = created_before.strftime('%Y-%m-%d')
            if archive_serial_number:
                params['archive_serial_number'] = archive_serial_number

            response = await self.client.get(
                f"{self.base_url}/api/documents/",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to search documents: {response.status_code} - {response.text}")
                return {"count": 0, "results": []}

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {"count": 0, "results": []}

    async def download_document(self, document_id: int) -> Optional[bytes]:
        """
        Download original document from Paperless-ngx

        Args:
            document_id: Paperless document ID

        Returns:
            Document bytes or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/documents/{document_id}/download/",
                headers=self._headers()
            )

            if response.status_code == 200:
                logger.info(f"Downloaded document from Paperless: {document_id}")
                return response.content
            return None

        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            return None

    async def get_document_text(self, document_id: int) -> Optional[str]:
        """
        Get OCR'd text content from a document

        Use for:
        - AI-powered document analysis
        - Extracting lease terms
        - Invoice data extraction
        - Searching within specific documents

        Args:
            document_id: Paperless document ID

        Returns:
            Extracted OCR text or None
        """
        try:
            doc = await self.get_document(document_id)
            if doc and doc.content:
                return doc.content
            return None

        except Exception as e:
            logger.error(f"Error getting document text: {e}")
            return None

    async def update_document(
        self,
        document_id: int,
        title: Optional[str] = None,
        correspondent_id: Optional[int] = None,
        document_type_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        archive_serial_number: Optional[str] = None
    ) -> Optional[PaperlessDocument]:
        """
        Update document metadata

        Args:
            document_id: Paperless document ID
            title: New title
            correspondent_id: New correspondent ID
            document_type_id: New document type ID
            tag_ids: New tag IDs (replaces existing)
            archive_serial_number: New archive serial number

        Returns:
            Updated document or None
        """
        try:
            updates = {}
            if title is not None:
                updates['title'] = title
            if correspondent_id is not None:
                updates['correspondent'] = correspondent_id
            if document_type_id is not None:
                updates['document_type'] = document_type_id
            if tag_ids is not None:
                updates['tags'] = tag_ids
            if archive_serial_number is not None:
                updates['archive_serial_number'] = archive_serial_number

            response = await self.client.patch(
                f"{self.base_url}/api/documents/{document_id}/",
                headers=self._headers(),
                json=updates
            )

            if response.status_code == 200:
                data = response.json()
                return PaperlessDocument(
                    id=data.get('id'),
                    title=data.get('title'),
                    correspondent=data.get('correspondent'),
                    document_type=data.get('document_type'),
                    tags=data.get('tags', []),
                    archive_serial_number=data.get('archive_serial_number')
                )
            else:
                logger.error(f"Failed to update document: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return None

    async def delete_document(self, document_id: int) -> bool:
        """
        Delete a document from Paperless-ngx

        Args:
            document_id: Paperless document ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/documents/{document_id}/",
                headers=self._headers()
            )

            if response.status_code == 204:
                logger.info(f"Deleted Paperless document: {document_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False

    # ========================================
    # Tag Management
    # ========================================

    async def create_tag(
        self,
        name: str,
        color: str = "#a6cee3",
        match: Optional[str] = None,
        matching_algorithm: int = 1
    ) -> Optional[PaperlessTag]:
        """
        Create a tag in Paperless-ngx

        Use for categorizing documents:
        - Property-specific: "sunset-apartments", "oak-tower"
        - Unit-specific: "unit-204", "unit-1a"
        - Type-specific: "lease", "invoice", "work-order"
        - Status-specific: "pending", "approved", "archived"

        Args:
            name: Tag name
            color: Hex color code (e.g., "#e74c3c")
            match: Auto-matching pattern (optional)
            matching_algorithm: 1=any, 2=all, 3=literal, 4=regex

        Returns:
            Created tag or None on failure
        """
        try:
            payload = {
                "name": name,
                "color": color,
                "matching_algorithm": matching_algorithm
            }
            if match:
                payload["match"] = match

            response = await self.client.post(
                f"{self.base_url}/api/tags/",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return PaperlessTag(
                    id=data.get('id'),
                    name=data.get('name'),
                    color=data.get('color'),
                    match=data.get('match'),
                    matching_algorithm=data.get('matching_algorithm', 1)
                )
            else:
                logger.error(f"Failed to create tag: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating tag: {e}")
            return None

    async def get_tags(self) -> List[PaperlessTag]:
        """Get all tags from Paperless-ngx"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/tags/",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    PaperlessTag(
                        id=tag.get('id'),
                        name=tag.get('name'),
                        color=tag.get('color'),
                        match=tag.get('match'),
                        matching_algorithm=tag.get('matching_algorithm', 1)
                    )
                    for tag in data.get('results', [])
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            return []

    async def tag_document(self, document_id: int, tag_ids: List[int]) -> bool:
        """
        Add tags to a document (adds to existing tags)

        Args:
            document_id: Paperless document ID
            tag_ids: List of tag IDs to add

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current document to preserve existing tags
            doc = await self.get_document(document_id)
            if not doc:
                return False

            # Combine existing and new tags
            all_tag_ids = list(set((doc.tags or []) + tag_ids))

            # Update document with combined tags
            result = await self.update_document(document_id, tag_ids=all_tag_ids)
            return result is not None

        except Exception as e:
            logger.error(f"Error tagging document: {e}")
            return False

    # ========================================
    # Correspondent Management
    # ========================================

    async def create_correspondent(
        self,
        name: str,
        match: Optional[str] = None,
        matching_algorithm: int = 1
    ) -> Optional[PaperlessCorrespondent]:
        """
        Create a correspondent (person/organization) in Paperless-ngx

        Use for:
        - Tenants (auto-tag all documents from tenant)
        - Contractors (organize invoices and work orders)
        - Vendors (utility companies, service providers)
        - Government agencies (tax authorities, inspectors)

        Args:
            name: Correspondent name
            match: Auto-matching pattern (optional)
            matching_algorithm: 1=any, 2=all, 3=literal, 4=regex

        Returns:
            Created correspondent or None on failure
        """
        try:
            payload = {
                "name": name,
                "matching_algorithm": matching_algorithm
            }
            if match:
                payload["match"] = match

            response = await self.client.post(
                f"{self.base_url}/api/correspondents/",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return PaperlessCorrespondent(
                    id=data.get('id'),
                    name=data.get('name'),
                    match=data.get('match'),
                    matching_algorithm=data.get('matching_algorithm', 1)
                )
            else:
                logger.error(f"Failed to create correspondent: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating correspondent: {e}")
            return None

    async def get_correspondents(self) -> List[PaperlessCorrespondent]:
        """Get all correspondents from Paperless-ngx"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/correspondents/",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    PaperlessCorrespondent(
                        id=corresp.get('id'),
                        name=corresp.get('name'),
                        match=corresp.get('match'),
                        matching_algorithm=corresp.get('matching_algorithm', 1)
                    )
                    for corresp in data.get('results', [])
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting correspondents: {e}")
            return []

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def upload_work_order_document(
        self,
        work_order_id: str,
        file_data: bytes,
        filename: str,
        document_type: str = "work_order",
        description: Optional[str] = None
    ) -> Optional[PaperlessDocument]:
        """
        Upload a work order related document

        Automatically links document to work order via archive_serial_number

        Args:
            work_order_id: SomniProperty work order ID
            file_data: Document bytes
            filename: Original filename
            document_type: Document type (work_order, invoice, receipt, etc.)
            description: Document description

        Returns:
            Created document or None on failure
        """
        title = f"WO-{work_order_id}: {filename}"
        if description:
            title = f"WO-{work_order_id}: {description}"

        return await self.upload_document(
            file_data=file_data,
            filename=filename,
            title=title,
            archive_serial_number=f"WO-{work_order_id}",
            metadata={"work_order_id": work_order_id, "type": document_type}
        )

    async def get_work_order_documents(self, work_order_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents linked to a work order

        Args:
            work_order_id: SomniProperty work order ID

        Returns:
            List of documents
        """
        result = await self.search_documents(
            archive_serial_number=f"WO-{work_order_id}"
        )
        return result.get('results', [])


# ========================================
# Singleton instance management
# ========================================

_paperless_client: Optional[PaperlessClient] = None


def get_paperless_client(
    base_url: str = "http://paperless.storage.svc.cluster.local:8000",
    api_token: Optional[str] = None
) -> PaperlessClient:
    """Get singleton Paperless-ngx client instance"""
    global _paperless_client
    if _paperless_client is None:
        _paperless_client = PaperlessClient(base_url=base_url, api_token=api_token)
    return _paperless_client


async def close_paperless_client():
    """Close singleton Paperless-ngx client"""
    global _paperless_client
    if _paperless_client:
        await _paperless_client.close()
        _paperless_client = None
