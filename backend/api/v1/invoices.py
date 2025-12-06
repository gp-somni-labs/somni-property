"""
Invoice Ninja API Endpoints
Professional invoicing and billing integration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
import logging

from db.database import get_db
from db.models import Tenant, Lease
from core.auth import get_auth_user, require_manager, AuthUser
from services.invoiceninja_client import InvoiceNinjaClient, get_invoiceninja_client

router = APIRouter()
logger = logging.getLogger(__name__)


# === Pydantic Models ===

class InvoiceClientCreate(BaseModel):
    """Create Invoice Ninja client from tenant"""
    tenant_id: UUID


class RentInvoiceCreate(BaseModel):
    """Generate rent invoice"""
    lease_id: UUID
    amount: Decimal = Field(..., description="Rent amount")
    due_date: date = Field(..., description="Payment due date")
    period: str = Field(default="Monthly Rent", description="Billing period description")


class InvoiceMarkPaid(BaseModel):
    """Mark invoice as paid"""
    amount: Decimal = Field(..., description="Payment amount")
    payment_date: Optional[date] = Field(default=None, description="Payment date (defaults to today)")
    payment_type: str = Field(default="Bank Transfer", description="Payment method")
    transaction_reference: Optional[str] = Field(default=None, description="Transaction reference")


class InvoiceResponse(BaseModel):
    """Invoice Ninja invoice details"""
    invoice_id: str
    client_id: str
    invoice_number: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    balance: Optional[float] = None
    due_date: Optional[str] = None
    created_at: Optional[str] = None
    public_notes: Optional[str] = None


class InvoiceListResponse(BaseModel):
    """List of invoices with pagination"""
    total: int
    page: int
    per_page: int
    invoices: List[InvoiceResponse]


# === Endpoints ===

@router.post("/tenants/{tenant_id}/create-invoice-client", tags=["invoices"])
async def create_invoice_client(
    tenant_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Create or sync a tenant as an Invoice Ninja client

    RBAC: Requires operator or admin role

    This creates a client record in Invoice Ninja for billing purposes.
    The tenant's UUID is stored as the client's id_number for cross-referencing.
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check if tenant already has Invoice Ninja client ID
    if tenant.invoiceninja_client_id:
        # Get existing client
        client = await invoiceninja.get_client(tenant.invoiceninja_client_id)
        if client:
            return {
                "message": "Tenant already has Invoice Ninja client",
                "client_id": tenant.invoiceninja_client_id,
                "client": client
            }

    # Create new Invoice Ninja client
    client = await invoiceninja.create_client(
        name=f"{tenant.first_name} {tenant.last_name}",
        email=tenant.email,
        phone=tenant.phone,
        id_number=str(tenant.id)  # Store tenant UUID for cross-reference
    )

    if not client:
        raise HTTPException(
            status_code=500,
            detail="Failed to create Invoice Ninja client"
        )

    # Store Invoice Ninja client ID in tenant record
    tenant.invoiceninja_client_id = client.get('id')
    await db.commit()

    logger.info(f"Created Invoice Ninja client for tenant {tenant_id}: {client.get('id')}")

    return {
        "message": "Invoice Ninja client created successfully",
        "tenant_id": str(tenant.id),
        "client_id": client.get('id'),
        "client": client
    }


@router.post("/invoices/generate-rent", tags=["invoices"])
async def generate_rent_invoice(
    invoice_data: RentInvoiceCreate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Generate a rent invoice for a lease

    RBAC: Requires operator or admin role

    This creates a professional rent invoice in Invoice Ninja that can be
    sent to the tenant via email and tracked for payment.
    """
    # Get lease with tenant
    result = await db.execute(
        select(Lease).where(Lease.id == invoice_data.lease_id)
    )
    lease = result.scalar_one_or_none()

    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found")

    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == lease.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Ensure tenant has Invoice Ninja client
    if not tenant.invoiceninja_client_id:
        # Auto-create Invoice Ninja client
        client = await invoiceninja.create_client(
            name=f"{tenant.first_name} {tenant.last_name}",
            email=tenant.email,
            phone=tenant.phone,
            id_number=str(tenant.id)
        )

        if not client:
            raise HTTPException(
                status_code=500,
                detail="Failed to create Invoice Ninja client for tenant"
            )

        tenant.invoiceninja_client_id = client.get('id')
        await db.commit()

    # Generate unit address for invoice
    unit_address = "Rental Unit"
    if hasattr(lease, 'unit') and lease.unit:
        unit_address = lease.unit.address or f"Unit {lease.unit.unit_number}"

    # Create rent invoice
    invoice = await invoiceninja.create_rent_invoice(
        client_id=tenant.invoiceninja_client_id,
        amount=invoice_data.amount,
        due_date=invoice_data.due_date,
        unit_address=unit_address,
        lease_id=str(lease.id),
        period=invoice_data.period
    )

    if not invoice:
        raise HTTPException(
            status_code=500,
            detail="Failed to create rent invoice in Invoice Ninja"
        )

    logger.info(f"Generated rent invoice for lease {invoice_data.lease_id}: {invoice.get('id')}")

    return {
        "message": "Rent invoice generated successfully",
        "invoice_id": invoice.get('id'),
        "invoice_number": invoice.get('number'),
        "amount": float(invoice_data.amount),
        "due_date": invoice_data.due_date.isoformat(),
        "lease_id": str(lease.id),
        "tenant_id": str(tenant.id),
        "invoice": invoice
    }


