"""
Labor Calculator Service
Intelligently estimates labor costs based on devices, products, and quote configuration
Calculates materials needed and provides detailed line-by-line breakdown
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LaborCalculator:
    """
    Calculate labor costs for smart home installations

    Intelligently estimates:
    - Installation labor based on device types and quantities
    - Configuration time for hubs and systems
    - Testing and commissioning
    - Training and documentation
    - Materials needed for each task
    """

    # Default labor rates by category ($/hour)
    DEFAULT_LABOR_RATES = {
        "installation": Decimal("85.00"),      # Physical installation
        "configuration": Decimal("95.00"),     # Software/system configuration
        "networking": Decimal("100.00"),       # Network setup
        "electrical": Decimal("110.00"),       # Electrical work
        "testing": Decimal("75.00"),           # Testing & QA
        "training": Decimal("65.00"),          # Customer training
        "project_management": Decimal("125.00")  # PM overhead
    }

    # Base installation times by device category (hours for first unit)
    BASE_INSTALLATION_TIMES = {
        "smart_lock": Decimal("1.5"),          # First lock takes longer
        "thermostat": Decimal("1.0"),
        "hub": Decimal("2.0"),                 # Hub/controller setup
        "camera": Decimal("1.5"),
        "doorbell": Decimal("1.25"),
        "sensor": Decimal("0.5"),
        "switch": Decimal("0.75"),
        "outlet": Decimal("0.75"),
        "garage_door": Decimal("2.0"),
        "shade": Decimal("1.0"),
        "irrigation": Decimal("3.0"),
        "leak_detector": Decimal("0.5"),
        "smoke_detector": Decimal("0.75"),
    }

    # Additional time per unit after the first (hours)
    ADDITIONAL_TIME_PER_UNIT = {
        "smart_lock": Decimal("0.75"),
        "thermostat": Decimal("0.5"),
        "hub": Decimal("1.0"),
        "camera": Decimal("0.75"),
        "doorbell": Decimal("0.5"),
        "sensor": Decimal("0.25"),
        "switch": Decimal("0.35"),
        "outlet": Decimal("0.35"),
        "garage_door": Decimal("1.0"),
        "shade": Decimal("0.5"),
        "irrigation": Decimal("1.5"),
        "leak_detector": Decimal("0.25"),
        "smoke_detector": Decimal("0.35"),
    }

    # Materials needed per device type
    TYPICAL_MATERIALS = {
        "smart_lock": [
            {"name": "Mounting screws", "unit": "set", "qty": 1, "cost_per_unit": Decimal("2.50")},
            {"name": "Wire nuts", "unit": "ea", "qty": 2, "cost_per_unit": Decimal("0.25")},
        ],
        "thermostat": [
            {"name": "Wire (18/5)", "unit": "ft", "qty": 25, "cost_per_unit": Decimal("0.35")},
            {"name": "Mounting plate", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("3.00")},
        ],
        "hub": [
            {"name": "CAT6 cable", "unit": "ft", "qty": 50, "cost_per_unit": Decimal("0.25")},
            {"name": "Ethernet keystone", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("2.00")},
            {"name": "Mounting bracket", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("5.00")},
        ],
        "camera": [
            {"name": "CAT6 cable", "unit": "ft", "qty": 75, "cost_per_unit": Decimal("0.25")},
            {"name": "Mounting bracket", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("8.00")},
            {"name": "Weatherproof box", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("12.00")},
        ],
        "doorbell": [
            {"name": "Doorbell wire (18/2)", "unit": "ft", "qty": 30, "cost_per_unit": Decimal("0.20")},
            {"name": "Mounting wedge", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("5.00")},
        ],
        "sensor": [
            {"name": "Mounting tape", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("1.50")},
        ],
        "switch": [
            {"name": "Wire nuts", "unit": "ea", "qty": 3, "cost_per_unit": Decimal("0.25")},
            {"name": "Wall plate", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("1.50")},
        ],
        "outlet": [
            {"name": "Wire nuts", "unit": "ea", "qty": 3, "cost_per_unit": Decimal("0.25")},
            {"name": "Wall plate", "unit": "ea", "qty": 1, "cost_per_unit": Decimal("1.50")},
        ],
    }

    def __init__(self, db_session=None):
        self.db = db_session
        self._labor_rates_cache = None
        self._installation_times_cache = None
        self._additional_times_cache = None
        self._all_installation_configs = None  # New: all config variations
        self._materials_cache = None
        self._cache_loaded = False

    async def _load_config_from_db(self):
        """Load labor configuration from database and cache it"""
        if self._cache_loaded or not self.db:
            return

        try:
            from db.models_labor_config import LaborRate, InstallationTime, DeviceMaterial

            # Load labor rates
            labor_rates = self.db.query(LaborRate).filter(LaborRate.is_active == True).all()
            self._labor_rates_cache = {
                rate.category: rate.rate_per_hour
                for rate in labor_rates
            }

            # Load installation times (all variations: generic, vendor-specific, complexity-specific)
            # Store as nested dict: category -> [(config_dict, priority_score)]
            install_times = self.db.query(InstallationTime).filter(InstallationTime.is_active == True).all()
            self._installation_times_cache = {}
            self._additional_times_cache = {}
            self._all_installation_configs = {}  # New: store all configs for smart matching

            for time_config in install_times:
                category = time_config.device_category

                if category not in self._all_installation_configs:
                    self._all_installation_configs[category] = []

                # Store configuration with metadata for smart matching
                config = {
                    "first_unit_hours": time_config.first_unit_hours,
                    "additional_unit_hours": time_config.additional_unit_hours,
                    "labor_category": time_config.labor_category,
                    "vendor": time_config.vendor,
                    "model": time_config.model,
                    "complexity_type": time_config.complexity_type,
                    "complexity_multiplier": time_config.complexity_multiplier or Decimal("1.00")
                }
                self._all_installation_configs[category].append(config)

                # Also maintain simple caches for generic entries (backwards compatibility)
                if not time_config.vendor and not time_config.model and not time_config.complexity_type:
                    self._installation_times_cache[category] = time_config.first_unit_hours
                    self._additional_times_cache[category] = time_config.additional_unit_hours

            # Load materials
            materials = self.db.query(DeviceMaterial).filter(DeviceMaterial.is_active == True).all()
            self._materials_cache = {}
            for material in materials:
                if material.device_category not in self._materials_cache:
                    self._materials_cache[material.device_category] = []

                self._materials_cache[material.device_category].append({
                    "name": material.material_name,
                    "unit": material.unit,
                    "qty": material.quantity_per_device,
                    "cost_per_unit": material.cost_per_unit
                })

            self._cache_loaded = True
            logger.info("✅ Labor configuration loaded from database")

        except Exception as e:
            logger.warning(f"⚠️  Failed to load labor config from database: {e}")
            logger.info("Using default hardcoded values as fallback")
            self._cache_loaded = False

    def _get_labor_rates(self) -> Dict[str, Decimal]:
        """Get labor rates (from cache or defaults)"""
        if self._labor_rates_cache:
            return self._labor_rates_cache.copy()
        return self.DEFAULT_LABOR_RATES.copy()

    def _get_best_installation_config(
        self,
        category: str,
        vendor: str | None = None,
        model: str | None = None,
        complexity_type: str | None = None
    ) -> Dict:
        """
        Get best matching installation configuration based on vendor, model, and complexity

        Priority order:
        1. Exact match (vendor + model + complexity)
        2. Vendor + model
        3. Vendor + complexity
        4. Complexity only
        5. Vendor only
        6. Generic (no vendor/model/complexity)
        """
        if not self._all_installation_configs or category not in self._all_installation_configs:
            # Fallback to hardcoded defaults
            return {
                "first_unit_hours": self.BASE_INSTALLATION_TIMES.get(category, Decimal("1.0")),
                "additional_unit_hours": self.ADDITIONAL_TIME_PER_UNIT.get(category, Decimal("0.5")),
                "labor_category": "installation",
                "complexity_multiplier": Decimal("1.00")
            }

        configs = self._all_installation_configs[category]

        # Try to find best match using priority scoring
        best_match = None
        best_score = -1

        for config in configs:
            score = 0

            # Exact match (highest priority)
            if (vendor and config.get("vendor") == vendor and
                model and config.get("model") == model and
                complexity_type and config.get("complexity_type") == complexity_type):
                score = 100
            # Vendor + model
            elif vendor and config.get("vendor") == vendor and model and config.get("model") == model:
                score = 80
            # Vendor + complexity
            elif vendor and config.get("vendor") == vendor and complexity_type and config.get("complexity_type") == complexity_type:
                score = 70
            # Complexity only
            elif complexity_type and config.get("complexity_type") == complexity_type and not config.get("vendor") and not config.get("model"):
                score = 60
            # Vendor only
            elif vendor and config.get("vendor") == vendor and not config.get("model") and not config.get("complexity_type"):
                score = 50
            # Generic (fallback)
            elif not config.get("vendor") and not config.get("model") and not config.get("complexity_type"):
                score = 10

            if score > best_score:
                best_score = score
                best_match = config

        if best_match:
            return best_match

        # If no match found, return defaults
        return {
            "first_unit_hours": self.BASE_INSTALLATION_TIMES.get(category, Decimal("1.0")),
            "additional_unit_hours": self.ADDITIONAL_TIME_PER_UNIT.get(category, Decimal("0.5")),
            "labor_category": "installation",
            "complexity_multiplier": Decimal("1.00")
        }

    def _get_installation_time(
        self,
        category: str,
        vendor: str | None = None,
        model: str | None = None,
        complexity_type: str | None = None
    ) -> Tuple[Decimal, Decimal]:
        """
        Get installation time for first unit and additional units with complexity multiplier applied
        Returns: (base_time, additional_time)
        """
        config = self._get_best_installation_config(category, vendor, model, complexity_type)
        multiplier = config.get("complexity_multiplier", Decimal("1.00"))

        base_time = config["first_unit_hours"] * multiplier
        additional_time = config["additional_unit_hours"] * multiplier

        return base_time, additional_time

    def _get_additional_time(self, category: str) -> Decimal:
        """Get additional time per unit (legacy method for backwards compatibility)"""
        if self._additional_times_cache:
            return self._additional_times_cache.get(category, Decimal("0.5"))
        return self.ADDITIONAL_TIME_PER_UNIT.get(category, Decimal("0.5"))

    def _get_materials(self, category: str) -> List[Dict]:
        """Get materials for category (from cache or defaults)"""
        if self._materials_cache:
            return self._materials_cache.get(category, [])
        return self.TYPICAL_MATERIALS.get(category, [])

    async def estimate_labor(
        self,
        quote_id: UUID,
        product_selections: List[Dict],
        include_materials: bool = True,
        labor_rate_override: Optional[Dict[str, Decimal]] = None
    ) -> Dict:
        """
        Estimate labor costs based on product selections

        Args:
            quote_id: UUID of the quote
            product_selections: List of selected products with quantities
                Format: [{"category": "smart_lock", "quantity": 15, "domain": "access_control"}]
            include_materials: Include material costs
            labor_rate_override: Override default labor rates

        Returns:
            Dict with labor items, total costs, and materials
        """

        # Load configuration from database
        await self._load_config_from_db()

        labor_rates = labor_rate_override or self._get_labor_rates()

        labor_items = []
        line_number = 1

        total_labor_hours = Decimal("0")
        total_labor_cost = Decimal("0")
        total_materials_cost = Decimal("0")

        # Group products by category for efficient calculation
        category_quantities = {}
        for product in product_selections:
            category = product.get("category", "").lower()
            quantity = Decimal(str(product.get("quantity", 0)))

            if category in category_quantities:
                category_quantities[category] += quantity
            else:
                category_quantities[category] = quantity

        # Calculate installation labor for each category
        for category, quantity in category_quantities.items():
            if quantity <= 0:
                continue

            # Get base time and additional time per unit from database
            # TODO: Extract vendor/model/complexity from product_selections if available
            base_time, additional_time = self._get_installation_time(category)

            # Calculate total hours: base_time + (additional_time * (quantity - 1))
            estimated_hours = base_time + (additional_time * (quantity - 1))

            # Apply efficiency factor (10% improvement per 10 devices due to repetition)
            if quantity > 10:
                efficiency_gain = 1 - (min(quantity - 10, 40) * Decimal("0.01"))
                estimated_hours = estimated_hours * efficiency_gain

            # Determine labor type
            labor_rate = labor_rates.get("installation", self.DEFAULT_LABOR_RATES["installation"])
            if category in ["hub", "controller"]:
                labor_rate = labor_rates.get("configuration", self.DEFAULT_LABOR_RATES["configuration"])
            elif category in ["switch", "outlet"]:
                labor_rate = labor_rates.get("electrical", self.DEFAULT_LABOR_RATES["electrical"])

            labor_subtotal = estimated_hours * labor_rate

            # Calculate materials
            materials_needed = []
            materials_subtotal = Decimal("0")

            materials_list = self._get_materials(category)
            if include_materials and materials_list:
                for material_template in materials_list:
                    material_qty = Decimal(str(material_template["qty"])) * quantity
                    material_cost = material_qty * material_template["cost_per_unit"]
                    materials_subtotal += material_cost

                    materials_needed.append({
                        "name": material_template["name"],
                        "quantity": float(material_qty),
                        "unit": material_template["unit"],
                        "cost_per_unit": float(material_template["cost_per_unit"]),
                        "total_cost": float(material_cost)
                    })

            total_cost = labor_subtotal + materials_subtotal

            # Create labor item
            labor_item = {
                "line_number": line_number,
                "category": "Installation",
                "task_name": f"Install {int(quantity)} {self._format_category_name(category)}",
                "description": self._generate_installation_description(category, int(quantity)),
                "scope_of_work": self._generate_scope_of_work(category, int(quantity)),
                "estimated_hours": float(estimated_hours),
                "hourly_rate": float(labor_rate),
                "labor_subtotal": float(labor_subtotal),
                "quantity": float(quantity),
                "unit_type": "per device",
                "associated_device_count": int(quantity),
                "materials_needed": materials_needed if include_materials else [],
                "materials_cost": float(materials_subtotal),
                "total_cost": float(total_cost),
                "is_auto_calculated": True,
                "is_optional": False,
                "requires_approval": False,
            }

            labor_items.append(labor_item)
            line_number += 1

            total_labor_hours += estimated_hours
            total_labor_cost += labor_subtotal
            total_materials_cost += materials_subtotal

        # Add system configuration labor
        if len(category_quantities) > 0:
            config_labor = await self._calculate_configuration_labor(
                category_quantities,
                labor_rates,
                line_number
            )
            if config_labor:
                labor_items.append(config_labor)
                line_number += 1
                total_labor_hours += Decimal(str(config_labor["estimated_hours"]))
                total_labor_cost += Decimal(str(config_labor["labor_subtotal"]))

        # Add testing & commissioning
        testing_labor = await self._calculate_testing_labor(
            category_quantities,
            labor_rates,
            line_number
        )
        if testing_labor:
            labor_items.append(testing_labor)
            line_number += 1
            total_labor_hours += Decimal(str(testing_labor["estimated_hours"]))
            total_labor_cost += Decimal(str(testing_labor["labor_subtotal"]))

        # Add customer training (if significant installation)
        total_devices = sum(category_quantities.values())
        if total_devices >= 10:
            training_labor = await self._calculate_training_labor(
                total_devices,
                labor_rates,
                line_number
            )
            if training_labor:
                labor_items.append(training_labor)
                line_number += 1
                total_labor_hours += Decimal(str(training_labor["estimated_hours"]))
                total_labor_cost += Decimal(str(training_labor["labor_subtotal"]))

        # Calculate project duration (assumes 1 technician, 8-hour days)
        estimated_duration_days = max(1, int((total_labor_hours / 8).to_integral_value()) + 1)

        return {
            "labor_items": labor_items,
            "total_labor_hours": float(total_labor_hours),
            "total_labor_cost": float(total_labor_cost),
            "total_materials_cost": float(total_materials_cost),
            "total_cost": float(total_labor_cost + total_materials_cost),
            "estimated_duration_days": estimated_duration_days
        }

    def _format_category_name(self, category: str) -> str:
        """Format category name for display"""
        name_map = {
            "smart_lock": "Smart Locks",
            "thermostat": "Thermostats",
            "hub": "Hubs/Controllers",
            "camera": "Security Cameras",
            "doorbell": "Smart Doorbells",
            "sensor": "Sensors",
            "switch": "Smart Switches",
            "outlet": "Smart Outlets",
            "garage_door": "Garage Door Controllers",
            "shade": "Smart Shades",
            "irrigation": "Irrigation Controllers",
            "leak_detector": "Leak Detectors",
            "smoke_detector": "Smoke Detectors",
        }
        return name_map.get(category, category.replace("_", " ").title())

    def _generate_installation_description(self, category: str, quantity: int) -> str:
        """Generate detailed description of installation work"""
        descriptions = {
            "smart_lock": f"Physical installation of {quantity} smart locks including mounting, wiring (if applicable), pairing with hub, and initial configuration. Includes testing lock/unlock functionality and battery installation.",
            "thermostat": f"Installation of {quantity} smart thermostats including removal of old thermostat, wiring verification, mounting, network pairing, and HVAC system testing.",
            "hub": f"Setup and configuration of {quantity} hub(s)/controller(s) including network connection, firmware updates, device pairing, and integration testing.",
            "camera": f"Installation of {quantity} security cameras including mounting, cable running (CAT6), network configuration, viewing angle optimization, and recording setup.",
            "doorbell": f"Installation of {quantity} smart doorbells including wiring, mounting, chime integration, network setup, and motion detection configuration.",
            "sensor": f"Installation of {quantity} sensors including mounting/placement, battery installation, hub pairing, and sensitivity testing.",
            "switch": f"Installation of {quantity} smart switches including electrical wiring, wall box mounting, load testing, and scene configuration.",
            "outlet": f"Installation of {quantity} smart outlets including electrical wiring, wall box mounting, load testing, and schedule setup.",
        }
        return descriptions.get(category, f"Installation and configuration of {quantity} {self._format_category_name(category)}.")

    def _generate_scope_of_work(self, category: str, quantity: int) -> str:
        """Generate detailed scope of work breakdown"""
        base_scope = f"""Scope of Work for {self._format_category_name(category)} Installation:

