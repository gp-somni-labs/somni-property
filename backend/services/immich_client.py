"""
Immich Integration Client for SomniProperty

Integrates with self-hosted Immich (AI-powered photo management) for:
- Photo documentation of work orders
- Property inspection photos
- Before/after comparison photos
- Album organization by property/unit
- AI-powered search (find photos by content)
- Face recognition for contractor verification
- Timeline-based photo browsing

Immich Service: immich.storage.svc.cluster.local
Documentation: https://immich.app/docs
API Docs: https://immich.app/docs/api
"""

import logging
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel
import io

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Immich asset types"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class AlbumSortOrder(Enum):
    """Album sorting options"""
    NEWEST_FIRST = "desc"
    OLDEST_FIRST = "asc"


class ImmichAsset(BaseModel):
    """Immich asset (photo/video) model"""
    id: str
    device_asset_id: Optional[str] = None
    owner_id: str
    device_id: str
    type: str
    original_path: Optional[str] = None
    original_file_name: str
    is_favorite: bool = False
    is_archived: bool = False
    duration: Optional[str] = None
    file_created_at: datetime
    file_modified_at: datetime
    updated_at: datetime
    is_trashed: bool = False
    trashed_at: Optional[datetime] = None
    exif_info: Optional[Dict[str, Any]] = None
    smart_info: Optional[Dict[str, Any]] = None


class ImmichAlbum(BaseModel):
    """Immich album model"""
    id: Optional[str] = None
    owner_id: Optional[str] = None
    album_name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    album_thumbnail_asset_id: Optional[str] = None
    asset_count: int = 0
    shared: bool = False


class ImmichSearchResult(BaseModel):
    """Immich search result model"""
    id: str
    type: str
    score: float
    asset: ImmichAsset


