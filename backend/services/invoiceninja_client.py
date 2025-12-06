"""
Invoice Ninja Integration Client for SomniProperty

Integrates with self-hosted Invoice Ninja (professional invoicing system) for:
- Professional invoice generation and delivery
- Client/tenant management
- Payment tracking and reconciliation
- Recurring invoices for rent collection
- Expense tracking
- Quote generation
- Time tracking for billable work
- Multi-currency support

Invoice Ninja Service: invoiceninja.utilities.svc.cluster.local
Documentation: https://invoiceninja.github.io/en/
API Docs: https://api-docs.invoicing.co/
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class InvoiceStatus(Enum):
    """Invoice Ninja invoice status"""
    DRAFT = 1
    SENT = 2
    VIEWED = 3
    APPROVED = 4
    PARTIAL = 5
    PAID = 6
    OVERDUE = -1
    UNPAID = -2


class PaymentType(Enum):
    """Common payment types"""
    BANK_TRANSFER = "1"
    CASH = "2"
    CREDIT_CARD = "3"
    CHECK = "5"
    PAYPAL = "6"
    STRIPE = "28"
    VENMO = "30"
    ZELLE = "31"


class InvoiceNinjaClient(BaseModel):
    """Invoice Ninja client/tenant model"""
    id: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country_id: Optional[str] = None
    id_number: Optional[str] = None
    vat_number: Optional[str] = None
    website: Optional[str] = None


class InvoiceLineItem(BaseModel):
    """Invoice line item"""
    product_key: str
    notes: str
    cost: float
    quantity: float = 1.0
    tax_name1: Optional[str] = None
    tax_rate1: Optional[float] = None
    tax_name2: Optional[str] = None
    tax_rate2: Optional[float] = None


class Invoice(BaseModel):
    """Invoice Ninja invoice model"""
    id: Optional[str] = None
    client_id: str
    invoice_number: Optional[str] = None
    po_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    line_items: List[InvoiceLineItem]
    public_notes: Optional[str] = None
    private_notes: Optional[str] = None
    terms: Optional[str] = None
    footer: Optional[str] = None
    discount: Optional[float] = None
    partial: Optional[float] = None
    partial_due_date: Optional[date] = None
    status_id: Optional[int] = None
    amount: Optional[float] = None
    balance: Optional[float] = None


class Payment(BaseModel):
    """Invoice Ninja payment model"""
    id: Optional[str] = None
    invoice_id: str
    amount: float
    payment_date: date
    payment_type_id: str = PaymentType.BANK_TRANSFER.value
    transaction_reference: Optional[str] = None
    private_notes: Optional[str] = None


class Product(BaseModel):
    """Invoice Ninja product/service model"""
    id: Optional[str] = None
    product_key: str  # Unique identifier (e.g., "rent", "water_utility")
    notes: str  # Description
    cost: float = 0.0  # Cost/wholesale price
    price: float = 0.0  # Retail/sale price
    quantity: float = 1.0  # Default quantity
    tax_name1: Optional[str] = None
    tax_rate1: Optional[float] = None
    tax_name2: Optional[str] = None
    tax_rate2: Optional[float] = None
    custom_value1: Optional[str] = None
    custom_value2: Optional[str] = None
    custom_value3: Optional[str] = None
    custom_value4: Optional[str] = None
    is_deleted: bool = False


class InvoiceNinjaClient:
    """Client for interacting with Invoice Ninja API"""

    def __init__(
        self,
        base_url: str = "http://invoiceninja.utilities.svc.cluster.local",
        api_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Invoice Ninja client

        Args:
            base_url: Invoice Ninja service URL
            api_token: Invoice Ninja API token (from Settings → Account Management → API Tokens)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        if self.api_token:
            headers["X-API-TOKEN"] = self.api_token
        return headers

    # ========================================
    # Client Management
    # ========================================

    async def create_client(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        address1: Optional[str] = None,
        address2: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        country_id: Optional[str] = None,
        id_number: Optional[str] = None,
        vat_number: Optional[str] = None,
        website: Optional[str] = None,
        custom_value1: Optional[str] = None,
        custom_value2: Optional[str] = None
    ) -> Optional[InvoiceNinjaClient]:
        """
        Create a client in Invoice Ninja

        Use for:
        - New tenants (create client when lease signed)
        - Property owners (if managing multiple properties)
        - Contractors (if invoicing for services)

        Args:
            name: Client/tenant name
            email: Email address
            phone: Phone number
            address1: Address line 1
            address2: Address line 2 (unit number)
            city: City
            state: State
            postal_code: Postal code
            country_id: Country ID (840 for USA)
            id_number: Custom ID (e.g., tenant UUID)
            vat_number: VAT/Tax ID
            website: Website URL
            custom_value1: Custom field 1 (e.g., property ID)
            custom_value2: Custom field 2 (e.g., unit number)

        Returns:
            Created client or None on failure
        """
        try:
            # Split name into first and last
            name_parts = name.split(maxsplit=1)
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            client_data = {
                "name": name,
                "contacts": [
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "phone": phone or ""
                    }
                ]
            }

            if address1:
                client_data["address1"] = address1
            if address2:
                client_data["address2"] = address2
            if city:
                client_data["city"] = city
            if state:
                client_data["state"] = state
            if postal_code:
                client_data["postal_code"] = postal_code
            if country_id:
                client_data["country_id"] = country_id
            if id_number:
                client_data["id_number"] = id_number
            if vat_number:
                client_data["vat_number"] = vat_number
            if website:
                client_data["website"] = website
            if custom_value1:
                client_data["custom_value1"] = custom_value1
            if custom_value2:
                client_data["custom_value2"] = custom_value2

            response = await self.client.post(
                f"{self.base_url}/api/v1/clients",
                headers=self._headers(),
                json=client_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                data = result.get('data', {})
                logger.info(f"Created Invoice Ninja client: {name}")
                return InvoiceNinjaClient(
                    id=data.get('id'),
                    name=data.get('name'),
                    email=email,
                    phone=phone,
                    address1=address1,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    id_number=id_number
                )
            else:
                logger.error(f"Failed to create client: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating Invoice Ninja client: {e}")
            return None

    async def get_client(self, client_id: str) -> Optional[InvoiceNinjaClient]:
        """
        Get client details

        Args:
            client_id: Invoice Ninja client ID

        Returns:
            Client details or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/clients/{client_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                contact = data.get('contacts', [{}])[0]
                return InvoiceNinjaClient(
                    id=data.get('id'),
                    name=data.get('name'),
                    email=contact.get('email', ''),
                    phone=contact.get('phone'),
                    address1=data.get('address1'),
                    address2=data.get('address2'),
                    city=data.get('city'),
                    state=data.get('state'),
                    postal_code=data.get('postal_code'),
                    id_number=data.get('id_number')
                )
            return None

        except Exception as e:
            logger.error(f"Error getting client: {e}")
            return None

    async def list_clients(
        self,
        page: int = 1,
        per_page: int = 20,
        filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List clients with pagination

        Args:
            page: Page number
            per_page: Results per page
            filter: Search filter (searches name, email, etc.)

        Returns:
            Clients list with pagination info
        """
        try:
            params = {
                'page': page,
                'per_page': per_page
            }
            if filter:
                params['filter'] = filter

            response = await self.client.get(
                f"{self.base_url}/api/v1/clients",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to list clients: {response.status_code} - {response.text}")
                return {"data": [], "meta": {}}

        except Exception as e:
            logger.error(f"Error listing clients: {e}")
            return {"data": [], "meta": {}}

    # ========================================
    # Invoice Management
    # ========================================

    async def create_invoice(
        self,
        client_id: str,
        line_items: List[InvoiceLineItem],
        invoice_date: Optional[date] = None,
        due_date: Optional[date] = None,
        invoice_number: Optional[str] = None,
        po_number: Optional[str] = None,
        discount: Optional[float] = None,
        partial: Optional[float] = None,
        partial_due_date: Optional[date] = None,
        public_notes: Optional[str] = None,
        private_notes: Optional[str] = None,
        terms: Optional[str] = None,
        footer: Optional[str] = None,
        auto_bill: bool = False
    ) -> Optional[Invoice]:
        """
        Create an invoice

        Use for:
        - Monthly rent invoices
        - Utility bill pass-through
        - Late fees
        - Damage charges
        - Service charges

        Args:
            client_id: Invoice Ninja client ID
            line_items: List of invoice line items
            invoice_date: Invoice date (defaults to today)
            due_date: Payment due date
            invoice_number: Custom invoice number
            po_number: Purchase order number (use for lease ID)
            discount: Discount amount or percentage
            partial: Partial payment amount
            partial_due_date: Partial payment due date
            public_notes: Notes visible to client
            private_notes: Internal notes
            terms: Invoice terms
            footer: Invoice footer
            auto_bill: Enable auto-billing if configured

        Returns:
            Created invoice or None on failure
        """
        try:
            invoice_data = {
                "client_id": client_id,
                "line_items": [
                    {
                        "product_key": item.product_key,
                        "notes": item.notes,
                        "cost": item.cost,
                        "quantity": item.quantity,
                        "tax_name1": item.tax_name1 or "",
                        "tax_rate1": item.tax_rate1 or 0,
                        "tax_name2": item.tax_name2 or "",
                        "tax_rate2": item.tax_rate2 or 0
                    }
                    for item in line_items
                ],
                "auto_bill": auto_bill
            }

            if invoice_date:
                invoice_data["invoice_date"] = invoice_date.isoformat()
            if due_date:
                invoice_data["due_date"] = due_date.isoformat()
            if invoice_number:
                invoice_data["number"] = invoice_number
            if po_number:
                invoice_data["po_number"] = po_number
            if discount is not None:
                invoice_data["discount"] = discount
            if partial is not None:
                invoice_data["partial"] = partial
            if partial_due_date:
                invoice_data["partial_due_date"] = partial_due_date.isoformat()
            if public_notes:
                invoice_data["public_notes"] = public_notes
            if private_notes:
                invoice_data["private_notes"] = private_notes
            if terms:
                invoice_data["terms"] = terms
            if footer:
                invoice_data["footer"] = footer

            response = await self.client.post(
                f"{self.base_url}/api/v1/invoices",
                headers=self._headers(),
                json=invoice_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                data = result.get('data', {})
                logger.info(f"Created Invoice Ninja invoice for client {client_id}")
                return Invoice(
                    id=data.get('id'),
                    client_id=client_id,
                    invoice_number=data.get('number'),
                    po_number=po_number,
                    line_items=line_items,
                    status_id=data.get('status_id'),
                    amount=data.get('amount'),
                    balance=data.get('balance')
                )
            else:
                logger.error(f"Failed to create invoice: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return None

    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """
        Get invoice details

        Args:
            invoice_id: Invoice Ninja invoice ID

        Returns:
            Invoice details or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/invoices/{invoice_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                return Invoice(
                    id=data.get('id'),
                    client_id=data.get('client_id'),
                    invoice_number=data.get('number'),
                    po_number=data.get('po_number'),
                    status_id=data.get('status_id'),
                    amount=data.get('amount'),
                    balance=data.get('balance'),
                    line_items=[]  # Would need to parse from data
                )
            return None

        except Exception as e:
            logger.error(f"Error getting invoice: {e}")
            return None

    async def list_invoices(
        self,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        List invoices with filtering

        Args:
            client_id: Filter by client ID
            status: Filter by status (active, paid, unpaid, overdue)
            page: Page number
            per_page: Results per page

        Returns:
            Invoices list with pagination info
        """
        try:
            params = {
                'page': page,
                'per_page': per_page
            }
            if client_id:
                params['client_id'] = client_id
            if status:
                params['status'] = status

            response = await self.client.get(
                f"{self.base_url}/api/v1/invoices",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to list invoices: {response.status_code} - {response.text}")
                return {"data": [], "meta": {}}

        except Exception as e:
            logger.error(f"Error listing invoices: {e}")
            return {"data": [], "meta": {}}

    async def send_invoice(self, invoice_id: str) -> bool:
        """
        Send invoice via email to client

        Args:
            invoice_id: Invoice Ninja invoice ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/invoices/{invoice_id}/email",
                headers=self._headers()
            )

            if response.status_code in [200, 204]:
                logger.info(f"Sent Invoice Ninja invoice: {invoice_id}")
                return True
            else:
                logger.error(f"Failed to send invoice: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending invoice: {e}")
            return False

    async def download_invoice_pdf(self, invoice_id: str) -> Optional[bytes]:
        """
        Download invoice as PDF

        Args:
            invoice_id: Invoice Ninja invoice ID

        Returns:
            PDF bytes or None on failure
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/invoices/{invoice_id}/download",
                headers=self._headers()
            )

            if response.status_code == 200:
                logger.info(f"Downloaded Invoice Ninja PDF: {invoice_id}")
                return response.content
            return None

        except Exception as e:
            logger.error(f"Error downloading invoice PDF: {e}")
            return None

    async def delete_invoice(self, invoice_id: str) -> bool:
        """
        Delete an invoice

        Args:
            invoice_id: Invoice Ninja invoice ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/invoices/{invoice_id}",
                headers=self._headers()
            )

            if response.status_code in [200, 204]:
                logger.info(f"Deleted Invoice Ninja invoice: {invoice_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting invoice: {e}")
            return False

    # ========================================
    # Payment Management
    # ========================================

    async def record_payment(
        self,
        invoice_id: str,
        amount: float,
        payment_date: Optional[date] = None,
        payment_type_id: str = PaymentType.BANK_TRANSFER.value,
        transaction_reference: Optional[str] = None,
        private_notes: Optional[str] = None
    ) -> Optional[Payment]:
        """
        Record a payment for an invoice

        Use for:
        - Recording rent payments
        - Marking invoices as paid
        - Tracking payment methods
        - Adding transaction references

        Args:
            invoice_id: Invoice Ninja invoice ID
            amount: Payment amount
            payment_date: Payment date (defaults to today)
            payment_type_id: Payment type ID
            transaction_reference: Transaction reference (check number, confirmation code)
            private_notes: Internal notes about payment

        Returns:
            Created payment or None on failure
        """
        try:
            payment_data = {
                "invoice_id": invoice_id,
                "amount": amount,
                "date": (payment_date or date.today()).isoformat(),
                "type_id": payment_type_id
            }

            if transaction_reference:
                payment_data["transaction_reference"] = transaction_reference
            if private_notes:
                payment_data["private_notes"] = private_notes

            response = await self.client.post(
                f"{self.base_url}/api/v1/payments",
                headers=self._headers(),
                json=payment_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                data = result.get('data', {})
                logger.info(f"Recorded payment for invoice {invoice_id}")
                return Payment(
                    id=data.get('id'),
                    invoice_id=invoice_id,
                    amount=amount,
                    payment_date=payment_date or date.today(),
                    payment_type_id=payment_type_id,
                    transaction_reference=transaction_reference
                )
            else:
                logger.error(f"Failed to record payment: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            return None

    # ========================================
    # Product Management
    # ========================================

    async def list_products(
        self,
        page: int = 1,
        per_page: int = 100,
        filter: Optional[str] = None,
        is_deleted: bool = False
    ) -> Dict[str, Any]:
        """
        List products with pagination

        Args:
            page: Page number
            per_page: Results per page (max 100)
            filter: Search filter (searches product_key, notes)
            is_deleted: Include deleted products

        Returns:
            Products list with pagination info
        """
        try:
            params = {
                'page': page,
                'per_page': min(per_page, 100)  # Cap at 100
            }
            if filter:
                params['filter'] = filter
            if is_deleted:
                params['is_deleted'] = 'true'

            response = await self.client.get(
                f"{self.base_url}/api/v1/products",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to list products: {response.status_code} - {response.text}")
                return {"data": [], "meta": {}}

        except Exception as e:
            logger.error(f"Error listing products: {e}")
            return {"data": [], "meta": {}}

    async def get_product(self, product_id: str) -> Optional[Product]:
        """
        Get product details

        Args:
            product_id: Invoice Ninja product ID

        Returns:
            Product details or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/products/{product_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                return Product(
                    id=data.get('id'),
                    product_key=data.get('product_key', ''),
                    notes=data.get('notes', ''),
                    cost=float(data.get('cost', 0)),
                    price=float(data.get('price', 0)),
                    quantity=float(data.get('quantity', 1)),
                    tax_name1=data.get('tax_name1'),
                    tax_rate1=float(data.get('tax_rate1')) if data.get('tax_rate1') else None,
                    tax_name2=data.get('tax_name2'),
                    tax_rate2=float(data.get('tax_rate2')) if data.get('tax_rate2') else None,
                    custom_value1=data.get('custom_value1'),
                    custom_value2=data.get('custom_value2'),
                    custom_value3=data.get('custom_value3'),
                    custom_value4=data.get('custom_value4'),
                    is_deleted=data.get('is_deleted', False)
                )
            return None

        except Exception as e:
            logger.error(f"Error getting product: {e}")
            return None

    async def create_product(
        self,
        product_key: str,
        notes: str,
        cost: float = 0.0,
        price: float = 0.0,
        quantity: float = 1.0,
        tax_name1: Optional[str] = None,
        tax_rate1: Optional[float] = None,
        tax_name2: Optional[str] = None,
        tax_rate2: Optional[float] = None,
        custom_value1: Optional[str] = None,
        custom_value2: Optional[str] = None,
        custom_value3: Optional[str] = None,
        custom_value4: Optional[str] = None
    ) -> Optional[Product]:
        """
        Create a product

        Use for:
        - Rent products (monthly rent)
        - Utility charges (water, electric, gas)
        - Fees (late fee, pet fee, parking)
        - Services (maintenance, cleaning)

        Args:
            product_key: Unique identifier (e.g., "rent", "water_utility")
            notes: Product description
            cost: Cost/wholesale price
            price: Retail/sale price
            quantity: Default quantity
            tax_name1: Primary tax name
            tax_rate1: Primary tax rate %
            tax_name2: Secondary tax name
            tax_rate2: Secondary tax rate %
            custom_value1-4: Custom fields

        Returns:
            Created product or None on failure
        """
        try:
            product_data = {
                "product_key": product_key,
                "notes": notes,
                "cost": cost,
                "price": price,
                "quantity": quantity
            }

            if tax_name1:
                product_data["tax_name1"] = tax_name1
            if tax_rate1 is not None:
                product_data["tax_rate1"] = tax_rate1
            if tax_name2:
                product_data["tax_name2"] = tax_name2
            if tax_rate2 is not None:
                product_data["tax_rate2"] = tax_rate2
            if custom_value1:
                product_data["custom_value1"] = custom_value1
            if custom_value2:
                product_data["custom_value2"] = custom_value2
            if custom_value3:
                product_data["custom_value3"] = custom_value3
            if custom_value4:
                product_data["custom_value4"] = custom_value4

            response = await self.client.post(
                f"{self.base_url}/api/v1/products",
                headers=self._headers(),
                json=product_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                data = result.get('data', {})
                logger.info(f"Created Invoice Ninja product: {product_key}")
                return Product(
                    id=data.get('id'),
                    product_key=product_key,
                    notes=notes,
                    cost=cost,
                    price=price,
                    quantity=quantity,
                    tax_name1=tax_name1,
                    tax_rate1=tax_rate1,
                    tax_name2=tax_name2,
                    tax_rate2=tax_rate2,
                    custom_value1=custom_value1,
                    custom_value2=custom_value2,
                    custom_value3=custom_value3,
                    custom_value4=custom_value4
                )
            else:
                logger.error(f"Failed to create product: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating product: {e}")
            return None

    async def update_product(
        self,
        product_id: str,
        product_key: Optional[str] = None,
        notes: Optional[str] = None,
        cost: Optional[float] = None,
        price: Optional[float] = None,
        quantity: Optional[float] = None,
        tax_name1: Optional[str] = None,
        tax_rate1: Optional[float] = None,
        tax_name2: Optional[str] = None,
        tax_rate2: Optional[float] = None,
        custom_value1: Optional[str] = None,
        custom_value2: Optional[str] = None,
        custom_value3: Optional[str] = None,
        custom_value4: Optional[str] = None
    ) -> Optional[Product]:
        """
        Update a product

        Args:
            product_id: Invoice Ninja product ID
            product_key: Unique identifier
            notes: Product description
            cost: Cost/wholesale price
            price: Retail/sale price
            quantity: Default quantity
            tax_name1: Primary tax name
            tax_rate1: Primary tax rate %
            tax_name2: Secondary tax name
            tax_rate2: Secondary tax rate %
            custom_value1-4: Custom fields

        Returns:
            Updated product or None on failure
        """
        try:
            product_data = {}

            if product_key is not None:
                product_data["product_key"] = product_key
            if notes is not None:
                product_data["notes"] = notes
            if cost is not None:
                product_data["cost"] = cost
            if price is not None:
                product_data["price"] = price
            if quantity is not None:
                product_data["quantity"] = quantity
            if tax_name1 is not None:
                product_data["tax_name1"] = tax_name1
            if tax_rate1 is not None:
                product_data["tax_rate1"] = tax_rate1
            if tax_name2 is not None:
                product_data["tax_name2"] = tax_name2
            if tax_rate2 is not None:
                product_data["tax_rate2"] = tax_rate2
            if custom_value1 is not None:
                product_data["custom_value1"] = custom_value1
            if custom_value2 is not None:
                product_data["custom_value2"] = custom_value2
            if custom_value3 is not None:
                product_data["custom_value3"] = custom_value3
            if custom_value4 is not None:
                product_data["custom_value4"] = custom_value4

            response = await self.client.put(
                f"{self.base_url}/api/v1/products/{product_id}",
                headers=self._headers(),
                json=product_data
            )

            if response.status_code == 200:
                result = response.json()
                data = result.get('data', {})
                logger.info(f"Updated Invoice Ninja product: {product_id}")
                return Product(
                    id=data.get('id'),
                    product_key=data.get('product_key', ''),
                    notes=data.get('notes', ''),
                    cost=float(data.get('cost', 0)),
                    price=float(data.get('price', 0)),
                    quantity=float(data.get('quantity', 1)),
                    tax_name1=data.get('tax_name1'),
                    tax_rate1=float(data.get('tax_rate1')) if data.get('tax_rate1') else None,
                    tax_name2=data.get('tax_name2'),
                    tax_rate2=float(data.get('tax_rate2')) if data.get('tax_rate2') else None,
                    custom_value1=data.get('custom_value1'),
                    custom_value2=data.get('custom_value2'),
                    custom_value3=data.get('custom_value3'),
                    custom_value4=data.get('custom_value4')
                )
            else:
                logger.error(f"Failed to update product: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return None

    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product (soft delete)

        Args:
            product_id: Invoice Ninja product ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/products/{product_id}",
                headers=self._headers()
            )

            if response.status_code in [200, 204]:
                logger.info(f"Deleted Invoice Ninja product: {product_id}")
                return True
            else:
                logger.error(f"Failed to delete product: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False

    # ========================================
    # Recurring Invoice Management
    # ========================================

    async def create_recurring_invoice(
        self,
        client_id: str,
        line_items: List[InvoiceLineItem],
        frequency_id: int = 5,  # 5 = monthly
        remaining_cycles: int = -1,  # -1 = infinite
        due_date_terms: Optional[str] = None,
        auto_bill: bool = True,
        public_notes: Optional[str] = None,
        terms: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a recurring invoice

        Perfect for monthly rent collection!

        Frequency IDs:
        - 1: Daily
        - 2: Weekly
        - 3: Bi-weekly
        - 4: Four weeks
        - 5: Monthly (default for rent)
        - 6: Two months
        - 7: Three months
        - 8: Four months
        - 9: Six months
        - 10: Annually

        Args:
            client_id: Invoice Ninja client ID
            line_items: Invoice line items (e.g., rent)
            frequency_id: Billing frequency (5 = monthly)
            remaining_cycles: Number of cycles (-1 = infinite)
            due_date_terms: Due date terms (e.g., "net 5" for 5 days)
            auto_bill: Enable auto-billing
            public_notes: Notes for tenant
            terms: Invoice terms

        Returns:
            Created recurring invoice or None on failure
        """
        try:
            recurring_data = {
                "client_id": client_id,
                "frequency_id": frequency_id,
                "remaining_cycles": remaining_cycles,
                "auto_bill": auto_bill,
                "line_items": [
                    {
                        "product_key": item.product_key,
                        "notes": item.notes,
                        "cost": item.cost,
                        "quantity": item.quantity
                    }
                    for item in line_items
                ]
            }

            if due_date_terms:
                recurring_data["due_date_terms"] = due_date_terms
            if public_notes:
                recurring_data["public_notes"] = public_notes
            if terms:
                recurring_data["terms"] = terms

            response = await self.client.post(
                f"{self.base_url}/api/v1/recurring_invoices",
                headers=self._headers(),
                json=recurring_data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Created recurring invoice for client {client_id}")
                return result.get('data')
            else:
                logger.error(f"Failed to create recurring invoice: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating recurring invoice: {e}")
            return None

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def create_rent_invoice(
        self,
        client_id: str,
        rent_amount: float,
        due_date: date,
        unit_address: str,
        lease_id: str,
        utilities: Optional[Dict[str, float]] = None,
        late_fees: Optional[float] = None,
        period: Optional[str] = None
    ) -> Optional[Invoice]:
        """
        Create a comprehensive rent invoice

        Args:
            client_id: Invoice Ninja client ID
            rent_amount: Base rent amount
            due_date: Payment due date
            unit_address: Unit address
            lease_id: Lease ID for reference
            utilities: Dict of utility charges (e.g., {"water": 45.50, "electric": 120.00})
            late_fees: Late fee amount (if applicable)
            period: Billing period (e.g., "January 2024")

        Returns:
            Created invoice or None on failure
        """
        if not period:
            period = due_date.strftime("%B %Y")

        line_items = [
            InvoiceLineItem(
                product_key="rent",
                notes=f"Monthly Rent - {unit_address}",
                cost=rent_amount,
                quantity=1.0
            )
        ]

        # Add utilities
        if utilities:
            for utility_name, utility_cost in utilities.items():
                line_items.append(
                    InvoiceLineItem(
                        product_key=f"utility_{utility_name.lower()}",
                        notes=f"{utility_name.title()} - {period}",
                        cost=utility_cost,
                        quantity=1.0
                    )
                )

        # Add late fees
        if late_fees and late_fees > 0:
            line_items.append(
                InvoiceLineItem(
                    product_key="late_fee",
                    notes="Late Payment Fee",
                    cost=late_fees,
                    quantity=1.0
                )
            )

        return await self.create_invoice(
            client_id=client_id,
            line_items=line_items,
            due_date=due_date,
            po_number=lease_id,
            public_notes=f"Rent invoice for {unit_address} - {period}",
            terms="Payment is due on or before the due date listed above. Late fees may apply after the due date.",
            footer=f"Lease ID: {lease_id}"
        )

    async def setup_monthly_rent_billing(
        self,
        client_id: str,
        rent_amount: float,
        unit_address: str,
        lease_id: str,
        due_day: int = 1,
        auto_bill: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Set up automatic monthly rent billing

        Args:
            client_id: Invoice Ninja client ID
            rent_amount: Monthly rent amount
            unit_address: Unit address
            lease_id: Lease ID
            due_day: Day of month rent is due (1-28)
            auto_bill: Enable automatic billing

        Returns:
            Created recurring invoice or None on failure
        """
        line_items = [
            InvoiceLineItem(
                product_key="rent",
                notes=f"Monthly Rent - {unit_address}",
                cost=rent_amount,
                quantity=1.0
            )
        ]

        return await self.create_recurring_invoice(
            client_id=client_id,
            line_items=line_items,
            frequency_id=5,  # Monthly
            remaining_cycles=-1,  # Infinite (until lease ends)
            due_date_terms=f"net {due_day}",
            auto_bill=auto_bill,
            public_notes=f"Monthly rent for {unit_address}",
            terms=f"Rent is due on the {due_day}{'st' if due_day == 1 else 'th'} of each month. Late fees may apply."
        )


# ========================================
# Singleton instance management
# ========================================

_invoiceninja_client: Optional[InvoiceNinjaClient] = None


def get_invoiceninja_client(
    base_url: str = "http://invoiceninja.utilities.svc.cluster.local",
    api_token: Optional[str] = None
) -> InvoiceNinjaClient:
    """Get singleton Invoice Ninja client instance"""
    global _invoiceninja_client
    if _invoiceninja_client is None:
        _invoiceninja_client = InvoiceNinjaClient(base_url=base_url, api_token=api_token)
    return _invoiceninja_client


async def close_invoiceninja_client():
    """Close singleton Invoice Ninja client"""
    global _invoiceninja_client
    if _invoiceninja_client:
        await _invoiceninja_client.close()
        _invoiceninja_client = None