1. Pre-Installation
   - Site survey and verification of installation locations
   - Verify power availability and network connectivity
   - Review customer requirements and preferences

2. Installation ({quantity} units)
   - Unbox and inspect devices for damage
   - Mount/install devices at designated locations
   - Run necessary wiring (power, data, control)
   - Make electrical/network connections
   - Secure all mounting hardware

3. Configuration
   - Power on devices and verify operation
   - Connect to network (WiFi/Ethernet)
   - Pair with hub/controller
   - Configure device settings per specifications
   - Test basic functionality

4. Quality Assurance
   - Verify all devices are communicating properly
   - Test remote access and control
   - Document device IDs and network addresses
   - Clean up installation area

5. Customer Handoff
   - Demonstrate device operation
   - Provide quick reference guide
   - Answer customer questions
"""
        return base_scope

    async def _calculate_configuration_labor(
        self,
        category_quantities: Dict[str, Decimal],
        labor_rates: Dict[str, Decimal],
        line_number: int
    ) -> Optional[Dict]:
        """Calculate system-wide configuration labor"""

        total_devices = sum(category_quantities.values())

        # Base configuration time: 2 hours for system setup
        # Additional time: 0.05 hours per device for integration
        config_hours = Decimal("2.0") + (total_devices * Decimal("0.05"))

        labor_rate = labor_rates.get("configuration", self.DEFAULT_LABOR_RATES["configuration"])
        labor_subtotal = config_hours * labor_rate

        return {
            "line_number": line_number,
            "category": "Configuration",
            "task_name": "System Configuration & Integration",
            "description": f"Configure central hub/controller, create automation rules, integrate {int(total_devices)} devices into unified system, setup user accounts and access controls, configure notifications and alerts.",
            "scope_of_work": """Scope of Work for System Configuration:

