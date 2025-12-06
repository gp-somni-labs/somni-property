"""
Somni Property Manager - File Storage Service
Handles file uploads, processing, and storage for visual quote assets
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io

from fastapi import UploadFile, HTTPException


class FileStorageService:
    """Service for handling file uploads and storage"""

    def __init__(self, storage_backend: str = "local"):
        """
        Initialize file storage service

        Args:
            storage_backend: 'local', 's3', or 'minio'
        """
        self.storage_backend = storage_backend
        self.local_storage_path = Path("/app/storage/visual-assets")

        # Create storage directories if they don't exist
        if storage_backend == "local":
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
            (self.local_storage_path / "originals").mkdir(exist_ok=True)
            (self.local_storage_path / "thumbnails").mkdir(exist_ok=True)

    async def upload_visual_asset(
        self,
        file: UploadFile,
        quote_id: str,
        asset_type: str
    ) -> dict:
        """
        Upload and process a visual asset file

        Args:
            file: Uploaded file
            quote_id: UUID of the quote
            asset_type: Type of asset (floor_plan, implementation_photo, comparison_photo)

        Returns:
            dict: File metadata including URLs
        """
        # Validate file
        self._validate_file(file, asset_type)

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = self._get_file_extension(file.filename)
        filename = f"{file_id}{file_ext}"

        # Read file content
        content = await file.read()

        # Process based on file type
        if asset_type in ["implementation_photo", "comparison_photo"]:
            # Image processing
            original_url, thumbnail_url = await self._process_image(
                content, filename, quote_id, asset_type
            )
        elif asset_type == "floor_plan":
            # Floor plan processing (can be image or PDF)
            if file_ext.lower() == ".pdf":
                original_url = await self._store_pdf(content, filename, quote_id)
                thumbnail_url = await self._generate_pdf_thumbnail(content, filename, quote_id)
            else:
                original_url, thumbnail_url = await self._process_image(
                    content, filename, quote_id, asset_type
                )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown asset type: {asset_type}")

        # Return metadata
        return {
            "id": file_id,
            "filename": file.filename,
            "file_url": original_url,
            "thumbnail_url": thumbnail_url,
            "file_size": len(content),
            "content_type": file.content_type
        }

    async def _process_image(
        self,
        content: bytes,
        filename: str,
        quote_id: str,
        asset_type: str
    ) -> Tuple[str, str]:
        """
        Process image file: resize and generate thumbnail

        Returns:
            Tuple of (original_url, thumbnail_url)
        """
        # Open image
        image = Image.open(io.BytesIO(content))

        # Convert RGBA to RGB if needed (for JPEG)
        if image.mode == "RGBA":
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image

        # Resize original to max 1920px width
        max_width = 1920
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Save original
        original_path = self.local_storage_path / "originals" / quote_id / asset_type / filename
        original_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as JPEG with optimization
        if filename.lower().endswith(('.jpg', '.jpeg')):
            image.save(original_path, "JPEG", quality=85, optimize=True)
        else:
            image.save(original_path, "PNG", optimize=True)

        # Generate thumbnail (400px width)
        thumbnail = image.copy()
        thumb_width = 400
        if thumbnail.width > thumb_width:
            ratio = thumb_width / thumbnail.width
            new_height = int(thumbnail.height * ratio)
            thumbnail = thumbnail.resize((thumb_width, new_height), Image.Resampling.LANCZOS)

        # Save thumbnail
        thumb_filename = f"thumb_{filename}"
        if not thumb_filename.lower().endswith(('.jpg', '.jpeg')):
            thumb_filename = thumb_filename.rsplit('.', 1)[0] + '.jpg'

        thumbnail_path = self.local_storage_path / "thumbnails" / quote_id / asset_type / thumb_filename
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail.save(thumbnail_path, "JPEG", quality=75, optimize=True)

        # Generate URLs
        original_url = f"/storage/visual-assets/originals/{quote_id}/{asset_type}/{filename}"
        thumbnail_url = f"/storage/visual-assets/thumbnails/{quote_id}/{asset_type}/{thumb_filename}"

        return original_url, thumbnail_url

    async def _store_pdf(self, content: bytes, filename: str, quote_id: str) -> str:
        """Store PDF file"""
        pdf_path = self.local_storage_path / "originals" / quote_id / "floor_plan" / filename
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        with open(pdf_path, 'wb') as f:
            f.write(content)

        return f"/storage/visual-assets/originals/{quote_id}/floor_plan/{filename}"

    async def _generate_pdf_thumbnail(self, content: bytes, filename: str, quote_id: str) -> str:
        """Generate thumbnail from PDF first page"""
        try:
            from pdf2image import convert_from_bytes

            # Convert first page to image
            images = convert_from_bytes(content, first_page=1, last_page=1)
            if not images:
                raise Exception("Failed to convert PDF to image")

            first_page = images[0]

            # Generate thumbnail
            thumb_width = 400
            ratio = thumb_width / first_page.width
            new_height = int(first_page.height * ratio)
            thumbnail = first_page.resize((thumb_width, new_height), Image.Resampling.LANCZOS)

            # Save thumbnail
            thumb_filename = filename.rsplit('.', 1)[0] + '_thumb.jpg'
            thumbnail_path = self.local_storage_path / "thumbnails" / quote_id / "floor_plan" / thumb_filename
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            thumbnail.save(thumbnail_path, "JPEG", quality=75, optimize=True)

            return f"/storage/visual-assets/thumbnails/{quote_id}/floor_plan/{thumb_filename}"
        except ImportError:
            # pdf2image not available, return placeholder
            return "/static/pdf_placeholder.png"
        except Exception as e:
            print(f"Failed to generate PDF thumbnail: {e}")
            return "/static/pdf_placeholder.png"

    def _validate_file(self, file: UploadFile, asset_type: str):
        """Validate uploaded file"""
        # Check file size (10MB for images, 50MB for PDFs)
        max_size = 50 * 1024 * 1024 if asset_type == "floor_plan" else 10 * 1024 * 1024

        # Validate content type
        allowed_types = {
            "floor_plan": ["image/jpeg", "image/png", "application/pdf"],
            "implementation_photo": ["image/jpeg", "image/png"],
            "comparison_photo": ["image/jpeg", "image/png"]
        }

        if file.content_type not in allowed_types.get(asset_type, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types.get(asset_type, []))}"
            )

    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        if not filename:
            return ".jpg"

        ext = Path(filename).suffix
        if not ext:
            return ".jpg"

        return ext.lower()


# Singleton instance
_file_storage_service = None


def get_file_storage_service() -> FileStorageService:
    """Get or create file storage service instance"""
    global _file_storage_service
    if _file_storage_service is None:
        _file_storage_service = FileStorageService(storage_backend="local")
    return _file_storage_service
