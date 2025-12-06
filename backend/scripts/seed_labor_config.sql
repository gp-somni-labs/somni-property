-- Seed Labor Configuration Data
-- Comprehensive vendor-specific installation times and materials

-- ============================================================================
-- 1. Labor Rates
-- ============================================================================
INSERT INTO labor_rates (category, rate_per_hour, description, is_active) VALUES
('installation', 85.00, 'Physical device installation and mounting', true),
('configuration', 95.00, 'Device setup, network configuration, and system integration', true),
('testing', 75.00, 'Testing, commissioning, and quality assurance', true),
('training', 65.00, 'Customer training and documentation', true),
('troubleshooting', 110.00, 'Diagnostic and repair work', true)
ON CONFLICT (category) DO UPDATE SET
  rate_per_hour = EXCLUDED.rate_per_hour,
  description = EXCLUDED.description,
  updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 2. Installation Times - Smart Locks (Vendor-Specific)
-- ============================================================================
INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
('smart_lock', 0.75, 0.50, 'installation', 'Standard smart lock installation - Yale, Schlage, August, Kwikset'),
('smart_deadbolt', 0.90, 0.60, 'installation', 'Smart deadbolt with keypad - requires drilling and wiring'),
('keyless_entry', 0.60, 0.40, 'installation', 'Keyless entry pad - surface mount'),
('lock_retrofit', 1.25, 0.75, 'installation', 'Retrofitting existing lock with smart module')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 3. Installation Times - Cameras & Security
-- ============================================================================
INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
('camera', 1.00, 0.75, 'installation', 'IP camera - indoor/outdoor, wired/wireless'),
('doorbell_camera', 1.25, 0.90, 'installation', 'Video doorbell - wiring, chime integration'),
('ptz_camera', 1.75, 1.25, 'installation', 'Pan-tilt-zoom camera - requires advanced mounting'),
('nvr', 2.00, 0.50, 'installation', 'Network video recorder - rack mount, cabling'),
('motion_sensor', 0.30, 0.20, 'installation', 'Wireless motion detector'),
('contact_sensor', 0.25, 0.15, 'installation', 'Door/window contact sensor'),
('glass_break_sensor', 0.50, 0.35, 'installation', 'Acoustic glass break detector'),
('security_panel', 1.50, 0.00, 'installation', 'Central security control panel')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 4. Installation Times - Climate Control
-- ============================================================================
INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
('thermostat', 0.75, 0.50, 'installation', 'Smart thermostat - C-wire present'),
('thermostat_no_c_wire', 1.50, 1.00, 'installation', 'Smart thermostat - requires C-wire installation'),
('smart_vent', 0.40, 0.30, 'installation', 'Smart HVAC vent - register replacement'),
('temp_sensor', 0.30, 0.20, 'installation', 'Remote temperature sensor'),
('humidity_sensor', 0.30, 0.20, 'installation', 'Humidity monitoring sensor'),
('hvac_controller', 2.00, 1.50, 'installation', 'Whole-home HVAC zone controller')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 5. Installation Times - Lighting
-- ============================================================================
INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
('smart_switch', 0.50, 0.35, 'installation', 'Smart light switch - neutral wire present'),
('smart_switch_no_neutral', 0.90, 0.60, 'installation', 'Smart switch - no neutral wire (requires special switch)'),
('smart_dimmer', 0.60, 0.40, 'installation', 'Smart dimmer switch'),
('smart_bulb', 0.15, 0.10, 'installation', 'Smart LED bulb - simple replacement'),
('smart_plug', 0.10, 0.05, 'installation', 'Smart outlet/plug - plug-in device'),
('outlet_smart', 0.60, 0.40, 'installation', 'Smart outlet - hardwired replacement'),
('led_strip', 0.75, 0.50, 'installation', 'LED strip lighting - adhesive mount, power'),
('outdoor_lighting', 1.00, 0.75, 'installation', 'Outdoor smart lighting - weatherproof installation')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 6. Installation Times - Hubs & Controllers
-- ============================================================================
INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
('hub', 1.00, 0.30, 'installation', 'Smart home hub - Zigbee/Z-Wave/Thread controller'),
('bridge', 0.75, 0.25, 'installation', 'Protocol bridge - Philips Hue, IKEA, etc.'),
('gateway', 1.25, 0.50, 'installation', 'Network gateway with rack mount'),
('voice_assistant', 0.40, 0.20, 'installation', 'Voice assistant speaker - plug and play'),
('display_hub', 0.75, 0.40, 'installation', 'Smart display with hub functionality')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 7. Installation Times - Sensors & Automation
-- ============================================================================
INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
('leak_sensor', 0.25, 0.15, 'installation', 'Water leak detector - battery powered'),
('smoke_detector', 0.60, 0.40, 'installation', 'Smart smoke/CO detector - hardwired'),
('smoke_detector_battery', 0.30, 0.20, 'installation', 'Smart smoke detector - battery only'),
('air_quality_sensor', 0.40, 0.25, 'installation', 'Air quality monitor - plug-in or battery'),
('occupancy_sensor', 0.35, 0.25, 'installation', 'Occupancy/presence detector'),
('light_sensor', 0.30, 0.20, 'installation', 'Ambient light sensor'),
('energy_monitor', 1.50, 1.00, 'installation', 'Whole-home energy monitor - breaker panel install'),
('valve_controller', 1.25, 0.90, 'installation', 'Smart water valve/shutoff')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 8. Installation Times - Media & Entertainment
-- ============================================================================
INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
('tv', 2.00, 1.50, 'installation', 'Wall-mounted TV with concealed wiring'),
('soundbar', 0.75, 0.50, 'installation', 'Soundbar installation and configuration'),
('speaker', 0.60, 0.40, 'installation', 'Wireless speaker - wall mount or stand'),
('receiver', 1.50, 0.75, 'installation', 'AV receiver - rack mount with wiring'),
('streaming_device', 0.30, 0.20, 'installation', 'Streaming media player - plug and play')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 9. Installation Times - Garage & Outdoor
-- ============================================================================
INSERT INTO installation_times (device_category, first_unit_hours, additional_unit_hours, labor_category, description) VALUES
('garage_door_opener', 1.50, 1.00, 'installation', 'Smart garage door controller with sensors'),
('sprinkler_controller', 2.00, 1.25, 'installation', 'Smart irrigation system controller'),
('outdoor_camera', 1.50, 1.00, 'installation', 'Outdoor security camera - weatherproof, wiring'),
('outdoor_sensor', 0.75, 0.50, 'installation', 'Outdoor motion/temp sensor - weatherproof')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 10. Device Materials (per device installation)
-- ============================================================================
INSERT INTO labor_materials (device_category, material_name, quantity_per_device, cost_per_unit, description) VALUES
-- Smart Locks
('smart_lock', 'Mounting screws', 4, 0.25, 'Stainless steel screws for lock installation'),
('smart_lock', 'Strike plate', 1, 8.00, 'Reinforced strike plate'),
('smart_deadbolt', 'Deadbolt strike', 1, 12.00, 'Heavy-duty deadbolt strike plate'),
('smart_deadbolt', 'Drill bits', 0.1, 15.00, 'Specialty drill bits for deadbolt holes'),

