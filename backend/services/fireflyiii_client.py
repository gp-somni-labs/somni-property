"""
Firefly III Integration Client for SomniProperty

Integrates with self-hosted Firefly III (personal finance manager) for:
- Property financial management
- Rent payment tracking
- Expense categorization
- Budget management
- Financial reporting
- Multi-property accounting
- Vendor payment tracking
- Tax preparation

Firefly III Service: fireflyiii.storage.svc.cluster.local
Documentation: https://docs.firefly-iii.org/
API Docs: https://api-docs.firefly-iii.org/
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
from decimal import Decimal
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """Firefly III transaction types"""
    WITHDRAWAL = "withdrawal"  # Expense
    DEPOSIT = "deposit"  # Income
    TRANSFER = "transfer"  # Between accounts


class AccountType(Enum):
    """Firefly III account types"""
    ASSET = "asset"  # Bank accounts, cash
    EXPENSE = "expense"  # Where money goes (vendors, utilities)
    REVENUE = "revenue"  # Where money comes from (tenants, rent)
    CASH = "cash"
    LOAN = "loan"
    DEBT = "debt"
    MORTGAGE = "mortgage"


class BudgetPeriod(Enum):
    """Budget period types"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class FireflyAccount(BaseModel):
    """Firefly III account model"""
    id: Optional[str] = None
    name: str
    account_type: str
    currency_code: str = "USD"
    current_balance: Optional[Decimal] = None
    iban: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None


class FireflyTransaction(BaseModel):
    """Firefly III transaction model"""
    id: Optional[str] = None
    transaction_type: str
    date: date
    amount: Decimal
    description: str
    source_id: Optional[str] = None  # Source account ID
    source_name: Optional[str] = None  # Source account name
    destination_id: Optional[str] = None  # Destination account ID
    destination_name: Optional[str] = None  # Destination account name
    category_name: Optional[str] = None
    budget_name: Optional[str] = None
    tags: Optional[List[str]] = []
    notes: Optional[str] = None
    external_id: Optional[str] = None  # For linking to work orders, etc.


class FireflyBudget(BaseModel):
    """Firefly III budget model"""
    id: Optional[str] = None
    name: str
    active: bool = True
    auto_budget_type: Optional[str] = None
    auto_budget_amount: Optional[Decimal] = None
    auto_budget_period: Optional[str] = None


class FireflyBudgetLimit(BaseModel):
    """Firefly III budget limit model"""
    id: Optional[str] = None
    budget_id: str
    start_date: date
    end_date: date
    amount: Decimal
    spent: Optional[Decimal] = None


class FireflyCategory(BaseModel):
    """Firefly III category model"""
    id: Optional[str] = None
    name: str
    notes: Optional[str] = None
    spent: Optional[Decimal] = None


