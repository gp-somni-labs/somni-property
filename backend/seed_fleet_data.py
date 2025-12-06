"""
Seed script to populate database with sample 3-tier fleet management data

Creates:
- 1 property
- 3 PropertyEdgeNodes (2 Tier 3, 1 Tier 2)
- 10 SmartDevices synced from Tier 3 hubs
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from db.database import AsyncSessionLocal
from db.models import Property, PropertyEdgeNode, SmartDevice


async def seed_data():
    async with AsyncSessionLocal() as session:
        print("🌱 Seeding 3-tier fleet management data...")

        # Create a sample property
        property_id = uuid.uuid4()
        property = Property(
            id=property_id,
            name="Sunset Apartments",
            address_line1="123 Main Street",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            property_type="residential",
            purchase_price=Decimal("2500000.00"),
            current_value=Decimal("2800000.00")
        )
        session.add(property)
        print(f"✅ Created property: {property.name}")

        # Create Tier 3 PropertyEdgeNode #1 (Home A)
        hub1_id = uuid.uuid4()
        hub1 = PropertyEdgeNode(
            id=hub1_id,
            property_id=property_id,
            hub_type='tier_3_residential',
            hostname='property-edge-001',
            ip_address='192.168.1.100',
            tailscale_ip='100.64.1.11',
            tailscale_hostname='property-edge-001.ts.net',
            status='online',
            deployed_stack='residential',
            manifest_version='a3c9f2e',  # Git commit SHA
            managed_by_tier1=True,
            auto_update_enabled=True,
            sync_status='synced',
            last_heartbeat=datetime.utcnow() - timedelta(minutes=2),
            last_sync=datetime.utcnow() - timedelta(minutes=15),
            device_count=6,
            resource_usage={'cpu': 35, 'memory': 48, 'disk': 42}
        )
        session.add(hub1)
        print(f"✅ Created Tier 3 hub: {hub1.hostname} (Unit 101)")

        # Create Tier 3 PropertyEdgeNode #2 (Home B)
        hub2_id = uuid.uuid4()
        hub2 = PropertyEdgeNode(
            id=hub2_id,
            property_id=property_id,
            hub_type='tier_3_residential',
            hostname='property-edge-002',
            ip_address='192.168.1.101',
            tailscale_ip='100.64.1.12',
            tailscale_hostname='property-edge-002.ts.net',
            status='online',
            deployed_stack='residential',
            manifest_version='a3c9f2e',
            managed_by_tier1=True,
            auto_update_enabled=True,
            sync_status='synced',
            last_heartbeat=datetime.utcnow() - timedelta(minutes=1),
            last_sync=datetime.utcnow() - timedelta(minutes=10),
            device_count=4,
            resource_usage={'cpu': 28, 'memory': 52, 'disk': 38}
        )
        session.add(hub2)
        print(f"✅ Created Tier 3 hub: {hub2.hostname} (Unit 205)")

        # Create Tier 2 PropertyEdgeNode (Building Hub)
        hub3_id = uuid.uuid4()
        hub3 = PropertyEdgeNode(
            id=hub3_id,
            property_id=property_id,
            hub_type='tier_2_property',
            hostname='property-hub-main',
            ip_address='192.168.1.10',
            tailscale_ip='100.64.1.10',
            tailscale_hostname='property-hub-main.ts.net',
            status='online',
            deployed_stack='property_manager',
            manifest_version='b7d4e1a',
            managed_by_tier1=True,
            auto_update_enabled=True,
            sync_status='synced',
            last_heartbeat=datetime.utcnow() - timedelta(seconds=30),
            last_sync=datetime.utcnow() - timedelta(minutes=5),
            device_count=24,  # Common area devices
            resource_usage={'cpu': 42, 'memory': 65, 'disk': 55}
        )
        session.add(hub3)
        print(f"✅ Created Tier 2 hub: {hub3.hostname} (Building Hub)")

        # Create SmartDevices synced from Hub #1 (Unit 101)
        devices_hub1 = [
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub1_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=15),
                home_assistant_entity_id='light.living_room',
                ha_domain='light',
                ha_state='on',
                ha_attributes={'brightness': 200, 'color_temp': 370},
                device_name='Living Room Light',
                device_type='light',
                manufacturer='Philips',
                model='Hue White Ambiance',
                status='active',
                health_status='healthy',
                last_seen=datetime.utcnow() - timedelta(minutes=2),
                location='Living Room - Unit 101'
            ),
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub1_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=15),
                home_assistant_entity_id='lock.front_door',
                ha_domain='lock',
                ha_state='locked',
                ha_attributes={'battery_level': 85},
                device_name='Front Door Lock',
                device_type='lock',
                manufacturer='Yale',
                model='Assure Lock SL',
                status='active',
                health_status='healthy',
                battery_level=85,
                last_seen=datetime.utcnow() - timedelta(minutes=1),
                location='Front Entry - Unit 101'
            ),
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub1_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=15),
                home_assistant_entity_id='climate.thermostat',
                ha_domain='climate',
                ha_state='heat',
                ha_attributes={'temperature': 72, 'target_temp': 70, 'humidity': 45},
                device_name='Thermostat',
                device_type='thermostat',
                manufacturer='Ecobee',
                model='SmartThermostat',
                status='active',
                health_status='healthy',
                last_seen=datetime.utcnow() - timedelta(minutes=3),
                location='Hallway - Unit 101'
            ),
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub1_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=15),
                home_assistant_entity_id='binary_sensor.motion_detector',
                ha_domain='binary_sensor',
                ha_state='off',
                ha_attributes={'device_class': 'motion'},
                device_name='Motion Detector',
                device_type='sensor',
                manufacturer='Aqara',
                model='Motion Sensor P1',
                status='active',
                health_status='healthy',
                battery_level=92,
                last_seen=datetime.utcnow() - timedelta(seconds=45),
                location='Living Room - Unit 101'
            ),
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub1_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=15),
                home_assistant_entity_id='switch.bedroom_lamp',
                ha_domain='switch',
                ha_state='off',
                ha_attributes={},
                device_name='Bedroom Lamp',
                device_type='switch',
                manufacturer='TP-Link',
                model='Kasa Smart Plug',
                status='active',
                health_status='healthy',
                last_seen=datetime.utcnow() - timedelta(minutes=5),
                location='Bedroom - Unit 101'
            ),
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub1_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=15),
                home_assistant_entity_id='sensor.temperature',
                ha_domain='sensor',
                ha_state='68.5',
                ha_attributes={'unit_of_measurement': '°F'},
                device_name='Temperature Sensor',
                device_type='sensor',
                manufacturer='Aqara',
                model='Temperature & Humidity Sensor',
                status='active',
                health_status='healthy',
                battery_level=78,
                last_seen=datetime.utcnow() - timedelta(minutes=1),
                location='Living Room - Unit 101'
            ),
        ]

        for device in devices_hub1:
            session.add(device)
        print(f"✅ Created {len(devices_hub1)} devices for {hub1.hostname}")

        # Create SmartDevices synced from Hub #2 (Unit 205)
        devices_hub2 = [
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub2_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=10),
                home_assistant_entity_id='light.kitchen',
                ha_domain='light',
                ha_state='off',
                ha_attributes={'brightness': 0},
                device_name='Kitchen Light',
                device_type='light',
                manufacturer='IKEA',
                model='TRADFRI',
                status='active',
                health_status='healthy',
                last_seen=datetime.utcnow() - timedelta(minutes=1),
                location='Kitchen - Unit 205'
            ),
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub2_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=10),
                home_assistant_entity_id='lock.back_door',
                ha_domain='lock',
                ha_state='locked',
                ha_attributes={'battery_level': 92},
                device_name='Back Door Lock',
                device_type='lock',
                manufacturer='Schlage',
                model='Encode Smart WiFi Deadbolt',
                status='active',
                health_status='healthy',
                battery_level=92,
                last_seen=datetime.utcnow() - timedelta(minutes=2),
                location='Back Entry - Unit 205'
            ),
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub2_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=10),
                home_assistant_entity_id='sensor.leak_detector',
                ha_domain='binary_sensor',
                ha_state='off',
                ha_attributes={'device_class': 'moisture', 'battery_level': 65},
                device_name='Leak Detector',
                device_type='sensor',
                manufacturer='Aqara',
                model='Water Leak Sensor',
                status='active',
                health_status='warning',
                battery_level=65,
                last_seen=datetime.utcnow() - timedelta(minutes=30),
                location='Bathroom - Unit 205'
            ),
            SmartDevice(
                id=uuid.uuid4(),
                property_id=property_id,
                sync_source='home_assistant',
                synced_from_hub_id=hub2_id,
                last_synced_at=datetime.utcnow() - timedelta(minutes=10),
                home_assistant_entity_id='camera.front_door',
                ha_domain='camera',
                ha_state='recording',
                ha_attributes={'motion_detected': False},
                device_name='Front Door Camera',
                device_type='camera',
                manufacturer='Wyze',
                model='Cam v3',
                status='active',
                health_status='healthy',
                last_seen=datetime.utcnow() - timedelta(seconds=20),
                location='Front Entry - Unit 205'
            ),
        ]

        for device in devices_hub2:
            session.add(device)
        print(f"✅ Created {len(devices_hub2)} devices for {hub2.hostname}")

        await session.commit()
        print("\n🎉 Successfully seeded database!")
        print(f"   📍 1 Property: {property.name}")
        print(f"   🖥️  3 Edge Nodes: 2 Tier 3 (residential) + 1 Tier 2 (property)")
        print(f"   💡 {len(devices_hub1) + len(devices_hub2)} Smart Devices synced from HA")
        print("\n✨ You can now view the Fleet Management and Smart Devices tabs!")


if __name__ == "__main__":
    asyncio.run(seed_data())