-- Cameras & Security
('camera', 'CAT6 cable', 50, 0.40, 'Per foot of network cable'),
('camera', 'Wall anchors', 4, 0.50, 'Heavy-duty wall anchors'),
('camera', 'Weatherproof box', 1, 15.00, 'Outdoor junction box for camera'),
('camera', 'Cable clips', 10, 0.10, 'Cable management clips'),
('doorbell_camera', 'Transformer', 0.3, 25.00, '16V-24V doorbell transformer (if needed)'),
('doorbell_camera', 'Chime adapter', 1, 12.00, 'Digital chime compatibility adapter'),
('ptz_camera', 'Heavy-duty mount', 1, 45.00, 'PTZ camera mounting bracket'),
('nvr', 'Hard drive', 1, 120.00, '2TB surveillance-grade HDD'),
('nvr', 'Rack rails', 1, 35.00, 'Server rack mounting rails'),

-- Climate Control
('thermostat', 'Wire nuts', 4, 0.15, 'Electrical wire connectors'),
('thermostat', 'Wall plate', 1, 8.00, 'Decorator wall plate'),
('thermostat_no_c_wire', 'C-wire kit', 1, 35.00, 'Add-a-wire C-wire adapter'),
('thermostat_no_c_wire', 'Electrical wire', 25, 0.30, 'Per foot of 18/5 thermostat wire'),

