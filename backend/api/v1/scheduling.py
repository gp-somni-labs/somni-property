"""
Scheduling API - Cal.com Integration

Provides availability checking and appointment booking for:
- Work order scheduling
- Service requests
- Move-in/move-out appointments
- Contractor availability
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timedelta
from pydantic import BaseModel, EmailStr
import logging

from db.database import get_db
from core.auth import get_auth_user, require_manager, AuthUser
from core.config import settings
from core.exceptions import CalComError, SchedulingConflictError, ServiceUnavailableError
from services.calcom_client import (
    CalcomClient, get_calcom_client, close_calcom_client,
    Booking, EventType, BookingStatus
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class AvailabilityRequest(BaseModel):
    """Request for availability check"""
    client_id: Optional[UUID] = None
    date_range_start: date
    date_range_end: date
    duration_minutes: int = 60


class AvailabilitySlot(BaseModel):
    """Available time slot"""
    start_time: datetime
    end_time: datetime
    available: bool = True


class BookingRequest(BaseModel):
    """Request to book an appointment"""
    event_type_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_time: datetime
    duration_minutes: int = 60
    attendee_email: EmailStr
    attendee_name: str
    location: Optional[str] = None
    client_id: Optional[str] = None
    work_order_id: Optional[str] = None
    booking_type: Optional[str] = None  # 'service_call', 'move_in', 'move_out', 'consultation'


class BookingResponse(BaseModel):
    """Booking confirmation"""
    booking_id: Optional[int] = None
    booking_uid: Optional[str] = None
    title: str
    start_time: datetime
    end_time: datetime
    attendees: List[dict]
    status: str
    calendar_link: Optional[str] = None
    location: Optional[str] = None


class EventTypeResponse(BaseModel):
    """Event type information"""
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    length: int  # Duration in minutes


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_calcom_client() -> CalcomClient:
    """Get configured Cal.com client or raise error if not configured."""
    if not settings.CALCOM_API_KEY:
        raise ServiceUnavailableError("Scheduling")

    return get_calcom_client(
        base_url=settings.CALCOM_URL,
        api_key=settings.CALCOM_API_KEY
    )


# ============================================================================
# ENDPOINTS - EVENT TYPES
# ============================================================================

@router.get("/event-types", response_model=List[EventTypeResponse])
async def list_event_types(
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all available event types for booking.

    Event types define the different kinds of appointments that can be scheduled.
    """
    calcom = _get_calcom_client()

    try:
        event_types = await calcom.list_event_types()
        return [
            EventTypeResponse(
                id=et.id,
                title=et.title,
                slug=et.slug,
                description=et.description,
                length=et.length
            )
            for et in event_types
        ]

    except CalComError as e:
        logger.error(f"Cal.com error listing event types: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error listing event types: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event types"
        )


# ============================================================================
# ENDPOINTS - AVAILABILITY
# ============================================================================

