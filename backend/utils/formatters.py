"""
Formatting Utility Functions
Format currency, phone numbers, addresses, etc. for display
"""

import re
from typing import Optional, Dict, Any
from decimal import Decimal


def format_currency(amount: float, currency_symbol: str = "$", include_cents: bool = True) -> str:
    """
    Format amount as currency

    Args:
        amount: Monetary amount
        currency_symbol: Currency symbol (default: "$")
        include_cents: Include cents in output (default: True)

    Returns:
        Formatted currency string

    Examples:
        >>> format_currency(1234.56)
        '$1,234.56'
        >>> format_currency(1234.56, include_cents=False)
        '$1,234'
    """
    try:
        decimal_amount = Decimal(str(amount))

        if include_cents:
            formatted = f"{decimal_amount:,.2f}"
        else:
            formatted = f"{int(decimal_amount):,}"

        return f"{currency_symbol}{formatted}"

    except (ValueError, TypeError):
        return f"{currency_symbol}0.00"


def format_phone(phone: str, format_type: str = "standard") -> str:
    """
    Format phone number for display

    Args:
        phone: Phone number (digits only or any format)
        format_type: "standard" (555-123-4567), "parentheses" ((555) 123-4567), "dots" (555.123.4567)

    Returns:
        Formatted phone number

    Examples:
        >>> format_phone("5551234567")
        '555-123-4567'
        >>> format_phone("5551234567", "parentheses")
        '(555) 123-4567'
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Need exactly 10 digits for US format
    if len(digits) != 10:
        return phone  # Return original if not valid

    area = digits[0:3]
    prefix = digits[3:6]
    number = digits[6:10]

    if format_type == "parentheses":
        return f"({area}) {prefix}-{number}"
    elif format_type == "dots":
        return f"{area}.{prefix}.{number}"
    else:  # standard
        return f"{area}-{prefix}-{number}"


def format_address(address_parts: Dict[str, str], format_type: str = "single_line") -> str:
    """
    Format address for display

    Args:
        address_parts: Dictionary with keys: street, city, state, postal_code, country
        format_type: "single_line" or "multi_line"

    Returns:
        Formatted address string

    Examples:
        >>> format_address({
        ...     "street": "123 Main St",
        ...     "city": "Springfield",
        ...     "state": "IL",
        ...     "postal_code": "62701"
        ... })
        '123 Main St, Springfield, IL 62701'
    """
    street = address_parts.get("street", "")
    city = address_parts.get("city", "")
    state = address_parts.get("state", "")
    postal_code = address_parts.get("postal_code", "")
    country = address_parts.get("country", "")

    if format_type == "multi_line":
        lines = []
        if street:
            lines.append(street)
        if city or state or postal_code:
            city_state_zip = f"{city}, {state} {postal_code}".strip()
            lines.append(city_state_zip)
        if country:
            lines.append(country)
        return "\n".join(lines)

    else:  # single_line
        parts = []
        if street:
            parts.append(street)
        if city:
            parts.append(city)
        if state:
            parts.append(state)
        if postal_code:
            parts.append(postal_code)
        if country and country != "US":
            parts.append(country)

        return ", ".join(parts)


def format_ssn(ssn: str, mask: bool = True) -> str:
    """
    Format SSN for display

    Args:
        ssn: Social Security Number
        mask: Mask first 5 digits (default: True)

    Returns:
        Formatted SSN

    Examples:
        >>> format_ssn("123456789")
        'XXX-XX-6789'
        >>> format_ssn("123456789", mask=False)
        '123-45-6789'
    """
    # Remove hyphens
    digits = ssn.replace('-', '')

    # Need exactly 9 digits
    if len(digits) != 9:
        return ssn  # Return original if not valid

    if mask:
        return f"XXX-XX-{digits[5:]}"
    else:
        return f"{digits[0:3]}-{digits[3:5]}-{digits[5:]}"


def format_percentage(value: float, decimal_places: int = 1, include_symbol: bool = True) -> str:
    """
    Format percentage for display

    Args:
        value: Percentage value (e.g., 25.5 for 25.5%)
        decimal_places: Number of decimal places (default: 1)
        include_symbol: Include % symbol (default: True)

    Returns:
        Formatted percentage

    Examples:
        >>> format_percentage(25.5)
        '25.5%'
        >>> format_percentage(25.5, decimal_places=0)
        '26%'
    """
    try:
        formatted = f"{float(value):.{decimal_places}f}"
        return f"{formatted}%" if include_symbol else formatted
    except (ValueError, TypeError):
        return "0.0%"


def format_name(first_name: str, last_name: str, middle_name: Optional[str] = None,
                format_type: str = "full") -> str:
    """
    Format person's name

    Args:
        first_name: First name
        last_name: Last name
        middle_name: Middle name (optional)
        format_type: "full" (John A. Smith), "last_first" (Smith, John), "initials" (J.A.S.)

    Returns:
        Formatted name
    """
    if format_type == "last_first":
        if middle_name:
            return f"{last_name}, {first_name} {middle_name[0]}."
        else:
            return f"{last_name}, {first_name}"

    elif format_type == "initials":
        initials = [first_name[0] if first_name else ""]
        if middle_name:
            initials.append(middle_name[0])
        initials.append(last_name[0] if last_name else "")
        return ".".join(initials) + "."

    else:  # full
        parts = [first_name]
        if middle_name:
            parts.append(f"{middle_name[0]}.")
        parts.append(last_name)
        return " ".join(parts)


def format_unit_number(unit_number: str, prefix: str = "Unit") -> str:
    """
    Format unit number with prefix

    Args:
        unit_number: Unit number
        prefix: Prefix to use (default: "Unit")

    Returns:
        Formatted unit designation

    Examples:
        >>> format_unit_number("101")
        'Unit 101'
        >>> format_unit_number("A", "Apt")
        'Apt A'
    """
    return f"{prefix} {unit_number}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")

    Examples:
        >>> format_file_size(1536)
        '1.5 KB'
        >>> format_file_size(1048576)
        '1.0 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to maximum length

    Args:
        text: Text to truncate
        max_length: Maximum length (default: 50)
        suffix: Suffix to add if truncated (default: "...")

    Returns:
        Truncated text

    Examples:
        >>> truncate_text("This is a very long text", max_length=10)
        'This is...'
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
