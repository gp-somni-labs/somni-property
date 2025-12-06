"""
Push Notification Service using Firebase Cloud Messaging (FCM)

Handles sending push notifications to contractor mobile apps for:
- Job assignments
- Time entry status updates
- Photo upload requests
- Message responses from managers
- Cost variance alerts
- Work approval notifications
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Firebase Cloud Messaging service for push notifications"""

    def __init__(self):
        self.initialized = False
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if already initialized
            if firebase_admin._apps:
                self.initialized = True
                return

            # Get service account credentials from environment
            firebase_creds_path = os.getenv('FIREBASE_CREDENTIALS_PATH')

            if not firebase_creds_path:
                logger.warning("Firebase credentials not configured. Push notifications disabled.")
                return

            # Initialize Firebase
            cred = credentials.Certificate(firebase_creds_path)
            firebase_admin.initialize_app(cred)

            self.initialized = True
            logger.info("Firebase Cloud Messaging initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.initialized = False

    def send_notification(
        self,
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Send push notification to a single device.

        Args:
            fcm_token: Device FCM registration token
            title: Notification title
            body: Notification body text
            data: Additional data payload (all values must be strings)
            image_url: Optional image URL for rich notification

        Returns:
            Message ID if successful, None otherwise
        """
        if not self.initialized:
            logger.error("Firebase not initialized")
            return None

        try:
            # Build notification message
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )

            # Build message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=fcm_token,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#2563eb',  # Primary blue
                        sound='default',
                        channel_id='job_updates'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body
                            )
                        )
                    )
                )
            )

            # Send message
            response = messaging.send(message)
            logger.info(f"Push notification sent successfully: {response}")
            return response

        except firebase_admin.exceptions.InvalidArgumentError as e:
            logger.error(f"Invalid FCM token: {e}")
            return None
        except firebase_admin.exceptions.UnavailableError as e:
            logger.error(f"FCM service unavailable: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return None

    def send_multicast(
        self,
        fcm_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to multiple devices.

        Args:
            fcm_tokens: List of device FCM tokens
            title: Notification title
            body: Notification body
            data: Additional data payload

        Returns:
            Dict with success/failure counts and responses
        """
        if not self.initialized:
            return {'success': 0, 'failure': len(fcm_tokens)}

        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                tokens=fcm_tokens,
                android=messaging.AndroidConfig(priority='high'),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound='default', badge=1)
                    )
                )
            )

            response = messaging.send_multicast(message)

            logger.info(
                f"Sent multicast notification: {response.success_count} success, "
                f"{response.failure_count} failure"
            )

            return {
                'success': response.success_count,
                'failure': response.failure_count,
                'responses': response.responses
            }

        except Exception as e:
            logger.error(f"Error sending multicast notification: {e}")
            return {'success': 0, 'failure': len(fcm_tokens)}

    # Template methods for contractor notifications

    def notify_job_assigned(
        self,
        fcm_token: str,
        task_description: str,
        quote_id: str,
        labor_item_id: str,
        estimated_hours: float
    ) -> Optional[str]:
        """Notify contractor of new job assignment"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="New Job Assigned! 🔧",
            body=f"{task_description} - Est. {estimated_hours} hours",
            data={
                'type': 'job_assigned',
                'labor_item_id': labor_item_id,
                'quote_id': quote_id,
                'action': 'open_job_detail'
            }
        )

    def notify_time_entry_approved(
        self,
        fcm_token: str,
        date: str,
        hours: float,
        amount: float,
        time_entry_id: str
    ) -> Optional[str]:
        """Notify contractor that time entry was approved"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="Time Entry Approved ✓",
            body=f"{date}: {hours} hours = ${amount:.2f}",
            data={
                'type': 'time_approved',
                'time_entry_id': time_entry_id,
                'action': 'open_time_entries'
            }
        )

    def notify_time_entry_rejected(
        self,
        fcm_token: str,
        date: str,
        reason: str,
        time_entry_id: str
    ) -> Optional[str]:
        """Notify contractor that time entry was rejected"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="Time Entry Rejected ❌",
            body=f"{date} - Reason: {reason}",
            data={
                'type': 'time_rejected',
                'time_entry_id': time_entry_id,
                'action': 'open_time_entries'
            }
        )

    def notify_manager_response(
        self,
        fcm_token: str,
        task_description: str,
        response: str,
        labor_item_id: str,
        note_id: str
    ) -> Optional[str]:
        """Notify contractor of manager's response to their question"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="Manager Response 💬",
            body=f"{task_description}: {response[:100]}",
            data={
                'type': 'manager_response',
                'labor_item_id': labor_item_id,
                'note_id': note_id,
                'action': 'open_communication'
            }
        )

    def notify_photo_upload_request(
        self,
        fcm_token: str,
        task_description: str,
        photo_type: str,
        labor_item_id: str
    ) -> Optional[str]:
        """Request contractor to upload specific photo type"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="Photo Upload Request 📸",
            body=f"Please upload {photo_type} photos for {task_description}",
            data={
                'type': 'photo_request',
                'labor_item_id': labor_item_id,
                'photo_type': photo_type,
                'action': 'open_camera'
            }
        )

    def notify_work_approved(
        self,
        fcm_token: str,
        task_description: str,
        total_amount: float,
        labor_item_id: str
    ) -> Optional[str]:
        """Notify contractor that work was approved"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="Work Approved! 🎉",
            body=f"{task_description} - Total payment: ${total_amount:.2f}",
            data={
                'type': 'work_approved',
                'labor_item_id': labor_item_id,
                'action': 'open_job_detail'
            }
        )

    def notify_materials_approved(
        self,
        fcm_token: str,
        task_description: str,
        materials_count: int,
        total_cost: float,
        labor_item_id: str
    ) -> Optional[str]:
        """Notify contractor that logged materials were approved"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="Materials Approved ✓",
            body=f"{materials_count} items totaling ${total_cost:.2f} approved",
            data={
                'type': 'materials_approved',
                'labor_item_id': labor_item_id,
                'action': 'open_materials'
            }
        )

    def notify_clock_out_reminder(
        self,
        fcm_token: str,
        task_description: str,
        hours_elapsed: float,
        labor_item_id: str
    ) -> Optional[str]:
        """Remind contractor to clock out"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="Clock Out Reminder ⏰",
            body=f"You've been clocked in for {hours_elapsed:.1f} hours. Don't forget to clock out!",
            data={
                'type': 'clock_out_reminder',
                'labor_item_id': labor_item_id,
                'action': 'open_time_clock'
            }
        )

    def notify_new_note(
        self,
        fcm_token: str,
        author: str,
        message: str,
        labor_item_id: str,
        note_id: str,
        requires_response: bool = False
    ) -> Optional[str]:
        """Notify contractor of new note/message"""
        title = "New Message 📩" if not requires_response else "Question from Manager ❓"

        return self.send_notification(
            fcm_token=fcm_token,
            title=title,
            body=f"{author}: {message[:100]}",
            data={
                'type': 'new_note',
                'labor_item_id': labor_item_id,
                'note_id': note_id,
                'requires_response': str(requires_response),
                'action': 'open_communication'
            }
        )

    def notify_job_status_change(
        self,
        fcm_token: str,
        task_description: str,
        new_status: str,
        labor_item_id: str
    ) -> Optional[str]:
        """Notify contractor of job status change"""
        status_messages = {
            'in_progress': 'Job started',
            'completed': 'Job marked as completed',
            'approved': 'Job approved by manager',
            'on_hold': 'Job put on hold'
        }

        return self.send_notification(
            fcm_token=fcm_token,
            title="Job Status Updated",
            body=f"{task_description}: {status_messages.get(new_status, new_status)}",
            data={
                'type': 'status_change',
                'labor_item_id': labor_item_id,
                'new_status': new_status,
                'action': 'open_job_detail'
            }
        )

    def notify_daily_summary(
        self,
        fcm_token: str,
        active_jobs: int,
        hours_today: float,
        earnings_today: float
    ) -> Optional[str]:
        """Send daily summary to contractor"""
        return self.send_notification(
            fcm_token=fcm_token,
            title="Daily Summary 📊",
            body=f"Active: {active_jobs} jobs | Today: {hours_today} hrs, ${earnings_today:.2f}",
            data={
                'type': 'daily_summary',
                'action': 'open_dashboard'
            }
        )

    # Topic-based notifications for broadcasts

    def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Send notification to all devices subscribed to a topic.

        Topics examples:
        - 'all_contractors' - Broadcast to all contractors
        - 'region_north' - Contractors in north region
        - 'emergency' - Emergency notifications
        """
        if not self.initialized:
            return None

        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                topic=topic,
                android=messaging.AndroidConfig(priority='high'),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound='default')
                    )
                )
            )

            response = messaging.send(message)
            logger.info(f"Topic notification sent to {topic}: {response}")
            return response

        except Exception as e:
            logger.error(f"Error sending topic notification: {e}")
            return None

    def subscribe_to_topic(self, fcm_tokens: List[str], topic: str) -> Dict[str, int]:
        """Subscribe devices to a topic"""
        if not self.initialized:
            return {'success': 0, 'failure': len(fcm_tokens)}

        try:
            response = messaging.subscribe_to_topic(fcm_tokens, topic)
            logger.info(f"Subscribed {response.success_count} devices to {topic}")

            return {
                'success': response.success_count,
                'failure': response.failure_count
            }

        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")
            return {'success': 0, 'failure': len(fcm_tokens)}

    def unsubscribe_from_topic(self, fcm_tokens: List[str], topic: str) -> Dict[str, int]:
        """Unsubscribe devices from a topic"""
        if not self.initialized:
            return {'success': 0, 'failure': len(fcm_tokens)}

        try:
            response = messaging.unsubscribe_from_topic(fcm_tokens, topic)
            logger.info(f"Unsubscribed {response.success_count} devices from {topic}")

            return {
                'success': response.success_count,
                'failure': response.failure_count
            }

        except Exception as e:
            logger.error(f"Error unsubscribing from topic: {e}")
            return {'success': 0, 'failure': len(fcm_tokens)}


# Global instance
push_notification_service = PushNotificationService()


# Helper function to get contractor FCM token from database
async def get_contractor_fcm_token(contractor_id: uuid.UUID, db: AsyncSession) -> Optional[str]:
    """Get contractor's FCM token from database"""
    try:
        from db.models import ServiceContractor

        query = select(ServiceContractor).where(ServiceContractor.id == contractor_id)
        result = await db.execute(query)
        contractor = result.scalar_one_or_none()

        if contractor:
            # Assuming fcm_token field exists in ServiceContractor model
            return getattr(contractor, 'fcm_token', None)

        return None

    except Exception as e:
        logger.error(f"Error getting contractor FCM token: {e}")
        return None


