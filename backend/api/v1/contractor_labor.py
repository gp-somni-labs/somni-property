"""
Contractor Labor Documentation API
Comprehensive endpoints for photo documentation, notes, time tracking, materials, and reporting
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal
import logging
import json

from db.database import get_db
from db.models_contractor_labor import (
    QuoteLaborItemPhoto,
    QuoteLaborItemNote,
    QuoteLaborTimeEntry,
    QuoteLaborMaterialUsed,
    QuoteLaborItemHistory,
    QuoteLaborBeforeAfterPair,
    ContractorWorkExample
)
from db.models_quotes import QuoteLaborItem as QuoteLaborItemModel
from db.models import Contractor
from api.schemas_contractor_labor import (
    # Photos
    QuoteLaborItemPhoto as QuoteLaborItemPhotoSchema,
    QuoteLaborItemPhotoCreate,
    QuoteLaborItemPhotoUpdate,
    PhotoUploadResponse,
    PhotoFilter,
    # Notes
    QuoteLaborItemNote as QuoteLaborItemNoteSchema,
    QuoteLaborItemNoteCreate,
    QuoteLaborItemNoteUpdate,
    QuoteLaborItemNoteResponse,
    NoteFilter,
    # Time Tracking
    QuoteLaborTimeEntry as QuoteLaborTimeEntrySchema,
    QuoteLaborTimeEntryCreate,
    QuoteLaborTimeEntryUpdate,
    QuoteLaborTimeEntryApproval,
    TimeEntryFilter,
    # Materials
    QuoteLaborMaterialUsed as QuoteLaborMaterialUsedSchema,
    QuoteLaborMaterialUsedCreate,
    QuoteLaborMaterialUsedUpdate,
    # Before/After
    QuoteLaborBeforeAfterPair as QuoteLaborBeforeAfterPairSchema,
    QuoteLaborBeforeAfterPairCreate,
    QuoteLaborBeforeAfterPairUpdate,
    # Work Examples
    ContractorWorkExample as ContractorWorkExampleSchema,
    ContractorWorkExampleCreate,
    ContractorWorkExampleUpdate,
    ContractorWorkExampleApproval,
    # Labor Item Updates
    QuoteLaborItemAssignment,
    QuoteLaborItemStatusUpdate,
    QuoteLaborItemActuals,
    QuoteLaborItemQC,
    QuoteLaborItemCustomerApproval,
    # Reporting
    LaborItemProgress,
    ContractorDashboard,
    LaborCostAnalysis
)
from core.auth import AuthUser, require_admin, require_manager
from services.file_storage import get_file_storage_service
from api.v1.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# PHOTO DOCUMENTATION ENDPOINTS
# ============================================================================

@router.post("/labor-items/{labor_item_id}/photos/upload", response_model=PhotoUploadResponse)
async def upload_photo(
    labor_item_id: UUID,
    file: UploadFile = File(...),
    photo_type: str = Form(...),
    caption: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photo_taken_by: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a photo for a labor item

    Supports: before, after, progress, issue, safety, equipment, completed photos
    No authentication required - allows contractors to upload from mobile app
    """
    # Verify labor item exists
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Upload file to storage
    storage_service = get_file_storage_service()
    file_url, file_path, file_size = await storage_service.upload_file(
        file,
        folder=f"labor-photos/{labor_item_id}"
    )

    logger.info(f"Uploaded photo for labor item {labor_item_id}: {file_url}")

    return PhotoUploadResponse(
        file_url=file_url,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type
    )


