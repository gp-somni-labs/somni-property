"""
Register existing standalone Home Assistant instances as Tier 0 nodes

This script registers your 5 existing self-managed Home Assistant instances
into SomniProperty as Tier 0 (Standalone) nodes.

INSTRUCTIONS:
1. Fill in the EXISTING_HA_INSTANCES array below with your actual data
2. Get Tailscale IPs: run `tailscale status` and find your HA instances
3. Get HA URLs: usually http://<tailscale_ip>:8123
4. Run: python register_tier0_instances.py

The script will:
- Create a property for each location (or use existing if you provide property_id)
- Register each HA instance as a Tier 0 node
- Set managed_by_tier1=False (self-managed)
- Set auto_update_enabled=False (no auto-updates)
- Mark sync_status as 'never_synced' initially
"""

import asyncio
import uuid
from datetime import datetime
from db.database import AsyncSessionLocal
from db.models import Property, PropertyEdgeNode

# ============================================================================
# TODO: FILL IN YOUR ACTUAL HOME ASSISTANT INSTANCE DATA BELOW
# ============================================================================

EXISTING_HA_INSTANCES = [
    {
        "property_name": "My Home",  # TODO: Change to actual property name
        "hostname": "ha-myhome",  # TODO: Change to actual hostname
        "tailscale_ip": "100.64.X.X",  # TODO: Get from: tailscale status
        "ha_url": "http://100.64.X.X:8123",  # TODO: Change X.X to actual IP
        "notes": "My personal residence - migrated from ha-manager",
        # Optional: If property already exists in database, provide its UUID
        "property_id": None,  # Or: "existing-property-uuid-here"
    },
    {
        "property_name": "Rental Property 1",
        "hostname": "ha-rental-1",
        "tailscale_ip": "100.64.X.X",  # TODO: Fill in
        "ha_url": "http://100.64.X.X:8123",
        "notes": "Single family rental - migrated from ha-manager",
        "property_id": None,
    },
    {
        "property_name": "Rental Property 2",
        "hostname": "ha-rental-2",
        "tailscale_ip": "100.64.X.X",  # TODO: Fill in
        "ha_url": "http://100.64.X.X:8123",
        "notes": "Apartment rental - migrated from ha-manager",
        "property_id": None,
    },
    {
        "property_name": "Vacation Home",
        "hostname": "ha-vacation",
        "tailscale_ip": "100.64.X.X",  # TODO: Fill in
        "ha_url": "http://100.64.X.X:8123",
        "notes": "Vacation property - migrated from ha-manager",
        "property_id": None,
    },
    {
        "property_name": "Parent's House",
        "hostname": "ha-parents",
        "tailscale_ip": "100.64.X.X",  # TODO: Fill in
        "ha_url": "http://100.64.X.X:8123",
        "notes": "Family property - migrated from ha-manager",
        "property_id": None,
    },
]

# ============================================================================
# REGISTRATION SCRIPT - DO NOT MODIFY BELOW THIS LINE
# ============================================================================

async def register_instances():
    """Register all existing HA instances as Tier 0 nodes"""
    async with AsyncSessionLocal() as session:
        print("=" * 70)
        print("🏠 Registering Tier 0 (Standalone) Home Assistant Instances")
        print("=" * 70)
        print()

        registered_count = 0

        for idx, ha in enumerate(EXISTING_HA_INSTANCES, 1):
            print(f"[{idx}/{ len(EXISTING_HA_INSTANCES)}] Processing: {ha['property_name']}")

            # Validate required fields
            if "100.64.X.X" in ha.get("tailscale_ip", ""):
                print(f"  ⚠️  SKIPPED: Please fill in the actual Tailscale IP")
                print()
                continue

            # Create or use existing property
            if ha.get("property_id"):
                property_id = uuid.UUID(ha["property_id"])
                print(f"  📍 Using existing property: {property_id}")
            else:
                property_id = uuid.uuid4()
                property = Property(
                    id=property_id,
                    name=ha["property_name"],
                    address_line1="TBD",  # User can update via UI later
                    city="TBD",
                    state="TBD",
                    zip_code="00000",
                    property_type="residential"
                )
                session.add(property)
                print(f"  ✅ Created new property: {ha['property_name']}")

            # Register as Tier 0 node
            node_id = uuid.uuid4()
            node = PropertyEdgeNode(
                id=node_id,
                property_id=property_id,

                # Tier 0 Configuration
                hub_type='tier_0_standalone',  # NEW: Tier 0 type
                managed_by_tier1=False,  # Self-managed
                auto_update_enabled=False,  # No automated updates

                # Connection Info
                hostname=ha["hostname"],
                tailscale_ip=ha["tailscale_ip"],
                api_url=ha["ha_url"],

                # Status
                status='online',  # Assume online, will update via health checks
                sync_status='never_synced',  # Will sync via HA integration addon

                # Metadata
                node_type='home_assistant',
                notes=ha.get("notes", "Migrated from ha-manager")
            )
            session.add(node)
            print(f"  ✅ Registered Tier 0 node: {ha['hostname']}")
            print(f"     • Tailscale IP: {ha['tailscale_ip']}")
            print(f"     • HA URL: {ha['ha_url']}")
            print(f"     • Management: Self-managed (Tier 0)")
            print()

            registered_count += 1

        # Commit all changes
        if registered_count > 0:
            await session.commit()
            print("=" * 70)
            print(f"🎉 Successfully registered {registered_count} Tier 0 nodes!")
            print("=" * 70)
            print()
            print("Next Steps:")
            print("1. Visit https://property.home.lan to view your Tier 0 nodes")
            print("2. Navigate to 'Edge Nodes' and filter by 'Tier 0'")
            print("3. Install the SomniProperty HA integration addon on each instance")
            print("4. Configure the addon with this Master Hub's API endpoint")
            print("5. Device sync will begin automatically once configured")
            print()
        else:
            print("⚠️  No instances were registered.")
            print("Please fill in the EXISTING_HA_INSTANCES data at the top of this script.")
            print()


if __name__ == "__main__":
    print()
    print("Starting Tier 0 registration...")
    print()
    asyncio.run(register_instances())
