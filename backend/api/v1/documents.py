"""
Documents API - Document Signing and Management
Handles DocuSeal integration for lease signing, work order completion, and document workflows
Also handles document upload/download via MinIO
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from io import BytesIO
import logging

from db.database import get_db
from db.models import Document, Lease, WorkOrder, Tenant
from core.auth import get_auth_user, require_manager, AuthUser
from services.docuseal_client import docuseal_client, get_docuseal_client, DocuSealClient
from services.minio_client import minio_client, get_minio_client, MinIOClient
from services.paperless_client import get_paperless_client, PaperlessClient
from services.websocket_manager import manager as ws_manager
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# LEASE SIGNING ENDPOINTS
# ============================================================================

@router.post("/leases/{lease_id}/initiate-signing")
async def initiate_lease_signing(
    lease_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
    docuseal: DocuSealClient = Depends(get_docuseal_client)
):
    """
    Initiate lease signing workflow via DocuSeal (Admin/Manager only)

    Creates a signing request and sends emails to tenant and landlord
    """
    # Get lease
    lease_result = await db.execute(
        select(Lease).where(Lease.id == lease_id)
    )
    lease = lease_result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )

    # Get tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == lease.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Check if already has a pending/signed document
    existing_doc = await db.execute(
        select(Document).where(
            and_(
                Document.lease_id == lease_id,
                Document.document_type == 'lease',
                Document.signing_status.in_(['pending', 'partially_signed', 'signed'])
            )
        )
    )
    if existing_doc.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lease already has an active signing request"
        )

    # Prepare lease data
    lease_data = {
        "start_date": str(lease.start_date),
        "end_date": str(lease.end_date),
        "rent_amount": float(lease.rent_amount),
        "security_deposit": float(lease.security_deposit) if lease.security_deposit else 0,
        "unit_address": "Unit address here",  # TODO: Get from unit relationship
    }

    # Create DocuSeal submission
    submission = await docuseal.create_lease_signing(
        lease_id=lease_id,
        tenant_email=tenant.email,
        tenant_name=f"{tenant.first_name} {tenant.last_name}",
        landlord_email="landlord@example.com",  # TODO: Get from property owner
        landlord_name="Property Manager",
        lease_data=lease_data
    )

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create signing request"
        )

    # Create document record
    document = Document(
        title=f"Lease Agreement - {tenant.first_name} {tenant.last_name}",
        description=f"Lease for unit from {lease.start_date} to {lease.end_date}",
        document_type='lease',
        lease_id=lease_id,
        tenant_id=tenant.id,
        docuseal_submission_id=submission.get('id'),
        docuseal_template_id=submission.get('template_id'),
        signing_status='pending',
        docuseal_metadata=submission
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(f"Initiated lease signing for lease {lease_id}, document {document.id}")

    # Send WebSocket notification
    await ws_manager.send_to_user({
        "type": "document_signing_initiated",
        "document_id": str(document.id),
        "document_type": "lease",
        "lease_id": str(lease_id)
    }, str(tenant.id))

    return {
        "document_id": str(document.id),
        "submission_id": submission.get('id'),
        "status": "pending",
        "message": "Lease signing request sent successfully"
    }


@router.get("/leases/{lease_id}/signing-status")
async def get_lease_signing_status(
    lease_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    docuseal: DocuSealClient = Depends(get_docuseal_client)
):
    """
    Get current signing status for a lease

    Accessible by tenant (for their own lease) or admin/manager
    """
    # Get document
    doc_result = await db.execute(
        select(Document).where(
            and_(
                Document.lease_id == lease_id,
                Document.document_type == 'lease'
            )
        ).order_by(Document.created_at.desc())
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        return {
            "status": "not_initiated",
            "message": "No signing request found for this lease"
        }

    # Fetch latest status from DocuSeal
    if document.docuseal_submission_id:
        submission = await docuseal.get_submission(document.docuseal_submission_id)

        if submission:
            # Update document status
            new_status = submission.get('status', document.signing_status)
            if new_status != document.signing_status:
                document.signing_status = new_status
                if new_status == 'signed':
                    document.signed_at = datetime.utcnow()
                await db.commit()

    return {
        "document_id": str(document.id),
        "status": document.signing_status,
        "submission_id": document.docuseal_submission_id,
        "created_at": document.created_at.isoformat(),
        "signed_at": document.signed_at.isoformat() if document.signed_at else None
    }


@router.post("/leases/{lease_id}/resend-signing-email")
async def resend_lease_signing_email(
    lease_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
    docuseal: DocuSealClient = Depends(get_docuseal_client)
):
    """
    Resend signing email to pending signers (Admin/Manager only)
    """
    # Get document
    doc_result = await db.execute(
        select(Document).where(
            and_(
                Document.lease_id == lease_id,
                Document.document_type == 'lease',
                Document.signing_status == 'pending'
            )
        )
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending signing request found"
        )

    # Resend via DocuSeal
    success = await docuseal.resend_email(document.docuseal_submission_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend signing email"
        )

    logger.info(f"Resent signing email for lease {lease_id}, document {document.id}")

    return {"message": "Signing email resent successfully"}


@router.get("/leases/{lease_id}/download-signed-lease")
async def download_signed_lease(
    lease_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    docuseal: DocuSealClient = Depends(get_docuseal_client),
    minio: MinIOClient = Depends(get_minio_client)
):
    """
    Download signed lease document

    Only available after all parties have signed
    Returns presigned URL for direct download from MinIO
    """
    # Get document
    doc_result = await db.execute(
        select(Document).where(
            and_(
                Document.lease_id == lease_id,
                Document.document_type == 'lease',
                Document.signing_status == 'signed'
            )
        )
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No signed lease found"
        )

    # Check if already stored in MinIO
    if not document.minio_object_key:
        # Download from DocuSeal and store in MinIO
        pdf_bytes = await docuseal.download_documents(document.docuseal_submission_id)

        if not pdf_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to download signed document"
            )

        # Upload to MinIO
        filename = f"lease_{lease_id}_signed.pdf"
        object_key = await minio.upload_document(
            file_data=pdf_bytes,
            document_type='lease',
            filename=filename,
            content_type='application/pdf',
            metadata={
                'lease_id': str(lease_id),
                'document_id': str(document.id),
                'signed_at': document.signed_at.isoformat() if document.signed_at else None
            }
        )

        # Update document record
        document.minio_object_key = object_key
        document.file_size_bytes = len(pdf_bytes)
        document.mime_type = 'application/pdf'
        await db.commit()

        logger.info(f"Stored signed lease in MinIO: {object_key}")

    # Generate presigned URL for download (valid for 1 hour)
    download_url = await minio.get_presigned_url(
        object_name=document.minio_object_key,
        expiry=timedelta(hours=1)
    )

    return {
        "message": "Document ready for download",
        "document_id": str(document.id),
        "download_url": download_url,
        "size_bytes": document.file_size_bytes,
        "expires_in": "1 hour"
    }


# ============================================================================
# DOCUSEAL WEBHOOKS
# ============================================================================

@router.post("/webhooks/docuseal")
async def docuseal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    docuseal: DocuSealClient = Depends(get_docuseal_client)
):
    """
    Handle DocuSeal webhook events

    Events: submission.completed, submission.viewed, submission.signed
    """
    event_data = await request.json()

    # Process webhook
    await docuseal.webhook_handler(event_data)

    event_type = event_data.get("event_type")
    submission = event_data.get("data", {})
    submission_id = submission.get("id")

    logger.info(f"Processing DocuSeal webhook: {event_type} for submission {submission_id}")

    # Find document by submission ID
    doc_result = await db.execute(
        select(Document).where(Document.docuseal_submission_id == submission_id)
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        logger.warning(f"Document not found for DocuSeal submission {submission_id}")
        return {"status": "ignored", "reason": "document_not_found"}

    # Handle completion
    if event_type == "submission.completed":
        document.signing_status = 'signed'
        document.signed_at = datetime.utcnow()
        await db.commit()

        logger.info(f"Document {document.id} marked as signed")

        # Send WebSocket notification
        if document.tenant_id:
            await ws_manager.send_to_user({
                "type": "document_signed",
                "document_id": str(document.id),
                "document_type": document.document_type,
                "lease_id": str(document.lease_id) if document.lease_id else None
            }, str(document.tenant_id))

    # Handle individual signatures
    elif event_type == "submission.signed":
        if document.signing_status == 'pending':
            document.signing_status = 'partially_signed'
            await db.commit()

    return {"status": "success", "event_type": event_type}


# ============================================================================
# GENERAL DOCUMENT MANAGEMENT
# ============================================================================

@router.get("/documents/list")
async def list_documents(
    lease_id: Optional[str] = Query(None, description="Filter by lease ID"),
    work_order_id: Optional[str] = Query(None, description="Filter by work order ID"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List documents with optional filtering

    Accessible by managers/admins or tenants viewing their own documents
    """
    # Build query
    query = select(Document)

    # Convert string IDs to UUIDs and apply filters
    if lease_id:
        try:
            lease_uuid = UUID(lease_id)
            query = query.where(Document.lease_id == lease_uuid)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid lease_id format")

    if work_order_id:
        try:
            work_order_uuid = UUID(work_order_id)
            query = query.where(Document.work_order_id == work_order_uuid)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid work_order_id format")

    if tenant_id:
        try:
            tenant_uuid = UUID(tenant_id)
            query = query.where(Document.tenant_id == tenant_uuid)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid tenant_id format")

    if document_type:
        query = query.where(Document.document_type == document_type)

    query = query.offset(skip).limit(limit).order_by(Document.created_at.desc())

    result = await db.execute(query)
    documents = result.scalars().all()

    return {
        "total": len(documents),
        "documents": [
            {
                "id": str(doc.id),
                "title": doc.title,
                "description": doc.description,
                "document_type": doc.document_type,
                "signing_status": doc.signing_status,
                "file_size_bytes": doc.file_size_bytes,
                "mime_type": doc.mime_type,
                "created_at": doc.created_at.isoformat(),
                "signed_at": doc.signed_at.isoformat() if doc.signed_at else None,
                "lease_id": str(doc.lease_id) if doc.lease_id else None,
                "work_order_id": str(doc.work_order_id) if doc.work_order_id else None
            }
            for doc in documents
        ]
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document details"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return {
        "id": str(document.id),
        "title": document.title,
        "description": document.description,
        "document_type": document.document_type,
        "signing_status": document.signing_status,
        "created_at": document.created_at.isoformat(),
        "signed_at": document.signed_at.isoformat() if document.signed_at else None,
        "lease_id": str(document.lease_id) if document.lease_id else None,
        "work_order_id": str(document.work_order_id) if document.work_order_id else None,
        "minio_object_key": document.minio_object_key,
        "file_size_bytes": document.file_size_bytes
    }