@router.get("/invoices", tags=["invoices"])
async def get_invoices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    client_id: Optional[str] = Query(None, description="Filter by Invoice Ninja client ID"),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    building_id: Optional[UUID] = Query(None, description="Filter by building ID"),
    status: Optional[str] = Query(None, description="Filter by status (draft, sent, paid, etc.)"),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Get invoices with pagination using skip/limit parameters

    This endpoint is compatible with the frontend's pagination expectations.
    Supports filtering by building_id, client_id (Invoice Ninja), tenant_id, and status.
    """
    from db.models import Unit

    # Convert skip/limit to page/per_page
    page = (skip // limit) + 1 if limit > 0 else 1
    per_page = limit

    # If tenant_id provided, get their Invoice Ninja client ID
    actual_client_id = client_id

    # Filter by building_id (get all tenants with units in that building)
    if building_id:
        # Get all units in the building
        units_result = await db.execute(
            select(Unit.id).where(Unit.building_id == building_id)
        )
        unit_ids = [row[0] for row in units_result.all()]

        if not unit_ids:
            return {
                "total": 0,
                "invoices": []
            }

        # Get all active leases for those units
        leases_result = await db.execute(
            select(Lease.tenant_id).where(Lease.unit_id.in_(unit_ids))
        )
        tenant_ids = list(set([row[0] for row in leases_result.all()]))

        if not tenant_ids:
            return {
                "total": 0,
                "invoices": []
            }

        # Get Invoice Ninja client IDs for these tenants
        tenants_result = await db.execute(
            select(Tenant).where(Tenant.id.in_(tenant_ids))
        )
        tenants = tenants_result.scalars().all()

        # Get invoices for all these tenants
        all_invoices = []
        for tenant in tenants:
            if tenant.invoiceninja_client_id:
                result = await invoiceninja.list_invoices(
                    client_id=tenant.invoiceninja_client_id,
                    status=status,
                    page=1,
                    per_page=1000  # Get all for filtering
                )
                all_invoices.extend(result.get('data', []))

        # Format and paginate
        formatted_invoices = []
        for invoice in all_invoices[skip:skip + limit]:
            formatted_invoices.append({
                "invoice_id": invoice.get('id'),
                "client_id": invoice.get('client_id'),
                "invoice_number": invoice.get('number'),
                "status": invoice.get('status_id'),
                "amount": invoice.get('amount'),
                "balance": invoice.get('balance'),
                "due_date": invoice.get('due_date'),
                "created_at": invoice.get('created_at'),
                "public_notes": invoice.get('public_notes')
            })

        return {
            "total": len(all_invoices),
            "invoices": formatted_invoices
        }

    if tenant_id:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if not tenant.invoiceninja_client_id:
            return {
                "total": 0,
                "invoices": []
            }

        actual_client_id = tenant.invoiceninja_client_id

    # Get invoices from Invoice Ninja
    result = await invoiceninja.list_invoices(
        client_id=actual_client_id,
        status=status,
        page=page,
        per_page=per_page
    )

    invoices = result.get('data', [])
    meta = result.get('meta', {})

    # Format response
    formatted_invoices = []
    for invoice in invoices:
        formatted_invoices.append({
            "invoice_id": invoice.get('id'),
            "client_id": invoice.get('client_id'),
            "invoice_number": invoice.get('number'),
            "status": invoice.get('status_id'),
            "amount": invoice.get('amount'),
            "balance": invoice.get('balance'),
            "due_date": invoice.get('due_date'),
            "created_at": invoice.get('created_at'),
            "public_notes": invoice.get('public_notes')
        })

    return {
        "total": meta.get('total', len(formatted_invoices)),
        "invoices": formatted_invoices
    }


@router.get("/invoices/summary", tags=["invoices"])
async def get_invoice_summary(
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Get summary statistics for all invoices

    Returns:
    - total_invoices: Total number of invoices
    - total_amount: Total invoice amount
    - total_paid: Total amount paid
    - total_outstanding: Total outstanding balance
    - overdue_count: Number of overdue invoices
    - overdue_amount: Total overdue amount
    """
    try:
        # Get all invoices
        result = await invoiceninja.list_invoices(page=1, per_page=1000)
        invoices = result.get('data', [])

        total_invoices = len(invoices)
        total_amount = sum(float(inv.get('amount', 0)) for inv in invoices)
        total_paid = sum(float(inv.get('amount', 0)) - float(inv.get('balance', 0)) for inv in invoices)
        total_outstanding = sum(float(inv.get('balance', 0)) for inv in invoices)

        # Count overdue invoices (status_id = 5 is overdue in Invoice Ninja)
        from datetime import date
        today = date.today().isoformat()

        overdue_invoices = [
            inv for inv in invoices
            if inv.get('balance', 0) > 0 and inv.get('due_date', '') < today
        ]
        overdue_count = len(overdue_invoices)
        overdue_amount = sum(float(inv.get('balance', 0)) for inv in overdue_invoices)

        return {
            "total_invoices": total_invoices,
            "total_amount": total_amount,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "overdue_count": overdue_count,
            "overdue_amount": overdue_amount
        }
    except Exception as e:
        logger.error(f"Error getting invoice summary: {e}")
        # Return default values if Invoice Ninja is not available
        return {
            "total_invoices": 0,
            "total_amount": 0.0,
            "total_paid": 0.0,
            "total_outstanding": 0.0,
            "overdue_count": 0,
            "overdue_amount": 0.0
        }


