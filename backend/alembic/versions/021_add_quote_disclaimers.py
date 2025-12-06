"""Add price increase disclaimers to quotes

Revision ID: 021_add_quote_disclaimers
Revises: 015_seed_pricing_tiers
Create Date: 2025-11-21 03:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '021_add_quote_disclaimers'
down_revision = '015_seed_pricing_tiers'
branch_labels = None
depends_on = None


# Default disclaimers for quote price increases
DEFAULT_DISCLAIMERS = [
    {
        "category": "Pre-Existing Conditions",
        "reason": "Hidden damage, structural issues, or pre-existing conditions discovered during inspection or initial work that were not visible or accessible during the quoting process"
    },
    {
        "category": "Code Compliance",
        "reason": "Additional work required to meet current building codes, fire safety regulations, ADA compliance, or other regulatory requirements not anticipated in the original scope"
    },
    {
        "category": "Hazardous Materials",
        "reason": "Discovery of asbestos, lead paint, mold, or other hazardous materials requiring specialized remediation and disposal procedures"
    },
    {
        "category": "Permit & Inspection Costs",
        "reason": "Permit fees, inspection costs, or engineering requirements that exceed initial estimates or were not included in the original quote"
    },
    {
        "category": "Material Cost Fluctuations",
        "reason": "Increases in material costs due to market conditions, supply chain disruptions, or manufacturer price changes occurring after quote date"
    },
    {
        "category": "Scope Changes",
        "reason": "Changes to project scope, specifications, or requirements requested by the client or required by discovered conditions"
    },
    {
        "category": "Access & Site Conditions",
        "reason": "Unexpected site access issues, utility relocations, or environmental conditions (weather, soil conditions, etc.) requiring additional time or resources"
    },
    {
        "category": "Labor & Timeline",
        "reason": "Extended project timeline, overtime requirements, or labor rate adjustments beyond the original estimate period"
    },
    {
        "category": "Integration Complexity",
        "reason": "Additional integration work required for compatibility with existing systems, legacy equipment, or third-party services not fully documented in original assessment"
    },
    {
        "category": "Emergency Services",
        "reason": "After-hours, weekend, or emergency service calls required to address urgent issues or maintain property operations"
    }
]


def upgrade():
    """Add price increase disclaimers field to quotes table"""

    # Add the disclaimers column
    op.add_column(
        'quotes',
        sa.Column(
            'price_increase_disclaimers',
            JSONB,
            nullable=True,
            comment='Array of potential reasons why the final price may exceed the quoted amount'
        )
    )

    # Set default disclaimers for all existing quotes
    op.execute(
        sa.text(
            """
            UPDATE quotes
            SET price_increase_disclaimers = :disclaimers
            WHERE price_increase_disclaimers IS NULL
            """
        ).bindparams(
            sa.bindparam('disclaimers', value=DEFAULT_DISCLAIMERS, type_=JSONB)
        )
    )

    print("✅ Added price_increase_disclaimers field to quotes table")
    print(f"✅ Set default disclaimers ({len(DEFAULT_DISCLAIMERS)} categories)")


def downgrade():
    """Remove price increase disclaimers field"""
    op.drop_column('quotes', 'price_increase_disclaimers')
    print("🗑️  Removed price_increase_disclaimers field from quotes table")
