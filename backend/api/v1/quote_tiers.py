"""
Quote Tiers API - Subscription tiers and product catalog
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any
import sys
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.database import get_db
from db.seed_subscription_tiers import SUBSCRIPTION_TIERS, ADD_ON_SERVICES
from db.seed_vendor_catalog import VENDOR_CATALOG, INSTALLATION_RATES, SETUP_PACKAGE
from services.labor_calculator import LaborCalculator

logger = logging.getLogger(__name__)

router = APIRouter()


def map_product_category_to_labor_category(product_category: str) -> str:
    """
    Map vendor catalog product_category to LaborCalculator category

    This ensures the LaborCalculator can recognize products from the catalog
    and apply appropriate labor rates and installation times.
    """
    category_mapping = {
        # Exact matches
        "switch": "switch",
        "hub": "hub",
        "camera": "camera",
        "doorbell": "doorbell",
        "smart_lock": "smart_lock",
        "thermostat": "thermostat",
        "sensor": "sensor",
        "outlet": "outlet",

        # Networking equipment -> hub
        "access_point": "hub",
        "gateway": "hub",
        "access_control_hub": "hub",

        # Simple installs -> sensor
        "bulb": "sensor",
        "card_reader": "sensor",
        "presence_sensor": "sensor",
        "multi_sensor": "sensor",

        # Electrical work -> similar categories
        "relay": "outlet",
        "dimmer": "switch",

        # Skip non-physical items
        "subscription": None,
    }

    return category_mapping.get(product_category, "sensor")  # Default to sensor for unknown


@router.get("/tiers")
async def get_subscription_tiers():
    """
    Get all subscription tier options for quote builder

    Returns Service Hours, Smart Actions, and Analytics tiers
    """
    return {
        "service_hours": SUBSCRIPTION_TIERS["service_hours"],
        "smart_actions": SUBSCRIPTION_TIERS["smart_actions"],
        "analytics": SUBSCRIPTION_TIERS["analytics"],
        "add_ons": ADD_ON_SERVICES
    }


@router.get("/catalog")
async def get_product_catalog():
    """
    Get vendor product catalog organized by domain

    Returns products grouped by: Network, Lighting, Security, Locks, Climate, Sensors
    """
    return {
        "domains": VENDOR_CATALOG,
        "installation_rates": INSTALLATION_RATES,
        "setup_package": SETUP_PACKAGE
    }


@router.get("/tiers/{tier_type}")
async def get_specific_tier_type(tier_type: str):
    """
    Get tiers for a specific type: service_hours, smart_actions, or analytics
    """
    if tier_type not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=404, detail=f"Tier type '{tier_type}' not found")

    return {
        "tier_type": tier_type,
        "tiers": SUBSCRIPTION_TIERS[tier_type]
    }


@router.get("/catalog/{domain}")
async def get_domain_products(domain: str):
    """
    Get products for a specific domain: network, lighting, security, locks, climate, sensors
    """
    if domain not in VENDOR_CATALOG:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")

    return {
        "domain": domain,
        **VENDOR_CATALOG[domain]
    }


@router.post("/calculate")
async def calculate_quote_pricing(quote_config: Dict[str, Any]):
    """
    Calculate comprehensive quote pricing

    Request body:
    {
        "customer_info": {...},
        "subscriptions": {
            "service_hours": "Professional",
            "smart_actions": "Premium",
            "analytics": null
        },
        "products": [
            {"domain": "network", "product_name": "UniFi Switch 24 PoE", "quantity": 2},
            ...
        ],
        "billing_period": "annual"  # or "monthly"
    }
    """

    line_items = []
    totals = {
        "monthly_subscriptions": 0,
        "one_time_hardware": 0,
        "one_time_installation": 0,
        "installation_hours": 0,
        "discounts_applied": []
    }

    billing_period = quote_config.get("billing_period", "monthly")
    subscriptions = quote_config.get("subscriptions", {})
    products = quote_config.get("products", [])

    # Calculate subscription costs
    for tier_type, tier_name in subscriptions.items():
        if not tier_name:
            continue

        if tier_type not in SUBSCRIPTION_TIERS:
            continue

        # Find the tier
        tier_data = next(
            (t for t in SUBSCRIPTION_TIERS[tier_type] if t["tier_name"] == tier_name),
            None
        )

        if not tier_data:
            continue

        # Get price based on billing period
        if billing_period == "annual" and "annual_price" in tier_data:
            monthly_price = tier_data["annual_price"] / 12
            annual_savings = tier_data.get("annual_savings", 0)
            if annual_savings > 0:
                totals["discounts_applied"].append({
                    "description": f"{tier_name} annual prepayment discount",
                    "amount": annual_savings
                })
        else:
            monthly_price = tier_data["monthly_price"]

        totals["monthly_subscriptions"] += monthly_price

        line_items.append({
            "category": f"subscription_{tier_type}",
            "description": f"{tier_name} - {tier_type.replace('_', ' ').title()}",
            "quantity": 1,
            "unit_price": monthly_price,
            "unit_type": "monthly",
            "subtotal": monthly_price,
            "tier_data": tier_data
        })

    # Calculate product costs
    for product_item in products:
        domain = product_item.get("domain")
        product_name = product_item.get("product_name")
        quantity = product_item.get("quantity", 1)

        if domain not in VENDOR_CATALOG:
            continue

        # Find product in catalog
        domain_data = VENDOR_CATALOG[domain]
        product = next(
            (p for p in domain_data["products"] if p["product_name"] == product_name),
            None
        )

        if not product:
            continue

        # Hardware cost
        hardware_cost = product["unit_price"] * quantity
        totals["one_time_hardware"] += hardware_cost

        line_items.append({
            "category": domain,
            "description": product["product_name"],
            "quantity": quantity,
            "unit_price": product["unit_price"],
            "unit_type": "one-time",
            "subtotal": hardware_cost,
            "vendor": product["vendor_name"],
            "specs": product.get("specs", {})
        })

        # Track product category for labor calculation
        # (installation time calculation moved to LaborCalculator)

    # Calculate detailed installation labor using LaborCalculator
    labor_items = []
    total_materials_cost = 0
    estimated_duration_days = 0

    if products:
        try:
            # Build product_selections for LaborCalculator
            product_selections = []
            for product_item in products:
                domain = product_item.get("domain")
                product_name = product_item.get("product_name")
                quantity = product_item.get("quantity", 1)

                if domain not in VENDOR_CATALOG:
                    continue

                # Find product in catalog
                domain_data = VENDOR_CATALOG[domain]
                product = next(
                    (p for p in domain_data["products"] if p["product_name"] == product_name),
                    None
                )

                if not product:
                    continue

                # Map product_category to labor_category
                labor_category = map_product_category_to_labor_category(product.get("product_category", ""))

                if labor_category:  # Skip None (subscriptions, etc.)
                    product_selections.append({
                        "category": labor_category,
                        "quantity": quantity,
                        "domain": domain
                    })

            # Call LaborCalculator for detailed breakdown
            if product_selections:
                labor_calc = LaborCalculator(db_session=None)
                labor_result = await labor_calc.estimate_labor(
                    quote_id=None,  # No quote ID yet (this is a calculation)
                    product_selections=product_selections,
                    include_materials=True
                )

                # Extract results
                labor_items = labor_result.get("labor_items", [])
                totals["installation_hours"] = labor_result.get("total_labor_hours", 0)
                totals["one_time_installation"] = labor_result.get("total_labor_cost", 0)
                total_materials_cost = labor_result.get("total_materials_cost", 0)
                estimated_duration_days = labor_result.get("estimated_duration_days", 0)

                # Add detailed labor line items
                for labor_item in labor_items:
                    line_items.append({
                        "category": "installation_labor",
                        "description": labor_item.get("task_name", "Labor"),
                        "quantity": labor_item.get("estimated_hours", 0),
                        "unit_price": labor_item.get("hourly_rate", 0),
                        "unit_type": "hours",
                        "subtotal": labor_item.get("labor_subtotal", 0),
                        "details": labor_item.get("description", ""),
                        "materials_cost": labor_item.get("materials_cost", 0)
                    })

                # Add materials line item if materials are needed
                if total_materials_cost > 0:
                    line_items.append({
                        "category": "installation_materials",
                        "description": "Installation Materials & Supplies",
                        "quantity": 1,
                        "unit_price": total_materials_cost,
                        "unit_type": "lot",
                        "subtotal": total_materials_cost
                    })

        except Exception as e:
            logger.warning(f"Failed to calculate detailed labor: {e}")
            # Fall back to simple calculation
            totals["installation_hours"] = sum(
                product.get("installation_time_hours", 0) * product.get("quantity", 1)
                for product in products
            )
            totals["one_time_installation"] = totals["installation_hours"] * INSTALLATION_RATES["standard_hourly"]

    # Apply bulk discounts for hardware
    total_devices = sum(p.get("quantity", 1) for p in products)
    if total_devices >= 50:
        discount_pct = INSTALLATION_RATES["bulk_discount_50_plus"]
        discount_amount = totals["one_time_hardware"] * discount_pct
        totals["one_time_hardware"] -= discount_amount
        totals["discounts_applied"].append({
            "description": f"Bulk hardware discount (50+ devices): {discount_pct*100:.0f}% off",
            "amount": discount_amount
        })
    elif total_devices >= 25:
        discount_pct = INSTALLATION_RATES["bulk_discount_25_plus"]
        discount_amount = totals["one_time_hardware"] * discount_pct
        totals["one_time_hardware"] -= discount_amount
        totals["discounts_applied"].append({
            "description": f"Bulk hardware discount (25+ devices): {discount_pct*100:.0f}% off",
            "amount": discount_amount
        })
    elif total_devices >= 10:
        discount_pct = INSTALLATION_RATES["bulk_discount_10_plus"]
        discount_amount = totals["one_time_hardware"] * discount_pct
        totals["one_time_hardware"] -= discount_amount
        totals["discounts_applied"].append({
            "description": f"Bulk hardware discount (10+ devices): {discount_pct*100:.0f}% off",
            "amount": discount_amount
        })

    # Calculate grand totals (including materials)
    totals["one_time_materials"] = total_materials_cost
    totals["one_time_total"] = totals["one_time_hardware"] + totals["one_time_installation"] + total_materials_cost
    totals["annual_subscription_total"] = totals["monthly_subscriptions"] * 12
    totals["year_1_total"] = totals["one_time_total"] + totals["annual_subscription_total"]
    totals["year_2plus_annual"] = totals["annual_subscription_total"]
    totals["estimated_duration_days"] = estimated_duration_days

    return {
        "line_items": line_items,
        "labor_items": labor_items,  # Detailed labor breakdown
        "totals": totals,
        "billing_period": billing_period,
        "summary": {
            "one_time_costs": {
                "hardware": totals["one_time_hardware"],
                "installation_labor": totals["one_time_installation"],
                "installation_materials": total_materials_cost,
                "total": totals["one_time_total"]
            },
            "recurring_costs": {
                "monthly": totals["monthly_subscriptions"],
                "annual": totals["annual_subscription_total"]
            },
            "grand_totals": {
                "year_1": totals["year_1_total"],
                "year_2_plus_annual": totals["year_2plus_annual"]
            },
            "project_details": {
                "estimated_labor_hours": totals["installation_hours"],
                "estimated_duration_days": estimated_duration_days,
                "labor_categories": len(labor_items)
            }
        }
    }
