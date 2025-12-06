"""
Client Media API Endpoints
Upload, manage, and retrieve client portfolio media (photos, videos, floorplans, 3D models)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from db.database import get_db
from api.schemas import (
    ClientMedia,
    ClientMediaUpdate,
    ClientMediaListResponse,
    ClientMediaUploadResponse,
    ClientMediaBulkDeleteRequest,
    ClientMediaBulkDeleteResponse,
    ClientMediaStatistics
)
from services.client_media_service import get_client_media_service, ClientMediaService
from core.auth import AuthUser, require_manager, require_admin

router = APIRouter()


@router.post("/{client_id}/media/upload", response_model=ClientMediaUploadResponse, status_code=201)
async def upload_client_media(
    client_id: UUID,
    file: UploadFile = File(...),
    media_type: str = Form(...),
    media_category: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Upload media file for client portfolio

    **Media Types:**
    - photo: Property photos, unit examples
    - video: Property tours, walkthroughs
    - floorplan: Floor plans, site plans, CAD files
    - 3d_model: 3D models (GLB, USDZ, etc.)
    - document: PDFs, permits, inspection reports
    - other: Other files

    **Media Categories:**
    - property_exterior: Exterior photos
    - property_interior: Interior photos
    - unit_example: Example unit photos
    - amenities: Amenity photos
    - floorplan: Floor plan documents
    - site_plan: Site plan documents
    - 3d_model: 3D models
    - permit: Permits and licenses
    - inspection: Inspection reports
    - other: Uncategorized

    **File Size Limits:**
    - Photos: 50 MB
    - Videos: 500 MB
    - Floorplans: 100 MB
    - 3D Models: 200 MB
    - Documents: 100 MB
    """
    media_service = get_client_media_service(db)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else []

    # Upload media
    media = await media_service.upload_media(
        client_id=client_id,
        file=file,
        media_type=media_type,
        media_category=media_category,
        title=title,
        description=description,
        tags=tag_list,
        uploaded_by=auth_user.username
    )

    return ClientMediaUploadResponse(
        media_id=media.id,
        file_name=media.file_name,
        file_size_bytes=media.file_size_bytes,
        mime_type=media.mime_type,
        minio_url=media.minio_url,
        processing_status=media.processing_status,
        message="File uploaded successfully"
    )


@router.get("/{client_id}/media", response_model=ClientMediaListResponse)
async def list_client_media(
    client_id: UUID,
    media_type: Optional[str] = Query(None, pattern="^(photo|video|floorplan|3d_model|document|other)$"),
    media_category: Optional[str] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List media files for a client with filtering

    **Filters:**
    - media_type: Filter by media type
    - media_category: Filter by category
    - tags: Filter by tags (comma-separated, matches any)
    - skip/limit: Pagination
    """
    media_service = get_client_media_service(db)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(',')] if tags else None

    # Get media list
    media_list, total = await media_service.list_client_media(
        client_id=client_id,
        media_type=media_type,
        media_category=media_category,
        tags=tag_list,
        skip=skip,
        limit=limit
    )

    return ClientMediaListResponse(
        items=media_list,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/media/{media_id}", response_model=ClientMedia)
async def get_media(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get specific media file by ID"""
    media_service = get_client_media_service(db)
    media = await media_service.get_media(media_id)

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    return media


@router.put("/media/{media_id}", response_model=ClientMedia)
async def update_media(
    media_id: UUID,
    update_data: ClientMediaUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Update media metadata (title, description, tags, category, etc.)"""
    media_service = get_client_media_service(db)
    media = await media_service.update_media(media_id, update_data)
    return media


@router.delete("/media/{media_id}", status_code=204)
async def delete_media(
    media_id: UUID,
    hard_delete: bool = Query(False, description="If true, permanently delete from storage"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Delete media file

    **Soft Delete (default):**
    - Marks file as deleted in database
    - File remains in storage
    - Can be recovered

    **Hard Delete (hard_delete=true):**
    - Permanently deletes file from storage
    - Removes database record
    - Cannot be recovered (Admin only)
    """
    media_service = get_client_media_service(db)
    await media_service.delete_media(media_id, hard_delete=hard_delete)
    return None


@router.post("/media/bulk-delete", response_model=ClientMediaBulkDeleteResponse)
async def bulk_delete_media(
    request: ClientMediaBulkDeleteRequest,
    hard_delete: bool = Query(False, description="If true, permanently delete from storage"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Bulk delete multiple media files (Admin only)

    Returns counts of deleted/failed files and any error messages
    """
    media_service = get_client_media_service(db)

    deleted_count, failed_ids, errors = await media_service.bulk_delete_media(
        media_ids=request.media_ids,
        hard_delete=hard_delete
    )

    return ClientMediaBulkDeleteResponse(
        deleted_count=deleted_count,
        failed_ids=failed_ids,
        errors=errors
    )


@router.get("/{client_id}/media/statistics", response_model=ClientMediaStatistics)
async def get_media_statistics(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get media statistics for client

    Returns counts by type/category, total size, etc.
    """
    media_service = get_client_media_service(db)
    stats = await media_service.get_media_statistics(client_id)
    return stats


@router.get("/media/{media_id}/download")
async def download_media(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Download media file through backend proxy

    This endpoint streams the file from MinIO through the backend,
    allowing browser access without exposing MinIO directly.
    """
    from fastapi.responses import StreamingResponse
    from services.minio_client import get_minio_client

    media_service = get_client_media_service(db)
    media = await media_service.get_media(media_id)

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Get file from MinIO
    minio_client = await get_minio_client()
    try:
        file_data = await minio_client.download_file(media.minio_object_key)

        # Stream file to browser
        return StreamingResponse(
            iter([file_data]),
            media_type=media.mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{media.original_file_name}"',
                "Cache-Control": "public, max-age=3600",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.get("/media/file")
async def download_media_file_by_path(
    path: str = Query(..., description="MinIO object path"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Download media file by MinIO path

    Used for downloading related files like .mtl or texture files
    for 3D models without requiring a media_id.
    """
    from fastapi.responses import StreamingResponse
    from services.minio_client import get_minio_client
    import mimetypes

    # Security: Ensure path starts with 'clients/' to prevent path traversal
    if not path.startswith('clients/'):
        raise HTTPException(status_code=400, detail="Invalid file path")

    minio_client = await get_minio_client()
    try:
        file_data = await minio_client.download_file(path)

        # Determine MIME type from file extension
        mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'

        # Get filename from path
        filename = path.split('/')[-1]

        # Stream file to browser
        return StreamingResponse(
            iter([file_data]),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",  # Allow Three.js to load textures
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
