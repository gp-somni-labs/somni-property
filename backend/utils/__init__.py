"""
Utility Functions for SomniProperty Backend
Common helper functions used across the application
"""

from .date_utils import (
    get_current_date,
    get_days_between,
    is_lease_expiring_soon,
    calculate_lease_end_date,
    is_payment_overdue,
    get_first_of_month,
    get_last_of_month,
    format_date_display
)

from .validators import (
    validate_email,
    validate_phone,
    validate_ssn,
    validate_unit_number,
    validate_amount,
    validate_postal_code
)

from .formatters import (
    format_currency,
    format_phone,
    format_address,
    format_ssn,
    format_percentage
)

from .calculations import (
    calculate_prorated_rent,
    calculate_late_fee,
    calculate_total_rent,
    calculate_security_deposit,
    calculate_utility_split,
    calculate_payment_breakdown
)

__all__ = [
    # Date utilities
    "get_current_date",
    "get_days_between",
    "is_lease_expiring_soon",
    "calculate_lease_end_date",
    "is_payment_overdue",
    "get_first_of_month",
    "get_last_of_month",
    "format_date_display",

    # Validators
    "validate_email",
    "validate_phone",
    "validate_ssn",
    "validate_unit_number",
    "validate_amount",
    "validate_postal_code",

    # Formatters
    "format_currency",
    "format_phone",
    "format_address",
    "format_ssn",
    "format_percentage",

    # Calculations
    "calculate_prorated_rent",
    "calculate_late_fee",
    "calculate_total_rent",
    "calculate_security_deposit",
    "calculate_utility_split",
    "calculate_payment_breakdown",
]
