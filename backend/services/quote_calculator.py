"""
Quote Calculator Service
Calculates pricing quotes based on units, tiers, and smart home services
Based on financial model from business analysis
"""

import logging
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime, timedelta
from uuid import UUID

logger = logging.getLogger(__name__)


class QuoteCalculator:
    """
    Calculate pricing quotes for property management services

    Based on realistic financial model:
    - Property Management: $2.50/unit/month (mid-tier)
    - Smart Home Basic: $15/unit/month
    - Smart Home Premium: $35/unit/month
    - Smart Home Enterprise: $75/unit/month
    - Additional fees: Late fees + Work order fees
    """

    # Default pricing (matches realistic financial model)
    DEFAULT_PRICING = {
        "property_mgmt_per_unit": Decimal("2.50"),
        "smart_home_basic": Decimal("15.00"),
        "smart_home_premium": Decimal("35.00"),
        "smart_home_enterprise": Decimal("75.00"),
        "late_fee_per_unit": Decimal("0.60"),  # 2% * $30 avg
        "work_order_fee_per_unit": Decimal("6.00"),  # 0.5 * $12 avg fee
    }

    def __init__(self, db_session=None):
        self.db = db_session

    async def calculate_quote(
        self,
        total_units: int,
        pricing_tier_id: Optional[UUID] = None,
        include_smart_home: bool = True,
        smart_home_penetration: Decimal = Decimal("25.0"),
        smart_home_tier_distribution: Optional[Dict[str, Decimal]] = None,
        discount_percentage: Decimal = Decimal("0.0"),
        product_selections: Optional[list] = None
    ) -> Dict:
        """
        Calculate complete quote pricing

        Args:
            total_units: Total number of units to manage
            pricing_tier_id: Optional custom pricing tier
            include_smart_home: Include smart home services
            smart_home_penetration: % of units with smart home (default 25%)
            smart_home_tier_distribution: Distribution across tiers (default: 70/25/5)
            discount_percentage: Discount % (0-100)
            product_selections: List of products with quantities for labor calculation
                Format: [{"category": "smart_lock", "quantity": 15}]

        Returns:
            Dict with complete pricing breakdown including labor and materials
        """

        # Get pricing tier or use defaults
        pricing = await self._get_pricing_tier(pricing_tier_id)

        # Calculate base property management
        monthly_property_mgmt = Decimal(total_units) * pricing["property_mgmt_per_unit"]

        # Calculate smart home services
        monthly_smart_home = Decimal("0.0")
        smart_home_units = 0
        smart_home_basic_units = 0
        smart_home_premium_units = 0
        smart_home_enterprise_units = 0

        if include_smart_home:
            if smart_home_tier_distribution is None:
                smart_home_tier_distribution = {
                    "basic": Decimal("70"),
                    "premium": Decimal("25"),
                    "enterprise": Decimal("5")
                }

            # Calculate units per tier
            smart_home_units = int((smart_home_penetration / 100) * total_units)
            smart_home_basic_units = int((smart_home_tier_distribution["basic"] / 100) * smart_home_units)
            smart_home_premium_units = int((smart_home_tier_distribution["premium"] / 100) * smart_home_units)
            smart_home_enterprise_units = int((smart_home_tier_distribution["enterprise"] / 100) * smart_home_units)

            # Calculate revenue
            monthly_smart_home = (
                (smart_home_basic_units * pricing["smart_home_basic"]) +
                (smart_home_premium_units * pricing["smart_home_premium"]) +
                (smart_home_enterprise_units * pricing["smart_home_enterprise"])
            )

        # Calculate additional fees (late fees, work orders)
        monthly_additional_fees = (
            (Decimal(total_units) * pricing["late_fee_per_unit"]) +
            (Decimal(total_units) * pricing["work_order_fee_per_unit"])
        )

        # Calculate subtotal
        monthly_subtotal = monthly_property_mgmt + monthly_smart_home + monthly_additional_fees

        # Apply discount
        monthly_discount = (monthly_subtotal * discount_percentage) / 100
        monthly_total = monthly_subtotal - monthly_discount

        # Calculate annual
        annual_total = monthly_total * 12

        # Setup fees (if in pricing tier)
        setup_fees = pricing.get("setup_fee", Decimal("0.0"))

        # Cost per unit (for transparency)
        cost_per_unit_monthly = monthly_total / total_units if total_units > 0 else Decimal("0.0")

        # Calculate labor and materials if products selected
        total_labor_cost = Decimal("0.0")
        total_materials_cost = Decimal("0.0")
        total_labor_hours = Decimal("0.0")
        project_duration_days = 0

        if product_selections and len(product_selections) > 0:
            try:
                from services.labor_calculator import LaborCalculator
                labor_calc = LaborCalculator(self.db)
                labor_result = await labor_calc.estimate_labor(
                    quote_id=None,  # Not saved yet, will be populated later
                    product_selections=product_selections,
                    include_materials=True
                )
                total_labor_cost = Decimal(str(labor_result['total_labor_cost']))
                total_materials_cost = Decimal(str(labor_result['total_materials_cost']))
                total_labor_hours = Decimal(str(labor_result['total_labor_hours']))
                project_duration_days = labor_result['estimated_duration_days']
            except Exception as e:
                logger.warning(f"Failed to calculate labor costs: {e}")
                # Continue without labor costs rather than failing entire quote

        # Calculate grand totals
        grand_total_one_time = setup_fees + total_labor_cost + total_materials_cost

        return {
            "total_units": total_units,

            # Monthly breakdown
            "monthly_property_mgmt": monthly_property_mgmt.quantize(Decimal("0.01")),
            "monthly_smart_home": monthly_smart_home.quantize(Decimal("0.01")),
            "monthly_additional_fees": monthly_additional_fees.quantize(Decimal("0.01")),
            "monthly_subtotal": monthly_subtotal.quantize(Decimal("0.01")),
            "monthly_discount": monthly_discount.quantize(Decimal("0.01")),
            "monthly_total": monthly_total.quantize(Decimal("0.01")),

            # Annual
            "annual_total": annual_total.quantize(Decimal("0.01")),

            # One-time costs (updated to include labor)
            "setup_fees": setup_fees.quantize(Decimal("0.01")),
            "total_labor_cost": total_labor_cost.quantize(Decimal("0.01")),
            "total_materials_cost": total_materials_cost.quantize(Decimal("0.01")),
            "total_labor_hours": total_labor_hours.quantize(Decimal("0.01")),
            "grand_total_one_time": grand_total_one_time.quantize(Decimal("0.01")),

            # Project timeline
            "project_duration_days": project_duration_days,

            # Per-unit
            "cost_per_unit_monthly": cost_per_unit_monthly.quantize(Decimal("0.01")),

            # Smart home breakdown
            "smart_home_units": smart_home_units,
            "smart_home_basic_units": smart_home_basic_units,
            "smart_home_premium_units": smart_home_premium_units,
            "smart_home_enterprise_units": smart_home_enterprise_units,

            # Pricing tier used
            "pricing_tier_id": pricing_tier_id,
        }

    async def generate_line_items(
        self,
        total_units: int,
        calculation: Dict,
        include_smart_home: bool = True,
        labor_items: Optional[list] = None
    ) -> list:
        """
        Generate detailed line items for quote including labor and materials

        Args:
            total_units: Number of units
            calculation: Quote calculation result
            include_smart_home: Whether to include smart home services
            labor_items: Optional list of detailed labor items from labor calculator

        Returns list of line item dicts ready for database insertion
        """
        line_items = []
        line_number = 1

        # Line 1: Property Management
        line_items.append({
            "line_number": line_number,
            "category": "Property Management",
            "description": "Property Management SaaS Platform - Per Unit",
            "quantity": Decimal(total_units),
            "unit_price": calculation["monthly_property_mgmt"] / total_units,
            "unit_type": "per unit/month",
            "subtotal": calculation["monthly_property_mgmt"]
        })
        line_number += 1

        # Smart home services
        if include_smart_home and calculation["smart_home_units"] > 0:
            if calculation["smart_home_basic_units"] > 0:
                line_items.append({
                    "line_number": line_number,
                    "category": "Smart Home Services",
                    "description": "Smart Home Basic Tier - Access control, basic automation",
                    "quantity": Decimal(calculation["smart_home_basic_units"]),
                    "unit_price": Decimal("15.00"),
                    "unit_type": "per unit/month",
                    "subtotal": Decimal(calculation["smart_home_basic_units"]) * Decimal("15.00")
                })
                line_number += 1

            if calculation["smart_home_premium_units"] > 0:
                line_items.append({
                    "line_number": line_number,
                    "category": "Smart Home Services",
                    "description": "Smart Home Premium Tier - Advanced automation, energy management",
                    "quantity": Decimal(calculation["smart_home_premium_units"]),
                    "unit_price": Decimal("35.00"),
                    "unit_type": "per unit/month",
                    "subtotal": Decimal(calculation["smart_home_premium_units"]) * Decimal("35.00")
                })
                line_number += 1

            if calculation["smart_home_enterprise_units"] > 0:
                line_items.append({
                    "line_number": line_number,
                    "category": "Smart Home Services",
                    "description": "Smart Home Enterprise Tier - Full automation, custom integrations",
                    "quantity": Decimal(calculation["smart_home_enterprise_units"]),
                    "unit_price": Decimal("75.00"),
                    "unit_type": "per unit/month",
                    "subtotal": Decimal(calculation["smart_home_enterprise_units"]) * Decimal("75.00")
                })
                line_number += 1

        # Additional services
        if calculation["monthly_additional_fees"] > 0:
            line_items.append({
                "line_number": line_number,
                "category": "Additional Services",
                "description": "Late fee processing & work order management",
                "quantity": Decimal(total_units),
                "unit_price": calculation["monthly_additional_fees"] / total_units,
                "unit_type": "per unit/month",
                "subtotal": calculation["monthly_additional_fees"]
            })
            line_number += 1

        # Setup fee (one-time)
        if calculation["setup_fees"] > 0:
            line_items.append({
                "line_number": line_number,
                "category": "Setup",
                "description": "One-time onboarding and setup",
                "quantity": Decimal("1"),
                "unit_price": calculation["setup_fees"],
                "unit_type": "one-time",
                "subtotal": calculation["setup_fees"]
            })
            line_number += 1

        # Labor costs (one-time installation)
        if calculation.get("total_labor_cost", 0) > 0:
            # Add summary labor line item
            line_items.append({
                "line_number": line_number,
                "category": "Installation Labor",
                "description": f"Professional installation labor ({calculation['total_labor_hours']} hours estimated)",
                "quantity": calculation["total_labor_hours"],
                "unit_price": calculation["total_labor_cost"] / calculation["total_labor_hours"] if calculation["total_labor_hours"] > 0 else Decimal("0"),
                "unit_type": "hours",
                "subtotal": calculation["total_labor_cost"]
            })
            line_number += 1

            # If detailed labor items provided, add them as sub-items
            if labor_items:
                for labor_item in labor_items:
                    line_items.append({
                        "line_number": line_number,
                        "category": "Installation Labor",
                        "description": f"  ↳ {labor_item['task_description']}",
                        "quantity": Decimal(str(labor_item['estimated_hours'])),
                        "unit_price": Decimal(str(labor_item['hourly_rate'])),
                        "unit_type": "hours",
                        "subtotal": Decimal(str(labor_item['estimated_labor_cost']))
                    })
                    line_number += 1

        # Materials costs (one-time)
        if calculation.get("total_materials_cost", 0) > 0:
            line_items.append({
                "line_number": line_number,
                "category": "Materials & Equipment",
                "description": "Hardware, devices, and installation materials",
                "quantity": Decimal("1"),
                "unit_price": calculation["total_materials_cost"],
                "unit_type": "lot",
                "subtotal": calculation["total_materials_cost"]
            })
            line_number += 1

            # If detailed material items available from labor calculator
            if labor_items:
                for labor_item in labor_items:
                    if labor_item.get('materials_needed'):
                        for material in labor_item['materials_needed']:
                            line_items.append({
                                "line_number": line_number,
                                "category": "Materials & Equipment",
                                "description": f"  ↳ {material['item_name']} ({material['quantity']} {material['unit']})",
                                "quantity": Decimal(str(material['quantity'])),
                                "unit_price": Decimal(str(material['unit_cost'])),
                                "unit_type": material['unit'],
                                "subtotal": Decimal(str(material['total_cost']))
                            })
                            line_number += 1

        return line_items

    async def _get_pricing_tier(self, pricing_tier_id: Optional[UUID] = None) -> Dict:
        """
        Get pricing from database tier or return defaults

        Returns dict with all pricing fields
        """
        if pricing_tier_id and self.db:
            try:
                from db.models_quotes import PricingTier
                from sqlalchemy import select

                query = select(PricingTier).where(PricingTier.id == pricing_tier_id)
                result = await self.db.execute(query)
                tier = result.scalar_one_or_none()

                if tier:
                    return {
                        "property_mgmt_per_unit": tier.price_per_unit_monthly,
                        "smart_home_basic": tier.smart_home_basic_price or self.DEFAULT_PRICING["smart_home_basic"],
                        "smart_home_premium": tier.smart_home_premium_price or self.DEFAULT_PRICING["smart_home_premium"],
                        "smart_home_enterprise": tier.smart_home_enterprise_price or self.DEFAULT_PRICING["smart_home_enterprise"],
                        "late_fee_per_unit": self.DEFAULT_PRICING["late_fee_per_unit"],
                        "work_order_fee_per_unit": self.DEFAULT_PRICING["work_order_fee_per_unit"],
                        "setup_fee": tier.setup_fee or Decimal("0.0"),
                    }
            except Exception as e:
                logger.warning(f"Failed to load pricing tier {pricing_tier_id}: {e}")

        # Return defaults
        return self.DEFAULT_PRICING.copy()

    @staticmethod
    def generate_quote_number(created_at: Optional[datetime] = None) -> str:
        """
        Generate unique quote number

        Format: Q-YYYY-NNNN
        Example: Q-2026-0001
        """
        if not created_at:
            created_at = datetime.utcnow()

        year = created_at.year

        # In production, query database for max number this year
        # For now, use timestamp-based number
        number = int(created_at.timestamp()) % 10000

        return f"Q-{year}-{number:04d}"

    @staticmethod
    def calculate_validity_date(days: int = 30) -> datetime:
        """Calculate quote expiration date (default 30 days)"""
        return datetime.utcnow() + timedelta(days=days)

    @staticmethod
    def format_currency(amount: Decimal) -> str:
        """Format decimal as currency string"""
        return f"${amount:,.2f}"

    def generate_quote_summary_text(self, quote_data: Dict) -> str:
        """
        Generate human-readable quote summary including labor and materials

        Returns formatted text suitable for email or PDF
        """
        # Build summary parts
        parts = []

        # Header
        parts.append("QUOTE SUMMARY")
        parts.append("=============")
        parts.append("")
        parts.append(f"Customer: {quote_data.get('customer_name', 'N/A')}")
        parts.append(f"Company: {quote_data.get('company_name', 'N/A')}")
        parts.append(f"Total Units: {quote_data.get('total_units', 0):,}")
        parts.append("")

        # Monthly recurring costs
        parts.append("MONTHLY RECURRING COSTS")
        parts.append("-----------------------")
        parts.append(f"Property Management:    {self.format_currency(quote_data.get('monthly_property_mgmt', 0))}")
        parts.append(f"Smart Home Services:    {self.format_currency(quote_data.get('monthly_smart_home', 0))}")
        parts.append(f"Additional Services:    {self.format_currency(quote_data.get('monthly_additional_fees', 0))}")
        parts.append(f"                        ─────────────")
        parts.append(f"Subtotal:               {self.format_currency(quote_data.get('monthly_subtotal', 0))}")
        parts.append("")

        if quote_data.get('monthly_discount', 0) > 0:
            parts.append(f"Discount ({quote_data.get('discount_percentage', 0)}%):           {self.format_currency(quote_data.get('monthly_discount', 0))}")
            parts.append("")

        parts.append(f"TOTAL MONTHLY:          {self.format_currency(quote_data.get('monthly_total', 0))}")
        parts.append(f"TOTAL ANNUAL:           {self.format_currency(quote_data.get('annual_total', 0))}")
        parts.append("")

        # One-time costs
        has_one_time_costs = (
            quote_data.get('setup_fees', 0) > 0 or
            quote_data.get('total_labor_cost', 0) > 0 or
            quote_data.get('total_materials_cost', 0) > 0
        )

        if has_one_time_costs:
            parts.append("ONE-TIME INSTALLATION COSTS")
            parts.append("---------------------------")

            if quote_data.get('setup_fees', 0) > 0:
                parts.append(f"Setup & Onboarding:     {self.format_currency(quote_data.get('setup_fees', 0))}")

            if quote_data.get('total_labor_cost', 0) > 0:
                labor_hours = quote_data.get('total_labor_hours', 0)
                parts.append(f"Installation Labor:     {self.format_currency(quote_data.get('total_labor_cost', 0))}")
                parts.append(f"  ({labor_hours} hours estimated)")

            if quote_data.get('total_materials_cost', 0) > 0:
                parts.append(f"Materials & Equipment:  {self.format_currency(quote_data.get('total_materials_cost', 0))}")

            parts.append(f"                        ─────────────")
            parts.append(f"TOTAL ONE-TIME:         {self.format_currency(quote_data.get('grand_total_one_time', 0))}")
            parts.append("")

            # Project timeline if labor involved
            if quote_data.get('project_duration_days', 0) > 0:
                parts.append(f"Estimated Installation Duration: {quote_data.get('project_duration_days')} days")
                parts.append("")

        # Cost breakdown
        parts.append(f"COST PER UNIT:          {self.format_currency(quote_data.get('cost_per_unit_monthly', 0))}/month")
        parts.append("")

        # Smart home breakdown
        if quote_data.get('smart_home_units', 0) > 0:
            parts.append("Smart Home Breakdown:")
            if quote_data.get('smart_home_basic_units', 0) > 0:
                parts.append(f"  Basic Tier:    {quote_data.get('smart_home_basic_units', 0)} units @ $15/month")
            if quote_data.get('smart_home_premium_units', 0) > 0:
                parts.append(f"  Premium Tier:  {quote_data.get('smart_home_premium_units', 0)} units @ $35/month")
            if quote_data.get('smart_home_enterprise_units', 0) > 0:
                parts.append(f"  Enterprise:    {quote_data.get('smart_home_enterprise_units', 0)} units @ $75/month")
            parts.append("")

        # Grand totals
        parts.append("═" * 50)
        if has_one_time_costs:
            parts.append(f"TOTAL FIRST MONTH:      {self.format_currency(quote_data.get('monthly_total', 0) + quote_data.get('grand_total_one_time', 0))}")
            parts.append(f"  (Monthly: {self.format_currency(quote_data.get('monthly_total', 0))} + One-time: {self.format_currency(quote_data.get('grand_total_one_time', 0))})")
        else:
            parts.append(f"TOTAL FIRST MONTH:      {self.format_currency(quote_data.get('monthly_total', 0))}")
        parts.append("═" * 50)
        parts.append("")

        # Validity
        parts.append(f"Quote valid until: {quote_data.get('valid_until', 'N/A')}")

        return "\n".join(parts)