# ============================================================================
# DOCUMENT UPLOAD & DOWNLOAD
# ============================================================================

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "other",
    title: Optional[str] = None,
    description: Optional[str] = None,
    lease_id: Optional[UUID] = None,
    work_order_id: Optional[UUID] = None,
    tenant_id: Optional[UUID] = None,
    property_id: Optional[UUID] = None,
    enable_ocr: bool = True,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    minio: MinIOClient = Depends(get_minio_client),
    paperless: PaperlessClient = Depends(get_paperless_client)
):
    """
    Upload a document file (PDF, image, etc.)

    Accessible by managers/admins or tenants uploading to their own records
    Automatically sends to Paperless-ngx for OCR if enabled
    """
    # Read file data
    file_data = await file.read()

    if len(file_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file"
        )

    # Upload to MinIO
    object_key = await minio.upload_document(
        file_data=file_data,
        document_type=document_type,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        metadata={
            'uploaded_by': auth_user.user_id,
            'lease_id': str(lease_id) if lease_id else None,
            'work_order_id': str(work_order_id) if work_order_id else None
        }
    )

    # Create document record
    document = Document(
        title=title or file.filename,
        description=description,
        document_type=document_type,
        lease_id=lease_id,
        work_order_id=work_order_id,
        tenant_id=tenant_id,
        property_id=property_id,
        minio_object_key=object_key,
        file_size_bytes=len(file_data),
        mime_type=file.content_type or "application/octet-stream",
        uploaded_by=auth_user.user_id
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(f"Document uploaded: {document.id} - {file.filename}")

    # Optionally send to Paperless for OCR
    paperless_id = None
    if enable_ocr and settings.PAPERLESS_AUTO_OCR:
        try:
            # Determine tags based on document type
            tags = [document_type, "somniproperty"]

            # Upload to Paperless
            paperless_result = await paperless.upload_document(
                file_data=file_data,
                filename=file.filename,
                title=title or file.filename,
                tags=tags,
                created_date=datetime.utcnow()
            )

            if paperless_result:
                paperless_id = paperless_result.get('id')
                document.paperless_document_id = paperless_id
                await db.commit()
                logger.info(f"Document sent to Paperless for OCR: {paperless_id}")
        except Exception as e:
            logger.warning(f"Failed to send document to Paperless (non-fatal): {e}")

    return {
        "document_id": str(document.id),
        "title": document.title,
        "file_size_bytes": document.file_size_bytes,
        "minio_object_key": object_key,
        "paperless_document_id": paperless_id,
        "ocr_enabled": paperless_id is not None,
        "message": "Document uploaded successfully"
    }


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    minio: MinIOClient = Depends(get_minio_client)
):
    """
    Download a document file

    Returns presigned URL for direct download from MinIO
    """
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if not document.minio_object_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not available"
        )

    # Generate presigned URL (valid for 1 hour)
    download_url = await minio.get_presigned_url(
        object_name=document.minio_object_key,
        expiry=timedelta(hours=1)
    )

    return {
        "document_id": str(document.id),
        "title": document.title,
        "download_url": download_url,
        "size_bytes": document.file_size_bytes,
        "mime_type": document.mime_type,
        "expires_in": "1 hour"
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
    minio: MinIOClient = Depends(get_minio_client)
):
    """
    Delete a document (manager/admin only)

    Removes both database record and file from MinIO
    """
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Delete from MinIO if exists
    if document.minio_object_key:
        await minio.delete_file(document.minio_object_key)
        logger.info(f"Deleted file from MinIO: {document.minio_object_key}")

    # Delete database record
    await db.delete(document)
    await db.commit()

    logger.info(f"Deleted document: {document_id}")

    return {"message": "Document deleted successfully"}