@router.get("/availability", response_model=List[AvailabilitySlot])
async def get_availability(
    event_type_id: int = Query(..., description="Event type ID to check availability for"),
    date_range_start: date = Query(..., description="Start date for availability"),
    date_range_end: date = Query(..., description="End date for availability"),
    timezone: str = Query("America/Los_Angeles", description="Timezone for results"),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available time slots for scheduling.

    Returns availability for the specified date range and event type.
    """
    calcom = _get_calcom_client()

    try:
        logger.info(f"Checking availability for event type {event_type_id} from {date_range_start} to {date_range_end}")

        # Get event type to know the duration
        event_type = await calcom.get_event_type(event_type_id)
        duration = event_type.length if event_type else 60

        # Get available slots
        start_datetime = datetime.combine(date_range_start, datetime.min.time())
        end_datetime = datetime.combine(date_range_end, datetime.max.time())

        available_times = await calcom.get_available_slots(
            event_type_id=event_type_id,
            start_date=start_datetime,
            end_date=end_datetime,
            timezone=timezone
        )

        # Convert to AvailabilitySlot format
        slots = [
            AvailabilitySlot(
                start_time=slot_time,
                end_time=slot_time + timedelta(minutes=duration),
                available=True
            )
            for slot_time in available_times
        ]

        return slots

    except CalComError as e:
        logger.error(f"Cal.com error getting availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error getting availability: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get availability"
        )


# ============================================================================
# ENDPOINTS - BOOKINGS
# ============================================================================

@router.post("/book", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking: BookingRequest,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new appointment booking.

    Books an appointment in Cal.com and sends confirmation emails.
    Requires manager/admin role.
    """
    calcom = _get_calcom_client()

    try:
        logger.info(f"Creating booking: {booking.title} for {booking.attendee_email}")

        # Use default event type if not specified
        event_type_id = booking.event_type_id or settings.CALCOM_DEFAULT_EVENT_TYPE_ID
        if not event_type_id:
            # Try to find or create a default event type
            event_types = await calcom.list_event_types()
            if event_types:
                event_type_id = event_types[0].id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No event types available. Please configure Cal.com event types."
                )

        # Build metadata
        metadata = {
            "source": "somniproperty",
            "created_by": auth_user.username
        }
        if booking.client_id:
            metadata["client_id"] = booking.client_id
        if booking.work_order_id:
            metadata["work_order_id"] = booking.work_order_id
        if booking.booking_type:
            metadata["booking_type"] = booking.booking_type

        # Create the booking
        result = await calcom.create_booking(
            event_type_id=event_type_id,
            start_time=booking.start_time,
            attendee_email=booking.attendee_email,
            attendee_name=booking.attendee_name,
            title=booking.title,
            description=booking.description,
            location=booking.location,
            metadata=metadata
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create booking"
            )

        return BookingResponse(
            booking_id=result.id,
            booking_uid=result.uid,
            title=result.title,
            start_time=result.start_time,
            end_time=result.end_time,
            attendees=[{"email": a["email"], "name": a["name"]} for a in result.attendees],
            status=result.status,
            location=result.location
        )

    except SchedulingConflictError as e:
        logger.warning(f"Scheduling conflict: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.message)
        )
    except CalComError as e:
        logger.error(f"Cal.com error creating booking: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create booking"
        )


@router.get("/bookings", response_model=List[BookingResponse])
async def list_bookings(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    from_date: Optional[date] = Query(None, description="Filter bookings starting after this date"),
    to_date: Optional[date] = Query(None, description="Filter bookings starting before this date"),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List bookings with optional filters.
    """
    calcom = _get_calcom_client()

    try:
        # Convert status string to enum if provided
        booking_status = None
        if status_filter:
            try:
                booking_status = BookingStatus(status_filter.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}. Valid values: PENDING, ACCEPTED, CANCELLED, REJECTED"
                )

        # Convert dates to datetime
        from_datetime = datetime.combine(from_date, datetime.min.time()) if from_date else None
        to_datetime = datetime.combine(to_date, datetime.max.time()) if to_date else None

        bookings = await calcom.list_bookings(
            status=booking_status,
            from_date=from_datetime,
            to_date=to_datetime
        )

        return [
            BookingResponse(
                booking_id=b.id,
                booking_uid=b.uid,
                title=b.title,
                start_time=b.start_time,
                end_time=b.end_time,
                attendees=[{"email": a["email"], "name": a["name"]} for a in b.attendees],
                status=b.status,
                location=b.location
            )
            for b in bookings
        ]

    except CalComError as e:
        logger.error(f"Cal.com error listing bookings: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing bookings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list bookings"
        )


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get booking details by ID."""
    calcom = _get_calcom_client()

    try:
        booking = await calcom.get_booking(booking_id)

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {booking_id} not found"
            )

        return BookingResponse(
            booking_id=booking.id,
            booking_uid=booking.uid,
            title=booking.title,
            start_time=booking.start_time,
            end_time=booking.end_time,
            attendees=[{"email": a["email"], "name": a["name"]} for a in booking.attendees],
            status=booking.status,
            location=booking.location
        )

    except CalComError as e:
        logger.error(f"Cal.com error getting booking: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting booking {booking_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get booking"
        )