@router.get("/invoices/overdue", tags=["invoices"])
async def get_overdue_invoices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Get all overdue invoices

    Returns invoices that have a positive balance and a due date in the past.
    """
    try:
        # Get all invoices
        page = (skip // limit) + 1 if limit > 0 else 1
        result = await invoiceninja.list_invoices(page=page, per_page=limit * 2)  # Get more to filter
        invoices = result.get('data', [])

        # Filter overdue invoices
        from datetime import date
        today = date.today().isoformat()

        overdue_invoices = [
            inv for inv in invoices
            if inv.get('balance', 0) > 0 and inv.get('due_date', '') < today
        ]

        # Apply pagination to filtered results
        paginated = overdue_invoices[skip:skip + limit]

        # Format response
        formatted_invoices = []
        for invoice in paginated:
            formatted_invoices.append({
                "invoice_id": invoice.get('id'),
                "client_id": invoice.get('client_id'),
                "invoice_number": invoice.get('number'),
                "status": invoice.get('status_id'),
                "amount": invoice.get('amount'),
                "balance": invoice.get('balance'),
                "due_date": invoice.get('due_date'),
                "created_at": invoice.get('created_at'),
                "public_notes": invoice.get('public_notes')
            })

        return {
            "total": len(overdue_invoices),
            "invoices": formatted_invoices
        }
    except Exception as e:
        logger.error(f"Error getting overdue invoices: {e}")
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )


@router.get("/invoices/list", tags=["invoices"])
async def list_invoices(
    client_id: Optional[str] = Query(None, description="Filter by Invoice Ninja client ID"),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status (draft, sent, paid, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    List invoices with optional filters

    Can filter by client ID, tenant ID, or invoice status.
    """
    # If tenant_id provided, get their Invoice Ninja client ID
    actual_client_id = client_id

    if tenant_id:
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        if not tenant.invoiceninja_client_id:
            return {
                "total": 0,
                "page": page,
                "per_page": per_page,
                "invoices": []
            }

        actual_client_id = tenant.invoiceninja_client_id

    # Get invoices from Invoice Ninja
    result = await invoiceninja.list_invoices(
        client_id=actual_client_id,
        status=status,
        page=page,
        per_page=per_page
    )

    invoices = result.get('data', [])
    meta = result.get('meta', {})

    # Format response
    formatted_invoices = []
    for invoice in invoices:
        formatted_invoices.append({
            "invoice_id": invoice.get('id'),
            "client_id": invoice.get('client_id'),
            "invoice_number": invoice.get('number'),
            "status": invoice.get('status_id'),
            "amount": invoice.get('amount'),
            "balance": invoice.get('balance'),
            "due_date": invoice.get('due_date'),
            "created_at": invoice.get('created_at'),
            "public_notes": invoice.get('public_notes')
        })

    return {
        "total": meta.get('total', len(formatted_invoices)),
        "page": page,
        "per_page": per_page,
        "invoices": formatted_invoices
    }


