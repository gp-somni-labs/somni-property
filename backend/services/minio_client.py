"""
MinIO Client Service
Object storage for documents, images, and files
"""

from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
import logging
from datetime import timedelta
from io import BytesIO
import uuid

from core.config import settings

logger = logging.getLogger(__name__)


class MinIOClient:
    """
    MinIO client for object storage

    Handles:
    - Document uploads (PDFs, images, etc.)
    - Signed documents from DocuSeal
    - Work order attachments
    - Tenant-uploaded files
    - Automatic bucket creation and management
    """

    def __init__(self):
        """Initialize MinIO client"""
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )

        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._bucket_checked = False

        logger.info(f"MinIO client initialized: {settings.MINIO_ENDPOINT}/{self.bucket_name}")

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist (called lazily on first use)"""
        if self._bucket_checked:
            return

        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.debug(f"MinIO bucket exists: {self.bucket_name}")
            self._bucket_checked = True
        except S3Error as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise

    async def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to MinIO

        Args:
            file_data: File bytes to upload
            object_name: Object name/path in MinIO (e.g., "documents/lease_123.pdf")
            content_type: MIME type of the file
            metadata: Additional metadata to store with the object

        Returns:
            Object key/path in MinIO
        """
        try:
            # Ensure bucket exists before upload
            self._ensure_bucket()

            # Convert bytes to BytesIO stream
            file_stream = BytesIO(file_data)
            file_size = len(file_data)

            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_stream,
                length=file_size,
                content_type=content_type,
                metadata=metadata or {}
            )

            logger.info(f"Uploaded file to MinIO: {object_name} ({file_size} bytes)")
            return object_name

        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise

    async def upload_document(
        self,
        file_data: bytes,
        document_type: str,
        filename: str,
        content_type: str = "application/pdf",
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a document with auto-generated path

        Args:
            file_data: File bytes
            document_type: Type of document (lease, work_order, invoice, etc.)
            filename: Original filename
            content_type: MIME type
            metadata: Additional metadata

        Returns:
            Object key in MinIO
        """
        # Generate unique object name
        unique_id = str(uuid.uuid4())
        object_name = f"documents/{document_type}/{unique_id}/{filename}"

        return await self.upload_file(
            file_data=file_data,
            object_name=object_name,
            content_type=content_type,
            metadata=metadata
        )

    async def download_file(self, object_name: str) -> bytes:
        """
        Download a file from MinIO

        Args:
            object_name: Object key/path in MinIO

        Returns:
            File bytes
        """
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            file_data = response.read()
            response.close()
            response.release_conn()

            logger.info(f"Downloaded file from MinIO: {object_name}")
            return file_data

        except S3Error as e:
            logger.error(f"Failed to download file from MinIO: {e}")
            raise

    async def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO

        Args:
            object_name: Object key/path in MinIO

        Returns:
            True if successful
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted file from MinIO: {object_name}")
            return True

        except S3Error as e:
            logger.error(f"Failed to delete file from MinIO: {e}")
            return False

    async def get_presigned_url(
        self,
        object_name: str,
        expiry: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Get a presigned URL for temporary file access

        Args:
            object_name: Object key/path in MinIO
            expiry: URL expiration time

        Returns:
            Presigned URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expiry
            )

            logger.info(f"Generated presigned URL for: {object_name}")
            return url

        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    async def list_files(self, prefix: str = "") -> list:
        """
        List files in MinIO with optional prefix

        Args:
            prefix: Object name prefix to filter (e.g., "documents/lease/")

        Returns:
            List of object metadata
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )

            file_list = []
            for obj in objects:
                file_list.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag
                })

            logger.info(f"Listed {len(file_list)} files with prefix: {prefix}")
            return file_list

        except S3Error as e:
            logger.error(f"Failed to list files in MinIO: {e}")
            return []

    async def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO

        Args:
            object_name: Object key/path in MinIO

        Returns:
            True if file exists
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False


# Global MinIO client instance
minio_client = MinIOClient()


async def get_minio_client() -> MinIOClient:
    """Dependency to get MinIO client instance"""
    return minio_client
