"""
Proactive Ticket Scheduler - Background Task Runner

Runs periodic tasks for:
- Auto-creating tickets from critical alerts
- Checking SLA breaches
- Other background maintenance tasks
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from db.database import get_db
from services.alert_monitor import check_critical_alerts_and_create_tickets, check_sla_breaches
from services.notification_service import send_notification

logger = logging.getLogger(__name__)


class ProactiveTicketScheduler:
    """Background task scheduler for proactive ticket creation"""

    def __init__(self):
        self.running = False
        self.tasks = []

    async def start(self):
        """Start all background tasks"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        logger.info("Starting proactive ticket scheduler")

        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._alert_monitor_loop()),
            asyncio.create_task(self._sla_check_loop()),
        ]

        logger.info(f"Started {len(self.tasks)} background tasks")

    async def stop(self):
        """Stop all background tasks"""
        if not self.running:
            return

        logger.info("Stopping proactive ticket scheduler")
        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for all tasks to finish
        await asyncio.gather(*self.tasks, return_exceptions=True)

        self.tasks = []
        logger.info("Proactive ticket scheduler stopped")

    async def _alert_monitor_loop(self):
        """Check for critical alerts every 5 minutes"""
        while self.running:
            try:
                async for db in get_db():
                    try:
                        tickets_created = await check_critical_alerts_and_create_tickets(db)
                        if tickets_created > 0:
                            logger.info(f"Alert monitor created {tickets_created} new tickets")
                    except Exception as e:
                        logger.error(f"Error in alert monitor loop: {e}", exc_info=True)
                    break  # Exit after one iteration

                # Wait 5 minutes before next check
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                logger.info("Alert monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in alert monitor loop: {e}", exc_info=True)
                # Wait 1 minute before retrying on error
                await asyncio.sleep(60)

    async def _sla_check_loop(self):
        """Check for SLA breaches every 15 minutes"""
        while self.running:
            try:
                async for db in get_db():
                    try:
                        breached_count = await check_sla_breaches(db)
                        if breached_count > 0:
                            logger.warning(f"Detected {breached_count} SLA breaches")
                    except Exception as e:
                        logger.error(f"Error in SLA check loop: {e}", exc_info=True)
                    break  # Exit after one iteration

                # Wait 15 minutes before next check
                await asyncio.sleep(900)

            except asyncio.CancelledError:
                logger.info("SLA check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in SLA check loop: {e}", exc_info=True)
                # Wait 5 minutes before retrying on error
                await asyncio.sleep(300)


# Global scheduler instance
scheduler = ProactiveTicketScheduler()


@asynccontextmanager
async def lifespan_scheduler() -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI app"""
    # Startup
    await scheduler.start()
    yield
    # Shutdown
    await scheduler.stop()
