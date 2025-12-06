"""
Cal.com Integration Client for SomniProperty

Integrates with self-hosted Cal.com (appointment scheduling) for:
- Auto-scheduling contractor appointments for approved work orders
- Managing contractor availability
- Sending appointment confirmations and reminders
- Syncing calendar events with property managers
- Tenant move-in/move-out appointments

Cal.com Service: calcom.utilities.svc.cluster.local:3000
Documentation: https://cal.com/docs
API Docs: https://cal.com/docs/api-reference
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BookingStatus(Enum):
    """Cal.com booking status"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class EventType(BaseModel):
    """Cal.com event type (booking page)"""
    id: Optional[int] = None
    title: str
    slug: str
    description: Optional[str] = None
    length: int  # Duration in minutes
    locations: Optional[List[Dict[str, str]]] = []
    hidden: bool = False
    position: int = 0
    user_id: Optional[int] = None


class Booking(BaseModel):
    """Cal.com booking/appointment"""
    id: Optional[int] = None
    uid: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[Dict[str, str]]  # [{"email": "...", "name": "..."}]
    event_type_id: int
    status: str = BookingStatus.PENDING.value
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class Availability(BaseModel):
    """Cal.com availability/schedule"""
    id: Optional[int] = None
    name: str
    timezone: str = "America/Chicago"
    schedule: List[Dict[str, Any]]  # Day-specific availability


