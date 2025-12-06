# Home Assistant Client Manager Integration Examples

This document provides practical examples of integrating the HA Client Manager into various SomniProperty backend services.

## Table of Contents
1. [Basic Usage](#basic-usage)
2. [In Background Jobs](#in-background-jobs)
3. [In Automated Maintenance](#in-automated-maintenance)
4. [In Customer Dashboard](#in-customer-dashboard)
5. [In Alerting Service](#in-alerting-service)
6. [In Billing Integration](#in-billing-integration)

---

## Basic Usage

### Simple Service Call

```python
from services.ha_client_manager import get_ha_client_manager

async def example_turn_on_lights():
    """Turn on all living room lights for client 001"""
    manager = await get_ha_client_manager()

    # Get all states
    states = await manager.get_states("001")

    # Find all living room lights
    living_room_lights = [
        state for state in states
        if state['entity_id'].startswith('light.')
        and 'living_room' in state['entity_id']
    ]

    # Turn them all on
    for light in living_room_lights:
        await manager.turn_on_light("001", light['entity_id'])
```

### Check Client Health

```python
async def monitor_client_health():
    """Check health of all clients and alert if issues"""
    manager = await get_ha_client_manager()
    health_results = await manager.check_all_clients_health()

    unhealthy_clients = []
    for client_id, health in health_results.items():
        if health['status'] != 'healthy':
            unhealthy_clients.append({
                'client_id': client_id,
                'client_name': health.get('client_name', 'Unknown'),
                'status': health['status'],
                'error': health.get('error')
            })

    if unhealthy_clients:
        # Send alert to operations team
        print(f"⚠️ {len(unhealthy_clients)} clients are unhealthy!")
        for client in unhealthy_clients:
            print(f"  - {client['client_name']} ({client['client_id']}): {client['status']}")
```

---

## In Background Jobs

### Scheduled Temperature Adjustments

```python
# File: services/scheduled_climate_control.py

from services.ha_client_manager import get_ha_client_manager
from datetime import datetime, time
import asyncio

class ScheduledClimateControl:
    """Automatically adjust client thermostats based on schedule"""

    async def run_morning_warmup(self):
        """
        Run at 6:00 AM: Set temperature to 70°F for all premium clients
        """
        manager = await get_ha_client_manager()

        # Get all premium clients
        clients = manager.get_all_clients()
        premium_clients = [c for c in clients if c.service_tier == "premium"]

        for client in premium_clients:
            # Get all climate entities
            states = await manager.get_states(client.client_id)
            climate_entities = [
                state['entity_id'] for state in states
                if state['entity_id'].startswith('climate.')
            ]

            # Set temperature for each thermostat
            for entity_id in climate_entities:
                await manager.set_temperature(
                    client.client_id,
                    entity_id,
                    70.0  # Morning warmup temperature
                )

            print(f"✓ Set morning temperature for {client.name}")

    async def run_energy_saving_mode(self):
        """
        Run at 10:00 PM: Set temperature to 65°F to save energy
        """
        manager = await get_ha_client_manager()

        clients = manager.get_all_clients()
        for client in clients:
            states = await manager.get_states(client.client_id)
            climate_entities = [
                state['entity_id'] for state in states
                if state['entity_id'].startswith('climate.')
            ]

            for entity_id in climate_entities:
                await manager.set_temperature(
                    client.client_id,
                    entity_id,
                    65.0  # Night energy-saving temperature
                )
```

---

## In Automated Maintenance

### Water Leak Detection Service

```python
# File: services/automated_leak_detection.py

from services.ha_client_manager import get_ha_client_manager
from services.notification_service import send_emergency_alert
from db.models import WorkOrder
from sqlalchemy.ext.asyncio import AsyncSession

class LeakDetectionService:
    """Monitor water leak sensors and create emergency work orders"""

    async def check_all_clients_for_leaks(self, db: AsyncSession):
        """Run every 5 minutes to check for water leaks"""
        manager = await get_ha_client_manager()

        for client_id in manager.get_client_ids():
            await self._check_client_leaks(client_id, db)

    async def _check_client_leaks(self, client_id: str, db: AsyncSession):
        """Check a single client for water leaks"""
        manager = await get_ha_client_manager()
        client_config = manager.get_client_config(client_id)

        # Get all states
        states = await manager.get_states(client_id)

        # Find water leak sensors
        leak_sensors = [
            state for state in states
            if ('water_leak' in state['entity_id'] or
                'leak_sensor' in state['entity_id'])
            and state['state'] in ['on', 'wet', 'detected']
        ]

        if leak_sensors:
            for sensor in leak_sensors:
                # Create emergency work order
                work_order = WorkOrder(
                    client_id=client_id,
                    title=f"EMERGENCY: Water Leak Detected",
                    description=f"Water leak detected at {sensor['attributes'].get('friendly_name', sensor['entity_id'])}",
                    priority="emergency",
                    category="plumbing",
                    status="pending",
                    entity_id=sensor['entity_id'],
                )
                db.add(work_order)
                await db.commit()

                # Send emergency notification
                await send_emergency_alert(
                    client_id=client_id,
                    client_name=client_config.name,
                    message=f"🚨 Water leak detected at {sensor['attributes'].get('friendly_name')}",
                    contact_phone=client_config.contact_phone,
                    contact_email=client_config.contact_email
                )

                # Send notification through Home Assistant
                await manager.send_notification(
                    client_id,
                    f"🚨 EMERGENCY: Water leak detected! SomniProperty has been notified and will dispatch maintenance immediately.",
                    title="WATER LEAK DETECTED"
                )

                print(f"🚨 Emergency work order created for {client_config.name}: Water leak")
```

### Battery Monitoring Service

```python
# File: services/battery_monitoring.py

from services.ha_client_manager import get_ha_client_manager
from services.notification_service import NotificationService

class BatteryMonitoringService:
    """Monitor battery levels across all clients and schedule replacements"""

    async def check_low_batteries(self):
        """Check for low batteries and schedule maintenance"""
        manager = await get_ha_client_manager()
        low_battery_threshold = 20  # 20% battery

        for client_id in manager.get_client_ids():
            client_config = manager.get_client_config(client_id)
            states = await manager.get_states(client_id)

            # Find battery sensors
            battery_sensors = [
                state for state in states
                if state['entity_id'].startswith('sensor.') and 'battery' in state['entity_id']
            ]

            low_batteries = []
            for sensor in battery_sensors:
                try:
                    battery_level = float(sensor['state'])
                    if battery_level < low_battery_threshold:
                        low_batteries.append({
                            'entity_id': sensor['entity_id'],
                            'friendly_name': sensor['attributes'].get('friendly_name', sensor['entity_id']),
                            'battery_level': battery_level
                        })
                except (ValueError, TypeError):
                    continue

            if low_batteries:
                # Create preventive maintenance work order
                devices_list = "\n".join([
                    f"- {b['friendly_name']}: {b['battery_level']}%"
                    for b in low_batteries
                ])

                print(f"📋 Scheduling battery replacements for {client_config.name}:")
                print(devices_list)

                # Send notification to client
                await manager.send_notification(
                    client_id,
                    f"The following devices have low batteries and need replacement:\n{devices_list}",
                    title="Battery Maintenance Scheduled"
                )
```

---

## In Customer Dashboard

### Real-Time Status Dashboard

```python
# File: api/v1/client_dashboard.py

from fastapi import APIRouter, Depends, HTTPException
from services.ha_client_manager import get_ha_client_manager, HAClientManager

router = APIRouter(prefix="/dashboard", tags=["Client Dashboard"])

@router.get("/client/{client_id}/overview")
async def get_client_overview(
    client_id: str,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get comprehensive overview of a client's smart home
    For use in customer-facing dashboard
    """
    client_config = manager.get_client_config(client_id)
    if not client_config:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get all states
    states = await manager.get_states(client_id)

    # Categorize entities
    lights = [s for s in states if s['entity_id'].startswith('light.')]
    climate = [s for s in states if s['entity_id'].startswith('climate.')]
    sensors = [s for s in states if s['entity_id'].startswith('sensor.')]
    switches = [s for s in states if s['entity_id'].startswith('switch.')]

    # Calculate summaries
    lights_on = len([l for l in lights if l['state'] == 'on'])

    # Get current temperature
    temp_sensors = [s for s in sensors if 'temperature' in s['entity_id']]
    avg_temp = None
    if temp_sensors:
        temps = []
        for t in temp_sensors:
            try:
                temps.append(float(t['state']))
            except:
                pass
        if temps:
            avg_temp = sum(temps) / len(temps)

    return {
        "client_id": client_id,
        "client_name": client_config.name,
        "service_tier": client_config.service_tier,
        "summary": {
            "total_devices": len(states),
            "lights": {
                "total": len(lights),
                "on": lights_on,
                "off": len(lights) - lights_on
            },
            "climate_zones": len(climate),
            "sensors": len(sensors),
            "switches": len(switches),
            "average_temperature": round(avg_temp, 1) if avg_temp else None
        },
        "recent_activity": await get_recent_activity(client_id, manager)
    }

async def get_recent_activity(client_id: str, manager):
    """Get recent activity for dashboard"""
    # This would get history of recent changes
    # For now, return placeholder
    return {
        "last_light_change": "2 minutes ago",
        "last_temperature_adjustment": "1 hour ago"
    }
```

---

## In Alerting Service

### Proactive Alert System

```python
# File: services/proactive_alerting.py

from services.ha_client_manager import get_ha_client_manager
from services.notification_service import send_sms, send_email
from datetime import datetime, timedelta

class ProactiveAlertingService:
    """Monitor client homes and send proactive alerts"""

    async def check_open_doors_overnight(self):
        """
        Alert if doors are left open after 10 PM
        Run every 30 minutes between 10 PM and 6 AM
        """
        manager = await get_ha_client_manager()
        current_hour = datetime.now().hour

        # Only run overnight
        if not (22 <= current_hour or current_hour <= 6):
            return

        for client_id in manager.get_client_ids():
            client_config = manager.get_client_config(client_id)
            states = await manager.get_states(client_id)

            # Find door sensors that are open
            open_doors = [
                state for state in states
                if (state['entity_id'].startswith('binary_sensor.') and
                    'door' in state['entity_id'] and
                    state['state'] == 'on')  # 'on' = open for binary sensors
            ]

            if open_doors:
                door_names = [d['attributes'].get('friendly_name', d['entity_id'])
                             for d in open_doors]

                message = f"🚪 The following doors are open:\n" + "\n".join(f"- {name}" for name in door_names)

                # Send notification through HA
                await manager.send_notification(
                    client_id,
                    message,
                    title="Doors Open Overnight"
                )

                # If premium client, also send SMS
                if client_config.service_tier == "premium" and client_config.contact_phone:
                    await send_sms(
                        client_config.contact_phone,
                        f"Alert for {client_config.name}: {message}"
                    )

    async def check_extreme_temperatures(self):
        """Alert on extreme temperature conditions"""
        manager = await get_ha_client_manager()

        for client_id in manager.get_client_ids():
            client_config = manager.get_client_config(client_id)
            states = await manager.get_states(client_id)

            temp_sensors = [
                state for state in states
                if (state['entity_id'].startswith('sensor.') and
                    'temperature' in state['entity_id'])
            ]

            for sensor in temp_sensors:
                try:
                    temp = float(sensor['state'])
                    unit = sensor['attributes'].get('unit_of_measurement', '°F')
                    location = sensor['attributes'].get('friendly_name', sensor['entity_id'])

                    # Check for freezing conditions
                    if unit == '°F' and temp < 40:
                        await manager.send_notification(
                            client_id,
                            f"❄️ Low temperature alert: {location} is at {temp}°F. Risk of pipe freezing!",
                            title="Freezing Temperature Alert"
                        )

                        # Create work order to check heating
                        print(f"🥶 Freezing temp alert for {client_config.name}: {location} at {temp}°F")

                    # Check for extreme heat
                    elif unit == '°F' and temp > 95:
                        await manager.send_notification(
                            client_id,
                            f"🔥 High temperature alert: {location} is at {temp}°F. HVAC may need attention.",
                            title="High Temperature Alert"
                        )

                        print(f"🔥 Heat alert for {client_config.name}: {location} at {temp}°F")

                except (ValueError, TypeError):
                    continue
```

---

## In Billing Integration

### Usage-Based Billing

```python
# File: services/usage_billing_service.py

from services.ha_client_manager import get_ha_client_manager
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import BillingRecord

class UsageBillingService:
    """Calculate usage-based billing from Home Assistant data"""

    async def calculate_monthly_usage(self, client_id: str, month: int, year: int, db: AsyncSession):
        """
        Calculate monthly usage metrics for billing

        Metrics:
        - Total API calls (automation triggers)
        - Remote access hours
        - Alert notifications sent
        - Devices monitored
        """
        manager = await get_ha_client_manager()
        client_config = manager.get_client_config(client_id)

        if not client_config:
            return None

        # Get current device count
        states = await manager.get_states(client_id)
        device_count = len(states)

        # Calculate usage tier pricing
        base_price = self._get_base_price(client_config.service_tier)
        device_fee = device_count * 0.50  # $0.50 per device per month

        # Get automation count (simplified - would track actual automation runs)
        automation_entities = [s for s in states if s['entity_id'].startswith('automation.')]
        automation_count = len(automation_entities)

        total_price = base_price + device_fee

        # Store billing record
        billing_record = BillingRecord(
            client_id=client_id,
            month=month,
            year=year,
            device_count=device_count,
            automation_count=automation_count,
            base_price=base_price,
            device_fee=device_fee,
            total_price=total_price,
            generated_at=datetime.now()
        )
        db.add(billing_record)
        await db.commit()

        return {
            "client_id": client_id,
            "client_name": client_config.name,
            "service_tier": client_config.service_tier,
            "billing_period": f"{month}/{year}",
            "metrics": {
                "devices_monitored": device_count,
                "automations_active": automation_count
            },
            "charges": {
                "base_price": base_price,
                "device_fee": device_fee,
                "total": total_price
            }
        }

    def _get_base_price(self, service_tier: str) -> float:
        """Get base price for service tier"""
        tiers = {
            "basic": 29.99,
            "standard": 49.99,
            "premium": 99.99,
            "enterprise": 299.99
        }
        return tiers.get(service_tier, 49.99)
```

---

## Integration with main.py

Update your `main.py` to initialize the HA Client Manager:

```python
# File: main.py

from fastapi import FastAPI
from services.ha_client_manager import (
    initialize_ha_client_manager,
    shutdown_ha_client_manager
)
from api.v1 import ha_clients

app = FastAPI(title="SomniProperty Manager")

@app.on_event("startup")
async def startup():
    """Initialize services on application startup"""
    # Initialize HA Client Manager
    await initialize_ha_client_manager()
    print("✓ Home Assistant Client Manager initialized")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on application shutdown"""
    await shutdown_ha_client_manager()
    print("✓ Home Assistant Client Manager shut down")

# Include the HA clients router
app.include_router(ha_clients.router, prefix="/api/v1")
```

---

## Testing the Integration

### Manual Testing

```bash
# Get all clients
curl http://localhost:8000/api/v1/ha-clients

# Get specific client info
curl http://localhost:8000/api/v1/ha-clients/001

# Check health of all clients
curl http://localhost:8000/api/v1/ha-clients/health/all

# Get states for a client
curl http://localhost:8000/api/v1/ha-clients/001/states

# Turn on a light
curl -X POST http://localhost:8000/api/v1/ha-clients/001/lights/turn_on \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "light.kitchen"}'

# Send a notification
curl -X POST http://localhost:8000/api/v1/ha-clients/001/notify \
  -H "Content-Type: application/json" \
  -d '{"message": "Test from SomniProperty", "title": "Test Notification"}'
```

### Unit Tests

```python
# File: tests/test_ha_client_manager.py

import pytest
from services.ha_client_manager import HAClientManager

@pytest.mark.asyncio
async def test_client_manager_initialization():
    """Test that client manager initializes correctly"""
    manager = HAClientManager(secrets_path="/tmp/test-secrets")
    await manager.initialize()

    clients = manager.get_all_clients()
    assert len(clients) >= 0  # Should not fail even with no clients

@pytest.mark.asyncio
async def test_health_check():
    """Test health check functionality"""
    manager = await get_ha_client_manager()

    # This would require a test HA instance or mocking
    # For now, just test that method exists and returns expected format
    health = await manager.check_health("001")
    assert "client_id" in health
    assert "status" in health
```

---

## Best Practices

1. **Error Handling**: Always wrap HA API calls in try-except blocks
2. **Timeouts**: Use appropriate timeouts for external API calls
3. **Rate Limiting**: Implement rate limiting to avoid overwhelming client HA instances
4. **Logging**: Log all client interactions for audit trail
5. **Security**: Never expose client tokens in API responses or logs
6. **Caching**: Consider caching state data to reduce API calls
7. **Webhooks**: Use Home Assistant webhooks for real-time updates instead of polling
8. **Retry Logic**: Implement retry logic for transient network failures
9. **Circuit Breaker**: Use circuit breaker pattern for unreachable clients
10. **Monitoring**: Track API response times and error rates per client

---

## Next Steps

1. Implement the examples that fit your use case
2. Add the HA clients router to your main.py
3. Update deployment to mount the Kubernetes secret
4. Test with a few pilot clients before rolling out to all
5. Set up monitoring and alerting for client health
6. Create customer-facing dashboard showing their HA data
