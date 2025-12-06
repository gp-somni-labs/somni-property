"""
Seed All 5 Somni Properties with Real Home Assistant Instances

Creates complete property data for:
1. George-Barsa (Tier 1)
2. Gerardo-Washington (Tier 1)
3. Misael-Cicero (Tier 2)
4. New England (Tier 2)
5. Angie-Washington (Tier 2)
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from db.database import AsyncSessionLocal
from db.models import (
    Property, Building, Unit, PropertyEdgeNode, SmartDevice,
    Client, Tenant, Lease
)


async def seed_all_properties():
    async with AsyncSessionLocal() as session:
        print("🌱 Seeding all 5 Somni properties with Home Assistant instances...")
        print("=" * 80)

        # =================================================================
        # PROPERTY 1: GEORGE-BARSA (TIER 1 - BASIC RESIDENTIAL)
        # =================================================================
        print("\n📍 Property 1: George-Barsa")
        george_barsa_id = uuid.uuid4()
        george_barsa = Property(
            id=george_barsa_id,
            name="George-Barsa Residence",
            address_line1="123 Barsa Street",
            city="Seattle",
            state="WA",
            zip_code="98101",
            property_type="residential",
            purchase_price=Decimal("450000.00"),
            current_value=Decimal("520000.00")
        )
        session.add(george_barsa)

        # Building for George-Barsa
        george_barsa_building_id = uuid.uuid4()
        george_barsa_building = Building(
            id=george_barsa_building_id,
            property_id=george_barsa_id,
            name="Main House",
            floors=2,
            total_units=1,
            year_built=2015,
            square_feet=2400,
            has_central_hvac=True,
            has_parking=True,
            parking_spaces=2
        )
        session.add(george_barsa_building)

        # Unit for George-Barsa
        george_barsa_unit_id = uuid.uuid4()
        george_barsa_unit = Unit(
            id=george_barsa_unit_id,
            building_id=george_barsa_building_id,
            unit_number="Main",
            floor=1,
            bedrooms=3,
            bathrooms=2,
            square_feet=1800,
            monthly_rent=Decimal("2500.00"),
            status="occupied",
            unit_type="single-family"
        )
        session.add(george_barsa_unit)

        # Home Assistant Hub for George-Barsa
        george_barsa_hub_id = uuid.uuid4()
        george_barsa_hub = PropertyEdgeNode(
            id=george_barsa_hub_id,
            property_id=george_barsa_id,
            hub_type='tier_0_standalone',
            hostname='george-barsa-ha',
            ip_address='192.168.1.50',
            tailscale_ip='100.64.1.50',
            tailscale_hostname='george-barsa.ts.net',
            api_url='http://george-barsa-ha.local:8123',
            status='online',
            deployed_stack='residential_basic',
            manifest_version='v1.0.0',
            managed_by_tier1=True,
            auto_update_enabled=True,
            sync_status='synced',
            last_heartbeat=datetime.utcnow() - timedelta(minutes=1),
            last_sync=datetime.utcnow() - timedelta(minutes=10),
            device_count=8,
            resource_usage={'cpu': 25, 'memory': 40, 'disk': 35}
        )
        session.add(george_barsa_hub)
        print(f"  ✅ Created HA Hub: {george_barsa_hub.hostname}")

        # =================================================================
        # PROPERTY 2: GERARDO-WASHINGTON (TIER 1 - BASIC RESIDENTIAL)
        # =================================================================
        print("\n📍 Property 2: Gerardo-Washington")
        gerardo_washington_id = uuid.uuid4()
        gerardo_washington = Property(
            id=gerardo_washington_id,
            name="Gerardo-Washington Residence",
            address_line1="456 Washington Ave",
            city="Tacoma",
            state="WA",
            zip_code="98402",
            property_type="residential",
            purchase_price=Decimal("380000.00"),
            current_value=Decimal("425000.00"),
        )
        session.add(gerardo_washington)

        # Building
        gerardo_washington_building_id = uuid.uuid4()
        gerardo_washington_building = Building(
            id=gerardo_washington_building_id,
            property_id=gerardo_washington_id,
            name="Main House",
            floors=2,
            total_units=1,
            year_built=2010,
            square_feet=2800,
            has_central_hvac=True,
            has_parking=True,
            parking_spaces=2
        )
        session.add(gerardo_washington_building)

        # Unit
        gerardo_washington_unit_id = uuid.uuid4()
        gerardo_washington_unit = Unit(
            id=gerardo_washington_unit_id,
            building_id=gerardo_washington_building_id,
            unit_number="Main",
            floor=1,
            bedrooms=3,
            bathrooms=2,
            square_feet=1650,
            monthly_rent=Decimal("2200.00"),
            status="occupied",
            unit_type="single-family"
        )
        session.add(gerardo_washington_unit)

        # Home Assistant Hub
        gerardo_washington_hub_id = uuid.uuid4()
        gerardo_washington_hub = PropertyEdgeNode(
            id=gerardo_washington_hub_id,
            property_id=gerardo_washington_id,
            hub_type='tier_0_standalone',
            hostname='gerardo-washington-ha',
            ip_address='192.168.1.51',
            tailscale_ip='100.64.1.51',
            tailscale_hostname='gerardo-washington.ts.net',
            api_url='http://gerardo-washington-ha.local:8123',
            status='online',
            deployed_stack='residential_basic',
            manifest_version='v1.0.0',
            managed_by_tier1=True,
            auto_update_enabled=True,
            sync_status='synced',
            last_heartbeat=datetime.utcnow() - timedelta(minutes=2),
            last_sync=datetime.utcnow() - timedelta(minutes=15),
            device_count=12,
            resource_usage={'cpu': 30, 'memory': 45, 'disk': 40}
        )
        session.add(gerardo_washington_hub)
        print(f"  ✅ Created HA Hub: {gerardo_washington_hub.hostname}")

        # =================================================================
        # PROPERTY 3: MISAEL-CICERO (TIER 2 - ADVANCED RESIDENTIAL)
        # =================================================================
        print("\n📍 Property 3: Misael-Cicero")
        misael_cicero_id = uuid.uuid4()
        misael_cicero = Property(
            id=misael_cicero_id,
            name="Misael-Cicero Residence",
            address_line1="789 Cicero Lane",
            city="Bellevue",
            state="WA",
            zip_code="98004",
            property_type="residential",
            purchase_price=Decimal("650000.00"),
            current_value=Decimal("720000.00")
        )
        session.add(misael_cicero)

        # Building
        misael_cicero_building_id = uuid.uuid4()
        misael_cicero_building = Building(
            id=misael_cicero_building_id,
            property_id=misael_cicero_id,
            name="Main House",
            floors=2,
            total_units=1,
            year_built=2018,
            square_feet=3200,
            has_central_hvac=True,
            has_parking=True,
            parking_spaces=3
        )
        session.add(misael_cicero_building)

        # Unit
        misael_cicero_unit_id = uuid.uuid4()
        misael_cicero_unit = Unit(
            id=misael_cicero_unit_id,
            building_id=misael_cicero_building_id,
            unit_number="Main",
            floor=1,
            bedrooms=4,
            bathrooms=3,
            square_feet=2400,
            monthly_rent=Decimal("3500.00"),
            status="occupied",
            unit_type="single-family"
        )
        session.add(misael_cicero_unit)

        # Home Assistant Hub
        misael_cicero_hub_id = uuid.uuid4()
        misael_cicero_hub = PropertyEdgeNode(
            id=misael_cicero_hub_id,
            property_id=misael_cicero_id,
            hub_type='tier_0_standalone',
            hostname='misael-cicero-ha',
            ip_address='192.168.1.52',
            tailscale_ip='100.64.1.52',
            tailscale_hostname='misael-cicero.ts.net',
            api_url='http://misael-cicero-ha.local:8123',
            status='online',
            deployed_stack='residential_premium',
            manifest_version='v2.0.0',
            managed_by_tier1=True,
            auto_update_enabled=True,
            sync_status='synced',
            last_heartbeat=datetime.utcnow() - timedelta(seconds=30),
            last_sync=datetime.utcnow() - timedelta(minutes=5),
            device_count=20,
            resource_usage={'cpu': 45, 'memory': 60, 'disk': 50}
        )
        session.add(misael_cicero_hub)
        print(f"  ✅ Created HA Hub: {misael_cicero_hub.hostname} (K3s enabled)")

        # =================================================================
        # PROPERTY 4: NEW ENGLAND (TIER 2 - ADVANCED RESIDENTIAL)
        # =================================================================
        print("\n📍 Property 4: New England")
        new_england_id = uuid.uuid4()
        new_england = Property(
            id=new_england_id,
            name="New England Estate",
            address_line1="321 Colonial Drive",
            city="Boston",
            state="MA",
            zip_code="02101",
            property_type="residential",
            purchase_price=Decimal("850000.00"),
            current_value=Decimal("950000.00")
        )
        session.add(new_england)

        # Building
        new_england_building_id = uuid.uuid4()
        new_england_building = Building(
            id=new_england_building_id,
            property_id=new_england_id,
            name="Main Estate",
            floors=3,
            total_units=1,
            year_built=2020,
            square_feet=5000,
            has_central_hvac=True,
            has_elevator=True,
            has_parking=True,
            parking_spaces=4
        )
        session.add(new_england_building)

        # Unit
        new_england_unit_id = uuid.uuid4()
        new_england_unit = Unit(
            id=new_england_unit_id,
            building_id=new_england_building_id,
            unit_number="Main",
            floor=1,
            bedrooms=5,
            bathrooms=4,
            square_feet=3200,
            monthly_rent=Decimal("4800.00"),
            status="occupied",
            unit_type="single-family"
        )
        session.add(new_england_unit)

        # Home Assistant Hub
        new_england_hub_id = uuid.uuid4()
        new_england_hub = PropertyEdgeNode(
            id=new_england_hub_id,
            property_id=new_england_id,
            hub_type='tier_0_standalone',
            hostname='new-england-ha',
            ip_address='192.168.1.53',
            tailscale_ip='100.64.1.53',
            tailscale_hostname='new-england.ts.net',
            api_url='http://new-england-ha.local:8123',
            status='online',
            deployed_stack='residential_enterprise',
            manifest_version='v2.1.0',
            managed_by_tier1=True,
            auto_update_enabled=True,
            sync_status='synced',
            last_heartbeat=datetime.utcnow() - timedelta(seconds=45),
            last_sync=datetime.utcnow() - timedelta(minutes=8),
            device_count=35,
            resource_usage={'cpu': 55, 'memory': 70, 'disk': 60}
        )
        session.add(new_england_hub)
        print(f"  ✅ Created HA Hub: {new_england_hub.hostname} (K3s enabled)")

        # =================================================================
        # PROPERTY 5: ANGIE-WASHINGTON (TIER 2 - ADVANCED RESIDENTIAL)
        # =================================================================
        print("\n📍 Property 5: Angie-Washington")
        angie_washington_id = uuid.uuid4()
        angie_washington = Property(
            id=angie_washington_id,
            name="Angie-Washington Residence",
            address_line1="555 Washington Heights",
            city="Olympia",
            state="WA",
            zip_code="98501",
            property_type="residential",
            purchase_price=Decimal("550000.00"),
            current_value=Decimal("600000.00")
        )
        session.add(angie_washington)

        # Building
        angie_washington_building_id = uuid.uuid4()
        angie_washington_building = Building(
            id=angie_washington_building_id,
            property_id=angie_washington_id,
            name="Main House",
            floors=2,
            total_units=1,
            year_built=2017,
            square_feet=2900,
            has_central_hvac=True,
            has_parking=True,
            parking_spaces=2
        )
        session.add(angie_washington_building)

        # Unit
        angie_washington_unit_id = uuid.uuid4()
        angie_washington_unit = Unit(
            id=angie_washington_unit_id,
            building_id=angie_washington_building_id,
            unit_number="Main",
            floor=1,
            bedrooms=4,
            bathrooms=3,
            square_feet=2200,
            monthly_rent=Decimal("3200.00"),
            status="occupied",
            unit_type="single-family"
        )
        session.add(angie_washington_unit)

        # Home Assistant Hub
        angie_washington_hub_id = uuid.uuid4()
        angie_washington_hub = PropertyEdgeNode(
            id=angie_washington_hub_id,
            property_id=angie_washington_id,
            hub_type='tier_0_standalone',
            hostname='angie-washington-ha',
            ip_address='192.168.1.54',
            tailscale_ip='100.64.1.54',
            tailscale_hostname='angie-washington.ts.net',
            api_url='http://angie-washington-ha.local:8123',
            status='online',
            deployed_stack='residential_premium',
            manifest_version='v2.0.0',
            managed_by_tier1=True,
            auto_update_enabled=True,
            sync_status='synced',
            last_heartbeat=datetime.utcnow() - timedelta(minutes=1),
            last_sync=datetime.utcnow() - timedelta(minutes=12),
            device_count=18,
            resource_usage={'cpu': 40, 'memory': 55, 'disk': 45}
        )
        session.add(angie_washington_hub)
        print(f"  ✅ Created HA Hub: {angie_washington_hub.hostname} (K3s enabled)")

        # =================================================================
        # ADD SAMPLE SMART DEVICES FOR EACH PROPERTY
        # =================================================================
        print("\n💡 Adding sample smart devices...")

        # George-Barsa devices
        george_devices = create_sample_devices(george_barsa_id, george_barsa_hub_id, "George-Barsa", 8)
        for device in george_devices:
            session.add(device)
        print(f"  ✅ Added {len(george_devices)} devices to George-Barsa")

        # Gerardo-Washington devices
        gerardo_devices = create_sample_devices(gerardo_washington_id, gerardo_washington_hub_id, "Gerardo-Washington", 12)
        for device in gerardo_devices:
            session.add(device)
        print(f"  ✅ Added {len(gerardo_devices)} devices to Gerardo-Washington")

        # Misael-Cicero devices
        misael_devices = create_sample_devices(misael_cicero_id, misael_cicero_hub_id, "Misael-Cicero", 20)
        for device in misael_devices:
            session.add(device)
        print(f"  ✅ Added {len(misael_devices)} devices to Misael-Cicero")

        # New England devices
        new_england_devices = create_sample_devices(new_england_id, new_england_hub_id, "New England", 35)
        for device in new_england_devices:
            session.add(device)
        print(f"  ✅ Added {len(new_england_devices)} devices to New England")

        # Angie-Washington devices
        angie_devices = create_sample_devices(angie_washington_id, angie_washington_hub_id, "Angie-Washington", 18)
        for device in angie_devices:
            session.add(device)
        print(f"  ✅ Added {len(angie_devices)} devices to Angie-Washington")

        # Commit all data
        await session.commit()

        print("\n" + "=" * 80)
        print("🎉 Successfully seeded all 5 Somni properties!")
        print("\n📊 Summary:")
        print(f"   📍 5 Properties created")
        print(f"   🏢 5 Buildings created")
        print(f"   🏠 5 Units created")
        print(f"   🖥️  5 Home Assistant hubs configured:")
        print(f"      - 2 Tier 1 (Basic): George-Barsa, Gerardo-Washington")
        print(f"      - 3 Tier 2 (Advanced): Misael-Cicero, New England, Angie-Washington")
        print(f"   💡 {8+12+20+35+18} Smart devices total")
        print("\n✨ All properties are now available in SomniProperty Manager!")
        print("   🌐 View at: https://somniproperty.home.lan")


def create_sample_devices(property_id, hub_id, property_name, count):
    """Create sample smart devices for a property"""
    devices = []
    device_types = [
        ('light', 'living_room', 'Living Room Light', 'Philips', 'Hue White Ambiance'),
        ('lock', 'front_door', 'Front Door Lock', 'Yale', 'Assure Lock SL'),
        ('climate', 'thermostat', 'Thermostat', 'Ecobee', 'SmartThermostat'),
        ('binary_sensor', 'motion', 'Motion Detector', 'Aqara', 'Motion Sensor'),
        ('switch', 'bedroom_lamp', 'Bedroom Lamp', 'TP-Link', 'Kasa Smart Plug'),
        ('sensor', 'temperature', 'Temperature Sensor', 'Aqara', 'Temp & Humidity'),
        ('light', 'kitchen', 'Kitchen Light', 'IKEA', 'TRADFRI'),
        ('lock', 'back_door', 'Back Door Lock', 'Schlage', 'Encode WiFi'),
        ('binary_sensor', 'leak', 'Leak Detector', 'Aqara', 'Water Leak Sensor'),
        ('camera', 'front_door', 'Front Door Camera', 'Wyze', 'Cam v3'),
        ('light', 'bedroom', 'Bedroom Light', 'Philips', 'Hue Color'),
        ('switch', 'patio', 'Patio Outlet', 'TP-Link', 'Outdoor Smart Plug'),
        ('sensor', 'humidity', 'Humidity Sensor', 'Aqara', 'Temp & Humidity'),
        ('binary_sensor', 'door', 'Door Sensor', 'Aqara', 'Door/Window Sensor'),
        ('light', 'bathroom', 'Bathroom Light', 'IKEA', 'TRADFRI'),
        ('climate', 'mini_split', 'Mini Split AC', 'Mitsubishi', 'M-Series'),
        ('camera', 'garage', 'Garage Camera', 'Wyze', 'Cam Pan'),
        ('lock', 'garage_door', 'Garage Lock', 'Chamberlain', 'MyQ Smart Lock'),
        ('sensor', 'energy', 'Energy Monitor', 'Emporia', 'Vue 2'),
        ('switch', 'garage_lights', 'Garage Lights', 'GE', 'Smart Switch'),
    ]

    for i in range(min(count, len(device_types))):
        domain, entity, name, manufacturer, model = device_types[i]

        device = SmartDevice(
            id=uuid.uuid4(),
            property_id=property_id,
            sync_source='home_assistant',
            synced_from_hub_id=hub_id,
            last_synced_at=datetime.utcnow() - timedelta(minutes=10),
            home_assistant_entity_id=f'{domain}.{entity}_{i}',
            ha_domain=domain,
            ha_state='on' if domain in ['light', 'switch'] else 'locked' if domain == 'lock' else 'idle',
            ha_attributes={'brightness': 200} if domain == 'light' else {},
            device_name=f"{name} {i+1}" if count > len(device_types) else name,
            device_type=domain,
            manufacturer=manufacturer,
            model=model,
            status='active',
            health_status='healthy',
            battery_level=85 if domain in ['binary_sensor', 'sensor', 'lock'] else None,
            last_seen=datetime.utcnow() - timedelta(minutes=2),
            location=f"{property_name} - Main Floor"
        )
        devices.append(device)

    return devices


if __name__ == "__main__":
    asyncio.run(seed_all_properties())