# Combined notification function (SMS + Push)
async def notify_contractor(
    contractor_id: uuid.UUID,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, str]] = None,
    db: AsyncSession = None,
    send_sms: bool = True,
    send_push: bool = True
) -> Dict[str, bool]:
    """
    Send both SMS and push notification to contractor.

    Args:
        contractor_id: Contractor UUID
        notification_type: Type of notification (for routing)
        title: Notification title (for push)
        message: Notification body/message
        data: Additional data payload (for push)
        db: Database session
        send_sms: Whether to send SMS
        send_push: Whether to send push notification

    Returns:
        Dict with SMS and push notification success status
    """
    results = {'sms_sent': False, 'push_sent': False}

    # Get contractor info
    try:
        from db.models import ServiceContractor

        query = select(ServiceContractor).where(ServiceContractor.id == contractor_id)
        result = await db.execute(query)
        contractor = result.scalar_one_or_none()

        if not contractor:
            logger.error(f"Contractor {contractor_id} not found")
            return results

        # Send SMS
        if send_sms and contractor.phone:
            from services.sms_service import send_sms_to_contractor
            sms_sent = await send_sms_to_contractor(contractor_id, message, db)
            results['sms_sent'] = sms_sent

        # Send Push Notification
        if send_push:
            fcm_token = getattr(contractor, 'fcm_token', None)
            if fcm_token:
                push_response = push_notification_service.send_notification(
                    fcm_token=fcm_token,
                    title=title,
                    body=message,
                    data=data
                )
                results['push_sent'] = push_response is not None

        return results

    except Exception as e:
        logger.error(f"Error notifying contractor: {e}")
        return results