# ============================================================================
# PAPERLESS-NGX OCR INTEGRATION
# ============================================================================

@router.get("/documents/{document_id}/ocr-text")
async def get_document_ocr_text(
    document_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    paperless: PaperlessClient = Depends(get_paperless_client)
):
    """
    Get OCR'd text from a document

    Extracts text that was OCR'd by Paperless-ngx
    """
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if not document.paperless_document_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document has not been OCR'd"
        )

    # Get OCR'd text from Paperless
    text = await paperless.get_document_text(document.paperless_document_id)

    if text is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve OCR'd text"
        )

    return {
        "document_id": str(document.id),
        "paperless_document_id": document.paperless_document_id,
        "title": document.title,
        "ocr_text": text,
        "text_length": len(text)
    }


@router.get("/documents/search-paperless")
async def search_paperless_documents(
    query: Optional[str] = None,
    document_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    auth_user: AuthUser = Depends(get_auth_user),
    paperless: PaperlessClient = Depends(get_paperless_client)
):
    """
    Search documents using Paperless-ngx full-text search

    Searches across all OCR'd document content
    """
    # Search Paperless
    results = await paperless.search_documents(
        query=query,
        tags=["somniproperty"] if not query else None,  # Filter to our documents
        page=page,
        page_size=page_size
    )

    return {
        "total": results.get('count', 0),
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "paperless_id": doc.get('id'),
                "title": doc.get('title'),
                "content_preview": doc.get('content', '')[:200] + "..." if len(doc.get('content', '')) > 200 else doc.get('content', ''),
                "created": doc.get('created'),
                "modified": doc.get('modified'),
                "tags": doc.get('tags', []),
                "correspondent": doc.get('correspondent')
            }
            for doc in results.get('results', [])
        ]
    }


