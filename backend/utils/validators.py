"""
Validation Utility Functions
Common validation for emails, phones, SSN, amounts, etc.
"""

import re
from typing import Optional
from decimal import Decimal, InvalidOperation


def validate_email(email: str) -> bool:
    """
    Validate email format

    Args:
        email: Email address to validate

    Returns:
        True if valid email format
    """
    if not email:
        return False

    # RFC 5322 simplified regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Validate US phone number (various formats accepted)

    Args:
        phone: Phone number to validate

    Accepts:
        - (555) 123-4567
        - 555-123-4567
        - 555.123.4567
        - 5551234567

    Returns:
        True if valid phone format
    """
    if not phone:
        return False

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Must be exactly 10 digits (US format)
    return len(digits) == 10


def validate_ssn(ssn: str, allow_partial: bool = False) -> bool:
    """
    Validate Social Security Number

    Args:
        ssn: SSN to validate
        allow_partial: Allow last 4 digits only (default: False)

    Accepts:
        - 123-45-6789
        - 123456789
        - 6789 (if allow_partial=True)

    Returns:
        True if valid SSN format
    """
    if not ssn:
        return False

    # Remove hyphens
    digits = ssn.replace('-', '')

    # Check if only digits
    if not digits.isdigit():
        return False

    # Full SSN: 9 digits
    if len(digits) == 9:
        return True

    # Partial SSN: last 4 digits
    if allow_partial and len(digits) == 4:
        return True

    return False


def validate_unit_number(unit_number: str) -> bool:
    """
    Validate unit number format

    Args:
        unit_number: Unit number to validate

    Accepts:
        - Alphanumeric
        - Can include hyphens and spaces
        - 1-20 characters

    Returns:
        True if valid unit number
    """
    if not unit_number:
        return False

    # 1-20 characters, alphanumeric with hyphens and spaces
    pattern = r'^[a-zA-Z0-9\s-]{1,20}$'
    return bool(re.match(pattern, unit_number))


def validate_amount(amount: str, min_value: float = 0.0, max_value: Optional[float] = None) -> bool:
    """
    Validate monetary amount

    Args:
        amount: Amount string to validate
        min_value: Minimum allowed value (default: 0.0)
        max_value: Maximum allowed value (default: None = no limit)

    Returns:
        True if valid amount
    """
    try:
        # Try to convert to Decimal for precision
        decimal_amount = Decimal(str(amount))

        # Check minimum
        if decimal_amount < Decimal(str(min_value)):
            return False

        # Check maximum if specified
        if max_value is not None and decimal_amount > Decimal(str(max_value)):
            return False

        return True

    except (InvalidOperation, ValueError, TypeError):
        return False


def validate_postal_code(postal_code: str, country: str = "US") -> bool:
    """
    Validate postal/ZIP code

    Args:
        postal_code: Postal code to validate
        country: Country code (default: "US")

    Returns:
        True if valid postal code for country
    """
    if not postal_code:
        return False

    if country == "US":
        # US ZIP code: 12345 or 12345-6789
        pattern = r'^\d{5}(-\d{4})?$'
        return bool(re.match(pattern, postal_code))

    elif country == "CA":
        # Canadian postal code: A1A 1A1
        pattern = r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$'
        return bool(re.match(pattern, postal_code.upper()))

    else:
        # Generic: 3-10 alphanumeric characters
        pattern = r'^[a-zA-Z0-9\s-]{3,10}$'
        return bool(re.match(pattern, postal_code))


def validate_percentage(percentage: float, min_value: float = 0.0, max_value: float = 100.0) -> bool:
    """
    Validate percentage value

    Args:
        percentage: Percentage value to validate
        min_value: Minimum allowed percentage (default: 0.0)
        max_value: Maximum allowed percentage (default: 100.0)

    Returns:
        True if valid percentage
    """
    try:
        value = float(percentage)
        return min_value <= value <= max_value
    except (ValueError, TypeError):
        return False


def validate_url(url: str) -> bool:
    """
    Validate URL format

    Args:
        url: URL to validate

    Returns:
        True if valid URL
    """
    if not url:
        return False

    # Simple URL validation
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    return bool(re.match(pattern, url))


def validate_date_range(start_date, end_date) -> bool:
    """
    Validate that start_date is before end_date

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        True if start_date < end_date
    """
    if not start_date or not end_date:
        return False

    return start_date < end_date