class CalcomClient:
    """Client for interacting with Cal.com API"""

    def __init__(
        self,
        base_url: str = "http://calcom.utilities.svc.cluster.local:3000",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Cal.com client

        Args:
            base_url: Cal.com service URL
            api_key: Cal.com API key (generate in Settings → Developer)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
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
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # ========================================
    # Event Type Management
    # ========================================

    async def create_event_type(
        self,
        title: str,
        slug: str,
        length: int,
        description: Optional[str] = None,
        locations: Optional[List[Dict[str, str]]] = None
    ) -> Optional[EventType]:
        """
        Create an event type (booking page)

        Use for different appointment types:
        - "Contractor Work Order" (2 hours)
        - "Property Showing" (30 min)
        - "Tenant Move-In Inspection" (1 hour)
        - "Emergency Repair" (flexible)

        Args:
            title: Event type title
            slug: URL slug (e.g., "contractor-work-order")
            length: Duration in minutes
            description: Event description
            locations: List of location options [{"type": "address", "address": "..."}]

        Returns:
            Created event type or None on failure
        """
        try:
            payload = {
                "title": title,
                "slug": slug,
                "length": length,
                "description": description or "",
                "locations": locations or [{"type": "inPerson"}],
                "hidden": False
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/event-types",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                event_type = data.get("event_type", data)
                return EventType(
                    id=event_type.get("id"),
                    title=event_type.get("title"),
                    slug=event_type.get("slug"),
                    description=event_type.get("description"),
                    length=event_type.get("length"),
                    locations=event_type.get("locations", [])
                )
            else:
                logger.error(f"Failed to create event type: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating event type: {e}")
            return None

    async def get_event_type(self, event_type_id: int) -> Optional[EventType]:
        """Get event type by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/event-types/{event_type_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                event_type = data.get("event_type", data)
                return EventType(
                    id=event_type.get("id"),
                    title=event_type.get("title"),
                    slug=event_type.get("slug"),
                    description=event_type.get("description"),
                    length=event_type.get("length"),
                    locations=event_type.get("locations", [])
                )
            return None

        except Exception as e:
            logger.error(f"Error getting event type: {e}")
            return None

    async def list_event_types(self) -> List[EventType]:
        """List all event types"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/event-types",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                event_types = data.get("event_types", data)
                return [
                    EventType(
                        id=et.get("id"),
                        title=et.get("title"),
                        slug=et.get("slug"),
                        description=et.get("description"),
                        length=et.get("length"),
                        locations=et.get("locations", [])
                    )
                    for et in event_types
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing event types: {e}")
            return []

    # ========================================
    # Booking Management
    # ========================================

    async def create_booking(
        self,
        event_type_id: int,
        start_time: datetime,
        attendee_email: str,
        attendee_name: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Booking]:
        """
        Create a booking/appointment

        Use for:
        - Scheduling contractors for approved work orders
        - Booking property showings
        - Setting move-in/move-out appointments

        Args:
            event_type_id: Event type ID
            start_time: Appointment start time
            attendee_email: Attendee email
            attendee_name: Attendee name
            title: Booking title (optional, defaults to event type title)
            description: Booking description
            location: Location (address or "phone" or "video")
            metadata: Additional metadata (e.g., {"work_order_id": "WO-123", "unit": "204"})

        Returns:
            Created booking or None on failure
        """
        try:
            # Get event type to calculate end time
            event_type = await self.get_event_type(event_type_id)
            if not event_type:
                logger.error(f"Event type {event_type_id} not found")
                return None

            end_time = start_time + timedelta(minutes=event_type.length)

            payload = {
                "eventTypeId": event_type_id,
                "start": start_time.isoformat(),
                "responses": {
                    "name": attendee_name,
                    "email": attendee_email,
                    "location": location or "inPerson",
                    "notes": description or ""
                },
                "timeZone": "America/Chicago",
                "language": "en",
                "metadata": metadata or {}
            }

            if title:
                payload["title"] = title

            response = await self.client.post(
                f"{self.base_url}/api/v1/bookings",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                booking = data.get("booking", data)
                return Booking(
                    id=booking.get("id"),
                    uid=booking.get("uid"),
                    title=booking.get("title", ""),
                    description=description,
                    start_time=start_time,
                    end_time=end_time,
                    attendees=[{"email": attendee_email, "name": attendee_name}],
                    event_type_id=event_type_id,
                    status=booking.get("status", BookingStatus.PENDING.value),
                    location=location,
                    metadata=metadata
                )
            else:
                logger.error(f"Failed to create booking: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            return None

    async def get_booking(self, booking_id: int) -> Optional[Booking]:
        """Get booking by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/bookings/{booking_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                booking = data.get("booking", data)
                return Booking(
                    id=booking.get("id"),
                    uid=booking.get("uid"),
                    title=booking.get("title", ""),
                    description=booking.get("description"),
                    start_time=datetime.fromisoformat(booking.get("startTime")),
                    end_time=datetime.fromisoformat(booking.get("endTime")),
                    attendees=booking.get("attendees", []),
                    event_type_id=booking.get("eventTypeId"),
                    status=booking.get("status", BookingStatus.PENDING.value),
                    location=booking.get("location"),
                    metadata=booking.get("metadata", {})
                )
            return None

        except Exception as e:
            logger.error(f"Error getting booking: {e}")
            return None

    async def list_bookings(
        self,
        status: Optional[BookingStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Booking]:
        """
        List bookings

        Args:
            status: Filter by status
            from_date: Filter bookings starting after this date
            to_date: Filter bookings starting before this date

        Returns:
            List of bookings
        """
        try:
            params = {}
            if status:
                params["status"] = status.value
            if from_date:
                params["afterStart"] = from_date.isoformat()
            if to_date:
                params["beforeEnd"] = to_date.isoformat()

            response = await self.client.get(
                f"{self.base_url}/api/v1/bookings",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                bookings = data.get("bookings", data)
                return [
                    Booking(
                        id=booking.get("id"),
                        uid=booking.get("uid"),
                        title=booking.get("title", ""),
                        description=booking.get("description"),
                        start_time=datetime.fromisoformat(booking.get("startTime")),
                        end_time=datetime.fromisoformat(booking.get("endTime")),
                        attendees=booking.get("attendees", []),
                        event_type_id=booking.get("eventTypeId"),
                        status=booking.get("status", BookingStatus.PENDING.value),
                        location=booking.get("location"),
                        metadata=booking.get("metadata", {})
                    )
                    for booking in bookings
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing bookings: {e}")
            return []

    async def cancel_booking(self, booking_id: int, reason: Optional[str] = None) -> bool:
        """
        Cancel a booking

        Args:
            booking_id: Booking ID
            reason: Cancellation reason

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "id": booking_id,
                "reason": reason or "Cancelled by property manager"
            }

            response = await self.client.delete(
                f"{self.base_url}/api/v1/bookings/{booking_id}",
                headers=self._headers(),
                json=payload
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error cancelling booking: {e}")
            return False

    async def reschedule_booking(
        self,
        booking_id: int,
        new_start_time: datetime,
        reason: Optional[str] = None
    ) -> Optional[Booking]:
        """
        Reschedule a booking

        Args:
            booking_id: Booking ID
            new_start_time: New start time
            reason: Reschedule reason

        Returns:
            Updated booking or None on failure
        """
        try:
            payload = {
                "start": new_start_time.isoformat(),
                "rescheduledReason": reason or "Rescheduled by property manager"
            }

            response = await self.client.patch(
                f"{self.base_url}/api/v1/bookings/{booking_id}",
                headers=self._headers(),
                json=payload
            )

            if response.status_code == 200:
                return await self.get_booking(booking_id)
            else:
                logger.error(f"Failed to reschedule booking: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error rescheduling booking: {e}")
            return None

    # ========================================
    # Availability Management
    # ========================================

    async def get_available_slots(
        self,
        event_type_id: int,
        start_date: datetime,
        end_date: datetime,
        timezone: str = "America/Chicago"
    ) -> List[datetime]:
        """
        Get available time slots for booking

        Use for:
        - Showing contractors available appointment times
        - Auto-suggesting appointment times

        Args:
            event_type_id: Event type ID
            start_date: Start of date range
            end_date: End of date range
            timezone: Timezone

        Returns:
            List of available start times
        """
        try:
            params = {
                "eventTypeId": event_type_id,
                "startTime": start_date.isoformat(),
                "endTime": end_date.isoformat(),
                "timeZone": timezone
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/slots",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                slots = data.get("slots", {})

                # Flatten slots by date
                available_times = []
                for date, times in slots.items():
                    for time_obj in times:
                        available_times.append(datetime.fromisoformat(time_obj.get("time")))

                return available_times
            return []

        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []

    # ========================================
    # Work Order Integration
    # ========================================

    async def schedule_work_order(
        self,
        work_order_id: str,
        work_order_title: str,
        work_order_description: str,
        contractor_email: str,
        contractor_name: str,
        property_address: str,
        preferred_start_time: Optional[datetime] = None,
        event_type_id: Optional[int] = None
    ) -> Optional[Booking]:
        """
        Schedule a contractor appointment for a work order

        Automatically:
        - Finds or creates appropriate event type
        - Suggests available time slots if no preferred time
        - Creates booking with work order metadata
        - Sends confirmation email to contractor

        Args:
            work_order_id: SomniProperty work order ID
            work_order_title: Work order title
            work_order_description: Work order description
            contractor_email: Contractor email
            contractor_name: Contractor name
            property_address: Property address
            preferred_start_time: Preferred appointment time (or None for next available)
            event_type_id: Event type ID (or None to use default "Contractor Work Order")

        Returns:
            Created booking or None on failure
        """
        try:
            # Find or create "Contractor Work Order" event type
            if not event_type_id:
                event_types = await self.list_event_types()
                contractor_event = next(
                    (et for et in event_types if "contractor" in et.title.lower()),
                    None
                )

                if not contractor_event:
                    contractor_event = await self.create_event_type(
                        title="Contractor Work Order",
                        slug="contractor-work-order",
                        length=120,  # 2 hours default
                        description="Scheduled contractor appointment for property maintenance"
                    )

                if not contractor_event:
                    logger.error("Failed to find or create contractor event type")
                    return None

                event_type_id = contractor_event.id

            # Determine appointment time
            if not preferred_start_time:
                # Get next available slot (tomorrow, 9 AM)
                tomorrow = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
                available_slots = await self.get_available_slots(
                    event_type_id=event_type_id,
                    start_date=tomorrow,
                    end_date=tomorrow + timedelta(days=7)  # Look ahead 1 week
                )

                if available_slots:
                    preferred_start_time = available_slots[0]
                else:
                    # Default to tomorrow 9 AM if no slots available
                    preferred_start_time = tomorrow

            # Create booking
            booking = await self.create_booking(
                event_type_id=event_type_id,
                start_time=preferred_start_time,
                attendee_email=contractor_email,
                attendee_name=contractor_name,
                title=f"Work Order: {work_order_title}",
                description=work_order_description,
                location=property_address,
                metadata={
                    "work_order_id": work_order_id,
                    "source": "somniproperty",
                    "type": "contractor_appointment"
                }
            )

            return booking

        except Exception as e:
            logger.error(f"Error scheduling work order: {e}")
            return None


# ========================================
# Singleton instance management
# ========================================

_calcom_client: Optional[CalcomClient] = None


def get_calcom_client(
    base_url: str = "http://calcom.utilities.svc.cluster.local:3000",
    api_key: Optional[str] = None
) -> CalcomClient:
    """Get singleton Cal.com client instance"""
    global _calcom_client
    if _calcom_client is None:
        _calcom_client = CalcomClient(base_url=base_url, api_key=api_key)
    return _calcom_client


async def close_calcom_client():
    """Close singleton Cal.com client"""
    global _calcom_client
    if _calcom_client:
        await _calcom_client.close()
        _calcom_client = None
