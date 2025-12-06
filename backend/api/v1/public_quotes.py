"""
Somni Property Manager - Public Quote API for Customer Portal
Public endpoints for customer portal (no auth required, token-based)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from datetime import datetime, timezone
import hmac
import hashlib
import json
from base64 import urlsafe_b64decode

from db.database import get_db
from db.models_quotes import (
    Quote as QuoteModel,
    QuoteProductOption as QuoteProductOptionModel,
    QuoteComment as QuoteCommentModel,
    QuoteCustomerSelection as QuoteCustomerSelectionModel
)
from api.schemas_quotes import (
    Quote,
    QuoteProductOption,
    QuoteComment, QuoteCommentCreate,
    QuoteCustomerSelection, QuoteCustomerSelectionCreate,
    QuoteApprovalRequest, QuoteRejectionRequest
)
from core.config import settings

router = APIRouter()


# ============================================================================
# TOKEN VALIDATION
# ============================================================================

async def validate_customer_token(
    quote_id: UUID,
    token: str,
    db: AsyncSession
) -> QuoteModel:
    """
    Validate customer portal token

    Returns quote if token is valid, raises HTTPException otherwise
    """
    # Get quote
    query = select(QuoteModel).where(QuoteModel.id == quote_id)
    result = await db.execute(query)
    quote_obj = result.scalar_one_or_none()

    if not quote_obj:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Check if token matches
    if quote_obj.customer_portal_token != token:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Check expiration
    if quote_obj.customer_portal_token_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token expired")

    # Validate HMAC signature
    try:
        token_decoded = json.loads(urlsafe_b64decode(token.encode()).decode())

        # Extract signature
        signature = token_decoded.pop('signature', None)
        if not signature:
            raise HTTPException(status_code=401, detail="Invalid token format")

        # Recreate signature
        if not settings.CUSTOMER_PORTAL_SECRET_KEY:
            raise HTTPException(
                status_code=500,
                detail="CUSTOMER_PORTAL_SECRET_KEY not configured. Contact system administrator."
            )
        message = json.dumps(token_decoded, sort_keys=True)
        expected_signature = hmac.new(
            settings.CUSTOMER_PORTAL_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid token signature")

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

    return quote_obj


# ============================================================================
# PUBLIC QUOTE VIEWING
# ============================================================================

@router.get("/public/quotes/{quote_id}", response_model=Quote)
async def get_public_quote(
    quote_id: UUID,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get quote details (PUBLIC - no auth, token required)

    Customer portal calls this to display quote with product tiers.
    """
    quote_obj = await validate_customer_token(quote_id, token, db)
    return quote_obj


