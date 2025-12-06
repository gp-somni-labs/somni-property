# Tier 0 Device Sync Design

## Overview

Tier 0 (Standalone) nodes are existing Home Assistant instances that sync their devices to SomniProperty Master Hub but remain self-managed. They do not receive K8s deployments.

## Architecture

```
┌────────────────────────────────────┐
│  Tier 0 Node                       │
│  (Standalone Home Assistant)       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ SomniProperty HA Integration │  │  (Future: Custom Component)
│  │ - Discovers entities         │  │
│  │ - Sends to Master Hub        │  │
│  │ - Periodic sync (5 min)      │  │
│  └──────────────────────────────┘  │
└─────────────┬───────────────────────┘
              │ HTTPS POST
              │ /api/v1/sync/devices
              ▼
┌────────────────────────────────────┐
│  Tier 1 (Master Hub)               │
│  SomniProperty Backend             │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ HubSyncService               │  │
│  │ - process_device_sync()      │  │
│  │ - Creates/updates devices    │  │
│  │ - Records sync metadata      │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

## Sync API Endpoint

### POST /api/v1/sync/devices

**Authentication:**
- Hub ID via header: `X-Hub-ID: <node-uuid>`
- Token via header: `Authorization: Bearer <token>` (optional for Tier 0, required for Tier 2/3)

**Request Body:**
```json
{
  "devices": [
    {
      "entity_id": "light.living_room",
      "name": "Living Room Light",
      "device_type": "light",
      "manufacturer": "Philips",
      "model": "Hue Bulb",
      "ha_domain": "light",
      "ha_state": "on",
      "ha_attributes": {
        "brightness": 255,
        "color_temp": 370
      },
      "location": "Living Room",
      "battery_level": null,
      "signal_strength": -50
    },
    {
      "entity_id": "sensor.temperature_bedroom",
      "name": "Bedroom Temperature",
      "device_type": "sensor",
      "manufacturer": "Xiaomi",
      "model": "Temperature Sensor",
      "ha_domain": "sensor",
      "ha_state": "21.5",
      "ha_attributes": {
        "unit_of_measurement": "°C",
        "device_class": "temperature"
      },
      "location": "Bedroom",
      "battery_level": 95,
      "signal_strength": -60
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "hub_id": "12345678-1234-1234-1234-123456789012",
  "devices_discovered": 150,
  "devices_added": 5,
  "devices_updated": 145,
  "devices_removed": 0,
  "sync_started_at": "2025-10-31T12:00:00Z",
  "sync_completed_at": "2025-10-31T12:00:05Z"
}
```

## Device Discovery Logic

The HA integration addon will:

1. **Query all entities** from Home Assistant using `hass.states.async_all()`
2. **Filter relevant entities** - exclude unavailable, unknown, etc.
3. **Map HA entity to SmartDevice schema:**
   - `entity_id` → `home_assistant_entity_id`
   - `state.state` → `ha_state`
   - `state.attributes` → `ha_attributes` (JSON)
   - Extract `friendly_name` → `device_name`
   - Extract `device_class` → used for `device_type` mapping
   - Extract device info (manufacturer, model) from `device_registry`

4. **Detect device type from domain:**
   - `light` → `smart_bulb`
   - `switch` → `smart_plug`
   - `sensor` → `sensor`
   - `binary_sensor` → `sensor`
   - `climate` → `thermostat`
   - `lock` → `smart_lock`
   - `camera` → `camera`
   - `cover` → `smart_lock` (for garage doors) or skip
   - `fan` → `other`
   - `media_player` → `other`

5. **Send to Master Hub** every 5 minutes (configurable)

## Sync Processing on Master Hub

When receiving a sync from Tier 0:

1. **Validate hub exists** and is Tier 0 (backend/services/hub_sync_service.py:19-28)
2. **Create DeviceSync record** to track sync operation
3. **Compare incoming devices with database:**
   - New `entity_id` → Create `SmartDevice` with `sync_source='home_assistant'`
   - Existing `entity_id` → Update `ha_state`, `ha_attributes`, `last_synced_at`
   - Missing `entity_id` (was in DB, not in sync) → Mark as inactive or delete
4. **Update hub sync status:**
   - `hub.sync_status = 'synced'`
   - `hub.last_sync = now()`
   - `hub.sync_error_message = None`
5. **Return sync summary** to HA instance

## Testing Without HA Integration

Use the test script (`test_tier0_sync.py`) to simulate a Tier 0 node sending devices:

```bash
cd backend
python test_tier0_sync.py --hub-id <tier-0-node-uuid>
```

This will:
- Send mock Home Assistant devices to the sync API
- Display the sync response
- Verify devices were created in database

## Home Assistant Integration Addon (Future)

### Structure:
```
custom_components/somniproperty/
├── __init__.py           # Integration setup
├── manifest.json         # Integration metadata
├── config_flow.py        # Configuration UI
├── const.py              # Constants
├── sync_service.py       # Device sync logic
└── strings.json          # Translations
```

### Configuration:
- **Master Hub URL**: http://somniproperty-backend.somniproperty.svc.cluster.local:8000 (or Tailscale IP)
- **Hub ID**: UUID from Tier 0 registration
- **Sync Interval**: 300 seconds (default)
- **Token**: Optional for Tier 0

### Installation:
1. Copy custom component to HA config directory
2. Restart Home Assistant
3. Add integration via UI
4. Enter Master Hub URL and Hub ID
5. Sync starts automatically

## Security Considerations

For Tier 0 (Standalone) nodes:
- **No token required** initially (simplified onboarding)
- Hub ID in header is sufficient for identification
- Future: Add optional API token for enhanced security
- All communication over Tailscale mesh (encrypted)

For Tier 2/3 (Managed) nodes:
- **Token required** (`hub.api_token_hash` bcrypt validation)
- Token generated during deployment
- Token rotation supported via API

## Sync Frequency

- **Default**: Every 5 minutes
- **On-demand**: User clicks "Sync Devices" button in UI (calls `POST /api/v1/sync/trigger/{hub_id}`)
- **Event-driven**: HA integration can trigger sync on significant state changes (optional future enhancement)

## Error Handling

If sync fails:
- `hub.sync_status = 'error'`
- `hub.sync_error_message = <error details>`
- DeviceSync record contains full error traceback
- HA integration retries after 5 minutes

## Monitoring

- **UI**: Edge Node Detail page shows sync status, last sync time, error messages
- **API**: `GET /api/v1/edge-nodes/{id}` includes sync metadata
- **DeviceSync table**: Full audit trail of all sync operations

## Backward Compatibility

- Existing manual devices (`sync_source='manual'`) are not affected
- Device monitoring service (work order creation) only monitors synced devices
- Tier 0 nodes cannot receive deployments (filtered out in UI and API)

---

**Status**: Design complete, backend APIs implemented, frontend UI deployed. Next: Create HA integration addon or use test script for validation.
