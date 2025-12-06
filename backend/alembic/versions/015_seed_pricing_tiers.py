"""Seed pricing tiers for Good/Better/Best pricing

Revision ID: 015_seed_pricing_tiers
Revises: 014_add_hub_spoke_federation
Create Date: 2025-11-21 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from decimal import Decimal
import uuid

# revision identifiers, used by Alembic.
revision = '015_seed_pricing_tiers'
down_revision = ('017_add_quote_enhancements', '020_add_project_phases')  # Merge migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Seed Good/Better/Best pricing tiers

    These tiers give customers psychological control through choice:
    - Starter (Good): Entry-level, budget-conscious
    - Professional (Better): Most Popular, best value
    - Enterprise (Best): Premium, unlimited features
    """

    # Define the pricing_tiers table for bulk insert
    pricing_tiers = table(
        'pricing_tiers',
        column('id', UUID),
        column('tier_name', sa.String),
        column('tier_level', sa.Integer),
        column('description', sa.Text),
        column('price_per_unit_monthly', sa.Numeric),
        column('min_units', sa.Integer),
        column('max_units', sa.Integer),
        column('base_monthly_fee', sa.Numeric),
        column('setup_fee', sa.Numeric),
        column('smart_home_basic_price', sa.Numeric),
        column('smart_home_premium_price', sa.Numeric),
        column('smart_home_enterprise_price', sa.Numeric),
        column('features_included', JSONB),
        column('support_level', sa.String),
        column('active', sa.Boolean)
    )

    # Starter Tier (Good) - Entry Level
    starter_features = [
        "Core property management software",
        "Tenant portal with online payments",
        "Basic maintenance request tracking",
        "Financial reporting & rent rolls",
        "Email support (24-48 hour response)",
        "Up to 25% smart home adoption",
        "Basic smart locks only",
        "Basic thermostats only"
    ]

    # Professional Tier (Better) - Most Popular ⭐
    professional_features = [
        "Everything in Starter",
        "Priority support (phone + email, 12-hour response)",
        "Advanced analytics & custom reporting",
        "REST API access for integrations",
        "Bulk operations & batch tools",
        "Multi-property management dashboard",
        "Up to 50% smart home adoption",
        "Premium smart locks with remote access",
        "Smart thermostats with scheduling",
        "Door/window sensors",
        "Motion sensors",
        "Basic energy monitoring"
    ]

    # Enterprise Tier (Best) - Premium
    enterprise_features = [
        "Everything in Professional",
        "White-glove support with dedicated account manager",
        "24/7 priority phone support",
        "Custom integrations & development",
        "Advanced automation workflows",
        "Custom dashboards & reports",
        "Multi-tenant architecture support",
        "Unlimited smart home adoption",
        "Full smart building capabilities",
        "Advanced HVAC controls",
        "Energy management & optimization",
        "Security cameras & access control",
        "Environmental sensors (CO2, VOC, etc.)",
        "Predictive maintenance alerts",
        "Building management system integration"
    ]

    # Insert the three tiers
    # Use raw SQL with ON CONFLICT DO NOTHING to avoid duplicate key errors
    conn = op.get_bind()

    tiers_data = [
        {
            'id': str(uuid.uuid4()),
            'tier_name': 'Starter',
            'tier_level': 1,
            'description': 'Perfect for getting started with professional property management',
            'price_per_unit_monthly': '2.50',
            'min_units': 0,
            'max_units': 50,
            'base_monthly_fee': '0.00',
            'setup_fee': '0.00',
            'smart_home_basic_price': '15.00',
            'smart_home_premium_price': None,
            'smart_home_enterprise_price': None,
            'features_included': starter_features,
            'support_level': 'Email (24-48hr response)',
            'active': True
        },
        {
            'id': str(uuid.uuid4()),
            'tier_name': 'Professional',
            'tier_level': 2,
            'description': 'Best value for growing portfolios - our most popular choice',
            'price_per_unit_monthly': '2.50',
            'min_units': 51,
            'max_units': 200,
            'base_monthly_fee': '0.00',
            'setup_fee': '0.00',
            'smart_home_basic_price': '15.00',
            'smart_home_premium_price': '35.00',
            'smart_home_enterprise_price': None,
            'features_included': professional_features,
            'support_level': 'Priority (Phone + Email, 12hr response)',
            'active': True
        },
        {
            'id': str(uuid.uuid4()),
            'tier_name': 'Enterprise',
            'tier_level': 3,
            'description': 'Full smart building capabilities for large portfolios',
            'price_per_unit_monthly': '2.50',
            'min_units': 201,
            'max_units': None,
            'base_monthly_fee': '0.00',
            'setup_fee': '0.00',
            'smart_home_basic_price': '15.00',
            'smart_home_premium_price': '35.00',
            'smart_home_enterprise_price': '75.00',
            'features_included': enterprise_features,
            'support_level': 'White-Glove (Dedicated Manager, 24/7)',
            'active': True
        }
    ]

    # Insert each tier, skipping if it already exists
    # Check if tiers already exist first to avoid ON CONFLICT complexity
    existing_tiers = conn.execute(sa.text("SELECT tier_name FROM pricing_tiers WHERE tier_name IN ('Starter', 'Professional', 'Enterprise')")).fetchall()
    existing_tier_names = {row[0] for row in existing_tiers}

    for tier in tiers_data:
        # Skip if tier already exists
        if tier['tier_name'] in existing_tier_names:
            continue

        # Convert None to NULL for SQL
        import json
        features_json = json.dumps(tier['features_included'])

        # Use raw SQL with proper parameter substitution
        conn.execute(sa.text("""
            INSERT INTO pricing_tiers (
                id, tier_name, tier_level, description,
                price_per_unit_monthly, min_units, max_units,
                base_monthly_fee, setup_fee,
                smart_home_basic_price, smart_home_premium_price, smart_home_enterprise_price,
                features_included, support_level, active
            )
            VALUES (
                CAST(:p_id AS uuid), :p_tier_name, :p_tier_level, :p_description,
                CAST(:p_price_per_unit_monthly AS numeric), :p_min_units, :p_max_units,
                CAST(:p_base_monthly_fee AS numeric), CAST(:p_setup_fee AS numeric),
                CAST(:p_smart_home_basic_price AS numeric),
                CASE WHEN :p_smart_home_premium_price = '' THEN NULL ELSE CAST(:p_smart_home_premium_price AS numeric) END,
                CASE WHEN :p_smart_home_enterprise_price = '' THEN NULL ELSE CAST(:p_smart_home_enterprise_price AS numeric) END,
                CAST(:p_features_included AS jsonb), :p_support_level, :p_active
            )
        """), {
            'p_id': tier['id'],
            'p_tier_name': tier['tier_name'],
            'p_tier_level': tier['tier_level'],
            'p_description': tier['description'],
            'p_price_per_unit_monthly': tier['price_per_unit_monthly'],
            'p_min_units': tier['min_units'],
            'p_max_units': tier['max_units'] if tier['max_units'] is not None else 999999,
            'p_base_monthly_fee': tier['base_monthly_fee'],
            'p_setup_fee': tier['setup_fee'],
            'p_smart_home_basic_price': tier['smart_home_basic_price'],
            'p_smart_home_premium_price': tier['smart_home_premium_price'] or '',
            'p_smart_home_enterprise_price': tier['smart_home_enterprise_price'] or '',
            'p_features_included': features_json,
            'p_support_level': tier['support_level'],
            'p_active': tier['active']
        })

    print("✅ Seeded 3 pricing tiers: Starter, Professional, Enterprise (skipped existing)")


def downgrade():
    """Remove seeded pricing tiers"""
    op.execute(
        "DELETE FROM pricing_tiers WHERE tier_name IN ('Starter', 'Professional', 'Enterprise')"
    )
    print("🗑️  Removed seeded pricing tiers")
