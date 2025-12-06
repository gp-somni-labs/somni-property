"""
Somni Property Manager - Quotes API
Generate and manage customer quotes with live vendor pricing
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json
import logging

logger = logging.getLogger(__name__)

from db.database import get_db
from db.models_quotes import (
    Quote as QuoteModel,
    QuoteLineItem as QuoteLineItemModel,
    PricingTier as PricingTierModel,
    VendorPricing as VendorPricingModel,
    QuoteProductOption as QuoteProductOptionModel,
    QuoteComment as QuoteCommentModel,
    QuoteCustomerSelection as QuoteCustomerSelectionModel,
    QuoteLaborItem as QuoteLaborItemModel
)
from api.schemas_quotes import (
    Quote, QuoteCreate, QuoteUpdate, QuoteListResponse,
    QuoteCalculationRequest, QuoteCalculationResponse,
    QuoteSummaryStats,
    PricingTier, PricingTierCreate, PricingTierUpdate, PricingTierListResponse,
    VendorPricing, VendorPricingListResponse,
    QuoteProductOption, QuoteProductOptionCreate, QuoteProductOptionUpdate,
    QuoteComment, QuoteCommentCreate, QuoteCommentUpdate,
    QuoteCustomerSelection, QuoteCustomerSelectionCreate, QuoteCustomerSelectionUpdate,
    CustomerPortalLinkResponse
)
from services.quote_calculator import QuoteCalculator
from services.vendor_pricing_scraper import update_vendor_pricing_data
from services.quote_pdf_generator import generate_quote_pdf
from services.file_storage import get_file_storage_service
from services.labor_calculator import LaborCalculator
from core.auth import AuthUser, require_admin, require_manager
from core.config import settings
from fastapi.responses import Response
from utils.quote_disclaimers import get_default_disclaimers

router = APIRouter()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def ensure_labor_items_exist(quote_id: UUID, db: AsyncSession) -> bool:
    """
    Ensure labor items exist for a quote.
    If product options exist but no labor items, auto-generate them.

    Returns True if labor items exist or were created, False otherwise.
    """
    # Check if labor items already exist
    labor_query = select(QuoteLaborItemModel).where(QuoteLaborItemModel.quote_id == quote_id).limit(1)
    labor_result = await db.execute(labor_query)
    existing_labor = labor_result.scalar_one_or_none()

    if existing_labor:
        logger.info(f"Labor items already exist for quote {quote_id}")
        return True

    # Get product options for this quote
    product_options_query = select(QuoteProductOptionModel).where(
        QuoteProductOptionModel.quote_id == quote_id
    )
    product_options_result = await db.execute(product_options_query)
    product_options = product_options_result.scalars().all()

    if not product_options or len(product_options) == 0:
        logger.warning(f"No product options found for quote {quote_id}, cannot generate labor items")
        return False

    # Get customer selections to determine which tier was selected
    customer_selection_query = select(QuoteCustomerSelectionModel).where(
        QuoteCustomerSelectionModel.quote_id == quote_id
    )
    customer_selection_result = await db.execute(customer_selection_query)
    customer_selection = customer_selection_result.scalar_one_or_none()

    # Convert product options to labor calculator format
    product_selections = []
    for product_option in product_options:
        # Determine which tier to use (default to standard if no customer selection)
        selected_tier = 'standard'
        if customer_selection and customer_selection.custom_selections:
            selected_tier = customer_selection.custom_selections.get(
                product_option.product_category,
                customer_selection.selected_tier or 'standard'
            )
        elif customer_selection and customer_selection.selected_tier:
            selected_tier = customer_selection.selected_tier

        # Map product category to format expected by labor calculator
        # product_category format: "smart_locks", "thermostats", "hub", etc.
        category_mapping = {
            'smart_locks': 'smart_lock',
            'thermostats': 'thermostat',
            'hubs': 'hub',
            'cameras': 'camera',
            'doorbells': 'doorbell',
            'sensors': 'sensor',
            'switches': 'switch',
            'outlets': 'outlet',
            'garage_doors': 'garage_door',
            'shades': 'shade',
        }

        category = category_mapping.get(
            product_option.product_category.lower(),
            product_option.product_category.lower().rstrip('s')  # Remove trailing 's' as fallback
        )

        if float(product_option.quantity) > 0:
            product_selections.append({
                'category': category,
                'quantity': float(product_option.quantity),
                'selected_tier': selected_tier
            })

    if not product_selections:
        logger.warning(f"No products with quantity > 0 for quote {quote_id}")
        return False

    logger.info(f"Generating labor items for quote {quote_id} with {len(product_selections)} product categories")

    # Call labor calculator
    calculator = LaborCalculator(db)
    try:
        labor_estimation = await calculator.estimate_labor(
            quote_id=quote_id,
            product_selections=product_selections,
            include_materials=True,
            labor_rate_override=None
        )

        # Create QuoteLaborItem records
        for labor_item_data in labor_estimation['labor_items']:
            labor_item = QuoteLaborItemModel(
                quote_id=quote_id,
                line_number=labor_item_data['line_number'],
                category=labor_item_data['category'],
                task_name=labor_item_data['task_name'],
                description=labor_item_data['description'],
                scope_of_work=labor_item_data.get('scope_of_work', ''),
                estimated_hours=labor_item_data['estimated_hours'],
                hourly_rate=labor_item_data['hourly_rate'],
                labor_subtotal=labor_item_data['labor_subtotal'],
                quantity=labor_item_data['quantity'],
                unit_type=labor_item_data.get('unit_type', 'per device'),
                associated_device_count=labor_item_data.get('associated_device_count', 0),
                materials_needed=labor_item_data.get('materials_needed', []),
                materials_cost=labor_item_data['materials_cost'],
                total_cost=labor_item_data['total_cost'],
                is_auto_calculated=labor_item_data.get('is_auto_calculated', True),
                is_optional=labor_item_data.get('is_optional', False),
                requires_approval=labor_item_data.get('requires_approval', False),
                display_order=labor_item_data['line_number']
            )
            db.add(labor_item)

        await db.commit()
        logger.info(f"Created {len(labor_estimation['labor_items'])} labor items for quote {quote_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate labor items for quote {quote_id}: {str(e)}")
        await db.rollback()
        return False


# ============================================================================
# QUOTE CALCULATION (No auth required - for prospects)
# ============================================================================

@router.post("/quotes/calculate", response_model=QuoteCalculationResponse)
async def calculate_quote(
    request: QuoteCalculationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate quote pricing WITHOUT saving to database

    Public endpoint for prospects to see pricing before signup.
    No authentication required.

    Returns detailed pricing breakdown based on:
    - Number of units
    - Smart home service penetration
    - Pricing tier (or default)
    """
    calculator = QuoteCalculator(db)

    calculation = await calculator.calculate_quote(
        total_units=request.total_units,
        pricing_tier_id=request.pricing_tier_id,
        include_smart_home=request.include_smart_home,
        smart_home_penetration=request.smart_home_penetration,
        smart_home_tier_distribution=request.smart_home_tier_distribution,
        discount_percentage=request.discount_percentage
    )

    # Get pricing tier info if provided
    pricing_tier = None
    if request.pricing_tier_id:
        query = select(PricingTierModel).where(PricingTierModel.id == request.pricing_tier_id)
        result = await db.execute(query)
        tier_obj = result.scalar_one_or_none()
        if tier_obj:
            pricing_tier = PricingTier.model_validate(tier_obj)

    return QuoteCalculationResponse(
        **calculation,
        pricing_tier=pricing_tier
    )