@router.get("/public/quotes/{quote_id}/product-options", response_model=List[QuoteProductOption])
async def get_public_quote_product_options(
    quote_id: UUID,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """Get product tier options (PUBLIC)"""
    await validate_customer_token(quote_id, token, db)

    query = select(QuoteProductOptionModel).where(
        QuoteProductOptionModel.quote_id == quote_id
    ).order_by(QuoteProductOptionModel.display_order.asc())

    result = await db.execute(query)
    options = result.scalars().all()
    return options


# ============================================================================
# PUBLIC QUOTE COMMENTS (Customer Collaboration)
# ============================================================================

@router.get("/public/quotes/{quote_id}/comments", response_model=List[QuoteComment])
async def get_public_quote_comments(
    quote_id: UUID,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get quote comments (PUBLIC - excludes internal comments)

    Customer can see their own comments and admin responses.
    """
    await validate_customer_token(quote_id, token, db)

    query = select(QuoteCommentModel).where(
        QuoteCommentModel.quote_id == quote_id,
        QuoteCommentModel.is_internal == False  # Only public comments
    ).order_by(QuoteCommentModel.created_at.asc())

    result = await db.execute(query)
    comments = result.scalars().all()
    return comments


@router.post("/public/quotes/{quote_id}/comments", response_model=QuoteComment, status_code=201)
async def create_public_quote_comment(
    quote_id: UUID,
    comment_data: QuoteCommentCreate,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a comment/question to quote (PUBLIC)

    Customer can ask questions, request changes, etc.
    """
    quote_obj = await validate_customer_token(quote_id, token, db)

    # Force customer attribution
    comment_obj = QuoteCommentModel(
        quote_id=quote_id,
        comment_text=comment_data.comment_text,
        comment_type=comment_data.comment_type or "question",
        line_item_id=comment_data.line_item_id,
        parent_comment_id=comment_data.parent_comment_id,
        created_by="customer",
        created_by_email=quote_obj.customer_email,
        is_internal=False  # Customer comments are never internal
    )

    db.add(comment_obj)
    await db.commit()
    await db.refresh(comment_obj)
    return comment_obj


# ============================================================================
# PRODUCT TIER SELECTION
# ============================================================================

@router.post("/public/quotes/{quote_id}/select-tier", response_model=QuoteCustomerSelection, status_code=201)
async def select_product_tier(
    quote_id: UUID,
    selection_data: QuoteCustomerSelectionCreate,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Customer selects product tier (PUBLIC)

    Can select:
    - All economy
    - All standard
    - All premium
    - Custom mix (economy locks + premium thermostat, etc)
    """
    await validate_customer_token(quote_id, token, db)

    # Check if selection already exists
    existing_query = select(QuoteCustomerSelectionModel).where(
        QuoteCustomerSelectionModel.quote_id == quote_id
    )
    existing_result = await db.execute(existing_query)
    existing_selection = existing_result.scalar_one_or_none()

    if existing_selection:
        # Update existing selection
        for key, value in selection_data.model_dump(exclude_unset=True).items():
            setattr(existing_selection, key, value)

        await db.commit()
        await db.refresh(existing_selection)
        return existing_selection

    else:
        # Create new selection
        selection_obj = QuoteCustomerSelectionModel(**selection_data.model_dump())
        db.add(selection_obj)
        await db.commit()
        await db.refresh(selection_obj)
        return selection_obj


@router.get("/public/quotes/{quote_id}/selection", response_model=QuoteCustomerSelection)
async def get_customer_selection(
    quote_id: UUID,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """Get customer's current product tier selection (PUBLIC)"""
    await validate_customer_token(quote_id, token, db)

    query = select(QuoteCustomerSelectionModel).where(
        QuoteCustomerSelectionModel.quote_id == quote_id
    )
    result = await db.execute(query)
    selection = result.scalar_one_or_none()

    if not selection:
        raise HTTPException(status_code=404, detail="No selection made yet")

    return selection


# ============================================================================
# QUOTE APPROVAL/REJECTION
# ============================================================================

@router.post("/public/quotes/{quote_id}/approve", response_model=Quote)
async def approve_quote(
    quote_id: UUID,
    approval_data: QuoteApprovalRequest,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Customer approves quote (PUBLIC)

    Updates quote status and triggers contract generation workflow.
    """
    quote_obj = await validate_customer_token(quote_id, token, db)

    if quote_obj.status == 'accepted':
        raise HTTPException(status_code=400, detail="Quote already accepted")

    if approval_data.approved:
        quote_obj.status = 'accepted'
        quote_obj.accepted_at = datetime.utcnow()

        # Update customer selection to approved
        selection_query = select(QuoteCustomerSelectionModel).where(
            QuoteCustomerSelectionModel.quote_id == quote_id
        )
        selection_result = await db.execute(selection_query)
        selection = selection_result.scalar_one_or_none()

        if selection:
            selection.approved = True
            selection.approved_at = datetime.utcnow()
            if approval_data.approval_notes:
                selection.customer_notes = approval_data.approval_notes

        # Add approval comment
        approval_comment = QuoteCommentModel(
            quote_id=quote_id,
            comment_text=approval_data.approval_notes or "Quote approved by customer",
            comment_type="approval",
            created_by="customer",
            created_by_email=quote_obj.customer_email,
            is_internal=False
        )
        db.add(approval_comment)

        await db.commit()
        await db.refresh(quote_obj)

        # TODO: Trigger contract generation workflow
        # TODO: Send notification to admin
        # TODO: Update client onboarding stage

        return quote_obj

    else:
        raise HTTPException(status_code=400, detail="Approval must be true")


@router.post("/public/quotes/{quote_id}/reject", response_model=Quote)
async def reject_quote(
    quote_id: UUID,
    rejection_data: QuoteRejectionRequest,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Customer rejects quote (PUBLIC)

    Updates quote status and notifies admin.
    """
    quote_obj = await validate_customer_token(quote_id, token, db)

    if quote_obj.status in ['accepted', 'rejected']:
        raise HTTPException(status_code=400, detail=f"Quote already {quote_obj.status}")

    quote_obj.status = 'rejected'
    quote_obj.rejected_at = datetime.utcnow()

    # Add rejection comment
    rejection_comment = QuoteCommentModel(
        quote_id=quote_id,
        comment_text=f"Quote rejected: {rejection_data.rejection_reason}\n\nSuggestions: {rejection_data.alternative_suggestions or 'None'}",
        comment_type="rejection",
        created_by="customer",
        created_by_email=quote_obj.customer_email,
        is_internal=False
    )
    db.add(rejection_comment)

    await db.commit()
    await db.refresh(quote_obj)

    # TODO: Send notification to admin

    return quote_obj


# ============================================================================
# CUSTOMER PORTAL STATE (Session Persistence)
# ============================================================================

@router.post("/public/quotes/{quote_id}/portal-state", status_code=200)
async def save_portal_state(
    quote_id: UUID,
    portal_state: dict,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Save customer portal state (PUBLIC)

    Tracks customer progress through portal: current tab, tabs viewed,
    scroll positions, last updated timestamp.

    State structure:
    {
        "current_tab": "overview" | "placements" | "comments" | "tiers",
        "tabs_viewed": ["overview", "placements"],
        "last_updated": "2025-11-23T17:30:00Z",
        "scroll_positions": {
            "overview": 0,
            "placements": 150
        }
    }
    """
    quote_obj = await validate_customer_token(quote_id, token, db)

    # Update portal state
    quote_obj.customer_portal_state = portal_state

    await db.commit()
    await db.refresh(quote_obj)

    return {"message": "Portal state saved successfully", "state": portal_state}


@router.get("/public/quotes/{quote_id}/portal-state")
async def get_portal_state(
    quote_id: UUID,
    token: str = Query(..., description="Secure customer portal token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer portal state (PUBLIC)

    Returns customer's progress through portal for restoring session.
    """
    quote_obj = await validate_customer_token(quote_id, token, db)

    return {
        "state": quote_obj.customer_portal_state or {},
        "has_state": quote_obj.customer_portal_state is not None
    }