class FireflyIIIClient:
    """Client for interacting with Firefly III API"""

    def __init__(
        self,
        base_url: str = "http://fireflyiii.storage.svc.cluster.local",
        api_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Firefly III client

        Args:
            base_url: Firefly III service URL
            api_token: Personal Access Token (from Profile → OAuth)
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
            "Accept": "application/vnd.api+json",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    # ========================================
    # Account Management
    # ========================================

    async def create_account(
        self,
        name: str,
        account_type: AccountType,
        currency_code: str = "USD",
        opening_balance: Optional[Decimal] = None,
        opening_balance_date: Optional[date] = None,
        account_number: Optional[str] = None,
        iban: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[FireflyAccount]:
        """
        Create an account in Firefly III

        Use for:
        - Property bank accounts (ASSET)
        - Tenant revenue accounts (REVENUE)
        - Vendor expense accounts (EXPENSE)
        - Security deposit accounts (ASSET)

        Args:
            name: Account name (e.g., "Sunset Apartments - Operating Account")
            account_type: Account type
            currency_code: Currency code (default: USD)
            opening_balance: Opening balance
            opening_balance_date: Opening balance date
            account_number: Account number
            iban: IBAN
            notes: Account notes

        Returns:
            Created account or None on failure
        """
        try:
            payload = {
                "name": name,
                "type": account_type.value,
                "currency_code": currency_code,
            }

            if opening_balance is not None:
                payload["opening_balance"] = str(opening_balance)
            if opening_balance_date:
                payload["opening_balance_date"] = opening_balance_date.isoformat()
            if account_number:
                payload["account_number"] = account_number
            if iban:
                payload["iban"] = iban
            if notes:
                payload["notes"] = notes

            response = await self.client.post(
                f"{self.base_url}/api/v1/accounts",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                account_data = data.get("data", {}).get("attributes", {})

                return FireflyAccount(
                    id=data.get("data", {}).get("id"),
                    name=account_data.get("name"),
                    account_type=account_data.get("type"),
                    currency_code=account_data.get("currency_code", "USD"),
                    current_balance=Decimal(account_data.get("current_balance", "0")),
                    iban=account_data.get("iban"),
                    account_number=account_data.get("account_number"),
                    notes=account_data.get("notes")
                )
            else:
                logger.error(f"Failed to create account: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating account: {e}")
            return None

    async def get_account(self, account_id: str) -> Optional[FireflyAccount]:
        """Get account by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/accounts/{account_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                account_data = data.get("data", {}).get("attributes", {})

                return FireflyAccount(
                    id=data.get("data", {}).get("id"),
                    name=account_data.get("name"),
                    account_type=account_data.get("type"),
                    currency_code=account_data.get("currency_code", "USD"),
                    current_balance=Decimal(account_data.get("current_balance", "0")),
                    iban=account_data.get("iban"),
                    account_number=account_data.get("account_number"),
                    notes=account_data.get("notes")
                )
            return None

        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None

    async def list_accounts(
        self,
        account_type: Optional[AccountType] = None
    ) -> List[FireflyAccount]:
        """
        List all accounts

        Args:
            account_type: Filter by account type (None = all types)

        Returns:
            List of accounts
        """
        try:
            params = {}
            if account_type:
                params["type"] = account_type.value

            response = await self.client.get(
                f"{self.base_url}/api/v1/accounts",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                accounts = data.get("data", [])

                return [
                    FireflyAccount(
                        id=account.get("id"),
                        name=account.get("attributes", {}).get("name"),
                        account_type=account.get("attributes", {}).get("type"),
                        currency_code=account.get("attributes", {}).get("currency_code", "USD"),
                        current_balance=Decimal(account.get("attributes", {}).get("current_balance", "0")),
                        iban=account.get("attributes", {}).get("iban"),
                        account_number=account.get("attributes", {}).get("account_number"),
                        notes=account.get("attributes", {}).get("notes")
                    )
                    for account in accounts
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing accounts: {e}")
            return []

    # ========================================
    # Transaction Management
    # ========================================

    async def create_transaction(
        self,
        transaction_type: TransactionType,
        date: date,
        amount: Decimal,
        description: str,
        source_id: Optional[str] = None,
        source_name: Optional[str] = None,
        destination_id: Optional[str] = None,
        destination_name: Optional[str] = None,
        category_name: Optional[str] = None,
        budget_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        external_id: Optional[str] = None
    ) -> Optional[FireflyTransaction]:
        """
        Create a transaction

        Use for:
        - Recording rent payments (DEPOSIT)
        - Recording expenses (WITHDRAWAL)
        - Transferring between accounts (TRANSFER)
        - Work order expenses (WITHDRAWAL with work_order_id tag)

        Args:
            transaction_type: Transaction type (deposit, withdrawal, transfer)
            date: Transaction date
            amount: Transaction amount
            description: Transaction description
            source_id: Source account ID (required for withdrawal/transfer)
            source_name: Source account name (alternative to source_id)
            destination_id: Destination account ID (required for deposit/transfer)
            destination_name: Destination account name (alternative to destination_id)
            category_name: Category name
            budget_name: Budget name
            tags: List of tags
            notes: Transaction notes
            external_id: External reference ID (e.g., work_order_id)

        Returns:
            Created transaction or None on failure
        """
        try:
            transaction_data = {
                "type": transaction_type.value,
                "date": date.isoformat(),
                "amount": str(amount),
                "description": description,
            }

            if source_id:
                transaction_data["source_id"] = source_id
            elif source_name:
                transaction_data["source_name"] = source_name

            if destination_id:
                transaction_data["destination_id"] = destination_id
            elif destination_name:
                transaction_data["destination_name"] = destination_name

            if category_name:
                transaction_data["category_name"] = category_name
            if budget_name:
                transaction_data["budget_name"] = budget_name
            if tags:
                transaction_data["tags"] = tags
            if notes:
                transaction_data["notes"] = notes
            if external_id:
                transaction_data["external_id"] = external_id

            payload = {
                "error_if_duplicate_hash": False,
                "apply_rules": True,
                "transactions": [transaction_data]
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/transactions",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                transaction = data.get("data", {}).get("attributes", {}).get("transactions", [{}])[0]

                return FireflyTransaction(
                    id=data.get("data", {}).get("id"),
                    transaction_type=transaction.get("type"),
                    date=datetime.fromisoformat(transaction.get("date")).date(),
                    amount=Decimal(transaction.get("amount")),
                    description=transaction.get("description"),
                    source_id=transaction.get("source_id"),
                    source_name=transaction.get("source_name"),
                    destination_id=transaction.get("destination_id"),
                    destination_name=transaction.get("destination_name"),
                    category_name=transaction.get("category_name"),
                    budget_name=transaction.get("budget_name"),
                    tags=transaction.get("tags", []),
                    notes=transaction.get("notes"),
                    external_id=transaction.get("external_id")
                )
            else:
                logger.error(f"Failed to create transaction: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None

    async def get_transaction(self, transaction_id: str) -> Optional[FireflyTransaction]:
        """Get transaction by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/transactions/{transaction_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                transaction = data.get("data", {}).get("attributes", {}).get("transactions", [{}])[0]

                return FireflyTransaction(
                    id=data.get("data", {}).get("id"),
                    transaction_type=transaction.get("type"),
                    date=datetime.fromisoformat(transaction.get("date")).date(),
                    amount=Decimal(transaction.get("amount")),
                    description=transaction.get("description"),
                    source_id=transaction.get("source_id"),
                    source_name=transaction.get("source_name"),
                    destination_id=transaction.get("destination_id"),
                    destination_name=transaction.get("destination_name"),
                    category_name=transaction.get("category_name"),
                    budget_name=transaction.get("budget_name"),
                    tags=transaction.get("tags", []),
                    notes=transaction.get("notes"),
                    external_id=transaction.get("external_id")
                )
            return None

        except Exception as e:
            logger.error(f"Error getting transaction: {e}")
            return None

    async def list_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None
    ) -> List[FireflyTransaction]:
        """
        List transactions

        Args:
            start_date: Filter transactions from this date
            end_date: Filter transactions to this date
            transaction_type: Filter by transaction type

        Returns:
            List of transactions
        """
        try:
            params = {}
            if start_date:
                params["start"] = start_date.isoformat()
            if end_date:
                params["end"] = end_date.isoformat()
            if transaction_type:
                params["type"] = transaction_type.value

            response = await self.client.get(
                f"{self.base_url}/api/v1/transactions",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                transactions = []

                for item in data.get("data", []):
                    trans_list = item.get("attributes", {}).get("transactions", [])
                    for transaction in trans_list:
                        transactions.append(FireflyTransaction(
                            id=item.get("id"),
                            transaction_type=transaction.get("type"),
                            date=datetime.fromisoformat(transaction.get("date")).date(),
                            amount=Decimal(transaction.get("amount")),
                            description=transaction.get("description"),
                            source_id=transaction.get("source_id"),
                            source_name=transaction.get("source_name"),
                            destination_id=transaction.get("destination_id"),
                            destination_name=transaction.get("destination_name"),
                            category_name=transaction.get("category_name"),
                            budget_name=transaction.get("budget_name"),
                            tags=transaction.get("tags", []),
                            notes=transaction.get("notes"),
                            external_id=transaction.get("external_id")
                        ))

                return transactions
            return []

        except Exception as e:
            logger.error(f"Error listing transactions: {e}")
            return []

    # ========================================
    # Budget Management
    # ========================================

    async def create_budget(
        self,
        name: str,
        auto_budget_type: Optional[str] = None,
        auto_budget_amount: Optional[Decimal] = None,
        auto_budget_period: Optional[str] = None
    ) -> Optional[FireflyBudget]:
        """
        Create a budget

        Use for:
        - Monthly maintenance budget per property
        - Annual capital improvements budget
        - Quarterly marketing budget
        - Emergency reserve budget

        Args:
            name: Budget name (e.g., "Sunset Apartments - Maintenance")
            auto_budget_type: Auto-budget type (fixed, adjusted)
            auto_budget_amount: Auto-budget amount
            auto_budget_period: Auto-budget period (monthly, quarterly, yearly)

        Returns:
            Created budget or None on failure
        """
        try:
            payload = {
                "name": name,
                "active": True
            }

            if auto_budget_type:
                payload["auto_budget_type"] = auto_budget_type
            if auto_budget_amount:
                payload["auto_budget_amount"] = str(auto_budget_amount)
            if auto_budget_period:
                payload["auto_budget_period"] = auto_budget_period

            response = await self.client.post(
                f"{self.base_url}/api/v1/budgets",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                budget_data = data.get("data", {}).get("attributes", {})

                return FireflyBudget(
                    id=data.get("data", {}).get("id"),
                    name=budget_data.get("name"),
                    active=budget_data.get("active", True),
                    auto_budget_type=budget_data.get("auto_budget_type"),
                    auto_budget_amount=Decimal(budget_data.get("auto_budget_amount", "0")) if budget_data.get("auto_budget_amount") else None,
                    auto_budget_period=budget_data.get("auto_budget_period")
                )
            else:
                logger.error(f"Failed to create budget: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating budget: {e}")
            return None

    async def list_budgets(self) -> List[FireflyBudget]:
        """List all budgets"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/budgets",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                budgets = data.get("data", [])

                return [
                    FireflyBudget(
                        id=budget.get("id"),
                        name=budget.get("attributes", {}).get("name"),
                        active=budget.get("attributes", {}).get("active", True),
                        auto_budget_type=budget.get("attributes", {}).get("auto_budget_type"),
                        auto_budget_amount=Decimal(budget.get("attributes", {}).get("auto_budget_amount", "0")) if budget.get("attributes", {}).get("auto_budget_amount") else None,
                        auto_budget_period=budget.get("attributes", {}).get("auto_budget_period")
                    )
                    for budget in budgets
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing budgets: {e}")
            return []

    async def set_budget_limit(
        self,
        budget_id: str,
        start_date: date,
        end_date: date,
        amount: Decimal
    ) -> Optional[FireflyBudgetLimit]:
        """
        Set a budget limit for a specific period

        Args:
            budget_id: Budget ID
            start_date: Start date of budget period
            end_date: End date of budget period
            amount: Budget limit amount

        Returns:
            Created budget limit or None on failure
        """
        try:
            payload = {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "amount": str(amount)
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/budgets/{budget_id}/limits",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                limit_data = data.get("data", {}).get("attributes", {})

                return FireflyBudgetLimit(
                    id=data.get("data", {}).get("id"),
                    budget_id=budget_id,
                    start_date=datetime.fromisoformat(limit_data.get("start")).date(),
                    end_date=datetime.fromisoformat(limit_data.get("end")).date(),
                    amount=Decimal(limit_data.get("amount", "0")),
                    spent=Decimal(limit_data.get("spent", "0")) if limit_data.get("spent") else None
                )
            else:
                logger.error(f"Failed to set budget limit: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error setting budget limit: {e}")
            return None

    # ========================================
    # Category Management
    # ========================================

    async def create_category(
        self,
        name: str,
        notes: Optional[str] = None
    ) -> Optional[FireflyCategory]:
        """
        Create a category

        Use for organizing expenses:
        - "Maintenance - HVAC"
        - "Maintenance - Plumbing"
        - "Utilities - Electric"
        - "Property Management Fees"
        - "Marketing & Advertising"

        Args:
            name: Category name
            notes: Category notes

        Returns:
            Created category or None on failure
        """
        try:
            payload = {
                "name": name
            }
            if notes:
                payload["notes"] = notes

            response = await self.client.post(
                f"{self.base_url}/api/v1/categories",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                category_data = data.get("data", {}).get("attributes", {})

                return FireflyCategory(
                    id=data.get("data", {}).get("id"),
                    name=category_data.get("name"),
                    notes=category_data.get("notes")
                )
            else:
                logger.error(f"Failed to create category: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return None

    async def list_categories(self) -> List[FireflyCategory]:
        """List all categories"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/categories",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                categories = data.get("data", [])

                return [
                    FireflyCategory(
                        id=category.get("id"),
                        name=category.get("attributes", {}).get("name"),
                        notes=category.get("attributes", {}).get("notes")
                    )
                    for category in categories
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing categories: {e}")
            return []

    # ========================================
    # Reporting
    # ========================================

    async def get_report(
        self,
        start_date: date,
        end_date: date,
        accounts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get financial report for a period

        Args:
            start_date: Report start date
            end_date: Report end date
            accounts: List of account IDs to include (None = all accounts)

        Returns:
            Report data with income, expenses, balance, etc.
        """
        try:
            params = {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
            if accounts:
                params["accounts"] = ",".join(accounts)

            response = await self.client.get(
                f"{self.base_url}/api/v1/summary/basic",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get report: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error getting report: {e}")
            return {}

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def record_rent_payment(
        self,
        tenant_name: str,
        property_name: str,
        unit_number: str,
        amount: Decimal,
        payment_date: date,
        destination_account_id: str,
        notes: Optional[str] = None
    ) -> Optional[FireflyTransaction]:
        """
        Record a rent payment

        Args:
            tenant_name: Tenant name
            property_name: Property name
            unit_number: Unit number
            amount: Payment amount
            payment_date: Payment date
            destination_account_id: Property bank account ID
            notes: Payment notes

        Returns:
            Created transaction or None on failure
        """
        description = f"Rent Payment - {property_name} Unit {unit_number}"
        tags = [
            "rent",
            f"property:{property_name}",
            f"unit:{unit_number}",
            f"tenant:{tenant_name}"
        ]

        return await self.create_transaction(
            transaction_type=TransactionType.DEPOSIT,
            date=payment_date,
            amount=amount,
            description=description,
            source_name=tenant_name,
            destination_id=destination_account_id,
            category_name="Rental Income",
            tags=tags,
            notes=notes
        )

    async def record_work_order_expense(
        self,
        work_order_id: str,
        property_name: str,
        vendor_name: str,
        amount: Decimal,
        expense_date: date,
        source_account_id: str,
        category: str = "Maintenance",
        notes: Optional[str] = None
    ) -> Optional[FireflyTransaction]:
        """
        Record a work order expense

        Args:
            work_order_id: Work order ID
            property_name: Property name
            vendor_name: Vendor name
            amount: Expense amount
            expense_date: Expense date
            source_account_id: Property bank account ID
            category: Expense category
            notes: Expense notes

        Returns:
            Created transaction or None on failure
        """
        description = f"Work Order {work_order_id} - {vendor_name}"
        tags = [
            "work_order",
            f"property:{property_name}",
            f"vendor:{vendor_name}",
            f"wo_id:{work_order_id}"
        ]

        return await self.create_transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            date=expense_date,
            amount=amount,
            description=description,
            source_id=source_account_id,
            destination_name=vendor_name,
            category_name=category,
            tags=tags,
            notes=notes,
            external_id=work_order_id
        )

    async def setup_property_finances(
        self,
        property_name: str,
        opening_balance: Decimal = Decimal("0")
    ) -> Optional[Dict[str, str]]:
        """
        Set up financial structure for a property

        Creates:
        - Operating account (ASSET)
        - Security deposits account (ASSET)
        - Maintenance budget
        - Utilities budget
        - Capital improvements budget

        Args:
            property_name: Property name
            opening_balance: Opening balance for operating account

        Returns:
            Dictionary with created account/budget IDs or None on failure
        """
        try:
            result = {}

            # Create operating account
            operating_account = await self.create_account(
                name=f"{property_name} - Operating Account",
                account_type=AccountType.ASSET,
                opening_balance=opening_balance,
                opening_balance_date=date.today(),
                notes=f"Primary operating account for {property_name}"
            )
            if operating_account:
                result["operating_account_id"] = operating_account.id

            # Create security deposits account
            security_account = await self.create_account(
                name=f"{property_name} - Security Deposits",
                account_type=AccountType.ASSET,
                notes=f"Security deposits held for {property_name}"
            )
            if security_account:
                result["security_account_id"] = security_account.id

            # Create maintenance budget
            maintenance_budget = await self.create_budget(
                name=f"{property_name} - Maintenance",
                auto_budget_type="fixed",
                auto_budget_period="monthly"
            )
            if maintenance_budget:
                result["maintenance_budget_id"] = maintenance_budget.id

            # Create utilities budget
            utilities_budget = await self.create_budget(
                name=f"{property_name} - Utilities",
                auto_budget_type="fixed",
                auto_budget_period="monthly"
            )
            if utilities_budget:
                result["utilities_budget_id"] = utilities_budget.id

            # Create capital improvements budget
            capital_budget = await self.create_budget(
                name=f"{property_name} - Capital Improvements",
                auto_budget_type="fixed",
                auto_budget_period="yearly"
            )
            if capital_budget:
                result["capital_budget_id"] = capital_budget.id

            logger.info(f"Financial structure created for {property_name}")
            return result

        except Exception as e:
            logger.error(f"Error setting up property finances: {e}")
            return None


# ========================================
# Singleton instance management
# ========================================

_fireflyiii_client: Optional[FireflyIIIClient] = None


def get_fireflyiii_client(
    base_url: str = "http://fireflyiii.storage.svc.cluster.local",
    api_token: Optional[str] = None
) -> FireflyIIIClient:
    """Get singleton Firefly III client instance"""
    global _fireflyiii_client
    if _fireflyiii_client is None:
        _fireflyiii_client = FireflyIIIClient(
            base_url=base_url,
            api_token=api_token
        )
    return _fireflyiii_client


async def close_fireflyiii_client():
    """Close singleton Firefly III client"""
    global _fireflyiii_client
    if _fireflyiii_client:
        await _fireflyiii_client.close()
        _fireflyiii_client = None
