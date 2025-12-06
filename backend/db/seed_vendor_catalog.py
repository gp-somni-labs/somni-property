#!/usr/bin/env python3
"""
Vendor product catalog organized by domain for quote builder
"""

VENDOR_CATALOG = {
    "network": {
        "domain_name": "Network Infrastructure",
        "domain_icon": "🌐",
        "description": "Enterprise-grade networking for reliable connectivity",
        "products": [
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Switch 8 (60W)",
                "product_category": "switch",
                "unit_price": 109.00,
                "description": "8-port Gigabit PoE switch, perfect for small deployments",
                "installation_time_hours": 0.5,
                "specs": {"ports": 8, "poe_budget": "60W", "mounting": "Desktop/Wall"}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Switch 24 PoE (250W)",
                "product_category": "switch",
                "unit_price": 379.00,
                "description": "24-port Gigabit PoE+ switch for medium deployments",
                "installation_time_hours": 1.0,
                "specs": {"ports": 24, "poe_budget": "250W", "mounting": "Rack"}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Switch 48 PoE (750W)",
                "product_category": "switch",
                "unit_price": 749.00,
                "description": "48-port Gigabit PoE+ switch for large deployments",
                "installation_time_hours": 1.5,
                "specs": {"ports": 48, "poe_budget": "750W", "mounting": "Rack"}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi AP U6 Lite",
                "product_category": "access_point",
                "unit_price": 99.00,
                "description": "WiFi 6 access point for standard coverage",
                "installation_time_hours": 0.5,
                "specs": {"wifi_standard": "WiFi 6", "coverage": "1,500 sq ft", "max_clients": 150}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi AP U6 Long-Range",
                "product_category": "access_point",
                "unit_price": 179.00,
                "description": "WiFi 6 long-range for large areas",
                "installation_time_hours": 0.5,
                "specs": {"wifi_standard": "WiFi 6", "coverage": "3,000 sq ft", "max_clients": 300}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Dream Machine Pro (UDM-Pro)",
                "product_category": "gateway",
                "unit_price": 379.00,
                "description": "Professional rack-mount gateway with IDS/IPS",
                "installation_time_hours": 2.0,
                "specs": {"throughput": "3.5 Gbps", "rack_mount": True, "protect_nvr": "Supports 20 cameras"}
            }
        ]
    },
    "lighting": {
        "domain_name": "Smart Lighting",
        "domain_icon": "💡",
        "description": "Energy-efficient smart lighting solutions",
        "products": [
            {
                "vendor_name": "Philips Hue",
                "product_name": "White A19 Bulb",
                "product_category": "bulb",
                "unit_price": 14.99,
                "description": "Basic white smart bulb, dimmable",
                "installation_time_hours": 0.1,
                "specs": {"color": "White only", "brightness": "800 lumens", "dimm able": True}
            },
            {
                "vendor_name": "Philips Hue",
                "product_name": "White and Color Ambiance A19 Bulb",
                "product_category": "bulb",
                "unit_price": 49.99,
                "description": "Full color smart bulb with 16 million colors",
                "installation_time_hours": 0.1,
                "specs": {"color": "16M colors", "brightness": "800 lumens", "dimmable": True}
            },
            {
                "vendor_name": "Philips Hue",
                "product_name": "Hue Bridge",
                "product_category": "hub",
                "unit_price": 59.99,
                "description": "Zigbee hub required for Hue system (supports up to 50 bulbs)",
                "installation_time_hours": 0.5,
                "specs": {"protocol": "Zigbee", "max_devices": 50, "required": "Yes for Hue"}
            },
            {
                "vendor_name": "Lutron",
                "product_name": "Caseta Smart Dimmer Switch",
                "product_category": "switch",
                "unit_price": 59.95,
                "description": "WiFi dimmer switch, works with existing wiring",
                "installation_time_hours": 0.5,
                "specs": {"type": "Dimmer", "protocol": "WiFi", "works_with": "Alexa, Google, HomeKit"}
            },
            {
                "vendor_name": "Lutron",
                "product_name": "Caseta Smart Hub (Bridge)",
                "product_category": "hub",
                "unit_price": 79.95,
                "description": "Central controller for Caseta devices",
                "installation_time_hours": 0.5,
                "specs": {"max_devices": 75, "required": "For advanced features"}
            }
        ]
    },
    "security": {
        "domain_name": "Security & Cameras",
        "domain_icon": "🎥",
        "description": "Professional security camera systems",
        "products": [
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Protect G4 Bullet Camera",
                "product_category": "camera",
                "unit_price": 199.00,
                "description": "4MP bullet camera with night vision",
                "installation_time_hours": 1.0,
                "specs": {"resolution": "4MP", "night_vision": "IR LEDs", "poe": True, "weatherproof": "IP67"}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Protect G4 Dome Camera",
                "product_category": "camera",
                "unit_price": 199.00,
                "description": "4MP dome camera with night vision",
                "installation_time_hours": 1.0,
                "specs": {"resolution": "4MP", "night_vision": "IR LEDs", "poe": True, "vandal_resistant": True}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Protect G4 Doorbell",
                "product_category": "doorbell",
                "unit_price": 199.00,
                "description": "Smart doorbell camera with two-way audio",
                "installation_time_hours": 1.5,
                "specs": {"resolution": "5MP", "two_way_audio": True, "poe": True, "package_detection": True}
            },
            {
                "vendor_name": "Ring",
                "product_name": "Ring Video Doorbell Pro 2",
                "product_category": "doorbell",
                "unit_price": 249.99,
                "description": "Premium doorbell camera with 3D motion detection",
                "installation_time_hours": 1.0,
                "specs": {"resolution": "1536p HD", "3d_motion": True, "bird_eye_view": True}
            },
            {
                "vendor_name": "Ring",
                "product_name": "Ring Protect Basic Plan",
                "product_category": "subscription",
                "unit_price": 4.99,
                "pricing_model": "monthly",
                "description": "Cloud recording for 1 camera, 180-day video history",
                "specs": {"cameras": 1, "history_days": 180}
            }
        ]
    },
    "locks": {
        "domain_name": "Smart Locks & Access Control",
        "domain_icon": "🔐",
        "description": "Secure smart lock and access control systems",
        "products": [
            {
                "vendor_name": "August",
                "product_name": "August WiFi Smart Lock (4th Gen)",
                "product_category": "smart_lock",
                "unit_price": 229.99,
                "description": "WiFi-enabled deadbolt, works with existing keys",
                "installation_time_hours": 0.75,
                "specs": {"connectivity": "WiFi", "works_with_existing_key": True, "auto_lock": True, "door_sense": True}
            },
            {
                "vendor_name": "August",
                "product_name": "August Smart Lock Pro",
                "product_category": "smart_lock",
                "unit_price": 279.99,
                "description": "Pro model with Z-Wave and remote access",
                "installation_time_hours": 0.75,
                "specs": {"connectivity": "WiFi + Z-Wave", "works_with_existing_key": True, "auto_lock": True, "remote_access": True}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Access Hub",
                "product_category": "access_control_hub",
                "unit_price": 189.00,
                "description": "Central access control hub for professional systems",
                "installation_time_hours": 1.5,
                "specs": {"max_readers": 32, "max_users": "Unlimited", "poe": True}
            },
            {
                "vendor_name": "Ubiquiti",
                "product_name": "UniFi Access Reader Lite",
                "product_category": "card_reader",
                "unit_price": 79.00,
                "description": "NFC card reader for doors",
                "installation_time_hours": 1.0,
                "specs": {"type": "NFC", "weatherproof": "IP54", "poe": True}
            }
        ]
    },
    "climate": {
        "domain_name": "Climate Control",
        "domain_icon": "🌡️",
        "description": "Smart thermostats and HVAC control",
        "products": [
            {
                "vendor_name": "Google Nest",
                "product_name": "Nest Learning Thermostat (3rd Gen)",
                "product_category": "thermostat",
                "unit_price": 249.00,
                "description": "Smart learning thermostat with auto-schedule",
                "installation_time_hours": 1.0,
                "specs": {"learning": True, "remote_control": True, "energy_history": True, "works_with": "Alexa, Google"}
            },
            {
                "vendor_name": "Google Nest",
                "product_name": "Nest Thermostat",
                "product_category": "thermostat",
                "unit_price": 129.99,
                "description": "Budget smart thermostat with scheduling",
                "installation_time_hours": 0.75,
                "specs": {"learning": False, "scheduling": True, "remote_control": True, "energy_saving": True}
            }
        ]
    },
    "sensors": {
        "domain_name": "Sensors & Automation",
        "domain_icon": "📡",
        "description": "Advanced sensors for presence, environment, and automation",
        "products": [
            {
                "vendor_name": "Apollo Automations",
                "product_name": "MSR-1 mmWave Sensor",
                "product_category": "presence_sensor",
                "unit_price": 39.99,
                "description": "Basic mmWave presence detection, ESPHome compatible",
                "installation_time_hours": 0.5,
                "specs": {"detection_type": "mmWave", "esphome": True, "range": "16 ft"}
            },
            {
                "vendor_name": "Apollo Automations",
                "product_name": "MSR-2 mmWave Multi-Sensor",
                "product_category": "multi_sensor",
                "unit_price": 59.99,
                "description": "Presence + temperature + humidity + lux",
                "installation_time_hours": 0.5,
                "specs": {"sensors": ["mmWave", "Temperature", "Humidity", "Lux"], "esphome": True}
            },
            {
                "vendor_name": "Apollo Automations",
                "product_name": "MTR-1 mmWave Multi-Tool",
                "product_category": "multi_sensor",
                "unit_price": 79.99,
                "description": "Advanced sensor with CO2 + VOC monitoring",
                "installation_time_hours": 0.5,
                "specs": {"sensors": ["mmWave", "Temp", "Humidity", "Lux", "CO2", "VOC"], "esphome": True}
            },
            {
                "vendor_name": "Shelly",
                "product_name": "Shelly 1 (WiFi Smart Relay)",
                "product_category": "relay",
                "unit_price": 14.95,
                "description": "Basic WiFi relay for any device, no hub required",
                "installation_time_hours": 0.5,
                "specs": {"connectivity": "WiFi", "max_load": "16A", "hub_required": False}
            },
            {
                "vendor_name": "Shelly",
                "product_name": "Shelly 1PM (WiFi Relay + Power Metering)",
                "product_category": "relay",
                "unit_price": 19.95,
                "description": "WiFi relay with energy monitoring",
                "installation_time_hours": 0.5,
                "specs": {"connectivity": "WiFi", "power_metering": True, "max_load": "16A"}
            },
            {
                "vendor_name": "Shelly",
                "product_name": "Shelly Dimmer 2",
                "product_category": "dimmer",
                "unit_price": 29.95,
                "description": "WiFi dimmer for LED lighting control",
                "installation_time_hours": 0.75,
                "specs": {"connectivity": "WiFi", "dimmable": True, "max_load": "200W"}
            }
        ]
    }
}


# Installation labor rates
INSTALLATION_RATES = {
    "standard_hourly": 150.00,
    "professional_hourly": 120.00,  # For service hours subscribers
    "bulk_discount_10_plus": 0.10,  # 10% off for 10+ devices
    "bulk_discount_25_plus": 0.15,  # 15% off for 25+ devices
    "bulk_discount_50_plus": 0.20   # 20% off for 50+ devices
}


# Setup/installation package (included with all quotes)
SETUP_PACKAGE = {
    "name": "Initial Setup & Configuration",
    "included_hours": 2,
    "description": "All installations include 2 hours of setup support",
    "includes": [
        "System planning and design consultation",
        "Network configuration and optimization",
        "Device pairing and integration",
        "Initial automation setup",
        "Training session for property managers"
    ]
}