@router.patch("/bookings/{booking_id}/reschedule", response_model=BookingResponse)
async def reschedule_booking(
    booking_id: int,
    new_start_time: datetime,
    reason: Optional[str] = None,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Reschedule a booking to a new time."""
    calcom = _get_calcom_client()

    try:
        booking = await calcom.reschedule_booking(
            booking_id=booking_id,
            new_start_time=new_start_time,
            reason=reason
        )

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {booking_id} not found or could not be rescheduled"
            )

        return BookingResponse(
            booking_id=booking.id,
            booking_uid=booking.uid,
            title=booking.title,
            start_time=booking.start_time,
            end_time=booking.end_time,
            attendees=[],
            status=booking.status
        )

    except SchedulingConflictError as e:
        logger.warning(f"Scheduling conflict on reschedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.message)
        )
    except CalComError as e:
        logger.error(f"Cal.com error rescheduling: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rescheduling booking {booking_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reschedule booking"
        )


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: int,
    reason: Optional[str] = None,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a booking."""
    calcom = _get_calcom_client()

    try:
        success = await calcom.cancel_booking(booking_id, reason)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {booking_id} not found or could not be cancelled"
            )

        logger.info(f"Booking {booking_id} cancelled by {auth_user.username}")

    except CalComError as e:
        logger.error(f"Cal.com error cancelling: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel booking"
        )


# ============================================================================
# ENDPOINTS - WORK ORDER SCHEDULING
# ============================================================================

@router.post("/work-orders/{work_order_id}/schedule", response_model=BookingResponse)
async def schedule_work_order(
    work_order_id: str,
    contractor_email: EmailStr,
    contractor_name: str,
    property_address: str,
    preferred_start_time: Optional[datetime] = None,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Schedule a contractor appointment for a work order.

    Automatically finds available slots and creates a booking with work order metadata.
    """
    calcom = _get_calcom_client()

    try:
        booking = await calcom.schedule_work_order(
            work_order_id=work_order_id,
            work_order_title=f"Work Order {work_order_id}",
            work_order_description=f"Scheduled service call for work order {work_order_id}",
            contractor_email=contractor_email,
            contractor_name=contractor_name,
            property_address=property_address,
            preferred_start_time=preferred_start_time
        )

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to schedule work order"
            )

        return BookingResponse(
            booking_id=booking.id,
            booking_uid=booking.uid,
            title=booking.title,
            start_time=booking.start_time,
            end_time=booking.end_time,
            attendees=[{"email": a["email"], "name": a["name"]} for a in booking.attendees],
            status=booking.status,
            location=booking.location
        )

    except CalComError as e:
        logger.error(f"Cal.com error scheduling work order: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error scheduling work order {work_order_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule work order"
        )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def scheduling_health():
    """Health check for scheduling service."""
    calcom_configured = bool(settings.CALCOM_API_KEY)

    health_status = {
        "status": "healthy" if calcom_configured else "unconfigured",
        "service": "scheduling",
        "calcom_url": settings.CALCOM_URL,
        "calcom_configured": calcom_configured,
        "timestamp": datetime.utcnow().isoformat()
    }

    # If configured, try to ping Cal.com
    if calcom_configured:
        try:
            calcom = _get_calcom_client()
            event_types = await calcom.list_event_types()
            health_status["calcom_status"] = "connected"
            health_status["event_types_count"] = len(event_types)
        except Exception as e:
            health_status["calcom_status"] = "error"
            health_status["calcom_error"] = str(e)
            health_status["status"] = "degraded"

    return health_status