class ImmichClient:
    """Client for interacting with Immich API"""

    def __init__(
        self,
        base_url: str = "http://immich.storage.svc.cluster.local",
        api_key: Optional[str] = None,
        timeout: int = 60  # Higher timeout for photo uploads
    ):
        """
        Initialize Immich client

        Args:
            base_url: Immich service URL
            api_key: Immich API key (from Settings → API Keys)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Accept": "application/json"
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    # ========================================
    # Asset Upload & Management
    # ========================================

    async def upload_photo(
        self,
        file_data: bytes,
        file_name: str,
        device_asset_id: Optional[str] = None,
        device_id: str = "somniproperty-system",
        file_created_at: Optional[datetime] = None,
        file_modified_at: Optional[datetime] = None,
        is_favorite: bool = False
    ) -> Optional[ImmichAsset]:
        """
        Upload a photo to Immich

        Use for:
        - Work order documentation (before/after photos)
        - Property inspection photos
        - Unit condition documentation
        - Maintenance record photos

        Args:
            file_data: Photo file bytes
            file_name: Original file name
            device_asset_id: Unique identifier (e.g., work_order_id + timestamp)
            device_id: Device identifier (default: somniproperty-system)
            file_created_at: Original file creation time
            file_modified_at: Original file modification time
            is_favorite: Mark as favorite

        Returns:
            Uploaded asset or None on failure
        """
        try:
            # Prepare multipart form data
            files = {
                'assetData': (file_name, io.BytesIO(file_data), 'image/jpeg')
            }

            data = {
                'deviceAssetId': device_asset_id or f"{file_name}-{datetime.now().timestamp()}",
                'deviceId': device_id,
                'fileCreatedAt': (file_created_at or datetime.now()).isoformat(),
                'fileModifiedAt': (file_modified_at or datetime.now()).isoformat(),
                'isFavorite': str(is_favorite).lower()
            }

            response = await self.client.post(
                f"{self.base_url}/api/asset/upload",
                headers={k: v for k, v in self._headers().items() if k != "Content-Type"},
                files=files,
                data=data
            )

            if response.status_code in [200, 201]:
                result = response.json()
                asset_id = result.get("id")

                # Get full asset details
                if asset_id:
                    return await self.get_asset(asset_id)
                return None
            else:
                logger.error(f"Failed to upload photo: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error uploading photo: {e}")
            return None

    async def get_asset(self, asset_id: str) -> Optional[ImmichAsset]:
        """Get asset details by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/asset/assetById/{asset_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return ImmichAsset(
                    id=data.get("id"),
                    device_asset_id=data.get("deviceAssetId"),
                    owner_id=data.get("ownerId"),
                    device_id=data.get("deviceId"),
                    type=data.get("type"),
                    original_path=data.get("originalPath"),
                    original_file_name=data.get("originalFileName"),
                    is_favorite=data.get("isFavorite", False),
                    is_archived=data.get("isArchived", False),
                    duration=data.get("duration"),
                    file_created_at=datetime.fromisoformat(data.get("fileCreatedAt").replace("Z", "+00:00")),
                    file_modified_at=datetime.fromisoformat(data.get("fileModifiedAt").replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(data.get("updatedAt").replace("Z", "+00:00")),
                    is_trashed=data.get("isTrashed", False),
                    exif_info=data.get("exifInfo"),
                    smart_info=data.get("smartInfo")
                )
            return None

        except Exception as e:
            logger.error(f"Error getting asset: {e}")
            return None

    async def download_asset(self, asset_id: str) -> Optional[bytes]:
        """
        Download asset file

        Args:
            asset_id: Asset ID

        Returns:
            Asset file bytes or None on failure
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/asset/file/{asset_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                return response.content
            return None

        except Exception as e:
            logger.error(f"Error downloading asset: {e}")
            return None

    async def update_asset(
        self,
        asset_id: str,
        is_favorite: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        Update asset metadata

        Args:
            asset_id: Asset ID
            is_favorite: Mark as favorite
            is_archived: Archive asset
            description: Asset description

        Returns:
            True if successful, False otherwise
        """
        try:
            updates = {}
            if is_favorite is not None:
                updates["isFavorite"] = is_favorite
            if is_archived is not None:
                updates["isArchived"] = is_archived
            if description is not None:
                updates["description"] = description

            if not updates:
                return True  # Nothing to update

            response = await self.client.put(
                f"{self.base_url}/api/asset/{asset_id}",
                headers=self._headers(),
                json=updates
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error updating asset: {e}")
            return False

    async def delete_asset(self, asset_id: str) -> bool:
        """
        Delete asset

        Args:
            asset_id: Asset ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/asset",
                headers=self._headers(),
                json={"ids": [asset_id]}
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error deleting asset: {e}")
            return False

    # ========================================
    # Album Management
    # ========================================

    async def create_album(
        self,
        album_name: str,
        description: Optional[str] = None,
        asset_ids: Optional[List[str]] = None
    ) -> Optional[ImmichAlbum]:
        """
        Create a photo album

        Use for organizing photos by:
        - Property (e.g., "Sunset Apartments")
        - Unit (e.g., "Unit 204")
        - Work Order (e.g., "WO-123 HVAC Repair")
        - Type (e.g., "Inspections 2024", "Before/After")

        Args:
            album_name: Album name
            description: Album description
            asset_ids: Initial asset IDs to add

        Returns:
            Created album or None on failure
        """
        try:
            payload = {
                "albumName": album_name,
                "description": description or "",
                "assetIds": asset_ids or []
            }

            response = await self.client.post(
                f"{self.base_url}/api/album",
                headers=self._headers(),
                json=payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return ImmichAlbum(
                    id=data.get("id"),
                    owner_id=data.get("ownerId"),
                    album_name=data.get("albumName"),
                    description=data.get("description"),
                    created_at=datetime.fromisoformat(data.get("createdAt").replace("Z", "+00:00")) if data.get("createdAt") else None,
                    updated_at=datetime.fromisoformat(data.get("updatedAt").replace("Z", "+00:00")) if data.get("updatedAt") else None,
                    album_thumbnail_asset_id=data.get("albumThumbnailAssetId"),
                    asset_count=data.get("assetCount", 0),
                    shared=data.get("shared", False)
                )
            else:
                logger.error(f"Failed to create album: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating album: {e}")
            return None

    async def get_album(self, album_id: str) -> Optional[ImmichAlbum]:
        """Get album details by ID"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/album/{album_id}",
                headers=self._headers()
            )

            if response.status_code == 200:
                data = response.json()
                return ImmichAlbum(
                    id=data.get("id"),
                    owner_id=data.get("ownerId"),
                    album_name=data.get("albumName"),
                    description=data.get("description"),
                    created_at=datetime.fromisoformat(data.get("createdAt").replace("Z", "+00:00")) if data.get("createdAt") else None,
                    updated_at=datetime.fromisoformat(data.get("updatedAt").replace("Z", "+00:00")) if data.get("updatedAt") else None,
                    album_thumbnail_asset_id=data.get("albumThumbnailAssetId"),
                    asset_count=data.get("assetCount", 0),
                    shared=data.get("shared", False)
                )
            return None

        except Exception as e:
            logger.error(f"Error getting album: {e}")
            return None

    async def list_albums(self, shared: Optional[bool] = None) -> List[ImmichAlbum]:
        """
        List all albums

        Args:
            shared: Filter by shared status (None = all)

        Returns:
            List of albums
        """
        try:
            params = {}
            if shared is not None:
                params["shared"] = str(shared).lower()

            response = await self.client.get(
                f"{self.base_url}/api/album",
                headers=self._headers(),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    ImmichAlbum(
                        id=album.get("id"),
                        owner_id=album.get("ownerId"),
                        album_name=album.get("albumName"),
                        description=album.get("description"),
                        created_at=datetime.fromisoformat(album.get("createdAt").replace("Z", "+00:00")) if album.get("createdAt") else None,
                        updated_at=datetime.fromisoformat(album.get("updatedAt").replace("Z", "+00:00")) if album.get("updatedAt") else None,
                        album_thumbnail_asset_id=album.get("albumThumbnailAssetId"),
                        asset_count=album.get("assetCount", 0),
                        shared=album.get("shared", False)
                    )
                    for album in data
                ]
            return []

        except Exception as e:
            logger.error(f"Error listing albums: {e}")
            return []

    async def add_to_album(self, album_id: str, asset_ids: List[str]) -> bool:
        """
        Add assets to an album

        Args:
            album_id: Album ID
            asset_ids: List of asset IDs to add

        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "ids": asset_ids
            }

            response = await self.client.put(
                f"{self.base_url}/api/album/{album_id}/assets",
                headers=self._headers(),
                json=payload
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error adding assets to album: {e}")
            return False

    async def remove_from_album(self, album_id: str, asset_ids: List[str]) -> bool:
        """
        Remove assets from an album

        Args:
            album_id: Album ID
            asset_ids: List of asset IDs to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/album/{album_id}/assets",
                headers=self._headers(),
                json={"ids": asset_ids}
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error removing assets from album: {e}")
            return False

    async def delete_album(self, album_id: str) -> bool:
        """
        Delete an album

        Args:
            album_id: Album ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/album/{album_id}",
                headers=self._headers()
            )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error deleting album: {e}")
            return False

    # ========================================
    # AI-Powered Search
    # ========================================

    async def search_photos(
        self,
        query: str,
        limit: int = 20
    ) -> List[ImmichSearchResult]:
        """
        Search photos using AI-powered content search

        Search examples:
        - "broken HVAC unit"
        - "water damage ceiling"
        - "kitchen renovation"
        - "before repair photos"
        - "contractor holding tools"

        Args:
            query: Natural language search query
            limit: Maximum results

        Returns:
            List of search results with relevance scores
        """
        try:
            payload = {
                "query": query,
                "type": "SMART_SEARCH"
            }

            response = await self.client.post(
                f"{self.base_url}/api/search",
                headers=self._headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                results = []

                assets = data.get("assets", {}).get("items", [])
                for item in assets[:limit]:
                    asset = item.get("data")
                    if asset:
                        results.append(ImmichSearchResult(
                            id=asset.get("id"),
                            type=asset.get("type"),
                            score=item.get("score", 0.0),
                            asset=ImmichAsset(
                                id=asset.get("id"),
                                device_asset_id=asset.get("deviceAssetId"),
                                owner_id=asset.get("ownerId"),
                                device_id=asset.get("deviceId"),
                                type=asset.get("type"),
                                original_path=asset.get("originalPath"),
                                original_file_name=asset.get("originalFileName"),
                                is_favorite=asset.get("isFavorite", False),
                                is_archived=asset.get("isArchived", False),
                                duration=asset.get("duration"),
                                file_created_at=datetime.fromisoformat(asset.get("fileCreatedAt").replace("Z", "+00:00")),
                                file_modified_at=datetime.fromisoformat(asset.get("fileModifiedAt").replace("Z", "+00:00")),
                                updated_at=datetime.fromisoformat(asset.get("updatedAt").replace("Z", "+00:00")),
                                is_trashed=asset.get("isTrashed", False),
                                exif_info=asset.get("exifInfo"),
                                smart_info=asset.get("smartInfo")
                            )
                        ))

                return results
            return []

        except Exception as e:
            logger.error(f"Error searching photos: {e}")
            return []

    async def search_by_metadata(
        self,
        original_file_name: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None
    ) -> List[ImmichAsset]:
        """
        Search photos by metadata (EXIF data)

        Args:
            original_file_name: Filter by filename
            city: Filter by city
            state: Filter by state
            country: Filter by country
            created_after: Filter by creation date (after)
            created_before: Filter by creation date (before)

        Returns:
            List of matching assets
        """
        try:
            payload = {
                "type": "METADATA"
            }

            if original_file_name:
                payload["originalFileName"] = original_file_name
            if city:
                payload["city"] = city
            if state:
                payload["state"] = state
            if country:
                payload["country"] = country
            if created_after:
                payload["createdAfter"] = created_after.isoformat()
            if created_before:
                payload["createdBefore"] = created_before.isoformat()

            response = await self.client.post(
                f"{self.base_url}/api/search",
                headers=self._headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                assets = data.get("assets", {}).get("items", [])

                results = []
                for item in assets:
                    asset = item.get("data") or item
                    results.append(ImmichAsset(
                        id=asset.get("id"),
                        device_asset_id=asset.get("deviceAssetId"),
                        owner_id=asset.get("ownerId"),
                        device_id=asset.get("deviceId"),
                        type=asset.get("type"),
                        original_path=asset.get("originalPath"),
                        original_file_name=asset.get("originalFileName"),
                        is_favorite=asset.get("isFavorite", False),
                        is_archived=asset.get("isArchived", False),
                        duration=asset.get("duration"),
                        file_created_at=datetime.fromisoformat(asset.get("fileCreatedAt").replace("Z", "+00:00")),
                        file_modified_at=datetime.fromisoformat(asset.get("fileModifiedAt").replace("Z", "+00:00")),
                        updated_at=datetime.fromisoformat(asset.get("updatedAt").replace("Z", "+00:00")),
                        is_trashed=asset.get("isTrashed", False),
                        exif_info=asset.get("exifInfo"),
                        smart_info=asset.get("smartInfo")
                    ))

                return results
            return []

        except Exception as e:
            logger.error(f"Error searching by metadata: {e}")
            return []

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def upload_work_order_photo(
        self,
        work_order_id: str,
        photo_data: bytes,
        photo_name: str,
        photo_type: str = "general",
        is_before_photo: bool = False,
        is_after_photo: bool = False
    ) -> Optional[ImmichAsset]:
        """
        Upload a work order photo with standardized naming

        Args:
            work_order_id: Work order ID
            photo_data: Photo file bytes
            photo_name: Original photo name
            photo_type: Photo type (general, damage, repair, inspection)
            is_before_photo: Mark as before photo
            is_after_photo: Mark as after photo

        Returns:
            Uploaded asset or None on failure
        """
        device_asset_id = f"wo-{work_order_id}-{photo_type}-{datetime.now().timestamp()}"

        if is_before_photo:
            device_asset_id += "-before"
        elif is_after_photo:
            device_asset_id += "-after"

        return await self.upload_photo(
            file_data=photo_data,
            file_name=photo_name,
            device_asset_id=device_asset_id,
            device_id="somniproperty-work-orders"
        )

    async def create_work_order_album(
        self,
        work_order_id: str,
        work_order_title: str,
        unit_number: Optional[str] = None
    ) -> Optional[ImmichAlbum]:
        """
        Create an album for a work order

        Args:
            work_order_id: Work order ID
            work_order_title: Work order title
            unit_number: Unit number (optional)

        Returns:
            Created album or None on failure
        """
        album_name = f"WO-{work_order_id}"
        if unit_number:
            album_name += f" - Unit {unit_number}"

        description = f"Photos for work order: {work_order_title}"

        return await self.create_album(
            album_name=album_name,
            description=description
        )

    async def link_photos_to_work_order(
        self,
        work_order_id: str,
        asset_ids: List[str]
    ) -> bool:
        """
        Link photos to a work order album

        Args:
            work_order_id: Work order ID
            asset_ids: List of asset IDs

        Returns:
            True if successful, False otherwise
        """
        # Find or create album for work order
        albums = await self.list_albums()
        work_order_album = None

        for album in albums:
            if album.album_name.startswith(f"WO-{work_order_id}"):
                work_order_album = album
                break

        if not work_order_album:
            # Create album if it doesn't exist
            work_order_album = await self.create_album(
                album_name=f"WO-{work_order_id}",
                description=f"Photos for work order {work_order_id}"
            )

        if work_order_album and work_order_album.id:
            return await self.add_to_album(work_order_album.id, asset_ids)

        return False


# ========================================
# Singleton instance management
# ========================================

_immich_client: Optional[ImmichClient] = None


def get_immich_client(
    base_url: str = "http://immich.storage.svc.cluster.local",
    api_key: Optional[str] = None
) -> ImmichClient:
    """Get singleton Immich client instance"""
    global _immich_client
    if _immich_client is None:
        _immich_client = ImmichClient(base_url=base_url, api_key=api_key)
    return _immich_client


async def close_immich_client():
    """Close singleton Immich client"""
    global _immich_client
    if _immich_client:
        await _immich_client.close()
        _immich_client = None
