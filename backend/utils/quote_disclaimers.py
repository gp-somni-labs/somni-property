"""
Quote Price Increase Disclaimers

Standard disclaimers explaining potential reasons why final costs may exceed quoted amounts.
Provides legal protection and sets proper expectations with customers.
"""

from typing import List, Dict


def get_default_disclaimers() -> List[Dict[str, str]]:
    """
    Returns the standard set of price increase disclaimers.

    These disclaimers protect against scope creep and unexpected conditions
    commonly encountered in property management and smart home installation projects.
    """
    return [
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


def get_disclaimer_summary() -> str:
    """
    Returns a formatted summary of all disclaimers for display in PDFs or emails.
    """
    disclaimers = get_default_disclaimers()

    lines = [
        "**Important Notice: Potential Price Adjustments**",
        "",
        "This quote represents our best estimate based on the information currently available. ",
        "The final price may be adjusted if any of the following conditions are encountered:",
        ""
    ]

    for i, disclaimer in enumerate(disclaimers, 1):
        lines.append(f"{i}. **{disclaimer['category']}**: {disclaimer['reason']}")
        lines.append("")

    lines.extend([
        "We will notify you immediately if any of these conditions are discovered and provide ",
        "a revised estimate before proceeding with additional work. Our goal is to ensure complete ",
        "transparency and avoid surprises in the final billing.",
        "",
        "By accepting this quote, you acknowledge these potential adjustment scenarios."
    ])

    return "\n".join(lines)


def format_disclaimers_for_pdf(disclaimers: List[Dict[str, str]] = None) -> str:
    """
    Formats disclaimers as HTML for inclusion in PDF templates.

    Args:
        disclaimers: Custom disclaimers, or None to use defaults

    Returns:
        HTML string ready for PDF rendering
    """
    if disclaimers is None:
        disclaimers = get_default_disclaimers()

    html_parts = [
        '<div class="disclaimers-section" style="margin-top: 30px; padding: 20px; background: #f9fafb; border-left: 4px solid #f59e0b; page-break-inside: avoid;">',
        '  <h3 style="color: #92400e; margin: 0 0 15px 0; font-size: 16px; font-weight: 600;">',
        '    ⚠️ Important: Potential Price Adjustments',
        '  </h3>',
        '  <p style="margin: 0 0 15px 0; font-size: 13px; color: #374151; line-height: 1.6;">',
        '    This quote represents our best estimate based on current information. The final price may be adjusted if any of the following conditions are encountered:',
        '  </p>',
        '  <ol style="margin: 0; padding-left: 20px; font-size: 12px; color: #4b5563; line-height: 1.8;">'
    ]

    for disclaimer in disclaimers:
        html_parts.append(
            f'    <li style="margin-bottom: 10px;"><strong>{disclaimer["category"]}:</strong> {disclaimer["reason"]}</li>'
        )

    html_parts.extend([
        '  </ol>',
        '  <p style="margin: 15px 0 0 0; font-size: 12px; color: #6b7280; font-style: italic; line-height: 1.6;">',
        '    We will notify you immediately if any of these conditions are discovered and provide a revised estimate before proceeding with additional work. ',
        '    By accepting this quote, you acknowledge these potential adjustment scenarios.',
        '  </p>',
        '</div>'
    ])

    return '\n'.join(html_parts)


def get_disclaimer_categories() -> List[str]:
    """Returns list of all disclaimer categories for filtering/searching."""
    return [d["category"] for d in get_default_disclaimers()]
