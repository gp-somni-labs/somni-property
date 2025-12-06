"""
Utility Monitoring Service
Handles per-unit electricity, water, and gas monitoring with intelligent anomaly detection
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import statistics

from db.models import (
    UtilityMeter,
    UtilityReading,
    UtilityAnomaly,
    Unit,
    WorkOrder
)

logger = logging.getLogger(__name__)


class UtilityMonitor:
    """
    Intelligent utility monitoring with anomaly detection
    """

    # Anomaly detection thresholds
    SPIKE_THRESHOLD = 2.0  # 200% of average
    LEAK_THRESHOLD = 1.5   # 150% of nighttime average
    ZERO_USAGE_HOURS = 24  # Hours of zero usage to flag

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def ingest_reading(
        self,
        meter_id: str,
        reading_value: Decimal,
        reading_timestamp: datetime,
        db: AsyncSession,
        reading_type: str = "automatic"
    ) -> UtilityReading:
        """
        Ingest a new utility reading and check for anomalies
        """
        try:
            # Get meter
            meter_query = select(UtilityMeter).where(UtilityMeter.id == meter_id)
            meter_result = await db.execute(meter_query)
            meter = meter_result.scalar_one_or_none()

            if not meter:
                raise ValueError(f"Meter {meter_id} not found")

            # Apply calibration factor
            calibrated_value = reading_value * meter.calibration_factor

            # Create reading
            reading = UtilityReading(
                meter_id=meter_id,
                reading_value=calibrated_value,
                reading_timestamp=reading_timestamp,
                reading_type=reading_type
            )

            db.add(reading)
            await db.flush()

            # Check for anomalies
            await self._detect_anomalies(meter, reading, db)

            await db.commit()

            self.logger.info(
                f"Ingested reading for meter {meter_id}: {calibrated_value} {meter.meter_type}"
            )

            return reading

        except Exception as e:
            self.logger.error(f"Error ingesting reading: {e}")
            await db.rollback()
            raise

    async def _detect_anomalies(
        self,
        meter: UtilityMeter,
        current_reading: UtilityReading,
        db: AsyncSession
    ):
        """
        Detect anomalies in utility usage
        """
        # Get historical readings (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)

        readings_query = select(UtilityReading).where(
            and_(
                UtilityReading.meter_id == meter.id,
                UtilityReading.reading_timestamp >= thirty_days_ago,
                UtilityReading.reading_timestamp < current_reading.reading_timestamp
            )
        ).order_by(UtilityReading.reading_timestamp)

        result = await db.execute(readings_query)
        historical_readings = result.scalars().all()

        if len(historical_readings) < 7:
            # Not enough data for anomaly detection
            return

        # Calculate statistics
        values = [float(r.reading_value) for r in historical_readings]
        avg_value = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0

        current_value = float(current_reading.reading_value)

        # Detect spike (sudden high usage)
        if current_value > avg_value * self.SPIKE_THRESHOLD:
            await self._create_anomaly(
                meter=meter,
                anomaly_type="spike",
                severity="high",
                description=f"Usage spike detected: {current_value:.2f} vs avg {avg_value:.2f}",
                expected_value=Decimal(str(avg_value)),
                actual_value=current_reading.reading_value,
                deviation_percent=Decimal(str((current_value - avg_value) / avg_value * 100)),
                db=db
            )

        # Detect potential leak (water meter specific)
        if meter.meter_type == "water":
            is_leak = await self._detect_leak(meter, current_reading, historical_readings, db)
            if is_leak:
                await self._create_anomaly(
                    meter=meter,
                    anomaly_type="leak",
                    severity="critical",
                    description=f"Possible water leak detected - continuous flow at {current_value:.2f}",
                    expected_value=Decimal("0"),
                    actual_value=current_reading.reading_value,
                    deviation_percent=Decimal("100"),
                    db=db
                )

        # Detect zero usage (meter offline or vacant unit)
        last_nonzero = None
        for reading in reversed(historical_readings):
            if float(reading.reading_value) > 0:
                last_nonzero = reading.reading_timestamp
                break

        if last_nonzero and current_value == 0:
            hours_zero = (current_reading.reading_timestamp - last_nonzero).total_seconds() / 3600
            if hours_zero > self.ZERO_USAGE_HOURS:
                await self._create_anomaly(
                    meter=meter,
                    anomaly_type="zero_usage",
                    severity="medium",
                    description=f"No usage for {hours_zero:.1f} hours - meter may be offline or unit vacant",
                    expected_value=Decimal(str(avg_value)),
                    actual_value=Decimal("0"),
                    deviation_percent=Decimal("-100"),
                    db=db
                )

    async def _detect_leak(
        self,
        meter: UtilityMeter,
        current_reading: UtilityReading,
        historical_readings: List[UtilityReading],
        db: AsyncSession
    ) -> bool:
        """
        Detect water leaks by analyzing nighttime usage patterns
        """
        # Get nighttime readings (12am - 6am) from last week
        week_ago = datetime.now() - timedelta(days=7)

        nighttime_query = select(UtilityReading).where(
            and_(
                UtilityReading.meter_id == meter.id,
                UtilityReading.reading_timestamp >= week_ago,
                func.extract('hour', UtilityReading.reading_timestamp).between(0, 6)
            )
        )

        result = await db.execute(nighttime_query)
        nighttime_readings = result.scalars().all()

        if len(nighttime_readings) < 5:
            return False

        # Calculate average nighttime usage
        nighttime_values = [float(r.reading_value) for r in nighttime_readings]
        avg_nighttime = statistics.mean(nighttime_values)

        current_value = float(current_reading.reading_value)

        # Check if current reading is during night and significantly higher
        current_hour = current_reading.reading_timestamp.hour
        if 0 <= current_hour <= 6:
            if current_value > avg_nighttime * self.LEAK_THRESHOLD:
                return True

        return False

    async def _create_anomaly(
        self,
        meter: UtilityMeter,
        anomaly_type: str,
        severity: str,
        description: str,
        expected_value: Decimal,
        actual_value: Decimal,
        deviation_percent: Decimal,
        db: AsyncSession
    ):
        """
        Create anomaly record and optionally create work order
        """
        # Check if similar anomaly already exists (within last hour)
        hour_ago = datetime.now() - timedelta(hours=1)

        existing_query = select(UtilityAnomaly).where(
            and_(
                UtilityAnomaly.meter_id == meter.id,
                UtilityAnomaly.anomaly_type == anomaly_type,
                UtilityAnomaly.detected_at >= hour_ago,
                UtilityAnomaly.status.in_(["open", "investigating"])
            )
        )

        result = await db.execute(existing_query)
        existing_anomaly = result.scalar_one_or_none()

        if existing_anomaly:
            # Don't create duplicate
            return

        # Create new anomaly
        anomaly = UtilityAnomaly(
            meter_id=meter.id,
            unit_id=meter.unit_id,
            anomaly_type=anomaly_type,
            severity=severity,
            description=description,
            expected_value=expected_value,
            actual_value=actual_value,
            deviation_percent=deviation_percent,
            status="open"
        )

        db.add(anomaly)
        await db.flush()

        # Create work order for critical anomalies
        if severity in ["high", "critical"]:
            await self._create_emergency_work_order(anomaly, meter, db)

        self.logger.warning(
            f"Anomaly detected: {anomaly_type} for meter {meter.id} - {description}"
        )

    async def _create_emergency_work_order(
        self,
        anomaly: UtilityAnomaly,
        meter: UtilityMeter,
        db: AsyncSession
    ):
        """
        Auto-create work order for critical utility issues
        """
        # TODO: Integrate with WorkOrder model
        work_order = WorkOrder(
            unit_id=meter.unit_id,
            title=f"URGENT: {anomaly.anomaly_type.upper()} - {meter.meter_type}",
            description=anomaly.description,
            priority="emergency" if anomaly.severity == "critical" else "high",
            status="submitted",
            category="utility",
            source="automated_monitoring"
        )

        db.add(work_order)
        await db.flush()

        # Link work order to anomaly
        anomaly.work_order_id = work_order.id

        self.logger.info(f"Created emergency work order {work_order.id} for anomaly {anomaly.id}")

    async def calculate_usage(
        self,
        meter_id: str,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> Dict:
        """
        Calculate total usage and cost for a billing period
        """
        readings_query = select(UtilityReading).where(
            and_(
                UtilityReading.meter_id == meter_id,
                UtilityReading.reading_timestamp >= start_date,
                UtilityReading.reading_timestamp <= end_date
            )
        ).order_by(UtilityReading.reading_timestamp)

        result = await db.execute(readings_query)
        readings = result.scalars().all()

        if len(readings) < 2:
            return {
                "total_usage": 0,
                "total_cost": 0,
                "readings_count": len(readings),
                "period_start": start_date,
                "period_end": end_date
            }

        # Calculate usage (difference between last and first reading)
        first_reading = readings[0]
        last_reading = readings[-1]

        total_usage = float(last_reading.reading_value - first_reading.reading_value)

        # Get meter to determine rate
        meter_query = select(UtilityMeter).where(UtilityMeter.id == meter_id)
        meter_result = await db.execute(meter_query)
        meter = meter_result.scalar_one_or_none()

        # Calculate cost based on meter type
        # TODO: Make rates configurable per property/building
        rate = self._get_utility_rate(meter.meter_type)
        total_cost = total_usage * rate

        return {
            "meter_type": meter.meter_type,
            "total_usage": round(total_usage, 2),
            "total_cost": round(total_cost, 2),
            "rate": rate,
            "readings_count": len(readings),
            "period_start": start_date,
            "period_end": end_date,
            "average_daily_usage": round(total_usage / ((end_date - start_date).days or 1), 2)
        }

    def _get_utility_rate(self, meter_type: str) -> float:
        """
        Get current utility rate (per kWh, gallon, therm)
        TODO: Make this configurable per property
        """
        rates = {
            "electricity": 0.12,  # $ per kWh
            "water": 0.005,       # $ per gallon
            "gas": 1.20           # $ per therm
        }
        return rates.get(meter_type, 0.10)

    async def get_unit_usage_summary(
        self,
        unit_id: str,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> Dict:
        """
        Get complete utility usage summary for a unit
        """
        # Get all meters for the unit
        meters_query = select(UtilityMeter).where(
            and_(
                UtilityMeter.unit_id == unit_id,
                UtilityMeter.is_active == True
            )
        )

        result = await db.execute(meters_query)
        meters = result.scalars().all()

        summary = {
            "unit_id": unit_id,
            "period_start": start_date,
            "period_end": end_date,
            "utilities": {},
            "total_cost": 0
        }

        for meter in meters:
            usage = await self.calculate_usage(
                str(meter.id),
                start_date,
                end_date,
                db
            )
            summary["utilities"][meter.meter_type] = usage
            summary["total_cost"] += usage["total_cost"]

        return summary

    async def get_anomalies_for_unit(
        self,
        unit_id: str,
        status: Optional[str] = None,
        db: AsyncSession
    ) -> List[UtilityAnomaly]:
        """
        Get all anomalies for a specific unit
        """
        query = select(UtilityAnomaly).where(UtilityAnomaly.unit_id == unit_id)

        if status:
            query = query.where(UtilityAnomaly.status == status)

        query = query.order_by(desc(UtilityAnomaly.detected_at))

        result = await db.execute(query)
        return result.scalars().all()


# Singleton instance
utility_monitor = UtilityMonitor()
