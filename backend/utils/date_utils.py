"""
Date and Time Utility Functions
Handles lease expirations, payment due dates, and date calculations
"""

from datetime import datetime, date, timedelta
from typing import Optional
import calendar


def get_current_date() -> date:
    """Get current date (useful for testing/mocking)"""
    return date.today()


def get_days_between(start_date: date, end_date: date) -> int:
    """Calculate days between two dates"""
    return (end_date - start_date).days


def is_lease_expiring_soon(lease_end_date: date, warning_days: int = 60) -> bool:
    """
    Check if lease is expiring within warning_days

    Args:
        lease_end_date: Lease end date
        warning_days: Number of days before expiration to warn (default: 60)

    Returns:
        True if lease expires within warning_days
    """
    days_until_expiration = get_days_between(get_current_date(), lease_end_date)
    return 0 < days_until_expiration <= warning_days


def calculate_lease_end_date(start_date: date, months: int) -> date:
    """
    Calculate lease end date from start date and duration

    Args:
        start_date: Lease start date
        months: Lease duration in months

    Returns:
        Lease end date
    """
    # Calculate target month and year
    total_months = start_date.month + months
    target_year = start_date.year + (total_months - 1) // 12
    target_month = ((total_months - 1) % 12) + 1

    # Handle day overflow (e.g., Jan 31 + 1 month = Feb 28)
    last_day_of_target_month = calendar.monthrange(target_year, target_month)[1]
    target_day = min(start_date.day, last_day_of_target_month)

    return date(target_year, target_month, target_day)


def is_payment_overdue(due_date: date, grace_period_days: int = 5) -> bool:
    """
    Check if payment is overdue (past due date + grace period)

    Args:
        due_date: Payment due date
        grace_period_days: Grace period in days (default: 5)

    Returns:
        True if payment is overdue
    """
    grace_end = due_date + timedelta(days=grace_period_days)
    return get_current_date() > grace_end


def get_first_of_month(reference_date: Optional[date] = None) -> date:
    """
    Get first day of month for given date

    Args:
        reference_date: Reference date (default: today)

    Returns:
        First day of the month
    """
    if reference_date is None:
        reference_date = get_current_date()
    return date(reference_date.year, reference_date.month, 1)


def get_last_of_month(reference_date: Optional[date] = None) -> date:
    """
    Get last day of month for given date

    Args:
        reference_date: Reference date (default: today)

    Returns:
        Last day of the month
    """
    if reference_date is None:
        reference_date = get_current_date()
    last_day = calendar.monthrange(reference_date.year, reference_date.month)[1]
    return date(reference_date.year, reference_date.month, last_day)


def format_date_display(date_value: date, format_type: str = "short") -> str:
    """
    Format date for display

    Args:
        date_value: Date to format
        format_type: "short" (MM/DD/YYYY), "long" (January 1, 2024), "iso" (2024-01-01)

    Returns:
        Formatted date string
    """
    if format_type == "short":
        return date_value.strftime("%m/%d/%Y")
    elif format_type == "long":
        return date_value.strftime("%B %d, %Y")
    elif format_type == "iso":
        return date_value.isoformat()
    else:
        return date_value.strftime("%m/%d/%Y")


def get_next_due_date(last_payment_date: date) -> date:
    """
    Calculate next rent due date (first of next month)

    Args:
        last_payment_date: Date of last payment

    Returns:
        Next due date (first of next month)
    """
    # Move to next month
    if last_payment_date.month == 12:
        return date(last_payment_date.year + 1, 1, 1)
    else:
        return date(last_payment_date.year, last_payment_date.month + 1, 1)


def get_days_in_month(reference_date: Optional[date] = None) -> int:
    """
    Get number of days in month

    Args:
        reference_date: Reference date (default: today)

    Returns:
        Number of days in the month
    """
    if reference_date is None:
        reference_date = get_current_date()
    return calendar.monthrange(reference_date.year, reference_date.month)[1]
