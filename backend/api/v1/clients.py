"""
Somni Property Manager - Clients API
CRUD endpoints for client management (Somni Intelligent Living as a Service)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID

from db.database import get_db
from db.models import Client as ClientModel, PropertyEdgeNode, Property, ClientMedia as ClientMediaModel
from api.schemas import (
    Client, ClientCreate, ClientUpdate, ClientListResponse, ClientInfrastructureResponse
)
from core.auth import AuthUser, require_admin, require_manager
from services.client_media_service import get_client_media_service

router = APIRouter()


@router.post("", response_model=Client, status_code=201)
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Create a new client (Admin only)"""
    client_obj = ClientModel(**client_data.model_dump())
    db.add(client_obj)
    await db.flush()
    await db.refresh(client_obj)
    return client_obj


@router.get("", response_model=ClientListResponse)
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None, description="Search by name, email, company, or phone"),
    tier: Optional[str] = Query(None, pattern="^(tier_0|tier_1|tier_2)$"),
    client_type: Optional[str] = Query(None, pattern="^(multi-unit|single-family)$"),
    status: Optional[str] = Query(None, pattern="^(active|suspended|cancelled|churned)$"),
    billing_status: Optional[str] = Query(None, pattern="^(active|suspended|cancelled|past_due)$"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all clients with pagination and filtering (Admin/Manager only)

    Filters:
    - search: Search by name, email, company name, or phone
    - tier: Filter by service tier (tier_0, tier_1, tier_2)
    - client_type: Filter by client type (multi-unit, single-family)
    - status: Filter by account status (active, suspended, cancelled, churned)
    - billing_status: Filter by billing status (active, suspended, cancelled, past_due)
    """
    # Build query with filters
    query = select(ClientModel)

    # Text search across name, email, company, phone
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (ClientModel.name.ilike(search_pattern)) |
            (ClientModel.email.ilike(search_pattern)) |
            (ClientModel.primary_contact_name.ilike(search_pattern)) |
            (ClientModel.phone.ilike(search_pattern))
        )

    if tier:
        query = query.where(ClientModel.tier == tier)
    if client_type:
        query = query.where(ClientModel.client_type == client_type)
    if status:
        query = query.where(ClientModel.status == status)
    if billing_status:
        query = query.where(ClientModel.billing_status == billing_status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get clients with pagination
    query = query.offset(skip).limit(limit).order_by(ClientModel.created_at.desc())
    result = await db.execute(query)
    clients = result.scalars().all()

    return ClientListResponse(
        total=total,
        items=clients,
        skip=skip,
        limit=limit
    )


@router.get("/{client_id}", response_model=Client)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific client by ID (Admin/Manager only)"""
    query = select(ClientModel).where(ClientModel.id == client_id)
    result = await db.execute(query)
    client_obj = result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    return client_obj


@router.put("/{client_id}", response_model=Client)
async def update_client(
    client_id: UUID,
    client_data: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Update a client (Admin only)"""
    query = select(ClientModel).where(ClientModel.id == client_id)
    result = await db.execute(query)
    client_obj = result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Update only provided fields
    update_data = client_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client_obj, key, value)

    await db.flush()
    await db.refresh(client_obj)
    return client_obj


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Delete a client (Admin only)"""
    query = select(ClientModel).where(ClientModel.id == client_id)
    result = await db.execute(query)
    client_obj = result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    await db.delete(client_obj)
    return None


@router.get("/{client_id}/infrastructure", response_model=ClientInfrastructureResponse)
async def get_client_infrastructure(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get client's linked infrastructure details (Admin/Manager only)

    Returns:
    - PropertyEdgeNode details (if linked for Tier 1/2)
    - Property details (if linked for Tier 2 Type A landlord clients)
    """
    # Get client
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get linked edge node if exists
    edge_node = None
    if client_obj.edge_node_id:
        edge_node_query = select(PropertyEdgeNode).where(PropertyEdgeNode.id == client_obj.edge_node_id)
        edge_node_result = await db.execute(edge_node_query)
        edge_node = edge_node_result.scalar_one_or_none()

    # Get linked property if exists
    property_obj = None
    if client_obj.property_id:
        property_query = select(Property).where(Property.id == client_obj.property_id)
        property_result = await db.execute(property_query)
        property_obj = property_result.scalar_one_or_none()

    return ClientInfrastructureResponse(
        client_id=client_obj.id,
        client_name=client_obj.name,
        client_tier=client_obj.tier,
        edge_node=edge_node,
        property=property_obj
    )


@router.get("/{client_id}/services/installed")
async def get_client_installed_services(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get client's installed services (stub endpoint)

    This is a stub endpoint that returns an empty array.
    Service catalog functionality will be implemented in a future release.
    """
    # Verify client exists
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Return empty array - stub implementation
    return []


@router.get("/{client_id}/services/available")
async def get_client_available_services(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get available services for client based on tier (stub endpoint)

    This is a stub endpoint that returns an empty array.
    Service catalog functionality will be implemented in a future release.
    """
    # Verify client exists
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Return empty array - stub implementation
    return []

@router.get("/{client_id}/floorplans")
async def get_client_floorplans(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get all floorplan files for a client

    Returns floor plans uploaded for this client (2D images, PDFs)
    """
    # Verify client exists
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get floorplan media
    media_query = select(ClientMediaModel).where(
        ClientMediaModel.client_id == client_id,
        ClientMediaModel.media_type == 'floorplan',
        ClientMediaModel.deleted_at.is_(None)
    ).order_by(ClientMediaModel.created_at.desc())

    result = await db.execute(media_query)
    floorplans = result.scalars().all()

    # Format response
    return {
        "floorplans": [
            {
                "id": str(fp.id),
                "name": fp.title or fp.original_file_name,
                "file_name": fp.file_name,
                "file_type": fp.mime_type,
                "file_size": fp.file_size_bytes,
                "url": fp.minio_url or fp.cdn_url,
                "thumbnail_url": fp.thumbnail_url,
                "uploaded_at": fp.created_at.isoformat() if fp.created_at else None,
                "description": fp.description,
                "tags": fp.tags or []
            }
            for fp in floorplans
        ]
    }


@router.post("/{client_id}/floorplans/upload")
async def upload_client_floorplan(
    client_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Upload a floorplan file for a client

    Accepts: PNG, JPG, PDF files
    """
    # Verify client exists
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Use media service to upload
    media_service = get_client_media_service(db)

    media = await media_service.upload_media(
        client_id=client_id,
        file=file,
        media_type='floorplan',
        media_category='floorplan',
        title=file.filename,
        uploaded_by=auth_user.username
    )

    return {
        "id": str(media.id),
        "name": media.title or media.original_file_name,
        "file_name": media.file_name,
        "file_type": media.mime_type,
        "file_size": media.file_size_bytes,
        "url": media.minio_url or media.cdn_url,
        "thumbnail_url": media.thumbnail_url,
        "uploaded_at": media.created_at.isoformat() if media.created_at else None,
        "processing_status": media.processing_status
    }


@router.delete("/{client_id}/floorplans/{floorplan_id}", status_code=204)
async def delete_client_floorplan(
    client_id: UUID,
    floorplan_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Delete a floorplan file"""
    # Verify client exists
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get floorplan
    media_query = select(ClientMediaModel).where(
        ClientMediaModel.id == floorplan_id,
        ClientMediaModel.client_id == client_id,
        ClientMediaModel.media_type == 'floorplan'
    )
    result = await db.execute(media_query)
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=404, detail="Floorplan not found")

    # Use media service to delete
    media_service = get_client_media_service(db)
    await media_service.delete_media(floorplan_id, hard_delete=False)

    return None


@router.get("/{client_id}/3d-scans")
async def get_client_3d_scans(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get all 3D scan files/links for a client

    Returns 3D models and scan links (Polycam, Matterport, etc.)
    """
    # Verify client exists
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get 3D model media
    media_query = select(ClientMediaModel).where(
        ClientMediaModel.client_id == client_id,
        ClientMediaModel.media_type == '3d_model',
        ClientMediaModel.deleted_at.is_(None)
    ).order_by(ClientMediaModel.created_at.desc())

    result = await db.execute(media_query)
    scans = result.scalars().all()

    # Format response
    return {
        "scans": [
            {
                "id": str(scan.id),
                "name": scan.title or scan.original_file_name,
                "url": scan.minio_url or scan.cdn_url,
                "embed_url": _get_embed_url(scan.minio_url or scan.cdn_url),
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
                "description": scan.description,
                "model_format": scan.model_format,
                "tags": scan.tags or []
            }
            for scan in scans
        ]
    }


@router.post("/{client_id}/3d-scans")
async def add_client_3d_scan(
    client_id: UUID,
    url: str = Form(...),
    name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Add a 3D scan URL for a client (Polycam, Matterport, etc.)

    For external 3D scan services, stores the URL as metadata
    """
    # Verify client exists
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Create media record for external 3D scan link
    import uuid
    media = ClientMediaModel(
        id=uuid.uuid4(),
        client_id=client_id,
        media_type='3d_model',
        media_category='3d_model',
        file_name=name or url,
        original_file_name=name or url,
        file_extension='url',
        mime_type='application/x-url',
        file_size_bytes=0,
        minio_bucket='external',
        minio_object_key=url,
        minio_url=url,
        title=name,
        description=f"External 3D scan: {url}",
        processing_status='completed',
        uploaded_by=auth_user.username,
        upload_source='web_ui'
    )

    db.add(media)
    await db.flush()
    await db.refresh(media)

    return {
        "scan": {
            "id": str(media.id),
            "name": media.title or media.original_file_name,
            "url": url,
            "embed_url": _get_embed_url(url),
            "created_at": media.created_at.isoformat() if media.created_at else None,
            "description": media.description
        }
    }


@router.delete("/{client_id}/3d-scans/{scan_id}", status_code=204)
async def delete_client_3d_scan(
    client_id: UUID,
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Delete a 3D scan"""
    # Verify client exists
    client_query = select(ClientModel).where(ClientModel.id == client_id)
    client_result = await db.execute(client_query)
    client_obj = client_result.scalar_one_or_none()

    if not client_obj:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get scan
    media_query = select(ClientMediaModel).where(
        ClientMediaModel.id == scan_id,
        ClientMediaModel.client_id == client_id,
        ClientMediaModel.media_type == '3d_model'
    )
    result = await db.execute(media_query)
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=404, detail="3D scan not found")

    # Use media service to delete
    media_service = get_client_media_service(db)
    await media_service.delete_media(scan_id, hard_delete=False)

    return None


def _get_embed_url(url: str) -> Optional[str]:
    """
    Convert public URL to embeddable iframe URL if possible

    Supports: Polycam, Matterport
    """
    if not url:
        return None

    # Polycam: https://poly.cam/capture/... -> embed URL
    if 'poly.cam/capture/' in url:
        # Polycam embed format
        return url.replace('poly.cam/capture/', 'poly.cam/embed/')

    # Matterport: https://my.matterport.com/show/?m=... -> iframe URL
    if 'matterport.com' in url and '?m=' in url:
        return url  # Matterport URLs are already embeddable

    # For other URLs, return None (will show as link instead of embed)
    return None
