"""
MQTT Watchdog Service
Monitors MQTT connection health and handles automatic reconnection
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class MQTTWatchdog:
    """
    MQTT Connection Watchdog

    Responsibilities:
    - Monitor MQTT connection status
    - Attempt automatic reconnection on failure
    - Create alerts for prolonged downtime
    - Track reconnection attempts and success/failure rates
    """

    def __init__(self):
        self.running = False
        self.last_check: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10  # Before giving up temporarily
        self.alert_threshold_minutes = 5  # Alert after 5 minutes of downtime
        self.check_interval_seconds = 60  # Check every minute
        self.start_time: Optional[datetime] = None

        # Downtime tracking
        self.downtime_started: Optional[datetime] = None
        self.total_reconnections = 0
        self.successful_reconnections = 0
        self.failed_reconnections = 0

    async def start(self):
        """Start the MQTT watchdog monitoring loop"""
        if self.running:
            logger.warning("MQTT watchdog is already running")
            return

        self.running = True
        self.start_time = datetime.utcnow()
        logger.info("🐕 MQTT Watchdog started")

        # Start monitoring loop in background
        asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop the MQTT watchdog"""
        self.running = False
        logger.info("MQTT Watchdog stopped")

    async def _monitor_loop(self):
        """Main monitoring loop - checks MQTT connection periodically"""
        while self.running:
            try:
                await asyncio.sleep(self.check_interval_seconds)
                await self._check_mqtt_health()
                self.last_check = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error in MQTT watchdog monitoring loop: {e}", exc_info=True)
                # Continue running even if there's an error
                await asyncio.sleep(5)

    async def _check_mqtt_health(self):
        """Check MQTT connection health and take action if needed"""
        try:
            from services.mqtt_client import mqtt_service

            if mqtt_service.is_connected():
                # MQTT is healthy
                self.last_heartbeat = datetime.utcnow()

                # Reset downtime tracking if we were previously down
                if self.downtime_started is not None:
                    downtime_duration = (datetime.utcnow() - self.downtime_started).total_seconds()
                    logger.info(f"✅ MQTT connection restored after {downtime_duration:.1f} seconds")
                    self.downtime_started = None

                    # Resolve any open MQTT alerts
                    await self._resolve_mqtt_alert()

                # Reset reconnection counter on successful connection
                if self.reconnect_attempts > 0:
                    self.successful_reconnections += 1
                    logger.info(f"MQTT reconnection successful (attempt {self.reconnect_attempts})")
                    self.reconnect_attempts = 0

            else:
                # MQTT is down - handle reconnection
                await self._handle_mqtt_down()

        except Exception as e:
            logger.error(f"Error checking MQTT health: {e}", exc_info=True)

    async def _handle_mqtt_down(self):
        """Handle MQTT connection failure"""
        # Start tracking downtime
        if self.downtime_started is None:
            self.downtime_started = datetime.utcnow()
            logger.warning("⚠️  MQTT connection lost")

        # Calculate downtime duration
        downtime_minutes = self._calculate_downtime_minutes()

        # Create alert if downtime exceeds threshold
        if downtime_minutes >= self.alert_threshold_minutes:
            await self._create_mqtt_alert(downtime_minutes)

        # Attempt reconnection if we haven't exceeded max attempts
        if self.reconnect_attempts < self.max_reconnect_attempts:
            await self._attempt_reconnect()
        else:
            # Exceeded max attempts - wait longer before resetting counter
            if downtime_minutes % 30 == 0:  # Every 30 minutes
                logger.warning(
                    f"MQTT still disconnected after {self.max_reconnect_attempts} attempts. "
                    f"Downtime: {downtime_minutes} minutes. Will keep trying..."
                )
                # Reset counter to try again
                self.reconnect_attempts = 0

    def _calculate_downtime_minutes(self) -> float:
        """Calculate how long MQTT has been down (in minutes)"""
        if self.downtime_started is None:
            return 0.0

        downtime = datetime.utcnow() - self.downtime_started
        return downtime.total_seconds() / 60

    async def _attempt_reconnect(self):
        """Attempt to reconnect to MQTT broker with exponential backoff"""
        from services.mqtt_client import mqtt_service

        self.reconnect_attempts += 1
        self.total_reconnections += 1

        # Exponential backoff: 2^attempt seconds, max 5 minutes (300s)
        backoff_seconds = min(2 ** self.reconnect_attempts, 300)

        logger.warning(
            f"🔄 MQTT reconnect attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} "
            f"(waiting {backoff_seconds}s with exponential backoff)"
        )

        await asyncio.sleep(backoff_seconds)

        try:
            # Attempt reconnection
            await mqtt_service.connect()
            logger.info("✅ MQTT reconnected successfully")

        except Exception as e:
            self.failed_reconnections += 1
            logger.error(f"❌ MQTT reconnect attempt {self.reconnect_attempts} failed: {e}")

            # If this was the last attempt, log a more severe warning
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                logger.error(
                    f"⚠️  Maximum reconnection attempts ({self.max_reconnect_attempts}) reached. "
                    "Will retry after cooldown period."
                )

    async def _create_mqtt_alert(self, downtime_minutes: float):
        """
        Create a system alert for MQTT downtime
        Integrates with the alerts system to notify administrators
        """
        try:
            from db.database import get_db
            from db.models import Alert
            from sqlalchemy import select

            # Only create one alert per downtime event (check if alert already exists)
            async for db in get_db():
                # Check if we already created an alert for this downtime
                result = await db.execute(
                    select(Alert)
                    .where(Alert.category == 'mqtt')
                    .where(Alert.source == 'system')
                    .where(Alert.status == 'open')
                    .order_by(Alert.occurred_at.desc())
                    .limit(1)
                )
                existing_alert = result.scalar_one_or_none()

                if existing_alert:
                    # Update existing alert with current downtime
                    # Create a new dict to avoid SQLAlchemy JSON column mutation issues
                    metadata = dict(existing_alert.alert_metadata) if existing_alert.alert_metadata else {}
                    metadata["downtime_minutes"] = downtime_minutes
                    metadata["reconnect_attempts"] = self.reconnect_attempts
                    metadata["last_check"] = datetime.utcnow().isoformat()
                    existing_alert.alert_metadata = metadata
                    await db.commit()
                    logger.debug(f"Updated existing MQTT alert (downtime: {downtime_minutes:.1f} min)")

                else:
                    # Create new alert
                    severity = "warning" if downtime_minutes < 15 else "critical"
                    alert = Alert(
                        severity=severity,
                        source="system",
                        category="mqtt",
                        message=(
                            f"MQTT broker connection has been down for {downtime_minutes:.1f} minutes. "
                            f"Attempted {self.reconnect_attempts} reconnections."
                        ),
                        entity_id="mqtt_broker",
                        alert_metadata={
                            "downtime_minutes": downtime_minutes,
                            "reconnect_attempts": self.reconnect_attempts,
                            "broker": "mqtt_service",
                        }
                    )
                    db.add(alert)
                    await db.commit()

                    logger.warning(
                        f"🚨 Created MQTT downtime alert: {downtime_minutes:.1f} minutes, "
                        f"{self.reconnect_attempts} reconnect attempts"
                    )

                break

        except Exception as e:
            logger.error(f"Failed to create MQTT alert: {e}", exc_info=True)

    async def _resolve_mqtt_alert(self):
        """Resolve MQTT downtime alert when connection is restored"""
        try:
            from db.database import get_db
            from db.models import Alert
            from sqlalchemy import select

            async for db in get_db():
                # Find unresolved MQTT alerts
                result = await db.execute(
                    select(Alert)
                    .where(Alert.category == 'mqtt')
                    .where(Alert.source == 'system')
                    .where(Alert.status == 'open')
                )
                alerts = result.scalars().all()

                # Resolve all unresolved MQTT alerts
                for alert in alerts:
                    alert.status = 'resolved'
                    alert.acknowledged_at = datetime.utcnow()
                    # Create a new dict to avoid SQLAlchemy JSON column mutation issues
                    metadata = dict(alert.alert_metadata) if alert.alert_metadata else {}
                    metadata["resolution"] = "MQTT connection restored"
                    metadata["resolved_at"] = datetime.utcnow().isoformat()
                    alert.alert_metadata = metadata

                await db.commit()

                if alerts:
                    logger.info(f"✅ Resolved {len(alerts)} MQTT downtime alert(s)")

                break

        except Exception as e:
            logger.error(f"Failed to resolve MQTT alert: {e}", exc_info=True)

    def get_stats(self) -> dict:
        """Get watchdog statistics for monitoring"""
        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

        downtime = None
        if self.downtime_started:
            downtime = (datetime.utcnow() - self.downtime_started).total_seconds()

        return {
            "running": self.running,
            "uptime_seconds": uptime,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "current_downtime_seconds": downtime,
            "reconnect_attempts": self.reconnect_attempts,
            "total_reconnections": self.total_reconnections,
            "successful_reconnections": self.successful_reconnections,
            "failed_reconnections": self.failed_reconnections,
            "success_rate": (
                self.successful_reconnections / self.total_reconnections * 100
                if self.total_reconnections > 0
                else 0
            )
        }


# Global MQTT watchdog instance
mqtt_watchdog = MQTTWatchdog()


async def get_mqtt_watchdog() -> MQTTWatchdog:
    """Dependency to get MQTT watchdog instance"""
    return mqtt_watchdog
