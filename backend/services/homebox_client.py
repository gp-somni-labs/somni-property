"""
Homebox Integration Client for SomniProperty

Integrates with self-hosted Homebox (home inventory management) for:
- Property asset tracking (appliances, HVAC, water heaters, etc.)
- Bill of Materials (BOM) creation for work orders
- Maintenance history tracking
- Per-tenant inventory management
- Warranty and purchase tracking

Homebox Service: homebox.utilities.svc.cluster.local:7745
Documentation: https://github.com/sysadminsmedia/homebox
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HomeboxAsset(BaseModel):
    """Homebox asset/item model"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    labels: Optional[List[str]] = []
    purchase_from: Optional[str] = None
    purchase_price: Optional[float] = None
    purchase_time: Optional[datetime] = None
    warranty_expires: Optional[datetime] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    notes: Optional[str] = None


class HomeboxLocation(BaseModel):
    """Homebox location model"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None


class HomeboxMaintenanceEntry(BaseModel):
    """Homebox maintenance log entry"""
    id: Optional[str] = None
    item_id: str
    name: str
    description: Optional[str] = None
    date: datetime
    cost: Optional[float] = None
    scheduled_date: Optional[datetime] = None
    completed: bool = False


class HomeboxBOM(BaseModel):
    """Bill of Materials for a work order"""
    work_order_id: str
    items: List[Dict[str, Any]]  # List of {name, quantity, estimated_cost, item_id?}
    total_estimated_cost: float
    notes: Optional[str] = None


class HomeboxClient:
    """Client for interacting with Homebox API"""

    def __init__(
        self,
        base_url: str = "http://homebox.utilities.svc.cluster.local:7745",
        api_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Homebox client

        Args:
            base_url: Homebox service URL
            api_token: API authentication token (from Homebox user settings)
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
            "Accept": "application/json"
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    # ========================================
    # Location Management (Property Hierarchy)
    # ========================================

    async def create_location(
        self,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> Optional[HomeboxLocation]:
        """
        Create a location in Homebox

        Use for creating property hierarchy:
        - Property Name (top level)
          - Building A
            - Unit 101
            - Unit 102
          - Common Areas
            - Gym
            - Pool

        Args:
            name: Location name (e.g., "Building A - Unit 204")
            description: Location description
            parent_id: Parent location ID for nesting

        Returns:
            Created location or None on failure
        """
        try:
            payload = {
                "name": name,
                "description": description or ""
            }
            if parent_id:
                payload["parentId"] = parent_id

            response = await self.client.post(
                f"{self.base_url}/api/v1/locations",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return HomeboxLocation(
                    id=data.get("id"),
                    name=data.get("name"),
                    description=data.get("description"),
                    parent_id=data.get("parentId")
                )
            else:
                logger.error(f"Failed to create location: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating location: {e}")
            return None

    async def get_location(self, location_id: str) -> Optional[HomeboxLocation]:
        """Get location by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/locations/{location_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return HomeboxLocation(
                    id=data.get("id"),
                    name=data.get("name"),
                    description=data.get("description"),
                    parent_id=data.get("parentId")
                )
            return None

        except Exception as e:
            logger.error(f"Error getting location: {e}")
            return None

    async def list_locations(self) -> List[HomeboxLocation]:
        """List all locations"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/locations",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                return [
                    HomeboxLocation(
                        id=item.get("id"),
                        name=item.get("name"),
                        description=item.get("description"),
                        parent_id=item.get("parentId")
                    )
                    for item in items
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing locations: {e}")
            return []

    # ========================================
    # Asset/Item Management
    # ========================================

    async def create_asset(self, asset: HomeboxAsset) -> Optional[HomeboxAsset]:
        """
        Create an asset/item in Homebox

        Use for tracking property assets:
        - Appliances (dishwasher, refrigerator, HVAC)
        - Equipment (water heater, furnace)
        - Per-tenant items (if configured)

        Args:
            asset: Asset details

        Returns:
            Created asset or None on failure
        """
        try:
            payload = {
                "name": asset.name,
                "description": asset.description or "",
                "locationId": asset.location_id,
                "labels": asset.labels or [],
                "purchaseFrom": asset.purchase_from or "",
                "purchasePrice": asset.purchase_price or 0,
                "modelNumber": asset.model_number or "",
                "serialNumber": asset.serial_number or "",
                "manufacturer": asset.manufacturer or "",
                "notes": asset.notes or ""
            }

            if asset.purchase_time:
                payload["purchaseTime"] = asset.purchase_time.isoformat()
            if asset.warranty_expires:
                payload["warrantyExpires"] = asset.warranty_expires.isoformat()

            response = await self.client.post(
                f"{self.base_url}/api/v1/items",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return HomeboxAsset(
                    id=data.get("id"),
                    name=data.get("name"),
                    description=data.get("description"),
                    location_id=data.get("locationId"),
                    labels=data.get("labels", []),
                    purchase_from=data.get("purchaseFrom"),
                    purchase_price=data.get("purchasePrice"),
                    model_number=data.get("modelNumber"),
                    serial_number=data.get("serialNumber"),
                    manufacturer=data.get("manufacturer"),
                    notes=data.get("notes")
                )
            else:
                logger.error(f"Failed to create asset: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating asset: {e}")
            return None

    async def get_asset(self, asset_id: str) -> Optional[HomeboxAsset]:
        """Get asset by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/items/{asset_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return HomeboxAsset(
                    id=data.get("id"),
                    name=data.get("name"),
                    description=data.get("description"),
                    location_id=data.get("locationId"),
                    labels=data.get("labels", []),
                    purchase_from=data.get("purchaseFrom"),
                    purchase_price=data.get("purchasePrice"),
                    model_number=data.get("modelNumber"),
                    serial_number=data.get("serialNumber"),
                    manufacturer=data.get("manufacturer"),
                    notes=data.get("notes")
                )
            return None

        except Exception as e:
            logger.error(f"Error getting asset: {e}")
            return None

    async def search_assets(
        self,
        location_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        query: Optional[str] = None
    ) -> List[HomeboxAsset]:
        """
        Search for assets

        Args:
            location_id: Filter by location
            labels: Filter by labels
            query: Search query string

        Returns:
            List of matching assets
        """
        try:
            params = {}
            if location_id:
                params["locations"] = location_id
            if labels:
                params["labels"] = ",".join(labels)
            if query:
                params["q"] = query

            response = await self.client.get(
                f"{self.base_url}/api/v1/items",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                return [
                    HomeboxAsset(
                        id=item.get("id"),
                        name=item.get("name"),
                        description=item.get("description"),
                        location_id=item.get("locationId"),
                        labels=item.get("labels", []),
                        purchase_from=item.get("purchaseFrom"),
                        purchase_price=item.get("purchasePrice"),
                        model_number=item.get("modelNumber"),
                        serial_number=item.get("serialNumber"),
                        manufacturer=item.get("manufacturer"),
                        notes=item.get("notes")
                    )
                    for item in items
                ]
            return []

        except Exception as e:
            logger.error(f"Error searching assets: {e}")
            return []

    # ========================================
    # Maintenance Tracking
    # ========================================

    async def create_maintenance_entry(
        self,
        entry: HomeboxMaintenanceEntry
    ) -> Optional[HomeboxMaintenanceEntry]:
        """
        Create a maintenance log entry for an asset

        Use for tracking:
        - Completed repairs
        - Scheduled maintenance
        - Service history

        Args:
            entry: Maintenance entry details

        Returns:
            Created entry or None on failure
        """
        try:
            payload = {
                "name": entry.name,
                "description": entry.description or "",
                "date": entry.date.isoformat(),
                "cost": entry.cost or 0,
                "completed": entry.completed
            }

            if entry.scheduled_date:
                payload["scheduledDate"] = entry.scheduled_date.isoformat()

            response = await self.client.post(
                f"{self.base_url}/api/v1/items/{entry.item_id}/maintenance",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return HomeboxMaintenanceEntry(
                    id=data.get("id"),
                    item_id=entry.item_id,
                    name=data.get("name"),
                    description=data.get("description"),
                    date=datetime.fromisoformat(data.get("date")),
                    cost=data.get("cost"),
                    completed=data.get("completed", False)
                )
            else:
                logger.error(f"Failed to create maintenance entry: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating maintenance entry: {e}")
            return None

    async def get_maintenance_history(self, asset_id: str) -> List[HomeboxMaintenanceEntry]:
        """Get maintenance history for an asset"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/items/{asset_id}/maintenance",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                entries = data.get("entries", [])
                return [
                    HomeboxMaintenanceEntry(
                        id=entry.get("id"),
                        item_id=asset_id,
                        name=entry.get("name"),
                        description=entry.get("description"),
                        date=datetime.fromisoformat(entry.get("date")),
                        cost=entry.get("cost"),
                        completed=entry.get("completed", False)
                    )
                    for entry in entries
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting maintenance history: {e}")
            return []

    # ========================================
    # Bill of Materials (BOM) for Work Orders
    # ========================================

    async def create_bom_for_work_order(
        self,
        work_order_id: str,
        work_order_description: str,
        items: List[Dict[str, Any]]
    ) -> Optional[HomeboxBOM]:
        """
        Create Bill of Materials (BOM) for a work order

        This creates a custom field or notes entry in Homebox to track
        parts/materials needed for a specific work order.

        Args:
            work_order_id: SomniProperty work order ID
            work_order_description: Work order description
            items: List of items needed [{"name": "Part X", "quantity": 2, "estimated_cost": 50.0}]

        Returns:
            BOM details or None on failure

        Example:
            Work Order: "Replace dishwasher in Unit 204"
            BOM:
              - Dishwasher model XYZ123: qty 1, $450
              - Water supply hose: qty 1, $15
              - Drain hose: qty 1, $12
              Total: $477
        """
        try:
            # Create a virtual "BOM" item in Homebox to track parts
            total_cost = sum(item.get("estimated_cost", 0) * item.get("quantity", 1) for item in items)

            bom_description = f"BOM for Work Order #{work_order_id}\n\n"
            bom_description += f"{work_order_description}\n\n"
            bom_description += "Parts/Materials:\n"

            for item in items:
                name = item.get("name", "Unknown")
                qty = item.get("quantity", 1)
                cost = item.get("estimated_cost", 0)
                bom_description += f"- {name}: qty {qty} @ ${cost:.2f} each = ${cost * qty:.2f}\n"

            bom_description += f"\nTotal Estimated Cost: ${total_cost:.2f}"

            # Create BOM as a special item with label "BOM"
            bom_item = HomeboxAsset(
                name=f"BOM: Work Order #{work_order_id}",
                description=bom_description,
                labels=["BOM", "work-order", f"wo-{work_order_id}"],
                notes=f"Auto-generated BOM for work order {work_order_id}"
            )

            created = await self.create_asset(bom_item)

            if created:
                return HomeboxBOM(
                    work_order_id=work_order_id,
                    items=items,
                    total_estimated_cost=total_cost,
                    notes=bom_description
                )
            return None

        except Exception as e:
            logger.error(f"Error creating BOM: {e}")
            return None

    async def get_warranty_expiring_soon(self, days: int = 30) -> List[HomeboxAsset]:
        """
        Get assets with warranties expiring within specified days

        Useful for proactive maintenance planning

        Args:
            days: Number of days to look ahead

        Returns:
            List of assets with expiring warranties
        """
        try:
            # This would require filtering on the client side
            # as Homebox may not support date range queries
            all_assets = await self.search_assets()

            expiring_soon = []
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            target_date = cutoff_date + timedelta(days=days)

            for asset in all_assets:
                if asset.warranty_expires:
                    if cutoff_date <= asset.warranty_expires <= target_date:
                        expiring_soon.append(asset)

            return expiring_soon

        except Exception as e:
            logger.error(f"Error getting expiring warranties: {e}")
            return []


# ========================================
# Singleton instance management
# ========================================

_homebox_client: Optional[HomeboxClient] = None


def get_homebox_client(
    base_url: str = "http://homebox.utilities.svc.cluster.local:7745",
    api_token: Optional[str] = None
) -> HomeboxClient:
    """Get singleton Homebox client instance"""
    global _homebox_client
    if _homebox_client is None:
        _homebox_client = HomeboxClient(base_url=base_url, api_token=api_token)
    return _homebox_client


async def close_homebox_client():
    """Close singleton Homebox client"""
    global _homebox_client
    if _homebox_client:
        await _homebox_client.close()
        _homebox_client = None