1. Hub/Controller Setup
   - Configure central controller/hub
   - Setup network connections
   - Apply firmware updates
   - Configure security settings

2. Device Integration
   - Add all devices to central system
   - Organize devices by room/zone
   - Create device groups and scenes
   - Configure device-specific settings

3. Automation & Rules
   - Create basic automation rules
   - Setup schedules and timers
   - Configure triggers and actions
   - Test automation sequences

4. User Management
   - Create user accounts
   - Setup access permissions
   - Configure mobile app access
   - Setup remote access (if applicable)

5. System Optimization
   - Optimize network performance
   - Configure backup settings
   - Setup notifications and alerts
   - Document system configuration
""",
            "estimated_hours": float(config_hours),
            "hourly_rate": float(labor_rate),
            "labor_subtotal": float(labor_subtotal),
            "quantity": 1,
            "unit_type": "per system",
            "associated_device_count": int(total_devices),
            "materials_needed": [],
            "materials_cost": 0,
            "total_cost": float(labor_subtotal),
            "is_auto_calculated": True,
            "is_optional": False,
            "requires_approval": False,
        }

    async def _calculate_testing_labor(
        self,
        category_quantities: Dict[str, Decimal],
        labor_rates: Dict[str, Decimal],
        line_number: int
    ) -> Optional[Dict]:
        """Calculate testing & commissioning labor"""

        total_devices = sum(category_quantities.values())

        # Testing time: 1 hour base + 0.1 hours per device
        testing_hours = Decimal("1.0") + (total_devices * Decimal("0.1"))

        labor_rate = labor_rates.get("testing", self.DEFAULT_LABOR_RATES["testing"])
        labor_subtotal = testing_hours * labor_rate

        return {
            "line_number": line_number,
            "category": "Testing",
            "task_name": "System Testing & Commissioning",
            "description": f"Comprehensive testing of all {int(total_devices)} devices, automation rules, and system integrations. Verify proper operation, network connectivity, and user access. Document any issues and resolve before customer handoff.",
            "scope_of_work": """Scope of Work for Testing & Commissioning:

