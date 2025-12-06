"""
Client Media Service
Handles file uploads, downloads, thumbnail generation, and media management for client portfolios
"""

import uuid
import os
import logging
from typing import Optional, List, Dict, Any, BinaryIO, Tuple
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import mimetypes
import zipfile
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from fastapi import UploadFile, HTTPException

from db.models import ClientMedia as ClientMediaModel, Client
from api.schemas import (
    ClientMediaCreate,
    ClientMediaUpdate,
    ClientMedia,
    ClientMediaStatistics
)
from services.minio_client import MinIOClient
from PIL import Image
import magic

logger = logging.getLogger(__name__)


class ClientMediaService:
    """
    Service for managing client portfolio media files

    Responsibilities:
    - File upload and validation
    - MinIO storage integration
    - Thumbnail generation (images/videos)
    - Metadata extraction
    - Media queries and filtering
    - Bulk operations
    """

    # File size limits (in bytes)
    MAX_FILE_SIZE = {
        'photo': 50 * 1024 * 1024,      # 50 MB
        'video': 500 * 1024 * 1024,     # 500 MB
        'floorplan': 100 * 1024 * 1024, # 100 MB
        '3d_model': 500 * 1024 * 1024,  # 500 MB (increased for ZIP archives with textures)
        'document': 100 * 1024 * 1024,  # 100 MB
        'other': 50 * 1024 * 1024       # 50 MB
    }

    # Allowed file extensions by media type
    ALLOWED_EXTENSIONS = {
        'photo': {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif', '.heic', '.heif'},
        'video': {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.mpeg', '.mpg'},
        'floorplan': {'.pdf', '.dwg', '.dxf', '.svg', '.png', '.jpg', '.step', '.stp', '.iges', '.igs'},
        '3d_model': {'.glb', '.gltf', '.usdz', '.ply', '.3ds', '.obj', '.mtl', '.fbx', '.stl',
                     '.jpg', '.jpeg', '.png', '.webp',  # Texture files for 3D models
                     '.zip'},  # ZIP archives containing .obj + .mtl + textures
        'document': {'.pdf', '.doc', '.docx', '.txt', '.md'},
        'other': {'.zip', '.tar', '.gz', '.7z'}
    }

    # Thumbnail settings
    THUMBNAIL_SIZE = (400, 300)  # width x height
    THUMBNAIL_QUALITY = 85

    def __init__(self, db: AsyncSession):
        """Initialize service with database session"""
        self.db = db
        self.minio_client = MinIOClient()
        self.bucket_name = "client-media"
        self._magic = magic.Magic(mime=True)

    async def upload_media(
        self,
        client_id: uuid.UUID,
        file: UploadFile,
        media_type: str,
        media_category: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None
    ) -> ClientMediaModel:
        """
        Upload a media file for a client

        Args:
            client_id: Client UUID
            file: Uploaded file
            media_type: Type of media (photo, video, floorplan, 3d_model, document, other)
            media_category: Category (property_exterior, property_interior, etc.)
            title: Optional title
            description: Optional description
            tags: Optional tags list
            uploaded_by: Optional username/email of uploader

        Returns:
            Created ClientMedia model

        Raises:
            HTTPException: If validation fails or upload errors
        """
        logger.info(f"Uploading media for client {client_id}: {file.filename}")

        # Validate client exists
        client = await self._get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Read file data
        file_data = await file.read()
        file_size = len(file_data)

        # Validate file
        self._validate_file(file.filename, file_data, file_size, media_type)

        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        object_key = f"clients/{client_id}/{media_type}/{unique_filename}"

        # Detect MIME type
        mime_type = self._detect_mime_type(file_data, file.filename)

        # Handle ZIP files for 3D models specially
        if media_type == '3d_model' and file_ext == '.zip':
            return await self._upload_3d_model_zip(
                client_id=client_id,
                file_data=file_data,
                original_filename=file.filename,
                media_category=media_category,
                title=title,
                description=description,
                tags=tags,
                uploaded_by=uploaded_by
            )

        # Upload to MinIO
        try:
            await self.minio_client.upload_file(
                file_data=file_data,
                object_name=object_key,
                content_type=mime_type,
                metadata={
                    'client_id': str(client_id),
                    'media_type': media_type,
                    'original_filename': file.filename
                }
            )
        except Exception as e:
            logger.error(f"Failed to upload to MinIO: {e}")
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

        # Generate presigned URL for access
        minio_url = await self._generate_presigned_url(object_key)

        # Extract metadata based on media type
        metadata = await self._extract_metadata(file_data, media_type, mime_type)

        # Create database record
        media_data = ClientMediaCreate(
            client_id=client_id,
            media_type=media_type,
            media_category=media_category,
            file_name=unique_filename,
            original_file_name=file.filename,
            file_extension=file_ext,
            mime_type=mime_type,
            file_size_bytes=file_size,
            minio_bucket=self.bucket_name,
            minio_object_key=object_key,
            minio_url=minio_url,
            title=title or file.filename,
            description=description,
            tags=tags or [],
            uploaded_by=uploaded_by,
            upload_source='web_ui',
            **metadata
        )

        media_obj = ClientMediaModel(**media_data.model_dump())
        self.db.add(media_obj)
        await self.db.flush()
        await self.db.refresh(media_obj)

        # Generate thumbnail asynchronously if applicable
        if media_type in ('photo', 'video'):
            try:
                await self._generate_thumbnail(media_obj, file_data)
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail: {e}")

        logger.info(f"Media uploaded successfully: {media_obj.id}")
        return media_obj

    async def get_media(self, media_id: uuid.UUID) -> Optional[ClientMediaModel]:
        """Get media by ID"""
        query = select(ClientMediaModel).where(
            and_(
                ClientMediaModel.id == media_id,
                ClientMediaModel.deleted_at == None
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_client_media(
        self,
        client_id: uuid.UUID,
        media_type: Optional[str] = None,
        media_category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ClientMediaModel], int]:
        """
        List media for a client with filtering

        Returns:
            Tuple of (media_list, total_count)
        """
        # Build query
        query = select(ClientMediaModel).where(
            and_(
                ClientMediaModel.client_id == client_id,
                ClientMediaModel.deleted_at == None
            )
        )

        if media_type:
            query = query.where(ClientMediaModel.media_type == media_type)

        if media_category:
            query = query.where(ClientMediaModel.media_category == media_category)

        if tags:
            # Match any of the provided tags
            query = query.where(ClientMediaModel.tags.overlap(tags))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results, ordered by created_at desc
        query = query.order_by(ClientMediaModel.display_order, ClientMediaModel.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        media_list = result.scalars().all()

        # Generate download URLs through backend proxy (accessible from browser)
        for media in media_list:
            if media.minio_object_key:
                # Use backend proxy URL instead of direct MinIO presigned URL
                media.minio_url = f"/api/v1/clients/media/{media.id}/download"
            if media.thumbnail_minio_key:
                # Thumbnails also use proxy (could optimize later with dedicated endpoint)
                media.thumbnail_url = f"/api/v1/clients/media/{media.id}/download"

        return list(media_list), total

    async def update_media(
        self,
        media_id: uuid.UUID,
        update_data: ClientMediaUpdate
    ) -> ClientMediaModel:
        """Update media metadata"""
        media = await self.get_media(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(media, key, value)

        media.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(media)

        logger.info(f"Media updated: {media_id}")
        return media

    async def delete_media(self, media_id: uuid.UUID, hard_delete: bool = False) -> bool:
        """
        Delete media (soft delete by default)

        Args:
            media_id: Media UUID
            hard_delete: If True, permanently delete from DB and MinIO

        Returns:
            True if successful
        """
        media = await self.get_media(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        if hard_delete:
            # Delete from MinIO
            try:
                await self.minio_client.delete_object(media.minio_object_key)
                if media.thumbnail_minio_key:
                    await self.minio_client.delete_object(media.thumbnail_minio_key)
            except Exception as e:
                logger.error(f"Failed to delete from MinIO: {e}")

            # Delete from database
            await self.db.delete(media)
            logger.info(f"Media hard deleted: {media_id}")
        else:
            # Soft delete
            media.deleted_at = datetime.utcnow()
            await self.db.flush()
            logger.info(f"Media soft deleted: {media_id}")

        return True

    async def bulk_delete_media(
        self,
        media_ids: List[uuid.UUID],
        hard_delete: bool = False
    ) -> Tuple[int, List[uuid.UUID], Dict[str, str]]:
        """
        Bulk delete media files

        Returns:
            Tuple of (deleted_count, failed_ids, errors)
        """
        deleted_count = 0
        failed_ids = []
        errors = {}

        for media_id in media_ids:
            try:
                await self.delete_media(media_id, hard_delete)
                deleted_count += 1
            except Exception as e:
                failed_ids.append(media_id)
                errors[str(media_id)] = str(e)
                logger.error(f"Failed to delete media {media_id}: {e}")

        return deleted_count, failed_ids, errors

    async def get_media_statistics(self, client_id: uuid.UUID) -> ClientMediaStatistics:
        """Get statistics for client's media"""
        query = select(ClientMediaModel).where(
            and_(
                ClientMediaModel.client_id == client_id,
                ClientMediaModel.deleted_at == None
            )
        )
        result = await self.db.execute(query)
        all_media = result.scalars().all()

        total_size = sum(m.file_size_bytes for m in all_media)
        by_type = {}
        by_category = {}

        for media in all_media:
            by_type[media.media_type] = by_type.get(media.media_type, 0) + 1
            by_category[media.media_category] = by_category.get(media.media_category, 0) + 1

        return ClientMediaStatistics(
            total_files=len(all_media),
            total_size_bytes=total_size,
            total_size_mb=round(total_size / (1024 * 1024), 2),
            by_type=by_type,
            by_category=by_category,
            photos_count=by_type.get('photo', 0),
            videos_count=by_type.get('video', 0),
            floorplans_count=by_type.get('floorplan', 0),
            models_3d_count=by_type.get('3d_model', 0),
            documents_count=by_type.get('document', 0)
        )

    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================

    async def _get_client(self, client_id: uuid.UUID) -> Optional[Client]:
        """Get client by ID"""
        query = select(Client).where(Client.id == client_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _validate_file(
        self,
        filename: str,
        file_data: bytes,
        file_size: int,
        media_type: str
    ):
        """
        Validate file before upload

        Raises HTTPException if validation fails
        """
        # Check file size
        max_size = self.MAX_FILE_SIZE.get(media_type, self.MAX_FILE_SIZE['other'])
        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size for {media_type}: {max_size / (1024*1024):.1f} MB"
            )

        # Check file extension
        file_ext = Path(filename).suffix.lower()
        allowed_exts = self.ALLOWED_EXTENSIONS.get(media_type, set())
        if file_ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"File extension {file_ext} not allowed for {media_type}. Allowed: {', '.join(allowed_exts)}"
            )

    def _detect_mime_type(self, file_data: bytes, filename: str) -> str:
        """Detect MIME type from file data and filename"""
        try:
            mime_type = self._magic.from_buffer(file_data)
            return mime_type
        except Exception as e:
            logger.warning(f"Failed to detect MIME type with magic: {e}")
            # Fallback to mimetypes library
            mime_type, _ = mimetypes.guess_type(filename)
            return mime_type or "application/octet-stream"

    async def _extract_metadata(
        self,
        file_data: bytes,
        media_type: str,
        mime_type: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from file based on type

        Returns dict with width, height, duration, etc.
        """
        metadata = {}

        try:
            if media_type == 'photo' and mime_type.startswith('image/'):
                # Extract image dimensions using Pillow
                image = Image.open(BytesIO(file_data))
                metadata['width'] = image.width
                metadata['height'] = image.height
                logger.debug(f"Extracted image dimensions: {image.width}x{image.height}")

            elif media_type == 'video':
                # Video metadata extraction would require ffmpeg/opencv
                # For now, we'll skip video metadata extraction
                # TODO: Add ffmpeg integration for video metadata
                pass

            elif media_type == 'floorplan' and mime_type == 'application/pdf':
                # PDF page count extraction
                # TODO: Add PyPDF2 integration for PDF metadata
                pass

            elif media_type == '3d_model':
                # 3D model metadata extraction
                # TODO: Add trimesh integration for 3D model metadata
                pass

        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")

        return metadata

    async def _generate_thumbnail(
        self,
        media: ClientMediaModel,
        file_data: bytes
    ):
        """Generate thumbnail for image or video"""
        try:
            if media.media_type == 'photo':
                # Generate image thumbnail
                image = Image.open(BytesIO(file_data))

                # Convert to RGB if necessary (for PNG with transparency, etc.)
                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')

                # Create thumbnail
                image.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # Save to bytes
                thumbnail_bytes = BytesIO()
                image.save(thumbnail_bytes, format='JPEG', quality=self.THUMBNAIL_QUALITY, optimize=True)
                thumbnail_bytes.seek(0)

                # Upload thumbnail to MinIO
                thumbnail_key = f"{media.minio_object_key}_thumb.jpg"
                await self.minio_client.upload_file(
                    file_data=thumbnail_bytes.getvalue(),
                    object_name=thumbnail_key,
                    content_type='image/jpeg'
                )

                # Update media record
                media.thumbnail_minio_key = thumbnail_key
                media.thumbnail_url = await self._generate_presigned_url(thumbnail_key)
                media.thumbnail_generated = True

                logger.info(f"Thumbnail generated: {thumbnail_key}")

            elif media.media_type == 'video':
                # Video thumbnail generation would require ffmpeg
                # TODO: Add ffmpeg integration for video thumbnails
                pass

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            raise

    async def _generate_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """Generate presigned URL for MinIO object"""
        try:
            url = await self.minio_client.get_presigned_url(
                object_name=object_key,
                expiry=timedelta(seconds=expires)
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return ""

    async def _upload_3d_model_zip(
        self,
        client_id: uuid.UUID,
        file_data: bytes,
        original_filename: str,
        media_category: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None
    ) -> ClientMediaModel:
        """
        Extract and upload 3D model from ZIP archive

        Expected structure:
        - model.obj (or any .obj file)
        - model.mtl (or any .mtl file)
        - textures/*.jpg, *.png, etc.

        Args:
            client_id: Client UUID
            file_data: ZIP file bytes
            original_filename: Original ZIP filename
            media_category: Category
            title: Optional title
            description: Optional description
            tags: Optional tags
            uploaded_by: Optional uploader

        Returns:
            Created ClientMedia model for the .obj file (with metadata linking to .mtl and textures)
        """
        logger.info(f"Extracting 3D model ZIP for client {client_id}: {original_filename}")

        try:
            # Extract ZIP
            zip_buffer = BytesIO(file_data)
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                # Find .obj, .mtl, and texture files
                obj_file = None
                mtl_file = None
                texture_files = []

                for file_info in zip_file.filelist:
                    filename = file_info.filename.lower()

                    # Skip directories and hidden files
                    if file_info.is_dir() or filename.startswith('.') or '/__MACOSX' in filename:
                        continue

                    if filename.endswith('.obj'):
                        obj_file = file_info.filename
                    elif filename.endswith('.mtl'):
                        mtl_file = file_info.filename
                    elif any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tga']):
                        texture_files.append(file_info.filename)

                if not obj_file:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP archive must contain at least one .obj file"
                    )

                # Generate unique directory for this model
                model_id = str(uuid.uuid4())
                base_path = f"clients/{client_id}/3d_model/{model_id}"

                # Upload .obj file
                obj_data = zip_file.read(obj_file)
                obj_key = f"{base_path}/{Path(obj_file).name}"
                await self.minio_client.upload_file(
                    file_data=obj_data,
                    object_name=obj_key,
                    content_type='model/obj',
                    metadata={
                        'client_id': str(client_id),
                        'media_type': '3d_model',
                        'original_filename': original_filename
                    }
                )

                # Upload .mtl file if present
                mtl_key = None
                if mtl_file:
                    mtl_data = zip_file.read(mtl_file)
                    mtl_key = f"{base_path}/{Path(mtl_file).name}"
                    await self.minio_client.upload_file(
                        file_data=mtl_data,
                        object_name=mtl_key,
                        content_type='model/mtl',
                        metadata={
                            'client_id': str(client_id),
                            'media_type': '3d_model',
                            'related_obj': obj_key
                        }
                    )

                # Upload texture files
                texture_keys = []
                for texture_file in texture_files:
                    texture_data = zip_file.read(texture_file)
                    texture_ext = Path(texture_file).suffix.lower()

                    # Determine MIME type
                    texture_mime = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.webp': 'image/webp',
                        '.bmp': 'image/bmp',
                        '.tga': 'image/tga'
                    }.get(texture_ext, 'application/octet-stream')

                    # Preserve directory structure for textures
                    texture_key = f"{base_path}/{texture_file}"
                    await self.minio_client.upload_file(
                        file_data=texture_data,
                        object_name=texture_key,
                        content_type=texture_mime,
                        metadata={
                            'client_id': str(client_id),
                            'media_type': '3d_model_texture',
                            'related_obj': obj_key
                        }
                    )
                    texture_keys.append(texture_key)

                logger.info(
                    f"Uploaded 3D model: {obj_key}, "
                    f"MTL: {mtl_key or 'none'}, "
                    f"Textures: {len(texture_keys)}"
                )

        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        except Exception as e:
            logger.error(f"Failed to extract 3D model ZIP: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process 3D model ZIP: {str(e)}")

        # Generate presigned URL for the .obj file
        minio_url = await self._generate_presigned_url(obj_key)

        # Create database record for the .obj file with metadata about related files
        additional_metadata = {
            'mtl_file': mtl_key,
            'texture_files': texture_keys,
            'model_id': model_id,
            'base_path': base_path
        }

        media_data = ClientMediaCreate(
            client_id=client_id,
            media_type='3d_model',
            media_category=media_category,
            file_name=f"{model_id}/{Path(obj_file).name}",
            original_file_name=original_filename,
            file_extension='.obj',
            mime_type='model/obj',
            file_size_bytes=len(obj_data),
            minio_bucket=self.bucket_name,
            minio_object_key=obj_key,
            minio_url=minio_url,
            title=title or Path(obj_file).stem,
            description=description,
            tags=tags or [],
            uploaded_by=uploaded_by,
            upload_source='web_ui',
            metadata_json=json.dumps(additional_metadata)
        )

        media_obj = ClientMediaModel(**media_data.model_dump())
        self.db.add(media_obj)
        await self.db.flush()
        await self.db.refresh(media_obj)

        logger.info(f"3D model uploaded successfully: {media_obj.id}")
        return media_obj


# Singleton instance
_client_media_service: Optional[ClientMediaService] = None


def get_client_media_service(db: AsyncSession) -> ClientMediaService:
    """Get or create ClientMediaService instance"""
    return ClientMediaService(db)