-- Lighting
('smart_switch', 'Wire nuts', 3, 0.15, 'Electrical wire connectors'),
('smart_switch', 'Wall plate', 1, 3.00, 'Decorator wall plate'),
('smart_switch_no_neutral', 'Neutral adapter', 1, 25.00, 'No-neutral compatibility module'),
('led_strip', 'Aluminum channel', 1, 18.00, 'Per meter of LED channel'),
('led_strip', 'End caps', 2, 2.00, 'LED strip end caps'),
('outdoor_lighting', 'Waterproof connectors', 2, 8.00, 'IP67 waterproof wire connectors'),

-- Hubs & Controllers
('hub', 'Ethernet cable', 1, 12.00, '6ft CAT6 network cable'),
('hub', 'USB power adapter', 1, 15.00, 'High-quality USB power supply'),
('gateway', 'Rack shelf', 0.3, 45.00, 'Vented rack shelf for network equipment'),

-- Sensors
('energy_monitor', 'Current transformers', 2, 35.00, 'Split-core CTs for energy monitoring'),
('valve_controller', 'Ball valve', 1, 85.00, '3/4" motorized ball valve'),
('valve_controller', 'Pipe fittings', 4, 8.00, 'Brass pipe fittings and adapters'),

-- General Materials
('ANY', 'Electrical tape', 0.1, 5.00, 'Professional-grade electrical tape'),
('ANY', 'Cable ties', 5, 0.10, 'UV-resistant cable ties'),
('ANY', 'Label maker tape', 0.5, 8.00, 'Device and wire labeling')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 11. Labor Templates (Task Breakdown)
-- ============================================================================
INSERT INTO labor_templates (device_category, task_name, task_order, hours_per_device, labor_category, description) VALUES
-- Smart Lock Templates
('smart_lock', 'Remove existing lock', 1, 0.15, 'installation', 'Remove old hardware, clean door'),
('smart_lock', 'Install smart lock', 2, 0.35, 'installation', 'Mount lock body, exterior assembly'),
('smart_lock', 'Configure & test', 3, 0.25, 'configuration', 'Pair with hub, test operation'),

-- Camera Templates
('camera', 'Run cabling', 1, 0.40, 'installation', 'Route and terminate network cable'),
('camera', 'Mount camera', 2, 0.30, 'installation', 'Physical mounting and aiming'),
('camera', 'Configure network', 3, 0.20, 'configuration', 'IP config, NVR integration'),
('camera', 'Test & adjust', 4, 0.10, 'testing', 'Verify video quality and motion detection'),

-- Thermostat Templates
('thermostat', 'Remove old thermostat', 1, 0.15, 'installation', 'Remove existing unit, check wiring'),
('thermostat', 'Install C-wire if needed', 2, 0.75, 'installation', 'Run C-wire from furnace (if needed)'),
('thermostat', 'Mount new thermostat', 3, 0.20, 'installation', 'Connect wires, mount to wall'),
('thermostat', 'Configure system', 4, 0.25, 'configuration', 'Setup schedules, integrate with system'),
('thermostat', 'Test HVAC control', 5, 0.15, 'testing', 'Verify heating/cooling/fan operation'),

-- Lighting Templates
('smart_switch', 'Turn off breaker', 1, 0.05, 'installation', 'Safety lockout'),
('smart_switch', 'Remove old switch', 2, 0.10, 'installation', 'Remove existing switch'),
('smart_switch', 'Install smart switch', 3, 0.25, 'installation', 'Wire and mount smart switch'),
('smart_switch', 'Pair with system', 4, 0.10, 'configuration', 'Add to smart home system'),

-- Hub Templates
('hub', 'Network setup', 1, 0.30, 'installation', 'Connect to network, update firmware'),
('hub', 'Configure hub', 2, 0.40, 'configuration', 'Setup accounts, security, integrations'),
('hub', 'Test connectivity', 3, 0.15, 'testing', 'Verify all protocols functioning'),
('hub', 'Document setup', 4, 0.15, 'training', 'Create documentation for customer')
ON CONFLICT DO NOTHING;
