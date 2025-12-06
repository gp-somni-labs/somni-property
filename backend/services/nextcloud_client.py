"""
Nextcloud Integration Client for SomniProperty

Integrates with self-hosted Nextcloud (file storage and collaboration) for:
- Document storage and organization
- File sharing and collaboration
- Property document management
- Tenant file portals
- Contract and lease storage
- Work order photo attachments
- WebDAV file operations

Nextcloud Service: nextcloud.storage.svc.cluster.local
Documentation: https://docs.nextcloud.com/
API Docs: https://docs.nextcloud.com/server/latest/developer_manual/client_apis/
WebDAV: https://docs.nextcloud.com/server/latest/developer_manual/client_apis/WebDAV/
"""

import logging
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import datetime
from enum import Enum
import httpx
from pydantic import BaseModel
import xml.etree.ElementTree as ET
from urllib.parse import quote

logger = logging.getLogger(__name__)


class ShareType(Enum):
    """Nextcloud share types"""
    USER = 0
    GROUP = 1
    PUBLIC_LINK = 3
    EMAIL = 4
    FEDERATED_CLOUD = 6
    CIRCLE = 7
    TALK_CONVERSATION = 10


class SharePermission(Enum):
    """Nextcloud share permissions"""
    READ = 1
    UPDATE = 2
    CREATE = 4
    DELETE = 8
    SHARE = 16
    ALL = 31  # READ + UPDATE + CREATE + DELETE + SHARE


class FileType(Enum):
    """File types"""
    FILE = "file"
    DIRECTORY = "directory"


class NextcloudFile(BaseModel):
    """Nextcloud file/folder model"""
    path: str
    name: str
    file_type: str  # "file" or "directory"
    size: int = 0
    modified: Optional[datetime] = None
    etag: Optional[str] = None
    content_type: Optional[str] = None


class NextcloudShare(BaseModel):
    """Nextcloud share model"""
    id: Optional[int] = None
    share_type: int
    share_with: Optional[str] = None  # User/group ID or email
    path: str
    permissions: int = SharePermission.READ.value
    token: Optional[str] = None  # For public links
    url: Optional[str] = None  # Public link URL
    expiration: Optional[datetime] = None