1. Device Testing
   - Test each device individually
   - Verify network connectivity
   - Test local and remote control
   - Verify status reporting

2. Automation Testing
   - Test all automation rules
   - Verify triggers and actions
   - Test schedules and timers
   - Verify scene functionality

3. Integration Testing
   - Test device-to-device interactions
   - Verify hub/controller communications
   - Test mobile app functionality
   - Verify cloud connectivity (if applicable)

4. Performance Testing
   - Measure response times
   - Test under load conditions
   - Verify network stability
   - Check for interference issues

5. Documentation
   - Document test results
   - Create punch list for any issues
   - Resolve outstanding issues
   - Final system verification
""",
            "estimated_hours": float(testing_hours),
            "hourly_rate": float(labor_rate),
            "labor_subtotal": float(labor_subtotal),
            "quantity": 1,
            "unit_type": "per system",
            "associated_device_count": int(total_devices),
            "materials_needed": [],
            "materials_cost": 0,
            "total_cost": float(labor_subtotal),
            "is_auto_calculated": True,
            "is_optional": False,
            "requires_approval": False,
        }

    async def _calculate_training_labor(
        self,
        total_devices: Decimal,
        labor_rates: Dict[str, Decimal],
        line_number: int
    ) -> Optional[Dict]:
        """Calculate customer training labor"""

        # Training time: 1.5 hours base for systems with 10+ devices
        # Additional 0.05 hours per device over 20
        training_hours = Decimal("1.5")
        if total_devices > 20:
            training_hours += (total_devices - 20) * Decimal("0.05")

        labor_rate = labor_rates.get("training", self.DEFAULT_LABOR_RATES["training"])
        labor_subtotal = training_hours * labor_rate

        return {
            "line_number": line_number,
            "category": "Training",
            "task_name": "Customer Training & Documentation",
            "description": "Comprehensive customer training on system operation, mobile app usage, automation features, and troubleshooting. Includes written documentation and quick reference guides.",
            "scope_of_work": """Scope of Work for Customer Training:

