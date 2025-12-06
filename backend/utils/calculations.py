"""
Financial Calculation Utility Functions
Rent prorations, late fees, security deposits, utility splits
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Dict, List, Optional
from .date_utils import get_days_between, get_days_in_month


def calculate_prorated_rent(
    monthly_rent: float,
    move_in_date: date,
    month_start_date: Optional[date] = None
) -> Decimal:
    """
    Calculate prorated rent for partial month

    Args:
        monthly_rent: Monthly rent amount
        move_in_date: Move-in date
        month_start_date: Start of month (default: first of move_in_date's month)

    Returns:
        Prorated rent amount

    Examples:
        >>> from datetime import date
        >>> calculate_prorated_rent(1000, date(2024, 1, 15))
        Decimal('548.39')  # 17 days out of 31
    """
    if month_start_date is None:
        month_start_date = date(move_in_date.year, move_in_date.month, 1)

    # Get days in the month
    days_in_month = get_days_in_month(move_in_date)

    # Get days remaining in month (including move-in day)
    days_remaining = days_in_month - move_in_date.day + 1

    # Calculate daily rate
    daily_rate = Decimal(str(monthly_rent)) / Decimal(days_in_month)

    # Calculate prorated amount
    prorated_amount = daily_rate * Decimal(days_remaining)

    # Round to 2 decimal places
    return prorated_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_late_fee(
    rent_amount: float,
    days_late: int,
    late_fee_type: str = "percentage",
    late_fee_value: float = 5.0,
    max_fee: Optional[float] = None
) -> Decimal:
    """
    Calculate late fee for overdue rent

    Args:
        rent_amount: Monthly rent amount
        days_late: Number of days payment is late
        late_fee_type: "percentage" or "flat" (default: "percentage")
        late_fee_value: Percentage (e.g., 5.0 for 5%) or flat amount (default: 5.0)
        max_fee: Maximum allowed fee (default: None = no limit)

    Returns:
        Late fee amount

    Examples:
        >>> calculate_late_fee(1000, 5, "percentage", 5.0)
        Decimal('50.00')  # 5% of $1000
        >>> calculate_late_fee(1000, 5, "flat", 50.0)
        Decimal('50.00')
    """
    if days_late <= 0:
        return Decimal('0.00')

    rent_decimal = Decimal(str(rent_amount))

    if late_fee_type == "percentage":
        # Calculate percentage of rent
        fee = rent_decimal * (Decimal(str(late_fee_value)) / Decimal('100'))
    else:  # flat
        # Use flat fee
        fee = Decimal(str(late_fee_value))

    # Apply maximum if specified
    if max_fee is not None:
        fee = min(fee, Decimal(str(max_fee)))

    return fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_total_rent(
    base_rent: float,
    utilities: Optional[float] = None,
    parking: Optional[float] = None,
    pet_fee: Optional[float] = None,
    other_fees: Optional[List[float]] = None
) -> Decimal:
    """
    Calculate total monthly rent including all fees

    Args:
        base_rent: Base monthly rent
        utilities: Utility fees (optional)
        parking: Parking fees (optional)
        pet_fee: Pet rent (optional)
        other_fees: List of other fees (optional)

    Returns:
        Total rent amount

    Examples:
        >>> calculate_total_rent(1000, utilities=50, parking=25, pet_fee=30)
        Decimal('1105.00')
    """
    total = Decimal(str(base_rent))

    if utilities:
        total += Decimal(str(utilities))
    if parking:
        total += Decimal(str(parking))
    if pet_fee:
        total += Decimal(str(pet_fee))
    if other_fees:
        for fee in other_fees:
            total += Decimal(str(fee))

    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_security_deposit(
    monthly_rent: float,
    deposit_multiplier: float = 1.5,
    max_deposit: Optional[float] = None
) -> Decimal:
    """
    Calculate security deposit amount

    Args:
        monthly_rent: Monthly rent amount
        deposit_multiplier: Multiple of monthly rent (default: 1.5)
        max_deposit: Maximum allowed deposit by law (default: None)

    Returns:
        Security deposit amount

    Examples:
        >>> calculate_security_deposit(1000)
        Decimal('1500.00')  # 1.5 months
        >>> calculate_security_deposit(1000, max_deposit=2000)
        Decimal('1500.00')
    """
    deposit = Decimal(str(monthly_rent)) * Decimal(str(deposit_multiplier))

    # Apply maximum if specified
    if max_deposit is not None:
        deposit = min(deposit, Decimal(str(max_deposit)))

    return deposit.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_utility_split(
    total_bill: float,
    num_units: int,
    unit_square_footages: Optional[List[float]] = None,
    split_type: str = "equal"
) -> Dict[int, Decimal]:
    """
    Calculate utility bill split across units

    Args:
        total_bill: Total utility bill amount
        num_units: Number of units
        unit_square_footages: List of unit square footages (for proportional split)
        split_type: "equal" or "proportional" (default: "equal")

    Returns:
        Dictionary mapping unit index to amount owed

    Examples:
        >>> calculate_utility_split(300, 3)
        {0: Decimal('100.00'), 1: Decimal('100.00'), 2: Decimal('100.00')}

        >>> calculate_utility_split(300, 3, [800, 1000, 1200], "proportional")
        {0: Decimal('80.00'), 1: Decimal('100.00'), 2: Decimal('120.00')}
    """
    bill_decimal = Decimal(str(total_bill))

    if split_type == "proportional" and unit_square_footages:
        # Calculate proportional split based on square footage
        total_sqft = sum(unit_square_footages)
        splits = {}

        for i, sqft in enumerate(unit_square_footages):
            proportion = Decimal(str(sqft)) / Decimal(str(total_sqft))
            amount = (bill_decimal * proportion).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            splits[i] = amount

        return splits

    else:  # equal split
        # Split equally
        per_unit = (bill_decimal / Decimal(num_units)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return {i: per_unit for i in range(num_units)}


def calculate_payment_breakdown(
    total_payment: float,
    rent_owed: float,
    late_fees_owed: float = 0.0,
    utilities_owed: float = 0.0,
    other_charges: Optional[Dict[str, float]] = None
) -> Dict[str, Decimal]:
    """
    Break down payment across multiple charges (rent, late fees, utilities, etc.)

    Args:
        total_payment: Total payment amount
        rent_owed: Rent amount owed
        late_fees_owed: Late fees owed (default: 0.0)
        utilities_owed: Utilities owed (default: 0.0)
        other_charges: Other charges dict (default: None)

    Returns:
        Dictionary showing how payment was allocated

    Examples:
        >>> calculate_payment_breakdown(1000, rent_owed=900, late_fees_owed=50, utilities_owed=50)
        {
            'rent': Decimal('900.00'),
            'late_fees': Decimal('50.00'),
            'utilities': Decimal('50.00'),
            'remaining': Decimal('0.00')
        }
    """
    payment = Decimal(str(total_payment))
    breakdown = {}

    # Apply to late fees first (standard practice)
    if late_fees_owed > 0:
        late_fees_decimal = Decimal(str(late_fees_owed))
        applied_to_late_fees = min(payment, late_fees_decimal)
        breakdown['late_fees'] = applied_to_late_fees
        payment -= applied_to_late_fees

    # Then apply to rent
    if rent_owed > 0 and payment > 0:
        rent_decimal = Decimal(str(rent_owed))
        applied_to_rent = min(payment, rent_decimal)
        breakdown['rent'] = applied_to_rent
        payment -= applied_to_rent

    # Then utilities
    if utilities_owed > 0 and payment > 0:
        utilities_decimal = Decimal(str(utilities_owed))
        applied_to_utilities = min(payment, utilities_decimal)
        breakdown['utilities'] = applied_to_utilities
        payment -= applied_to_utilities

    # Then other charges
    if other_charges and payment > 0:
        for charge_name, charge_amount in other_charges.items():
            if payment <= 0:
                break
            charge_decimal = Decimal(str(charge_amount))
            applied = min(payment, charge_decimal)
            breakdown[charge_name] = applied
            payment -= applied

    # Any remaining credit
    breakdown['remaining'] = payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return breakdown


def calculate_annual_rent_increase(
    current_rent: float,
    increase_type: str = "percentage",
    increase_value: float = 3.0,
    max_increase: Optional[float] = None
) -> Decimal:
    """
    Calculate new rent after annual increase

    Args:
        current_rent: Current monthly rent
        increase_type: "percentage" or "flat" (default: "percentage")
        increase_value: Percentage or flat amount (default: 3.0%)
        max_increase: Maximum allowed increase (default: None)

    Returns:
        New monthly rent amount

    Examples:
        >>> calculate_annual_rent_increase(1000, "percentage", 3.0)
        Decimal('1030.00')  # 3% increase
        >>> calculate_annual_rent_increase(1000, "flat", 50)
        Decimal('1050.00')
    """
    rent_decimal = Decimal(str(current_rent))

    if increase_type == "percentage":
        increase = rent_decimal * (Decimal(str(increase_value)) / Decimal('100'))
    else:  # flat
        increase = Decimal(str(increase_value))

    # Apply maximum if specified
    if max_increase is not None:
        increase = min(increase, Decimal(str(max_increase)))

    new_rent = rent_decimal + increase
    return new_rent.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_move_out_charges(
    security_deposit: float,
    damages: Optional[List[Dict[str, float]]] = None,
    unpaid_rent: float = 0.0,
    cleaning_fee: float = 0.0
) -> Dict[str, Decimal]:
    """
    Calculate move-out charges and security deposit refund

    Args:
        security_deposit: Security deposit amount
        damages: List of damage items with amounts (optional)
        unpaid_rent: Unpaid rent amount (default: 0.0)
        cleaning_fee: Cleaning fee (default: 0.0)

    Returns:
        Dictionary with charges breakdown and refund amount

    Examples:
        >>> calculate_move_out_charges(
        ...     1500,
        ...     damages=[{'description': 'Carpet damage', 'amount': 200}],
        ...     cleaning_fee=150
        ... )
        {
            'deposit': Decimal('1500.00'),
            'damages': Decimal('200.00'),
            'cleaning': Decimal('150.00'),
            'unpaid_rent': Decimal('0.00'),
            'total_charges': Decimal('350.00'),
            'refund': Decimal('1150.00')
        }
    """
    deposit_decimal = Decimal(str(security_deposit))
    result = {
        'deposit': deposit_decimal,
        'damages': Decimal('0.00'),
        'cleaning': Decimal(str(cleaning_fee)),
        'unpaid_rent': Decimal(str(unpaid_rent)),
    }

    # Calculate total damages
    if damages:
        total_damages = sum(Decimal(str(item.get('amount', 0))) for item in damages)
        result['damages'] = total_damages.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Calculate total charges
    total_charges = result['damages'] + result['cleaning'] + result['unpaid_rent']
    result['total_charges'] = total_charges.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Calculate refund (can be negative if charges exceed deposit)
    refund = deposit_decimal - total_charges
    result['refund'] = refund.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return result