class NextcloudClient:
    """Client for interacting with Nextcloud API"""

    def __init__(
        self,
        base_url: str = "http://nextcloud.storage.svc.cluster.local",
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 60
    ):
        """
        Initialize Nextcloud client

        Args:
            base_url: Nextcloud service URL
            username: Nextcloud username
            password: Nextcloud password (or app password)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

        # WebDAV endpoint
        self.webdav_url = f"{self.base_url}/remote.php/dav/files/{username}"
        # OCS API endpoint
        self.ocs_url = f"{self.base_url}/ocs/v2.php"

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _auth(self) -> Optional[tuple]:
        """Get HTTP basic authentication tuple"""
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def _headers(self, ocs: bool = False) -> Dict[str, str]:
        """
        Get request headers

        Args:
            ocs: If True, add OCS API format header
        """
        headers = {
            "Accept": "application/json" if ocs else "application/xml",
        }
        if ocs:
            headers["OCS-APIRequest"] = "true"
        return headers

    # ========================================
    # WebDAV File Operations
    # ========================================

    async def create_folder(self, path: str) -> bool:
        """
        Create a folder in Nextcloud

        Use for:
        - Property folders (e.g., "/Properties/Sunset Apartments")
        - Unit folders (e.g., "/Properties/Sunset Apartments/Unit 204")
        - Document categories (e.g., "/Documents/Leases", "/Documents/Work Orders")

        Args:
            path: Folder path (e.g., "/Properties/Sunset Apartments")

        Returns:
            True if successful, False otherwise
        """
        try:
            folder_url = f"{self.webdav_url}/{quote(path.lstrip('/'))}"

            response = await self.client.request(
                method="MKCOL",
                url=folder_url,
                auth=self._auth()
            )

            if response.status_code in [201, 405]:  # 201 Created, 405 if already exists
                logger.info(f"Folder created/exists: {path}")
                return True
            else:
                logger.error(f"Failed to create folder: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return False

    async def upload_file(
        self,
        local_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        remote_path: str = "",
        content_type: Optional[str] = None
    ) -> bool:
        """
        Upload a file to Nextcloud

        Use for:
        - Lease documents
        - Work order photos
        - Tenant-submitted documents
        - Property inspection reports

        Args:
            local_path: Local file path to upload
            file_content: File content as bytes (alternative to local_path)
            remote_path: Remote path in Nextcloud (e.g., "/Documents/lease-2024.pdf")
            content_type: MIME type (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read file content
            if file_content is None:
                if local_path is None:
                    logger.error("Either local_path or file_content must be provided")
                    return False
                with open(local_path, 'rb') as f:
                    file_content = f.read()

            file_url = f"{self.webdav_url}/{quote(remote_path.lstrip('/'))}"

            headers = {}
            if content_type:
                headers["Content-Type"] = content_type

            response = await self.client.put(
                url=file_url,
                content=file_content,
                auth=self._auth(),
                headers=headers
            )

            if response.status_code in [201, 204]:  # 201 Created, 204 Updated
                logger.info(f"File uploaded: {remote_path}")
                return True
            else:
                logger.error(f"Failed to upload file: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False

    async def download_file(self, remote_path: str) -> Optional[bytes]:
        """
        Download a file from Nextcloud

        Args:
            remote_path: Remote file path (e.g., "/Documents/lease-2024.pdf")

        Returns:
            File content as bytes or None on failure
        """
        try:
            file_url = f"{self.webdav_url}/{quote(remote_path.lstrip('/'))}"

            response = await self.client.get(
                url=file_url,
                auth=self._auth()
            )

            if response.status_code == 200:
                logger.info(f"File downloaded: {remote_path}")
                return response.content
            else:
                logger.error(f"Failed to download file: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None

    async def list_files(
        self,
        path: str = "/",
        depth: int = 1
    ) -> List[NextcloudFile]:
        """
        List files in a directory

        Args:
            path: Directory path (e.g., "/Properties/Sunset Apartments")
            depth: Depth of listing (1 = immediate children, infinity = recursive)

        Returns:
            List of files and folders
        """
        try:
            folder_url = f"{self.webdav_url}/{quote(path.lstrip('/'))}"

            # WebDAV PROPFIND request
            propfind_body = '''<?xml version="1.0" encoding="UTF-8"?>
            <d:propfind xmlns:d="DAV:">
                <d:prop>
                    <d:resourcetype/>
                    <d:getcontentlength/>
                    <d:getcontenttype/>
                    <d:getlastmodified/>
                    <d:getetag/>
                </d:prop>
            </d:propfind>'''

            response = await self.client.request(
                method="PROPFIND",
                url=folder_url,
                content=propfind_body,
                auth=self._auth(),
                headers={"Depth": str(depth)}
            )

            if response.status_code == 207:  # Multi-Status
                return self._parse_propfind_response(response.text, path)
            else:
                logger.error(f"Failed to list files: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def _parse_propfind_response(self, xml_text: str, base_path: str) -> List[NextcloudFile]:
        """Parse WebDAV PROPFIND XML response"""
        files = []

        try:
            # Parse XML with namespace handling
            root = ET.fromstring(xml_text)
            namespaces = {
                'd': 'DAV:',
                'oc': 'http://owncloud.org/ns'
            }

            for response in root.findall('.//d:response', namespaces):
                href = response.find('d:href', namespaces)
                if href is None:
                    continue

                path = href.text

                # Skip the base directory itself
                if path.rstrip('/').endswith(base_path.rstrip('/')):
                    continue

                propstat = response.find('.//d:propstat', namespaces)
                if propstat is None:
                    continue

                prop = propstat.find('d:prop', namespaces)
                if prop is None:
                    continue

                # Determine file type
                resourcetype = prop.find('d:resourcetype', namespaces)
                is_collection = resourcetype is not None and len(list(resourcetype)) > 0
                file_type = FileType.DIRECTORY.value if is_collection else FileType.FILE.value

                # Get file properties
                size_elem = prop.find('d:getcontentlength', namespaces)
                size = int(size_elem.text) if size_elem is not None and size_elem.text else 0

                content_type_elem = prop.find('d:getcontenttype', namespaces)
                content_type = content_type_elem.text if content_type_elem is not None else None

                etag_elem = prop.find('d:getetag', namespaces)
                etag = etag_elem.text if etag_elem is not None else None

                # Extract filename from path
                name = path.rstrip('/').split('/')[-1]

                files.append(NextcloudFile(
                    path=path,
                    name=name,
                    file_type=file_type,
                    size=size,
                    content_type=content_type,
                    etag=etag
                ))

            return files

        except Exception as e:
            logger.error(f"Error parsing PROPFIND response: {e}")
            return []

    async def delete_file(self, path: str) -> bool:
        """
        Delete a file or folder

        Args:
            path: File/folder path (e.g., "/Documents/old-lease.pdf")

        Returns:
            True if successful, False otherwise
        """
        try:
            file_url = f"{self.webdav_url}/{quote(path.lstrip('/'))}"

            response = await self.client.delete(
                url=file_url,
                auth=self._auth()
            )

            if response.status_code == 204:
                logger.info(f"File deleted: {path}")
                return True
            else:
                logger.error(f"Failed to delete file: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    async def move_file(self, source_path: str, destination_path: str) -> bool:
        """
        Move or rename a file

        Args:
            source_path: Source file path
            destination_path: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            source_url = f"{self.webdav_url}/{quote(source_path.lstrip('/'))}"
            dest_url = f"{self.webdav_url}/{quote(destination_path.lstrip('/'))}"

            response = await self.client.request(
                method="MOVE",
                url=source_url,
                auth=self._auth(),
                headers={"Destination": dest_url}
            )

            if response.status_code in [201, 204]:
                logger.info(f"File moved: {source_path} -> {destination_path}")
                return True
            else:
                logger.error(f"Failed to move file: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False

    async def copy_file(self, source_path: str, destination_path: str) -> bool:
        """
        Copy a file

        Args:
            source_path: Source file path
            destination_path: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            source_url = f"{self.webdav_url}/{quote(source_path.lstrip('/'))}"
            dest_url = f"{self.webdav_url}/{quote(destination_path.lstrip('/'))}"

            response = await self.client.request(
                method="COPY",
                url=source_url,
                auth=self._auth(),
                headers={"Destination": dest_url}
            )

            if response.status_code in [201, 204]:
                logger.info(f"File copied: {source_path} -> {destination_path}")
                return True
            else:
                logger.error(f"Failed to copy file: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False

    # ========================================
    # OCS Sharing API
    # ========================================

    async def share_file(
        self,
        path: str,
        share_type: ShareType,
        share_with: Optional[str] = None,
        permissions: SharePermission = SharePermission.READ,
        password: Optional[str] = None,
        expiration_date: Optional[datetime] = None
    ) -> Optional[NextcloudShare]:
        """
        Share a file or folder

        Use for:
        - Sharing lease documents with tenants
        - Creating public links for work order photos
        - Sharing property documents with contractors

        Args:
            path: File/folder path to share
            share_type: Type of share (USER, GROUP, PUBLIC_LINK, etc.)
            share_with: User ID, group ID, or email (not needed for public links)
            permissions: Share permissions
            password: Password protection (for public links)
            expiration_date: Share expiration date

        Returns:
            Created share or None on failure
        """
        try:
            payload = {
                "path": path,
                "shareType": share_type.value,
                "permissions": permissions.value
            }

            if share_with:
                payload["shareWith"] = share_with
            if password:
                payload["password"] = password
            if expiration_date:
                payload["expireDate"] = expiration_date.strftime("%Y-%m-%d")

            response = await self.client.post(
                f"{self.ocs_url}/apps/files_sharing/api/v1/shares",
                auth=self._auth(),
                headers=self._headers(ocs=True),
                params={"format": "json"},
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                share_data = data.get("ocs", {}).get("data", {})

                return NextcloudShare(
                    id=share_data.get("id"),
                    share_type=share_data.get("share_type"),
                    share_with=share_data.get("share_with"),
                    path=share_data.get("path"),
                    permissions=share_data.get("permissions"),
                    token=share_data.get("token"),
                    url=share_data.get("url")
                )
            else:
                logger.error(f"Failed to create share: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating share: {e}")
            return None

    async def get_shares(self, path: Optional[str] = None) -> List[NextcloudShare]:
        """
        Get shares for a file/folder or all shares

        Args:
            path: File/folder path (None = all shares)

        Returns:
            List of shares
        """
        try:
            params = {"format": "json"}
            if path:
                params["path"] = path

            response = await self.client.get(
                f"{self.ocs_url}/apps/files_sharing/api/v1/shares",
                auth=self._auth(),
                headers=self._headers(ocs=True),
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                shares_data = data.get("ocs", {}).get("data", [])

                return [
                    NextcloudShare(
                        id=share.get("id"),
                        share_type=share.get("share_type"),
                        share_with=share.get("share_with"),
                        path=share.get("path"),
                        permissions=share.get("permissions"),
                        token=share.get("token"),
                        url=share.get("url")
                    )
                    for share in shares_data
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting shares: {e}")
            return []

    async def delete_share(self, share_id: int) -> bool:
        """
        Delete a share

        Args:
            share_id: Share ID

        Returns:
            True if successful, False otherwise
        """
        try:
            response = await self.client.delete(
                f"{self.ocs_url}/apps/files_sharing/api/v1/shares/{share_id}",
                auth=self._auth(),
                headers=self._headers(ocs=True),
                params={"format": "json"}
            )

            if response.status_code == 200:
                logger.info(f"Share deleted: {share_id}")
                return True
            else:
                logger.error(f"Failed to delete share: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error deleting share: {e}")
            return False

    # ========================================
    # SomniProperty Integration Helpers
    # ========================================

    async def setup_property_structure(self, property_name: str) -> bool:
        """
        Create folder structure for a property

        Creates:
        - /Properties/{property_name}/
        - /Properties/{property_name}/Leases/
        - /Properties/{property_name}/Work Orders/
        - /Properties/{property_name}/Inspections/
        - /Properties/{property_name}/Financial/
        - /Properties/{property_name}/Photos/

        Args:
            property_name: Property name

        Returns:
            True if successful, False otherwise
        """
        base_path = f"/Properties/{property_name}"
        folders = [
            base_path,
            f"{base_path}/Leases",
            f"{base_path}/Work Orders",
            f"{base_path}/Inspections",
            f"{base_path}/Financial",
            f"{base_path}/Photos"
        ]

        for folder in folders:
            if not await self.create_folder(folder):
                return False

        logger.info(f"Property structure created: {property_name}")
        return True

    async def upload_work_order_photo(
        self,
        property_name: str,
        work_order_id: str,
        photo_content: bytes,
        photo_name: str
    ) -> Optional[str]:
        """
        Upload a work order photo

        Args:
            property_name: Property name
            work_order_id: Work order ID
            photo_content: Photo content as bytes
            photo_name: Photo filename

        Returns:
            Remote file path or None on failure
        """
        remote_path = f"/Properties/{property_name}/Work Orders/{work_order_id}_{photo_name}"

        if await self.upload_file(file_content=photo_content, remote_path=remote_path):
            return remote_path
        return None

    async def share_lease_with_tenant(
        self,
        lease_path: str,
        tenant_email: str,
        expiration_days: Optional[int] = None
    ) -> Optional[str]:
        """
        Share a lease document with a tenant via email

        Args:
            lease_path: Path to lease document
            tenant_email: Tenant email
            expiration_days: Days until share expires (None = no expiration)

        Returns:
            Share URL or None on failure
        """
        expiration = None
        if expiration_days:
            from datetime import timedelta
            expiration = datetime.now() + timedelta(days=expiration_days)

        share = await self.share_file(
            path=lease_path,
            share_type=ShareType.EMAIL,
            share_with=tenant_email,
            permissions=SharePermission.READ,
            expiration_date=expiration
        )

        return share.url if share else None

    async def create_public_link(
        self,
        path: str,
        password: Optional[str] = None,
        expiration_days: int = 7
    ) -> Optional[str]:
        """
        Create a public link for a file/folder

        Use for sharing work order photos or documents with contractors

        Args:
            path: File/folder path
            password: Optional password protection
            expiration_days: Days until link expires

        Returns:
            Public link URL or None on failure
        """
        from datetime import timedelta
        expiration = datetime.now() + timedelta(days=expiration_days)

        share = await self.share_file(
            path=path,
            share_type=ShareType.PUBLIC_LINK,
            permissions=SharePermission.READ,
            password=password,
            expiration_date=expiration
        )

        return share.url if share else None


# ========================================
# Singleton instance management
# ========================================

_nextcloud_client: Optional[NextcloudClient] = None


def get_nextcloud_client(
    base_url: str = "http://nextcloud.storage.svc.cluster.local",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> NextcloudClient:
    """Get singleton Nextcloud client instance"""
    global _nextcloud_client
    if _nextcloud_client is None:
        _nextcloud_client = NextcloudClient(
            base_url=base_url,
            username=username,
            password=password
        )
    return _nextcloud_client


async def close_nextcloud_client():
    """Close singleton Nextcloud client"""
    global _nextcloud_client
    if _nextcloud_client:
        await _nextcloud_client.close()
        _nextcloud_client = None