@router.get("/invoices/{invoice_id}", tags=["invoices"])
async def get_invoice(
    invoice_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Get detailed invoice information
    """
    invoice = await invoiceninja.get_invoice(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "invoice_id": invoice.get('id'),
        "client_id": invoice.get('client_id'),
        "invoice_number": invoice.get('number'),
        "status": invoice.get('status_id'),
        "amount": invoice.get('amount'),
        "balance": invoice.get('balance'),
        "due_date": invoice.get('due_date'),
        "created_at": invoice.get('created_at'),
        "public_notes": invoice.get('public_notes'),
        "line_items": invoice.get('line_items', []),
        "invoice": invoice
    }


@router.get("/invoices/{invoice_id}/download-pdf", tags=["invoices"])
async def download_invoice_pdf(
    invoice_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Download invoice as PDF

    Returns the PDF bytes for the invoice.
    """
    pdf_bytes = await invoiceninja.download_invoice_pdf(invoice_id)

    if not pdf_bytes:
        raise HTTPException(
            status_code=500,
            detail="Failed to download invoice PDF"
        )

    from fastapi.responses import Response

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice_{invoice_id}.pdf"
        }
    )


@router.post("/invoices/{invoice_id}/send", tags=["invoices"])
async def send_invoice(
    invoice_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Send invoice via email to the client

    Invoice Ninja will send a professional email with the invoice attached
    to the email address on file for the client.
    """
    success = await invoiceninja.send_invoice(invoice_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send invoice email"
        )

    logger.info(f"Sent invoice {invoice_id} via email")

    return {
        "message": "Invoice sent successfully",
        "invoice_id": invoice_id
    }


@router.post("/invoices/{invoice_id}/mark-paid", tags=["invoices"])
async def mark_invoice_paid(
    invoice_id: str,
    payment_data: InvoiceMarkPaid,
    auth_user: AuthUser = Depends(get_auth_user),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Mark an invoice as paid

    Records a payment against the invoice in Invoice Ninja.
    This is typically called automatically when a Stripe payment succeeds.
    """
    success = await invoiceninja.mark_invoice_paid(
        invoice_id=invoice_id,
        amount=payment_data.amount,
        payment_date=payment_data.payment_date,
        payment_type=payment_data.payment_type,
        transaction_reference=payment_data.transaction_reference
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to mark invoice as paid"
        )

    logger.info(f"Marked invoice {invoice_id} as paid: ${payment_data.amount}")

    return {
        "message": "Invoice marked as paid successfully",
        "invoice_id": invoice_id,
        "amount_paid": float(payment_data.amount)
    }


@router.delete("/invoices/{invoice_id}", tags=["invoices"])
async def delete_invoice(
    invoice_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Delete an invoice

    Use with caution - this permanently removes the invoice from Invoice Ninja.
    """
    success = await invoiceninja.delete_invoice(invoice_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete invoice"
        )

    logger.info(f"Deleted invoice {invoice_id}")

    return {
        "message": "Invoice deleted successfully",
        "invoice_id": invoice_id
    }