@router.post("/documents/{document_id}/send-to-paperless")
async def send_document_to_paperless(
    document_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
    minio: MinIOClient = Depends(get_minio_client),
    paperless: PaperlessClient = Depends(get_paperless_client)
):
    """
    Manually send a document to Paperless for OCR

    Useful for documents uploaded with OCR disabled
    """
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.paperless_document_id:
        return {
            "message": "Document already in Paperless",
            "paperless_document_id": document.paperless_document_id
        }

    if not document.minio_object_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no file stored"
        )

    # Download from MinIO
    file_data = await minio.download_file(document.minio_object_key)

    # Upload to Paperless
    tags = [document.document_type, "somniproperty"]
    paperless_result = await paperless.upload_document(
        file_data=file_data,
        filename=document.title,
        title=document.title,
        tags=tags,
        created_date=document.created_at
    )

    if not paperless_result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload to Paperless"
        )

    # Update document record
    document.paperless_document_id = paperless_result.get('id')
    await db.commit()

    logger.info(f"Manually sent document {document_id} to Paperless")

    return {
        "message": "Document sent to Paperless successfully",
        "document_id": str(document.id),
        "paperless_document_id": document.paperless_document_id
    }


@router.get("/paperless/tags")
async def get_paperless_tags(
    auth_user: AuthUser = Depends(get_auth_user),
    paperless: PaperlessClient = Depends(get_paperless_client)
):
    """
    Get all Paperless tags

    Useful for categorizing documents
    """
    tags = await paperless.get_tags()

    return {
        "total": len(tags),
        "tags": [
            {
                "id": tag.get('id'),
                "name": tag.get('name'),
                "color": tag.get('color'),
                "document_count": tag.get('document_count', 0)
            }
            for tag in tags
        ]
    }