1. System Overview
   - Introduction to smart home system
   - Overview of installed devices
   - System capabilities and features
   - Safety and best practices

2. Device Operation
   - How to control individual devices
   - Using mobile app
   - Voice control (if applicable)
   - Manual override procedures

3. Automation Features
   - Creating and editing automation rules
   - Using scenes and modes
   - Setting schedules
   - Configuring notifications

4. Troubleshooting
   - Common issues and solutions
   - How to restart devices
   - Network troubleshooting basics
   - When to call for support

5. Documentation
   - Provide user manuals
   - Create custom quick reference guide
   - Provide contact information for support
   - Review warranty and maintenance
""",
            "estimated_hours": float(training_hours),
            "hourly_rate": float(labor_rate),
            "labor_subtotal": float(labor_subtotal),
            "quantity": 1,
            "unit_type": "per system",
            "associated_device_count": int(total_devices),
            "materials_needed": [
                {
                    "name": "Printed user manual",
                    "quantity": 1,
                    "unit": "ea",
                    "cost_per_unit": 15.0,
                    "total_cost": 15.0
                },
                {
                    "name": "Quick reference cards",
                    "quantity": 5,
                    "unit": "ea",
                    "cost_per_unit": 2.0,
                    "total_cost": 10.0
                }
            ],
            "materials_cost": 25.0,
            "total_cost": float(labor_subtotal + Decimal("25.0")),
            "is_auto_calculated": True,
            "is_optional": True,  # Training can be optional
            "requires_approval": False,
        }

    @staticmethod
    def format_currency(amount: Decimal) -> str:
        """Format decimal as currency string"""
        return f"${amount:,.2f}"

    @staticmethod
    def format_hours(hours: Decimal) -> str:
        """Format hours with proper decimal places"""
        return f"{hours:.2f} hours"