@router.post("/labor-items/{labor_item_id}/photos", response_model=QuoteLaborItemPhotoSchema, status_code=201)
async def create_photo_record(
    labor_item_id: UUID,
    photo: QuoteLaborItemPhotoCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a photo record after uploading file

    Links uploaded photo file to labor item with metadata
    """
    # Verify labor item exists
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Create photo record
    new_photo = QuoteLaborItemPhoto(
        labor_item_id=labor_item_id,
        **photo.model_dump(exclude={'labor_item_id', 'gps_coordinates'})
    )

    # Handle GPS coordinates if provided
    if photo.gps_coordinates:
        # PostgreSQL POINT format: POINT(longitude latitude)
        lat = photo.gps_coordinates.get('lat')
        lng = photo.gps_coordinates.get('lng')
        if lat and lng:
            from sqlalchemy import text
            await db.execute(
                text("UPDATE quote_labor_item_photos SET gps_coordinates = POINT(:lng, :lat) WHERE id = :id"),
                {"lng": lng, "lat": lat, "id": str(new_photo.id)}
            )

    db.add(new_photo)
    await db.commit()
    await db.refresh(new_photo)

    # Log history
    await _log_history(
        db, labor_item_id, "photo_added", None, photo.photo_type,
        photo.photo_taken_by or "unknown", "contractor"
    )

    logger.info(f"Created photo record {new_photo.id} for labor item {labor_item_id}")

    return new_photo


@router.get("/labor-items/{labor_item_id}/photos", response_model=List[QuoteLaborItemPhotoSchema])
async def list_labor_item_photos(
    labor_item_id: UUID,
    photo_type: Optional[str] = None,
    show_to_customer: Optional[bool] = None,
    approved_only: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    List all photos for a labor item

    Filter by photo_type, visibility, approval status
    """
    query = select(QuoteLaborItemPhoto).where(QuoteLaborItemPhoto.labor_item_id == labor_item_id)

    if photo_type:
        query = query.where(QuoteLaborItemPhoto.photo_type == photo_type)

    if show_to_customer is not None:
        query = query.where(QuoteLaborItemPhoto.show_to_customer == show_to_customer)

    if approved_only:
        query = query.where(QuoteLaborItemPhoto.approved_for_display == True)

    query = query.order_by(QuoteLaborItemPhoto.display_order, QuoteLaborItemPhoto.photo_taken_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    photos = result.scalars().all()

    return [QuoteLaborItemPhotoSchema.model_validate(p) for p in photos]


@router.put("/labor-items/{labor_item_id}/photos/{photo_id}", response_model=QuoteLaborItemPhotoSchema)
async def update_photo(
    labor_item_id: UUID,
    photo_id: UUID,
    photo_update: QuoteLaborItemPhotoUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update photo metadata (caption, annotations, display settings)"""
    query = select(QuoteLaborItemPhoto).where(
        QuoteLaborItemPhoto.id == photo_id,
        QuoteLaborItemPhoto.labor_item_id == labor_item_id
    )
    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Update fields
    update_data = photo_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(photo, field, value)

    await db.commit()
    await db.refresh(photo)

    logger.info(f"Updated photo {photo_id} for labor item {labor_item_id}")

    return photo


@router.delete("/labor-items/{labor_item_id}/photos/{photo_id}", status_code=204)
async def delete_photo(
    labor_item_id: UUID,
    photo_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Delete a photo (manager only)"""
    query = select(QuoteLaborItemPhoto).where(
        QuoteLaborItemPhoto.id == photo_id,
        QuoteLaborItemPhoto.labor_item_id == labor_item_id
    )
    result = await db.execute(query)
    photo = result.scalar_one_or_none()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    await db.delete(photo)
    await db.commit()

    logger.info(f"Deleted photo {photo_id} from labor item {labor_item_id}")

    return None


# ============================================================================
# NOTES & COMMUNICATION ENDPOINTS
# ============================================================================

@router.post("/labor-items/{labor_item_id}/notes", response_model=QuoteLaborItemNoteSchema, status_code=201)
async def create_note(
    labor_item_id: UUID,
    note: QuoteLaborItemNoteCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a note/update for a labor item

    Types: progress_update, issue, material_request, question, completion, customer_feedback
    """
    # Verify labor item exists
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Create note
    new_note = QuoteLaborItemNote(
        labor_item_id=labor_item_id,
        **note.model_dump(exclude={'labor_item_id', 'location_coords'})
    )

    # Handle GPS coordinates if provided
    if note.location_coords:
        lat = note.location_coords.get('lat')
        lng = note.location_coords.get('lng')
        if lat and lng:
            from sqlalchemy import text
            await db.execute(
                text("UPDATE quote_labor_item_notes SET location_coords = POINT(:lng, :lat) WHERE id = :id"),
                {"lng": lng, "lat": lat, "id": str(new_note.id)}
            )

    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)

    # Log history
    await _log_history(
        db, labor_item_id, "note_added", None, note.note_type,
        note.created_by, note.created_by_type
    )

    # Auto-update labor item status if completion note
    if note.note_type == "completion":
        labor_item.work_status = "needs_review"
        labor_item.work_completed_at = datetime.utcnow()
        await db.commit()

    logger.info(f"Created note {new_note.id} for labor item {labor_item_id}: {note.note_type}")

    return new_note


@router.get("/labor-items/{labor_item_id}/notes", response_model=List[QuoteLaborItemNoteSchema])
async def list_labor_item_notes(
    labor_item_id: UUID,
    note_type: Optional[str] = None,
    requires_response: Optional[bool] = None,
    is_internal: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """List all notes for a labor item with optional filters"""
    query = select(QuoteLaborItemNote).where(QuoteLaborItemNote.labor_item_id == labor_item_id)

    if note_type:
        query = query.where(QuoteLaborItemNote.note_type == note_type)

    if requires_response is not None:
        query = query.where(QuoteLaborItemNote.requires_response == requires_response)

    if is_internal is not None:
        query = query.where(QuoteLaborItemNote.is_internal == is_internal)

    query = query.order_by(QuoteLaborItemNote.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    notes = result.scalars().all()

    return [QuoteLaborItemNoteSchema.model_validate(n) for n in notes]


@router.post("/labor-items/{labor_item_id}/notes/{note_id}/respond", response_model=QuoteLaborItemNoteSchema)
async def respond_to_note(
    labor_item_id: UUID,
    note_id: UUID,
    response: QuoteLaborItemNoteResponse,
    db: AsyncSession = Depends(get_db)
):
    """Respond to a note that requires response"""
    query = select(QuoteLaborItemNote).where(
        QuoteLaborItemNote.id == note_id,
        QuoteLaborItemNote.labor_item_id == labor_item_id
    )
    result = await db.execute(query)
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Update response fields
    note.responded_to = True
    note.responded_by = response.responded_by
    note.responded_at = datetime.utcnow()
    note.response_text = response.response_text

    await db.commit()
    await db.refresh(note)

    logger.info(f"Responded to note {note_id} for labor item {labor_item_id}")

    return note


@router.put("/labor-items/{labor_item_id}/notes/{note_id}", response_model=QuoteLaborItemNoteSchema)
async def update_note(
    labor_item_id: UUID,
    note_id: UUID,
    note_update: QuoteLaborItemNoteUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a note"""
    query = select(QuoteLaborItemNote).where(
        QuoteLaborItemNote.id == note_id,
        QuoteLaborItemNote.labor_item_id == labor_item_id
    )
    result = await db.execute(query)
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Update fields
    update_data = note_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)

    await db.commit()
    await db.refresh(note)

    return note


# ============================================================================
# TIME TRACKING ENDPOINTS
# ============================================================================

@router.post("/labor-items/{labor_item_id}/time-entries/clock-in", response_model=QuoteLaborTimeEntrySchema, status_code=201)
async def clock_in(
    labor_item_id: UUID,
    worker_name: str = Form(...),
    worker_role: Optional[str] = Form(None),
    contractor_id: Optional[UUID] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Clock in to start work on a labor item

    Captures GPS location for verification
    """
    # Verify labor item exists
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Create time entry
    time_entry = QuoteLaborTimeEntry(
        labor_item_id=labor_item_id,
        contractor_id=contractor_id,
        worker_name=worker_name,
        worker_role=worker_role,
        work_date=date.today(),
        start_time=datetime.now().time(),
        duration_hours=Decimal("0"),  # Will be calculated at clock out
        hourly_rate=labor_item.hourly_rate
    )

    # Handle GPS coordinates
    if latitude and longitude:
        from sqlalchemy import text
        await db.execute(
            text("UPDATE quote_labor_time_entries SET clock_in_location = POINT(:lng, :lat) WHERE id = :id"),
            {"lng": longitude, "lat": latitude, "id": str(time_entry.id)}
        )

    db.add(time_entry)

    # Update labor item status if not already in progress
    if labor_item.work_status == "assigned":
        labor_item.work_status = "in_progress"
        labor_item.work_started_at = datetime.utcnow()

    await db.commit()
    await db.refresh(time_entry)

    logger.info(f"Clock in for labor item {labor_item_id} by {worker_name}")

    return time_entry


@router.put("/labor-items/{labor_item_id}/time-entries/{time_entry_id}/clock-out", response_model=QuoteLaborTimeEntrySchema)
async def clock_out(
    labor_item_id: UUID,
    time_entry_id: UUID,
    work_description: Optional[str] = Form(None),
    tasks_completed: Optional[str] = Form(None),  # JSON array as string
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    break_hours: Optional[float] = Form(0),
    db: AsyncSession = Depends(get_db)
):
    """
    Clock out to end work session

    Calculates duration and captures completion GPS
    """
    query = select(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.id == time_entry_id,
        QuoteLaborTimeEntry.labor_item_id == labor_item_id
    )
    result = await db.execute(query)
    time_entry = result.scalar_one_or_none()

    if not time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    # Calculate duration
    end_time = datetime.now().time()
    start_datetime = datetime.combine(time_entry.work_date, time_entry.start_time)
    end_datetime = datetime.combine(time_entry.work_date, end_time)

    total_hours = (end_datetime - start_datetime).total_seconds() / 3600
    duration = Decimal(str(total_hours)) - Decimal(str(break_hours))

    time_entry.end_time = end_time
    time_entry.duration_hours = duration
    time_entry.break_duration_hours = Decimal(str(break_hours))
    time_entry.work_description = work_description

    if tasks_completed:
        time_entry.tasks_completed = json.loads(tasks_completed)

    # Calculate cost
    if time_entry.hourly_rate:
        time_entry.total_cost = duration * time_entry.hourly_rate

    # Handle GPS coordinates
    if latitude and longitude:
        from sqlalchemy import text
        await db.execute(
            text("UPDATE quote_labor_time_entries SET clock_out_location = POINT(:lng, :lat) WHERE id = :id"),
            {"lng": longitude, "lat": latitude, "id": str(time_entry.id)}
        )

    await db.commit()
    await db.refresh(time_entry)

    # Update labor item actual hours
    await _update_labor_item_actuals(db, labor_item_id)

    logger.info(f"Clock out for time entry {time_entry_id}: {duration} hours")

    return time_entry


@router.get("/labor-items/{labor_item_id}/time-entries", response_model=List[QuoteLaborTimeEntrySchema])
async def list_time_entries(
    labor_item_id: UUID,
    approved: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """List all time entries for a labor item"""
    query = select(QuoteLaborTimeEntry).where(QuoteLaborTimeEntry.labor_item_id == labor_item_id)

    if approved is not None:
        query = query.where(QuoteLaborTimeEntry.approved == approved)

    if date_from:
        query = query.where(QuoteLaborTimeEntry.work_date >= date_from)

    if date_to:
        query = query.where(QuoteLaborTimeEntry.work_date <= date_to)

    query = query.order_by(QuoteLaborTimeEntry.work_date.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()

    return [QuoteLaborTimeEntrySchema.model_validate(e) for e in entries]


@router.put("/labor-items/{labor_item_id}/time-entries/{time_entry_id}/approve", response_model=QuoteLaborTimeEntrySchema)
async def approve_time_entry(
    labor_item_id: UUID,
    time_entry_id: UUID,
    approval: QuoteLaborTimeEntryApproval,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Approve or reject a time entry (manager only)"""
    query = select(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.id == time_entry_id,
        QuoteLaborTimeEntry.labor_item_id == labor_item_id
    )
    result = await db.execute(query)
    time_entry = result.scalar_one_or_none()

    if not time_entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    time_entry.approved = approval.approved
    time_entry.approved_by = approval.approved_by
    time_entry.approved_at = datetime.utcnow()

    if approval.notes:
        time_entry.notes = approval.notes

    await db.commit()
    await db.refresh(time_entry)

    logger.info(f"Time entry {time_entry_id} {'approved' if approval.approved else 'rejected'} by {approval.approved_by}")

    return time_entry


# ============================================================================
# MATERIALS TRACKING ENDPOINTS
# ============================================================================

@router.post("/labor-items/{labor_item_id}/materials", response_model=QuoteLaborMaterialUsedSchema, status_code=201)
async def log_material_usage(
    labor_item_id: UUID,
    material: QuoteLaborMaterialUsedCreate,
    db: AsyncSession = Depends(get_db)
):
    """Log materials used for a labor item"""
    # Verify labor item exists
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Create material record
    new_material = QuoteLaborMaterialUsed(
        labor_item_id=labor_item_id,
        **material.model_dump(exclude={'labor_item_id'})
    )

    # Calculate total cost
    if material.unit_cost and material.quantity_used:
        new_material.total_cost = material.unit_cost * material.quantity_used

    # Calculate variance if estimated
    if material.was_estimated and material.estimated_quantity:
        new_material.quantity_variance = material.quantity_used - material.estimated_quantity

    db.add(new_material)
    await db.commit()
    await db.refresh(new_material)

    # Update labor item actual materials cost
    await _update_labor_item_actuals(db, labor_item_id)

    # Log history
    await _log_history(
        db, labor_item_id, "material_logged", None, material.material_name,
        material.recorded_by or "contractor", "contractor"
    )

    logger.info(f"Logged material usage for labor item {labor_item_id}: {material.material_name}")

    return new_material


@router.get("/labor-items/{labor_item_id}/materials", response_model=List[QuoteLaborMaterialUsedSchema])
async def list_materials_used(
    labor_item_id: UUID,
    material_category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """List all materials used for a labor item"""
    query = select(QuoteLaborMaterialUsed).where(QuoteLaborMaterialUsed.labor_item_id == labor_item_id)

    if material_category:
        query = query.where(QuoteLaborMaterialUsed.material_category == material_category)

    query = query.order_by(QuoteLaborMaterialUsed.used_date.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    materials = result.scalars().all()

    return [QuoteLaborMaterialUsedSchema.model_validate(m) for m in materials]


@router.put("/labor-items/{labor_item_id}/materials/{material_id}", response_model=QuoteLaborMaterialUsedSchema)
async def update_material_usage(
    labor_item_id: UUID,
    material_id: UUID,
    material_update: QuoteLaborMaterialUsedUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a material usage record"""
    query = select(QuoteLaborMaterialUsed).where(
        QuoteLaborMaterialUsed.id == material_id,
        QuoteLaborMaterialUsed.labor_item_id == labor_item_id
    )
    result = await db.execute(query)
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(status_code=404, detail="Material record not found")

    # Update fields
    update_data = material_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(material, field, value)

    # Recalculate total cost if quantity or unit cost changed
    if 'quantity_used' in update_data or 'unit_cost' in update_data:
        if material.unit_cost and material.quantity_used:
            material.total_cost = material.unit_cost * material.quantity_used

    await db.commit()
    await db.refresh(material)

    # Update labor item actuals
    await _update_labor_item_actuals(db, labor_item_id)

    return material


# ============================================================================
# BEFORE/AFTER PAIRS ENDPOINTS
# ============================================================================

@router.post("/labor-items/{labor_item_id}/before-after-pairs", response_model=QuoteLaborBeforeAfterPairSchema, status_code=201)
async def create_before_after_pair(
    labor_item_id: UUID,
    pair: QuoteLaborBeforeAfterPairCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a before/after photo pair for showcasing work"""
    # Verify labor item exists
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Verify photos exist
    photos_query = select(QuoteLaborItemPhoto).where(
        QuoteLaborItemPhoto.id.in_([pair.before_photo_id, pair.after_photo_id])
    )
    photos_result = await db.execute(photos_query)
    photos = photos_result.scalars().all()

    if len(photos) != 2:
        raise HTTPException(status_code=404, detail="One or both photos not found")

    # Create pair
    new_pair = QuoteLaborBeforeAfterPair(
        labor_item_id=labor_item_id,
        **pair.model_dump(exclude={'labor_item_id'})
    )

    # Calculate improvement percentage if measurements provided
    if pair.before_measurement and pair.after_measurement and pair.before_measurement != 0:
        improvement = ((pair.after_measurement - pair.before_measurement) / pair.before_measurement) * 100
        new_pair.improvement_percentage = Decimal(str(improvement))

    db.add(new_pair)
    await db.commit()
    await db.refresh(new_pair)

    logger.info(f"Created before/after pair {new_pair.id} for labor item {labor_item_id}")

    return new_pair


@router.get("/labor-items/{labor_item_id}/before-after-pairs", response_model=List[QuoteLaborBeforeAfterPairSchema])
async def list_before_after_pairs(
    labor_item_id: UUID,
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List all before/after pairs for a labor item"""
    query = select(QuoteLaborBeforeAfterPair).where(
        QuoteLaborBeforeAfterPair.labor_item_id == labor_item_id
    ).options(
        joinedload(QuoteLaborBeforeAfterPair.before_photo),
        joinedload(QuoteLaborBeforeAfterPair.after_photo)
    )

    if featured_only:
        query = query.where(QuoteLaborBeforeAfterPair.featured == True)

    query = query.order_by(QuoteLaborBeforeAfterPair.display_order)

    result = await db.execute(query)
    pairs = result.scalars().all()

    return [QuoteLaborBeforeAfterPairSchema.model_validate(p) for p in pairs]


@router.put("/labor-items/{labor_item_id}/before-after-pairs/{pair_id}/feature", response_model=QuoteLaborBeforeAfterPairSchema)
async def feature_before_after_pair(
    labor_item_id: UUID,
    pair_id: UUID,
    featured: bool = True,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Mark a before/after pair as featured for PDF/marketing"""
    query = select(QuoteLaborBeforeAfterPair).where(
        QuoteLaborBeforeAfterPair.id == pair_id,
        QuoteLaborBeforeAfterPair.labor_item_id == labor_item_id
    )
    result = await db.execute(query)
    pair = result.scalar_one_or_none()

    if not pair:
        raise HTTPException(status_code=404, detail="Before/after pair not found")

    pair.featured = featured
    await db.commit()
    await db.refresh(pair)

    logger.info(f"Before/after pair {pair_id} featured={featured}")

    return pair


# ============================================================================
# LABOR ITEM STATUS & ASSIGNMENT ENDPOINTS
# ============================================================================

@router.put("/labor-items/{labor_item_id}/assign", response_model=Dict[str, str])
async def assign_contractor(
    labor_item_id: UUID,
    assignment: QuoteLaborItemAssignment,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Assign a contractor to a labor item"""
    # Verify labor item exists
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Verify contractor exists
    contractor_query = select(Contractor).where(Contractor.id == assignment.assigned_contractor_id)
    contractor_result = await db.execute(contractor_query)
    contractor = contractor_result.scalar_one_or_none()

    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    # Update labor item
    old_contractor = labor_item.assigned_contractor_id
    labor_item.assigned_contractor_id = assignment.assigned_contractor_id
    labor_item.contractor_assigned_at = datetime.utcnow()
    labor_item.contractor_assigned_by = assignment.contractor_assigned_by
    labor_item.work_status = "assigned"

    if assignment.access_notes:
        labor_item.access_notes = assignment.access_notes

    if assignment.safety_notes:
        labor_item.safety_notes = assignment.safety_notes

    await db.commit()

    # Log history
    await _log_history(
        db, labor_item_id, "contractor_assigned",
        str(old_contractor) if old_contractor else None,
        str(assignment.assigned_contractor_id),
        assignment.contractor_assigned_by, "staff"
    )

    logger.info(f"Assigned contractor {assignment.assigned_contractor_id} to labor item {labor_item_id}")

    return {"status": "assigned", "message": f"Contractor {contractor.company_name} assigned successfully"}


@router.put("/labor-items/{labor_item_id}/status", response_model=Dict[str, str])
async def update_work_status(
    labor_item_id: UUID,
    status_update: QuoteLaborItemStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update the work status of a labor item"""
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    old_status = labor_item.work_status
    labor_item.work_status = status_update.work_status

    # Set timestamps based on status
    if status_update.work_status == "in_progress" and not labor_item.work_started_at:
        labor_item.work_started_at = datetime.utcnow()
    elif status_update.work_status == "completed":
        labor_item.work_completed_at = datetime.utcnow()

    await db.commit()

    # Log history
    await _log_history(
        db, labor_item_id, "status_change",
        old_status, status_update.work_status,
        status_update.changed_by, status_update.changed_by_type,
        status_update.status_notes
    )

    logger.info(f"Updated labor item {labor_item_id} status: {old_status} -> {status_update.work_status}")

    return {"status": "updated", "new_status": status_update.work_status}


@router.put("/labor-items/{labor_item_id}/actuals", response_model=Dict[str, str])
async def update_actuals(
    labor_item_id: UUID,
    actuals: QuoteLaborItemActuals,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Update actual costs and hours (manager approval)"""
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    # Update actuals
    labor_item.actual_hours = actuals.actual_hours
    labor_item.actual_labor_cost = actuals.actual_labor_cost
    labor_item.actual_materials_cost = actuals.actual_materials_cost
    labor_item.actual_total_cost = actuals.actual_total_cost

    # Calculate variances
    labor_item.hours_variance = actuals.actual_hours - labor_item.estimated_hours
    labor_item.cost_variance = actuals.actual_total_cost - labor_item.total_cost

    await db.commit()

    # Create note with variance explanation
    variance_note = QuoteLaborItemNote(
        labor_item_id=labor_item_id,
        note_type="completion",
        note_title="Final Cost Reconciliation",
        note_text=actuals.variance_explanation,
        created_by=auth_user.username,
        created_by_type="staff",
        is_internal=False,
        show_to_customer=True
    )
    db.add(variance_note)
    await db.commit()

    logger.info(f"Updated actuals for labor item {labor_item_id}: {actuals.actual_total_cost}")

    return {"status": "updated", "variance": str(labor_item.cost_variance)}


@router.put("/labor-items/{labor_item_id}/qc", response_model=Dict[str, str])
async def perform_qc(
    labor_item_id: UUID,
    qc: QuoteLaborItemQC,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Perform quality control check (manager only)"""
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        raise HTTPException(status_code=404, detail="Labor item not found")

    labor_item.qc_passed = qc.qc_passed
    labor_item.qc_performed_by = qc.qc_performed_by
    labor_item.qc_performed_at = datetime.utcnow()
    labor_item.qc_notes = qc.qc_notes

    if qc.qc_passed:
        labor_item.work_status = "completed"

    await db.commit()

    logger.info(f"QC performed for labor item {labor_item_id}: {'PASSED' if qc.qc_passed else 'FAILED'}")

    return {"status": "qc_complete", "passed": qc.qc_passed}


# ============================================================================
# CONTRACTOR DASHBOARD & REPORTING
# ============================================================================

@router.get("/contractors/{contractor_id}/dashboard", response_model=ContractorDashboard)
async def get_contractor_dashboard(
    contractor_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get contractor dashboard with active work, stats, and pending items"""
    # Get contractor info
    contractor_query = select(Contractor).where(Contractor.id == contractor_id)
    contractor_result = await db.execute(contractor_query)
    contractor = contractor_result.scalar_one_or_none()

    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    # Get active labor items
    active_query = select(QuoteLaborItemModel).where(
        QuoteLaborItemModel.assigned_contractor_id == contractor_id,
        QuoteLaborItemModel.work_status.in_(['assigned', 'in_progress'])
    )
    active_result = await db.execute(active_query)
    active_items = active_result.scalars().all()

    # Get completed count
    completed_query = select(func.count()).select_from(QuoteLaborItemModel).where(
        QuoteLaborItemModel.assigned_contractor_id == contractor_id,
        QuoteLaborItemModel.work_status == 'completed'
    )
    completed_result = await db.execute(completed_query)
    completed_count = completed_result.scalar()

    # Get this week's hours
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_hours_query = select(func.sum(QuoteLaborTimeEntry.duration_hours)).select_from(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor_id,
        QuoteLaborTimeEntry.work_date >= week_start
    )
    week_hours_result = await db.execute(week_hours_query)
    week_hours = week_hours_result.scalar() or Decimal("0")

    # Get this week's earnings
    week_earnings_query = select(func.sum(QuoteLaborTimeEntry.total_cost)).select_from(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor_id,
        QuoteLaborTimeEntry.work_date >= week_start,
        QuoteLaborTimeEntry.approved == True
    )
    week_earnings_result = await db.execute(week_earnings_query)
    week_earnings = week_earnings_result.scalar() or Decimal("0")

    # Get pending approvals count
    pending_query = select(func.count()).select_from(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor_id,
        QuoteLaborTimeEntry.approved == False
    )
    pending_result = await db.execute(pending_query)
    pending_count = pending_result.scalar()

    # Build active labor items progress
    active_labor_items = []
    for item in active_items:
        # Calculate progress percentage based on time entries
        time_query = select(func.sum(QuoteLaborTimeEntry.duration_hours)).select_from(QuoteLaborTimeEntry).where(
            QuoteLaborTimeEntry.labor_item_id == item.id
        )
        time_result = await db.execute(time_query)
        actual_hours = time_result.scalar() or Decimal("0")

        progress = min(100, int((actual_hours / item.estimated_hours) * 100)) if item.estimated_hours else 0

        # Get counts
        photo_count_query = select(func.count()).select_from(QuoteLaborItemPhoto).where(
            QuoteLaborItemPhoto.labor_item_id == item.id
        )
        photo_count = (await db.execute(photo_count_query)).scalar()

        note_count_query = select(func.count()).select_from(QuoteLaborItemNote).where(
            QuoteLaborItemNote.labor_item_id == item.id
        )
        note_count = (await db.execute(note_count_query)).scalar()

        time_count_query = select(func.count()).select_from(QuoteLaborTimeEntry).where(
            QuoteLaborTimeEntry.labor_item_id == item.id
        )
        time_count = (await db.execute(time_count_query)).scalar()

        active_labor_items.append(LaborItemProgress(
            labor_item_id=item.id,
            task_name=item.task_name,
            work_status=item.work_status,
            progress_percentage=progress,
            estimated_hours=item.estimated_hours,
            actual_hours=actual_hours,
            hours_variance=actual_hours - item.estimated_hours,
            estimated_cost=item.labor_subtotal,
            actual_cost=item.actual_labor_cost or Decimal("0"),
            cost_variance=(item.actual_labor_cost or Decimal("0")) - item.labor_subtotal,
            photo_count=photo_count,
            note_count=note_count,
            time_entry_count=time_count,
            last_update=item.updated_at
        ))

    # Get recent notes
    recent_notes_query = select(QuoteLaborItemNote).join(
        QuoteLaborItemModel, QuoteLaborItemNote.labor_item_id == QuoteLaborItemModel.id
    ).where(
        QuoteLaborItemModel.assigned_contractor_id == contractor_id
    ).order_by(QuoteLaborItemNote.created_at.desc()).limit(10)
    recent_notes_result = await db.execute(recent_notes_query)
    recent_notes = [QuoteLaborItemNoteSchema.model_validate(n) for n in recent_notes_result.scalars().all()]

    # Get pending time entries
    pending_time_query = select(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor_id,
        QuoteLaborTimeEntry.approved == False
    ).order_by(QuoteLaborTimeEntry.work_date.desc()).limit(10)
    pending_time_result = await db.execute(pending_time_query)
    pending_time_entries = [QuoteLaborTimeEntrySchema.model_validate(t) for t in pending_time_result.scalars().all()]

    return ContractorDashboard(
        contractor_id=contractor_id,
        contractor_name=contractor.company_name,
        active_jobs_count=len(active_items),
        completed_jobs_count=completed_count,
        total_hours_this_week=week_hours,
        total_earnings_this_week=week_earnings,
        pending_approvals_count=pending_count,
        active_labor_items=active_labor_items,
        recent_notes=recent_notes,
        pending_time_entries=pending_time_entries
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _log_history(
    db: AsyncSession,
    labor_item_id: UUID,
    change_type: str,
    old_value: Optional[str],
    new_value: str,
    changed_by: str,
    changed_by_type: str,
    change_reason: Optional[str] = None
):
    """Log a history entry for a labor item"""
    history_entry = QuoteLaborItemHistory(
        labor_item_id=labor_item_id,
        change_type=change_type,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
        changed_by_type=changed_by_type,
        change_reason=change_reason
    )
    db.add(history_entry)
    await db.commit()


async def _update_labor_item_actuals(db: AsyncSession, labor_item_id: UUID):
    """Update labor item actual costs based on time entries and materials"""
    # Get labor item
    labor_item_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.id == labor_item_id)
    labor_item_result = await db.execute(labor_item_query)
    labor_item = labor_item_result.scalar_one_or_none()

    if not labor_item:
        return

    # Calculate actual hours from time entries
    time_query = select(func.sum(QuoteLaborTimeEntry.duration_hours)).select_from(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.labor_item_id == labor_item_id
    )
    time_result = await db.execute(time_query)
    actual_hours = time_result.scalar() or Decimal("0")

    # Calculate actual labor cost from time entries
    cost_query = select(func.sum(QuoteLaborTimeEntry.total_cost)).select_from(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.labor_item_id == labor_item_id
    )
    cost_result = await db.execute(cost_query)
    actual_labor_cost = cost_result.scalar() or Decimal("0")

    # Calculate actual materials cost
    materials_query = select(func.sum(QuoteLaborMaterialUsed.total_cost)).select_from(QuoteLaborMaterialUsed).where(
        QuoteLaborMaterialUsed.labor_item_id == labor_item_id
    )
    materials_result = await db.execute(materials_query)
    actual_materials_cost = materials_result.scalar() or Decimal("0")

    # Update labor item
    labor_item.actual_hours = actual_hours
    labor_item.actual_labor_cost = actual_labor_cost
    labor_item.actual_materials_cost = actual_materials_cost
    labor_item.actual_total_cost = actual_labor_cost + actual_materials_cost

    # Calculate variances
    labor_item.hours_variance = actual_hours - labor_item.estimated_hours
    labor_item.cost_variance = labor_item.actual_total_cost - labor_item.total_cost

    await db.commit()


# ============================================================================
# MOBILE APP DASHBOARD ENDPOINTS (somni-employee integration)
# These endpoints use JWT auth and look up contractor by email/username
# ============================================================================

async def _get_contractor_for_user(db: AsyncSession, current_user: dict) -> Contractor:
    """
    Get contractor record for authenticated JWT user.
    Looks up by email or username matching contact_name.
    """
    email = current_user.get("email")
    username = current_user.get("username")

    # First try by email
    if email:
        result = await db.execute(
            select(Contractor).where(Contractor.email == email)
        )
        contractor = result.scalar_one_or_none()
        if contractor:
            return contractor

    # Then try by username matching contact_name or company_name
    if username:
        result = await db.execute(
            select(Contractor).where(
                or_(
                    Contractor.contact_name == username,
                    Contractor.company_name == username
                )
            )
        )
        contractor = result.scalar_one_or_none()
        if contractor:
            return contractor

    raise HTTPException(
        status_code=404,
        detail="No contractor profile found for this account. Contact admin to link your account."
    )


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get contractor dashboard statistics (somni-employee mobile app).

    Returns summary stats: active jobs, completed, hours, earnings.
    """
    contractor = await _get_contractor_for_user(db, current_user)

    # Get active jobs count
    active_query = select(func.count()).select_from(QuoteLaborItemModel).where(
        QuoteLaborItemModel.assigned_contractor_id == contractor.id,
        QuoteLaborItemModel.work_status.in_(['assigned', 'in_progress'])
    )
    active_result = await db.execute(active_query)
    active_jobs = active_result.scalar() or 0

    # Get completed count
    completed_query = select(func.count()).select_from(QuoteLaborItemModel).where(
        QuoteLaborItemModel.assigned_contractor_id == contractor.id,
        QuoteLaborItemModel.work_status == 'completed'
    )
    completed_result = await db.execute(completed_query)
    completed_jobs = completed_result.scalar() or 0

    # Get this week's hours
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_hours_query = select(func.sum(QuoteLaborTimeEntry.duration_hours)).select_from(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor.id,
        QuoteLaborTimeEntry.work_date >= week_start
    )
    week_hours_result = await db.execute(week_hours_query)
    week_hours = float(week_hours_result.scalar() or 0)

    # Get this week's approved earnings
    week_earnings_query = select(func.sum(QuoteLaborTimeEntry.total_cost)).select_from(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor.id,
        QuoteLaborTimeEntry.work_date >= week_start,
        QuoteLaborTimeEntry.approved == True
    )
    week_earnings_result = await db.execute(week_earnings_query)
    week_earnings = float(week_earnings_result.scalar() or 0)

    # Pending approvals
    pending_query = select(func.count()).select_from(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor.id,
        QuoteLaborTimeEntry.approved == False
    )
    pending_result = await db.execute(pending_query)
    pending_approvals = pending_result.scalar() or 0

    return {
        "contractor_id": str(contractor.id),
        "contractor_name": contractor.company_name,
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs,
        "week_hours": week_hours,
        "week_earnings": week_earnings,
        "pending_approvals": pending_approvals
    }


@router.get("/dashboard/activity")
async def get_dashboard_activity(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, le=50)
):
    """
    Get recent activity feed (somni-employee mobile app).

    Returns recent notes, photos, and time entries.
    """
    contractor = await _get_contractor_for_user(db, current_user)

    # Get recent notes
    recent_notes_query = select(QuoteLaborItemNote).join(
        QuoteLaborItemModel, QuoteLaborItemNote.labor_item_id == QuoteLaborItemModel.id
    ).where(
        QuoteLaborItemModel.assigned_contractor_id == contractor.id
    ).order_by(QuoteLaborItemNote.created_at.desc()).limit(limit // 2)
    recent_notes_result = await db.execute(recent_notes_query)
    notes = recent_notes_result.scalars().all()

    # Get recent time entries
    recent_time_query = select(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor.id
    ).order_by(QuoteLaborTimeEntry.work_date.desc()).limit(limit // 2)
    recent_time_result = await db.execute(recent_time_query)
    time_entries = recent_time_result.scalars().all()

    # Build activity feed
    activity = []

    for note in notes:
        activity.append({
            "type": "note",
            "id": str(note.id),
            "labor_item_id": str(note.labor_item_id),
            "content": note.note_text[:100] if note.note_text else "",
            "created_at": note.created_at.isoformat() if note.created_at else None
        })

    for entry in time_entries:
        activity.append({
            "type": "time_entry",
            "id": str(entry.id),
            "labor_item_id": str(entry.labor_item_id),
            "hours": float(entry.duration_hours) if entry.duration_hours else 0,
            "approved": entry.approved,
            "work_date": entry.work_date.isoformat() if entry.work_date else None
        })

    # Sort by date (most recent first)
    activity.sort(
        key=lambda x: x.get("created_at") or x.get("work_date") or "",
        reverse=True
    )

    return {
        "contractor_id": str(contractor.id),
        "activity": activity[:limit]
    }


@router.get("/dashboard/today")
async def get_dashboard_today(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get today's work schedule (somni-employee mobile app).

    Returns active labor items and today's time entries.
    """
    contractor = await _get_contractor_for_user(db, current_user)
    today = date.today()

    # Get active labor items
    active_query = select(QuoteLaborItemModel).where(
        QuoteLaborItemModel.assigned_contractor_id == contractor.id,
        QuoteLaborItemModel.work_status.in_(['assigned', 'in_progress'])
    )
    active_result = await db.execute(active_query)
    active_items = active_result.scalars().all()

    # Get today's time entries
    today_time_query = select(QuoteLaborTimeEntry).where(
        QuoteLaborTimeEntry.contractor_id == contractor.id,
        QuoteLaborTimeEntry.work_date == today
    )
    today_time_result = await db.execute(today_time_query)
    today_entries = today_time_result.scalars().all()

    # Check for active clock-in (no clock-out yet)
    active_clock = None
    for entry in today_entries:
        if entry.clock_in and not entry.clock_out:
            active_clock = {
                "id": str(entry.id),
                "labor_item_id": str(entry.labor_item_id),
                "clock_in": entry.clock_in.isoformat(),
                "location": entry.clock_in_location
            }
            break

    # Format active items
    work_items = []
    for item in active_items:
        work_items.append({
            "id": str(item.id),
            "task_name": item.task_name,
            "work_status": item.work_status,
            "estimated_hours": float(item.estimated_hours) if item.estimated_hours else 0,
            "location": None  # Would need to join with quote/property for location
        })

    # Calculate today's hours
    today_hours = sum(
        float(e.duration_hours) if e.duration_hours else 0
        for e in today_entries
    )

    return {
        "contractor_id": str(contractor.id),
        "contractor_name": contractor.company_name,
        "date": today.isoformat(),
        "work_items": work_items,
        "today_hours": today_hours,
        "active_clock_in": active_clock,
        "time_entries_today": len(today_entries)
    }