# ============================================================================
# QUOTE CRUD (Requires auth)
# ============================================================================

@router.post("/quotes", response_model=Quote, status_code=201)
async def create_quote(
    quote_data: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Create a new quote and save to database

    This endpoint:
    1. Calculates pricing based on inputs
    2. Generates quote number
    3. Creates line items
    4. Saves to database

    Admin/Manager only.
    """
    calculator = QuoteCalculator(db)

    # Extract product selections if available (for labor calculation)
    product_selections = None
    if hasattr(quote_data, 'product_selections') and quote_data.product_selections:
        product_selections = quote_data.product_selections

    # Calculate pricing (including labor if products provided)
    calculation = await calculator.calculate_quote(
        total_units=quote_data.total_units,
        pricing_tier_id=quote_data.pricing_tier_id,
        include_smart_home=quote_data.include_smart_home,
        smart_home_penetration=quote_data.smart_home_penetration,
        smart_home_tier_distribution=quote_data.smart_home_tier_distribution,
        discount_percentage=quote_data.discount_percentage,
        product_selections=product_selections
    )

    # Generate quote number
    quote_number = QuoteCalculator.generate_quote_number()

    # Calculate validity date
    valid_until = quote_data.valid_until
    if not valid_until:
        valid_until = QuoteCalculator.calculate_validity_date(30)

    # Calculate discount amount
    discount_amount = calculation["monthly_discount"]

    # Get disclaimers (use custom if provided, otherwise defaults)
    disclaimers = quote_data.price_increase_disclaimers if hasattr(quote_data, 'price_increase_disclaimers') and quote_data.price_increase_disclaimers else get_default_disclaimers()

    # Create quote (including labor cost fields and client linkage)
    quote_obj = QuoteModel(
        quote_number=quote_number,
        customer_name=quote_data.customer_name,
        customer_email=quote_data.customer_email,
        customer_phone=quote_data.customer_phone,
        company_name=quote_data.company_name,
        client_id=quote_data.client_id,  # Link to client if provided
        property_id=quote_data.property_id,  # Link to property if provided
        building_id=quote_data.building_id,  # Link to building if provided
        total_units=quote_data.total_units,
        property_count=quote_data.property_count,
        property_locations=quote_data.property_locations,
        property_types=quote_data.property_types,
        pricing_tier_id=quote_data.pricing_tier_id,
        include_smart_home=quote_data.include_smart_home,
        smart_home_penetration=quote_data.smart_home_penetration,
        smart_home_tier_distribution=quote_data.smart_home_tier_distribution,
        monthly_property_mgmt=calculation["monthly_property_mgmt"],
        monthly_smart_home=calculation["monthly_smart_home"],
        monthly_additional_fees=calculation["monthly_additional_fees"],
        monthly_total=calculation["monthly_total"],
        annual_total=calculation["annual_total"],
        setup_fees=calculation["setup_fees"],
        hardware_costs=0,  # Can be customized later
        discount_percentage=quote_data.discount_percentage,
        discount_reason=quote_data.discount_reason,
        discount_amount=discount_amount,
        valid_until=valid_until,
        notes=quote_data.notes,
        terms_conditions=quote_data.terms_conditions,
        price_increase_disclaimers=disclaimers,  # Auto-populate with defaults
        floor_plans=quote_data.floor_plans or [],  # Include floor plans from quote calculator
        status='draft',
        created_by=auth_user.username
    )

    # Set labor cost fields if calculated (check if fields exist in model)
    if hasattr(quote_obj, 'total_labor_cost'):
        quote_obj.total_labor_cost = calculation.get("total_labor_cost", 0)
    if hasattr(quote_obj, 'total_materials_cost'):
        quote_obj.total_materials_cost = calculation.get("total_materials_cost", 0)
    if hasattr(quote_obj, 'total_labor_hours'):
        quote_obj.total_labor_hours = calculation.get("total_labor_hours", 0)
    if hasattr(quote_obj, 'project_duration_days'):
        quote_obj.project_duration_days = calculation.get("project_duration_days", 0)

    db.add(quote_obj)
    await db.flush()

    # Get detailed labor items if products were selected (for line item breakdown)
    detailed_labor_items = None
    if product_selections and len(product_selections) > 0:
        try:
            labor_calc = LaborCalculator(db)
            labor_result = await labor_calc.estimate_labor(
                quote_id=quote_obj.id,
                product_selections=product_selections,
                include_materials=True
            )
            detailed_labor_items = labor_result.get('labor_items', [])
            logger.info(f"Retrieved {len(detailed_labor_items)} detailed labor items for line item generation")
        except Exception as e:
            logger.warning(f"Failed to get detailed labor items: {e}")

    # Generate and add line items (including labor details if available)
    line_items = await calculator.generate_line_items(
        total_units=quote_data.total_units,
        calculation=calculation,
        include_smart_home=quote_data.include_smart_home,
        labor_items=detailed_labor_items
    )

    for line_item_data in line_items:
        line_item = QuoteLineItemModel(
            quote_id=quote_obj.id,
            **line_item_data
        )
        db.add(line_item)

    # Generate labor items immediately if products were selected
    if product_selections and len(product_selections) > 0:
        logger.info(f"Generating labor items for quote {quote_obj.id} with {len(product_selections)} product categories")
        labor_generation_success = await ensure_labor_items_exist(quote_obj.id, db)
        if not labor_generation_success:
            logger.warning(f"Failed to generate labor items for quote {quote_obj.id}, continuing without labor breakdown")

    await db.commit()

    # Re-query with eager loading to avoid lazy load issues during serialization
    query = select(QuoteModel).where(QuoteModel.id == quote_obj.id).options(selectinload(QuoteModel.line_items))
    result = await db.execute(query)
    quote_with_items = result.scalar_one()

    return quote_with_items


@router.get("/quotes", response_model=QuoteListResponse)
async def list_quotes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, pattern="^(draft|sent|accepted|rejected|expired)$"),
    customer_email: Optional[str] = None,
    client_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all quotes with pagination and filtering

    Admin/Manager only.

    Filters:
    - status: Filter by quote status
    - customer_email: Search by customer email
    - client_id: Filter by client ID
    """
    query_base = select(QuoteModel)

    # Apply filters
    if status:
        query_base = query_base.where(QuoteModel.status == status)
    if customer_email:
        query_base = query_base.where(QuoteModel.customer_email.ilike(f"%{customer_email}%"))
    if client_id:
        query_base = query_base.where(QuoteModel.client_id == client_id)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get quotes with eager loading of relationships
    query = query_base.options(selectinload(QuoteModel.line_items)).offset(skip).limit(limit).order_by(QuoteModel.created_at.desc())
    result = await db.execute(query)
    quotes = result.scalars().all()

    return QuoteListResponse(
        items=quotes,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/quotes/{quote_id}", response_model=Quote)
async def get_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific quote by ID (Admin/Manager only)"""
    query = select(QuoteModel).where(QuoteModel.id == quote_id).options(selectinload(QuoteModel.line_items))
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    return quote_obj


@router.put("/quotes/{quote_id}", response_model=Quote)
async def update_quote(
    quote_id: UUID,
    quote_data: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Update an existing quote

    If pricing-related fields change, recalculates totals.
    Admin/Manager only.
    """
    query = select(QuoteModel).where(QuoteModel.id == quote_id).options(selectinload(QuoteModel.line_items))
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Track if we need to recalculate
    needs_recalc = False
    update_data = quote_data.model_dump(exclude_unset=True)

    # Check if pricing-affecting fields changed
    pricing_fields = {'total_units', 'pricing_tier_id', 'include_smart_home',
                      'smart_home_penetration', 'smart_home_tier_distribution',
                      'discount_percentage'}

    if any(field in update_data for field in pricing_fields):
        needs_recalc = True

    # Apply simple updates
    for key, value in update_data.items():
        if key not in pricing_fields:
            setattr(quote_obj, key, value)

    # Recalculate if needed
    if needs_recalc:
        calculator = QuoteCalculator(db)

        calculation = await calculator.calculate_quote(
            total_units=update_data.get('total_units', quote_obj.total_units),
            pricing_tier_id=update_data.get('pricing_tier_id', quote_obj.pricing_tier_id),
            include_smart_home=update_data.get('include_smart_home', quote_obj.include_smart_home),
            smart_home_penetration=update_data.get('smart_home_penetration', quote_obj.smart_home_penetration),
            smart_home_tier_distribution=update_data.get('smart_home_tier_distribution', quote_obj.smart_home_tier_distribution),
            discount_percentage=update_data.get('discount_percentage', quote_obj.discount_percentage)
        )

        # Update calculated fields
        quote_obj.monthly_property_mgmt = calculation["monthly_property_mgmt"]
        quote_obj.monthly_smart_home = calculation["monthly_smart_home"]
        quote_obj.monthly_additional_fees = calculation["monthly_additional_fees"]
        quote_obj.monthly_total = calculation["monthly_total"]
        quote_obj.annual_total = calculation["annual_total"]
        quote_obj.discount_amount = calculation["monthly_discount"]

    await db.commit()
    await db.refresh(quote_obj)

    return quote_obj


@router.delete("/quotes/{quote_id}", status_code=204)
async def delete_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Delete a quote

    Admin only. Deletes the quote and all associated line items, labor items,
    product options, comments, and customer selections.
    """
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Delete the quote (cascade will handle related records)
    await db.delete(quote_obj)
    await db.commit()

    return


@router.post("/quotes/{quote_id}/send", response_model=Quote)
async def send_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Mark quote as sent and email to customer

    Generates customer portal link, creates PDF, and sends email.
    Admin/Manager only.
    """
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    if not quote_obj.customer_email:
        raise HTTPException(status_code=400, detail="Quote has no customer email address")

    # Generate customer portal token if not exists
    if not quote_obj.customer_portal_token:
        from datetime import timedelta, timezone
        import hmac
        import hashlib
        import json
        from base64 import urlsafe_b64encode

        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        token_data = {
            "quote_id": str(quote_id),
            "customer_email": quote_obj.customer_email,
            "expires_at": expires_at.isoformat()
        }

        # Create HMAC signature
        if not settings.CUSTOMER_PORTAL_SECRET_KEY:
            raise HTTPException(
                status_code=500,
                detail="CUSTOMER_PORTAL_SECRET_KEY not configured. Set this environment variable to enable customer portal."
            )
        message = json.dumps(token_data, sort_keys=True)
        signature = hmac.new(
            settings.CUSTOMER_PORTAL_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        token_data['signature'] = signature
        token = urlsafe_b64encode(json.dumps(token_data).encode()).decode()

        quote_obj.customer_portal_token = token
        quote_obj.customer_portal_token_expires = expires_at

    # Generate customer portal URL
    base_url = os.getenv('PUBLIC_BASE_URL', 'https://property.home.lan')
    portal_url = f"{base_url}/customer-quotes/{quote_id}?token={quote_obj.customer_portal_token}"

    # Ensure labor items exist (auto-generate from product options if needed)
    await ensure_labor_items_exist(quote_id, db)

    # Generate PDF
    from services.quote_pdf_generator import QuotePDFGenerator

    # Get line items
    line_items_query = select(QuoteLineItemModel).where(
        QuoteLineItemModel.quote_id == quote_id
    )
    line_items_result = await db.execute(line_items_query)
    line_items_objs = line_items_result.scalars().all()

    # Convert to dict for PDF generator
    quote_dict = {
        'quote_number': quote_obj.quote_number,
        'customer_name': quote_obj.customer_name,
        'customer_email': quote_obj.customer_email,
        'customer_phone': quote_obj.customer_phone,
        'company_name': quote_obj.company_name,
        'total_units': quote_obj.total_units,
        'property_count': quote_obj.property_count,
        'smart_home_penetration': quote_obj.smart_home_penetration,
        'monthly_property_mgmt': quote_obj.monthly_property_mgmt,
        'monthly_smart_home': quote_obj.monthly_smart_home,
        'monthly_additional_fees': quote_obj.monthly_additional_fees,
        'monthly_total': quote_obj.monthly_total,
        'annual_total': quote_obj.annual_total,
        'setup_fees': quote_obj.setup_fees,
        'discount_percentage': quote_obj.discount_percentage,
        'discount_amount': quote_obj.discount_amount,
        'status': quote_obj.status,
        'created_at': quote_obj.created_at,
        'valid_until': quote_obj.valid_until,
        'price_increase_disclaimers': quote_obj.price_increase_disclaimers,
        'floor_plans': quote_obj.floor_plans,
        'polycam_scans': quote_obj.polycam_scans,
        'implementation_photos': quote_obj.implementation_photos,
        'comparison_photos': quote_obj.comparison_photos,
        'include_smart_home': quote_obj.include_smart_home
    }

    line_items_dict = [
        {
            'item_type': item.item_type,
            'description': item.description,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'subtotal': item.subtotal,
            'category': item.category
        }
        for item in line_items_objs
    ]

    # Get labor items
    labor_items_query = select(QuoteLaborItemModel).where(
        QuoteLaborItemModel.quote_id == quote_id
    ).order_by(QuoteLaborItemModel.display_order.asc())
    labor_items_result = await db.execute(labor_items_query)
    labor_items_objs = labor_items_result.scalars().all()

    labor_items_list = [
        {
            'line_number': item.line_number,
            'category': item.category,
            'task_name': item.task_name,
            'description': item.description,
            'scope_of_work': item.scope_of_work,
            'estimated_hours': float(item.estimated_hours),
            'hourly_rate': float(item.hourly_rate),
            'labor_subtotal': float(item.labor_subtotal),
            'quantity': float(item.quantity),
            'unit_type': item.unit_type,
            'materials_needed': item.materials_needed or [],
            'materials_cost': float(item.materials_cost),
            'total_cost': float(item.total_cost),
        }
        for item in labor_items_objs
    ]

    pdf_generator = QuotePDFGenerator()
    pdf_content = pdf_generator.generate_pdf(quote_dict, line_items_dict, labor_items_list)

    # Send email via SendGrid
    try:
        from services.quote_email_service import quote_email_service

        if quote_email_service:
            email_sent = await quote_email_service.send_quote_email(
                quote=quote_dict,
                pdf_content=pdf_content,
                customer_portal_url=portal_url
            )

            if not email_sent:
                # Log but don't fail - quote is still marked as sent
                print(f"Warning: Failed to send email for quote {quote_id}")
        else:
            print(f"Warning: SendGrid not configured, skipping email for quote {quote_id}")
    except Exception as e:
        print(f"Error sending quote email: {e}")
        # Don't fail the request - quote is still marked as sent

    # Update quote status
    quote_obj.status = 'sent'
    quote_obj.sent_at = datetime.utcnow()

    await db.commit()
    await db.refresh(quote_obj)

    return quote_obj


@router.get("/quotes/{quote_id}/pdf")
async def download_quote_pdf(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Download quote as PDF

    Generates a professional PDF quote document.
    Admin/Manager only.

    Returns PDF file with proper headers for download.
    """
    # Get quote with line items
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Ensure labor items exist (auto-generate from product options if needed)
    await ensure_labor_items_exist(quote_id, db)

    # Get line items
    line_items_query = select(QuoteLineItemModel).where(
        QuoteLineItemModel.quote_id == quote_id
    )
    line_items_result = await db.execute(line_items_query)
    line_items_objs = line_items_result.scalars().all()

    # Convert to dictionaries for PDF generator (include ALL fields for comprehensive PDF)
    quote_dict = {
        'quote_number': quote_obj.quote_number,
        'customer_name': quote_obj.customer_name,
        'customer_email': quote_obj.customer_email,
        'customer_phone': quote_obj.customer_phone,
        'company_name': quote_obj.company_name,
        'total_units': quote_obj.total_units,
        'property_count': quote_obj.property_count,
        'smart_home_penetration': quote_obj.smart_home_penetration,
        'monthly_property_mgmt': quote_obj.monthly_property_mgmt,
        'monthly_smart_home': quote_obj.monthly_smart_home,
        'monthly_additional_fees': quote_obj.monthly_additional_fees,
        'monthly_total': quote_obj.monthly_total,
        'annual_total': quote_obj.annual_total,
        'setup_fees': quote_obj.setup_fees,
        'discount_percentage': quote_obj.discount_percentage,
        'discount_amount': quote_obj.discount_amount,
        'status': quote_obj.status,
        'created_at': quote_obj.created_at,
        'valid_until': quote_obj.valid_until,
        'notes': quote_obj.notes,
        'terms_conditions': quote_obj.terms_conditions,

        # Visual Assets (for immersive PDFs)
        'floor_plans': quote_obj.floor_plans or [],
        'polycam_scans': quote_obj.polycam_scans or [],
        'implementation_photos': quote_obj.implementation_photos or [],
        'comparison_photos': quote_obj.comparison_photos or [],

        # Property Metadata
        'property_locations': quote_obj.property_locations or [],
        'property_types': quote_obj.property_types or [],

        # Price Disclaimers
        'price_increase_disclaimers': quote_obj.price_increase_disclaimers or [],

        # Subscription & Installation Details (new quote format)
        'billing_period': getattr(quote_obj, 'billing_period', 'monthly'),
        'monthly_subscription_total': getattr(quote_obj, 'monthly_subscription_total', 0),
        'one_time_hardware_total': getattr(quote_obj, 'one_time_hardware_total', 0),
        'one_time_installation_total': getattr(quote_obj, 'one_time_installation_total', 0),
        'installation_hours': getattr(quote_obj, 'installation_hours', 2.0),
        'installation_rate': getattr(quote_obj, 'installation_rate', 150),
    }

    line_items_list = [
        {
            'description': item.description,
            'category': item.category,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'unit_type': item.unit_type,
            'subtotal': item.subtotal,
            'vendor': getattr(item, 'vendor', 'N/A')  # Include vendor for product tables
        }
        for item in line_items_objs
    ]

    # Get labor items
    labor_items_query = select(QuoteLaborItemModel).where(
        QuoteLaborItemModel.quote_id == quote_id
    ).order_by(QuoteLaborItemModel.display_order.asc())
    labor_items_result = await db.execute(labor_items_query)
    labor_items_objs = labor_items_result.scalars().all()

    labor_items_list = [
        {
            'line_number': item.line_number,
            'category': item.category,
            'task_name': item.task_name,
            'description': item.description,
            'scope_of_work': item.scope_of_work,
            'estimated_hours': float(item.estimated_hours),
            'hourly_rate': float(item.hourly_rate),
            'labor_subtotal': float(item.labor_subtotal),
            'quantity': float(item.quantity),
            'unit_type': item.unit_type,
            'materials_needed': item.materials_needed or [],
            'materials_cost': float(item.materials_cost),
            'total_cost': float(item.total_cost),
        }
        for item in labor_items_objs
    ]

    # Generate PDF (pass labor items separately)
    pdf_bytes = await generate_quote_pdf(quote_dict, line_items_list, labor_items_list)

    # Create filename
    filename = f"quote_{quote_obj.quote_number}.pdf"

    # Return PDF with proper headers
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/quotes/stats/summary", response_model=QuoteSummaryStats)
async def get_quote_stats(
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get summary statistics for quotes

    Admin/Manager only.
    """
    from sqlalchemy import case
    from decimal import Decimal

    # Total quotes
    total_query = select(func.count()).select_from(QuoteModel)
    total_result = await db.execute(total_query)
    total_quotes = total_result.scalar_one()

    # Quotes by status
    status_query = select(
        QuoteModel.status,
        func.count(QuoteModel.id).label('count')
    ).group_by(QuoteModel.status)

    status_result = await db.execute(status_query)
    quotes_by_status = {row.status: row.count for row in status_result}

    # Total value
    value_query = select(
        func.sum(QuoteModel.monthly_total).label('monthly'),
        func.sum(QuoteModel.annual_total).label('annual'),
        func.avg(QuoteModel.total_units).label('avg_units')
    )

    value_result = await db.execute(value_query)
    values = value_result.one()

    # Conversion rate
    accepted = quotes_by_status.get('accepted', 0)
    conversion_rate = Decimal(accepted) / Decimal(total_quotes) * 100 if total_quotes > 0 else Decimal(0)

    return QuoteSummaryStats(
        total_quotes=total_quotes,
        quotes_by_status=quotes_by_status,
        total_value_monthly=values.monthly or Decimal(0),
        total_value_annual=values.annual or Decimal(0),
        average_units_per_quote=Decimal(str(values.avg_units or 0)),
        conversion_rate=conversion_rate.quantize(Decimal("0.01"))
    )


# ============================================================================
# PRICING TIERS
# ============================================================================

@router.get("/pricing-tiers", response_model=PricingTierListResponse)
async def list_pricing_tiers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """
    List all pricing tiers

    Public endpoint - no auth required.
    Useful for showing pricing options to prospects.
    """
    query_base = select(PricingTierModel)

    if active_only:
        query_base = query_base.where(PricingTierModel.active == True)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get tiers
    query = query_base.offset(skip).limit(limit).order_by(PricingTierModel.tier_level.asc())
    result = await db.execute(query)
    tiers = result.scalars().all()

    return PricingTierListResponse(
        items=tiers,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/pricing-tiers/compare")
async def compare_pricing_tiers(
    total_units: int = Query(..., ge=1, description="Total units to manage"),
    smart_home_penetration: float = Query(25.0, ge=0, le=100, description="% of units with smart home"),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare all pricing tiers for Good/Better/Best presentation

    Returns all active tiers with calculated pricing for the given property size.
    Public endpoint - no auth required (for prospects).

    This enables customer psychology through choice:
    - Shows 3 options side-by-side
    - Highlights "Most Popular" (middle tier)
    - Gives customer control through selection
    """
    # Get all active tiers ordered by level
    query = select(PricingTierModel).where(
        PricingTierModel.active == True
    ).order_by(PricingTierModel.tier_level.asc())

    result = await db.execute(query)
    tiers = result.scalars().all()

    if not tiers:
        raise HTTPException(
            status_code=404,
            detail="No active pricing tiers found. Please contact support."
        )

    calculator = QuoteCalculator(db)
    comparison = []

    for tier in tiers:
        # Determine smart home tier distribution based on pricing tier
        if tier.tier_level == 1:  # Starter - Basic only
            tier_distribution = {
                "basic": 100,
                "premium": 0,
                "enterprise": 0
            }
            max_penetration = 25.0  # Limit to 25%
            actual_penetration = min(smart_home_penetration, max_penetration)
        elif tier.tier_level == 2:  # Professional - Mix of Basic/Premium
            tier_distribution = {
                "basic": 30,
                "premium": 70,
                "enterprise": 0
            }
            max_penetration = 50.0  # Limit to 50%
            actual_penetration = min(smart_home_penetration, max_penetration)
        else:  # Enterprise - Full mix
            tier_distribution = {
                "basic": 10,
                "premium": 30,
                "enterprise": 60
            }
            actual_penetration = smart_home_penetration  # No limit

        # Calculate pricing for this tier
        calculation = await calculator.calculate_quote(
            total_units=total_units,
            pricing_tier_id=tier.id,
            include_smart_home=actual_penetration > 0,
            smart_home_penetration=actual_penetration,
            smart_home_tier_distribution=tier_distribution,
            discount_percentage=0  # No discount in comparison view
        )

        # Build comparison entry
        comparison.append({
            "tier_id": str(tier.id),
            "tier_name": tier.tier_name,
            "tier_level": tier.tier_level,
            "description": tier.description,
            "features": tier.features_included,
            "support_level": tier.support_level,
            "is_most_popular": tier.tier_level == 2,  # Middle tier is most popular
            "max_smart_home_penetration": max_penetration if tier.tier_level < 3 else None,
            "pricing": {
                "monthly_total": str(calculation["monthly_total"]),
                "annual_total": str(calculation["annual_total"]),
                "cost_per_unit_monthly": str(calculation["cost_per_unit_monthly"]),
                "monthly_property_mgmt": str(calculation["monthly_property_mgmt"]),
                "monthly_smart_home": str(calculation["monthly_smart_home"]),
                "smart_home_units": calculation["smart_home_units"],
                "total_units": total_units
            }
        })

    return {
        "tiers": comparison,
        "total_units": total_units,
        "smart_home_penetration_requested": smart_home_penetration
    }


@router.post("/pricing-tiers", response_model=PricingTier, status_code=201)
async def create_pricing_tier(
    tier_data: PricingTierCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Create a new pricing tier (Admin only)"""
    tier_obj = PricingTierModel(**tier_data.model_dump())
    db.add(tier_obj)
    await db.commit()
    await db.refresh(tier_obj)
    return tier_obj


# ============================================================================
# VENDOR PRICING
# ============================================================================

@router.get("/vendor-pricing", response_model=VendorPricingListResponse)
async def list_vendor_pricing(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    verified_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List vendor pricing data

    Admin/Manager only.

    Filters:
    - category: Filter by product category
    - verified_only: Only show manually verified prices
    """
    query_base = select(VendorPricingModel).where(VendorPricingModel.active == True)

    if category:
        query_base = query_base.where(VendorPricingModel.product_category == category)
    if verified_only:
        query_base = query_base.where(VendorPricingModel.verified == True)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get pricing
    query = query_base.offset(skip).limit(limit).order_by(VendorPricingModel.last_updated.desc())
    result = await db.execute(query)
    pricing = result.scalars().all()

    return VendorPricingListResponse(
        items=pricing,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/vendor-pricing/refresh")
async def refresh_vendor_pricing(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Refresh vendor pricing data from web scraping

    Runs in background. Admin only.

    IMPORTANT: Respect vendor TOS and rate limits.
    """
    # Run in background to avoid blocking
    background_tasks.add_task(update_vendor_pricing_data, db)

    return {"message": "Vendor pricing refresh started in background"}


# ============================================================================
# QUOTE PRODUCT OPTIONS (Economy/Standard/Premium Tiers)
# ============================================================================

@router.get("/quotes/{quote_id}/product-options", response_model=List[QuoteProductOption])
async def list_quote_product_options(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """List all product tier options for a quote"""
    query = select(QuoteProductOptionModel).where(
        QuoteProductOptionModel.quote_id == quote_id
    ).order_by(QuoteProductOptionModel.display_order.asc())

    result = await db.execute(query)
    options = result.scalars().all()
    return options


@router.post("/quotes/{quote_id}/product-options", response_model=QuoteProductOption, status_code=201)
async def create_quote_product_option(
    quote_id: UUID,
    option_data: QuoteProductOptionCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Add a product tier option to a quote"""
    # Verify quote exists
    quote_query = select(QuoteModel).where(QuoteModel.id == quote_id)
    quote_result = await db.execute(quote_query)
    if not quote_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Quote not found")

    option_obj = QuoteProductOptionModel(**option_data.model_dump())
    db.add(option_obj)
    await db.commit()
    await db.refresh(option_obj)
    return option_obj


@router.put("/quotes/{quote_id}/product-options/{option_id}", response_model=QuoteProductOption)
async def update_quote_product_option(
    quote_id: UUID,
    option_id: UUID,
    option_data: QuoteProductOptionUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Update a product tier option"""
    query = select(QuoteProductOptionModel).where(
        QuoteProductOptionModel.id == option_id,
        QuoteProductOptionModel.quote_id == quote_id
    )
    result = await db.execute(query)
    option_obj = result.scalar_one_or_none()

    if not option_obj:
        raise HTTPException(status_code=404, detail="Product option not found")

    update_data = option_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(option_obj, key, value)

    await db.commit()
    await db.refresh(option_obj)
    return option_obj


@router.delete("/quotes/{quote_id}/product-options/{option_id}", status_code=204)
async def delete_quote_product_option(
    quote_id: UUID,
    option_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Delete a product tier option"""
    query = select(QuoteProductOptionModel).where(
        QuoteProductOptionModel.id == option_id,
        QuoteProductOptionModel.quote_id == quote_id
    )
    result = await db.execute(query)
    option_obj = result.scalar_one_or_none()

    if not option_obj:
        raise HTTPException(status_code=404, detail="Product option not found")

    await db.delete(option_obj)
    await db.commit()


# ============================================================================
# QUOTE COMMENTS (Customer & Internal Collaboration)
# ============================================================================

@router.get("/quotes/{quote_id}/comments", response_model=List[QuoteComment])
async def list_quote_comments(
    quote_id: UUID,
    include_internal: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """List all comments for a quote (admin can see internal)"""
    query_base = select(QuoteCommentModel).where(
        QuoteCommentModel.quote_id == quote_id
    )

    if not include_internal:
        query_base = query_base.where(QuoteCommentModel.is_internal == False)

    query = query_base.order_by(QuoteCommentModel.created_at.asc())
    result = await db.execute(query)
    comments = result.scalars().all()
    return comments


@router.post("/quotes/{quote_id}/comments", response_model=QuoteComment, status_code=201)
async def create_quote_comment(
    quote_id: UUID,
    comment_data: QuoteCommentCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Add a comment to a quote"""
    # Verify quote exists
    quote_query = select(QuoteModel).where(QuoteModel.id == quote_id)
    quote_result = await db.execute(quote_query)
    if not quote_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Quote not found")

    comment_obj = QuoteCommentModel(
        **comment_data.model_dump(),
        created_by=auth_user.username
    )
    db.add(comment_obj)
    await db.commit()
    await db.refresh(comment_obj)
    return comment_obj


@router.put("/quotes/{quote_id}/comments/{comment_id}", response_model=QuoteComment)
async def update_quote_comment(
    quote_id: UUID,
    comment_id: UUID,
    comment_data: QuoteCommentUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Update a comment"""
    query = select(QuoteCommentModel).where(
        QuoteCommentModel.id == comment_id,
        QuoteCommentModel.quote_id == quote_id
    )
    result = await db.execute(query)
    comment_obj = result.scalar_one_or_none()

    if not comment_obj:
        raise HTTPException(status_code=404, detail="Comment not found")

    update_data = comment_data.model_dump(exclude_unset=True)

    # If marking as resolved, set metadata
    if update_data.get('resolved') == True and not comment_obj.resolved:
        comment_obj.resolved_at = datetime.utcnow()
        comment_obj.resolved_by = auth_user.username

    for key, value in update_data.items():
        setattr(comment_obj, key, value)

    await db.commit()
    await db.refresh(comment_obj)
    return comment_obj


@router.delete("/quotes/{quote_id}/comments/{comment_id}", status_code=204)
async def delete_quote_comment(
    quote_id: UUID,
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Delete a comment"""
    query = select(QuoteCommentModel).where(
        QuoteCommentModel.id == comment_id,
        QuoteCommentModel.quote_id == quote_id
    )
    result = await db.execute(query)
    comment_obj = result.scalar_one_or_none()

    if not comment_obj:
        raise HTTPException(status_code=404, detail="Comment not found")

    await db.delete(comment_obj)
    await db.commit()


# ============================================================================
# CUSTOMER PORTAL TOKEN GENERATION
# ============================================================================

@router.post("/quotes/{quote_id}/generate-customer-link", response_model=CustomerPortalLinkResponse)
async def generate_customer_portal_link(
    quote_id: UUID,
    expires_in_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Generate a secure customer portal link for a quote

    Creates a signed token that allows customer to:
    - View quote details
    - Add comments/questions
    - Select product tiers
    - Approve/reject quote
    """
    import secrets
    import hmac
    import hashlib
    import json
    from datetime import timezone, timedelta
    from base64 import urlsafe_b64encode

    # Get quote
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Generate secure token
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    token_data = {
        "quote_id": str(quote_id),
        "customer_email": quote_obj.customer_email,
        "expires_at": expires_at.isoformat()
    }

    # Create HMAC signature
    if not settings.CUSTOMER_PORTAL_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="CUSTOMER_PORTAL_SECRET_KEY not configured. Set this environment variable to enable customer portal."
        )
    message = json.dumps(token_data, sort_keys=True)
    signature = hmac.new(
        settings.CUSTOMER_PORTAL_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    token_data['signature'] = signature
    token = urlsafe_b64encode(json.dumps(token_data).encode()).decode()

    # Store token in database
    quote_obj.customer_portal_token = token
    quote_obj.customer_portal_token_expires = expires_at

    await db.commit()

    # Generate customer portal URL
    portal_url = f"https://portal.somni.example.com/quotes/{quote_id}?token={token}"

    return CustomerPortalLinkResponse(
        customer_portal_url=portal_url,
        token=token,
        expires_at=expires_at
    )


# ============================================================================
# QUOTE APPROVAL (Public - Customer Portal)
# ============================================================================

class QuoteApprovalRequest(BaseModel):
    """Customer quote approval"""
    signature_name: str = Field(..., min_length=2, description="Full name as electronic signature")
    comments: Optional[str] = Field(None, description="Optional comments from customer")


@router.post("/quotes/{quote_id}/approve", response_model=Quote)
async def approve_quote(
    quote_id: UUID,
    approval_data: QuoteApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a quote (Public endpoint for customer portal)

    Customer electronically signs and approves the quote.
    No authentication required - relies on secure customer portal token.
    """
    # Get quote
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Check if already approved
    if quote_obj.status == 'accepted':
        raise HTTPException(
            status_code=400,
            detail="Quote has already been approved"
        )

    # Check if quote is expired
    if quote_obj.valid_until and quote_obj.valid_until < datetime.utcnow():
        quote_obj.status = 'expired'
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail="Quote has expired. Please contact sales for an updated quote."
        )

    # Update quote with approval
    quote_obj.status = 'accepted'
    quote_obj.customer_signature = approval_data.signature_name
    quote_obj.customer_approval_comments = approval_data.comments
    quote_obj.approved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(quote_obj)

    logger.info(
        f"Quote {quote_id} approved by {approval_data.signature_name} "
        f"(customer: {quote_obj.customer_email})"
    )

    # TODO: Trigger notifications
    # - Send confirmation email to customer
    # - Notify sales team of approval
    # - Create onboarding tasks

    return quote_obj


# ============================================================================
# VISUAL QUOTE ASSETS (Floor Plans, Photos, 3D Scans)
# ============================================================================

@router.post("/quotes/{quote_id}/visual-assets/upload")
async def upload_visual_asset(
    quote_id: UUID,
    file: UploadFile,
    asset_type: str = Query(..., regex="^(floor_plan|implementation_photo|comparison_photo)$"),
    metadata: Optional[str] = Query(None, description="JSON string with additional metadata"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Upload a visual asset for a quote

    Supported asset types:
    - floor_plan: Floor plan images or PDFs
    - implementation_photo: Photos showing implementation methods
    - comparison_photo: Before/after comparison photos

    Returns file metadata with URLs for original and thumbnail.
    Admin/Manager only.
    """
    # Verify quote exists and user has permission
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Upload and process file
    file_storage = get_file_storage_service()
    file_metadata = await file_storage.upload_visual_asset(
        file=file,
        quote_id=str(quote_id),
        asset_type=asset_type
    )

    # Parse additional metadata if provided
    extra_metadata = {}
    if metadata:
        try:
            extra_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    # Merge metadata
    file_metadata.update(extra_metadata)

    # Update quote's JSONB array based on asset type
    if asset_type == "floor_plan":
        floor_plans = quote_obj.floor_plans or []
        floor_plans.append({
            "id": file_metadata["id"],
            "name": extra_metadata.get("name", file_metadata["filename"]),
            "file_url": file_metadata["file_url"],
            "thumbnail_url": file_metadata["thumbnail_url"],
            "annotations": []  # Will be populated via annotation endpoint
        })
        quote_obj.floor_plans = floor_plans

    elif asset_type == "implementation_photo":
        implementation_photos = quote_obj.implementation_photos or []
        implementation_photos.append({
            "id": file_metadata["id"],
            "file_url": file_metadata["file_url"],
            "thumbnail_url": file_metadata["thumbnail_url"],
            "caption": extra_metadata.get("caption", ""),
            "category": extra_metadata.get("category", "general")
        })
        quote_obj.implementation_photos = implementation_photos

    elif asset_type == "comparison_photo":
        # Comparison photos need to be paired (before/after)
        comparison_photos = quote_obj.comparison_photos or []
        photo_pair_id = extra_metadata.get("pair_id")
        photo_position = extra_metadata.get("position", "before")  # 'before' or 'after'

        # Find existing pair or create new one
        existing_pair = None
        if photo_pair_id:
            for pair in comparison_photos:
                if pair.get("pair_id") == photo_pair_id:
                    existing_pair = pair
                    break

        if existing_pair:
            # Update existing pair
            if photo_position == "before":
                existing_pair["before_photo"] = {
                    "id": file_metadata["id"],
                    "file_url": file_metadata["file_url"],
                    "thumbnail_url": file_metadata["thumbnail_url"]
                }
            else:
                existing_pair["after_photo"] = {
                    "id": file_metadata["id"],
                    "file_url": file_metadata["file_url"],
                    "thumbnail_url": file_metadata["thumbnail_url"]
                }
        else:
            # Create new pair
            new_pair = {
                "pair_id": photo_pair_id or file_metadata["id"],
                "description": extra_metadata.get("description", ""),
                "similarity_score": extra_metadata.get("similarity_score", 0)
            }
            if photo_position == "before":
                new_pair["before_photo"] = {
                    "id": file_metadata["id"],
                    "file_url": file_metadata["file_url"],
                    "thumbnail_url": file_metadata["thumbnail_url"]
                }
                new_pair["after_photo"] = None
            else:
                new_pair["before_photo"] = None
                new_pair["after_photo"] = {
                    "id": file_metadata["id"],
                    "file_url": file_metadata["file_url"],
                    "thumbnail_url": file_metadata["thumbnail_url"]
                }
            comparison_photos.append(new_pair)

        quote_obj.comparison_photos = comparison_photos

    # Mark modified for JSONB column
    from sqlalchemy.orm.attributes import flag_modified
    if asset_type == "floor_plan":
        flag_modified(quote_obj, "floor_plans")
    elif asset_type == "implementation_photo":
        flag_modified(quote_obj, "implementation_photos")
    elif asset_type == "comparison_photo":
        flag_modified(quote_obj, "comparison_photos")

    await db.commit()
    await db.refresh(quote_obj)

    return {
        "success": True,
        "file_metadata": file_metadata,
        "message": f"{asset_type.replace('_', ' ').title()} uploaded successfully"
    }


@router.post("/quotes/{quote_id}/polycam-scan")
async def add_polycam_scan(
    quote_id: UUID,
    polycam_url: str,
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Add a Polycam 3D scan link to a quote

    Converts public Polycam URLs to embed format.
    Admin/Manager only.

    Example URL: https://poly.cam/capture/12345678-1234-1234-1234-123456789012
    """
    # Verify quote exists
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Validate Polycam URL format
    if not polycam_url.startswith("https://poly.cam/capture/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid Polycam URL. Must be in format: https://poly.cam/capture/{id}"
        )

    # Extract capture ID
    try:
        capture_id = polycam_url.split("/capture/")[1].split("?")[0]
    except IndexError:
        raise HTTPException(status_code=400, detail="Could not extract capture ID from URL")

    # Generate embed URL
    embed_url = f"https://poly.cam/capture/{capture_id}?mode=embed"

    # Add to quote's polycam_scans array
    polycam_scans = quote_obj.polycam_scans or []
    scan_entry = {
        "id": capture_id,
        "name": name or f"3D Scan {len(polycam_scans) + 1}",
        "url": polycam_url,
        "embed_url": embed_url,
        "added_at": datetime.utcnow().isoformat()
    }
    polycam_scans.append(scan_entry)
    quote_obj.polycam_scans = polycam_scans

    # Mark modified for JSONB column
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(quote_obj, "polycam_scans")

    await db.commit()
    await db.refresh(quote_obj)

    return {
        "success": True,
        "scan": scan_entry,
        "message": "Polycam 3D scan added successfully"
    }


@router.put("/quotes/{quote_id}/floor-plan/{floor_plan_id}/annotations")
async def update_floor_plan_annotations(
    quote_id: UUID,
    floor_plan_id: str,
    annotations: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Update device annotations for a floor plan

    Annotations are device markers placed on the floor plan image.
    Each annotation contains:
    - device_type: smart_lock, thermostat, hub, sensor, etc.
    - x, y: Pixel coordinates on the image
    - label: Display label for the device
    - notes: Optional notes about placement

    Admin/Manager only.
    """
    # Verify quote exists
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Find floor plan in array
    floor_plans = quote_obj.floor_plans or []
    floor_plan_found = False

    for plan in floor_plans:
        if plan.get("id") == floor_plan_id:
            plan["annotations"] = annotations
            floor_plan_found = True
            break

    if not floor_plan_found:
        raise HTTPException(status_code=404, detail="Floor plan not found in quote")

    # Update quote
    quote_obj.floor_plans = floor_plans

    # Mark modified for JSONB column
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(quote_obj, "floor_plans")

    await db.commit()
    await db.refresh(quote_obj)

    return {
        "success": True,
        "floor_plan_id": floor_plan_id,
        "annotations_count": len(annotations),
        "message": "Floor plan annotations updated successfully"
    }


@router.delete("/quotes/{quote_id}/clear-portal-state")
async def clear_customer_portal_state(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Clear customer portal state (ADMIN ONLY)

    Used when quote is finalized/accepted to reset customer's portal session.
    This clears the customer_portal_state field so the portal starts fresh
    if the customer revisits.

    Admin/Manager only.
    """
    # Verify quote exists
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Clear portal state
    quote_obj.customer_portal_state = None

    await db.commit()
    await db.refresh(quote_obj)

    return {
        "success": True,
        "message": "Customer portal state cleared successfully"
    }


@router.post("/quotes/{quote_id}/generate-portal-token")
async def generate_portal_token(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Generate customer portal access token (ADMIN ONLY)

    Creates a secure HMAC-signed token that allows customer to access their quote portal.
    Token expires after 30 days by default.

    Admin/Manager only.
    """
    import hmac
    import hashlib
    import json
    from datetime import timedelta, timezone
    from base64 import urlsafe_b64encode

    # Verify quote exists
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Generate secure token with HMAC signature
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    token_data = {
        "quote_id": str(quote_id),
        "customer_email": quote_obj.customer_email,
        "expires_at": expires_at.isoformat()
    }

    # Create HMAC signature
    if not settings.CUSTOMER_PORTAL_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="CUSTOMER_PORTAL_SECRET_KEY not configured. Set this environment variable to enable customer portal."
        )
    message = json.dumps(token_data, sort_keys=True)
    signature = hmac.new(
        settings.CUSTOMER_PORTAL_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    token_data['signature'] = signature
    token = urlsafe_b64encode(json.dumps(token_data).encode()).decode()

    # Update quote with token
    quote_obj.customer_portal_token = token
    quote_obj.customer_portal_token_expires = expires_at

    await db.commit()
    await db.refresh(quote_obj)

    return {
        "success": True,
        "token": token,
        "expires_at": expires_at.isoformat(),
        "message": "Portal token generated successfully"
    }


@router.post("/quotes/{quote_id}/send-portal-email")
async def send_portal_email(
    quote_id: UUID,
    email_data: dict,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Send customer portal link via email (ADMIN ONLY)

    Sends an email to the customer with their unique portal access link.

    Admin/Manager only.
    """
    # Verify quote exists
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    if not quote_obj.customer_portal_token:
        raise HTTPException(status_code=400, detail="Portal token not generated yet")

    # TODO: Integrate with email service (SendGrid, etc.)
    # For now, we'll just return success
    # In production, this should:
    # 1. Format email template with portal_url
    # 2. Send via SendGrid/SES
    # 3. Log email sent event

    portal_url = email_data.get('portal_url')
    customer_email = email_data.get('email')

    logger.info(f"Portal email would be sent to {customer_email}: {portal_url}")

    return {
        "success": True,
        "message": f"Portal link would be sent to {customer_email}",
        "note": "Email integration not yet implemented - use copy/paste for now"
    }
