"""
InvoiceNinja Products API Endpoints

Provides a proxy layer between SomniProperty frontend and InvoiceNinja Products API.
Implements caching to reduce API calls and improve performance.

Architecture:
- InvoiceNinja = Source of Truth for customer-facing products
- Redis caching with 5-minute TTL
- Admin-only create/update/delete operations
- Read operations available to all authenticated users
"""

import json
import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from core.auth import get_auth_user, require_manager, AuthUser
from services.invoiceninja_client import get_invoiceninja_client, Product
from services.redis_service import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])

# Cache configuration
CACHE_PREFIX = "invoiceninja:products"
CACHE_TTL = 300  # 5 minutes


# Response Models
class ProductResponse(BaseModel):
    """Product response model for API"""
    id: str
    product_key: str
    notes: str
    cost: Decimal
    price: Decimal
    quantity: Decimal = Decimal("1.0")
    tax_name1: Optional[str] = None
    tax_rate1: Optional[Decimal] = None
    tax_name2: Optional[str] = None
    tax_rate2: Optional[Decimal] = None
    custom_value1: Optional[str] = None
    custom_value2: Optional[str] = None
    custom_value3: Optional[str] = None
    custom_value4: Optional[str] = None
    is_deleted: bool = False

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Product list response with pagination"""
    total: int
    page: int
    per_page: int
    total_pages: int
    products: List[ProductResponse]


class ProductCreateRequest(BaseModel):
    """Request model for creating a product"""
    product_key: str = Field(..., min_length=1, max_length=100)
    notes: str = Field(..., min_length=1, max_length=1000)
    cost: Decimal = Field(default=Decimal("0.0"), ge=0)
    price: Decimal = Field(default=Decimal("0.0"), ge=0)
    quantity: Decimal = Field(default=Decimal("1.0"), gt=0)
    tax_name1: Optional[str] = None
    tax_rate1: Optional[Decimal] = Field(default=None, ge=0, le=100)
    tax_name2: Optional[str] = None
    tax_rate2: Optional[Decimal] = Field(default=None, ge=0, le=100)
    custom_value1: Optional[str] = None
    custom_value2: Optional[str] = None
    custom_value3: Optional[str] = None
    custom_value4: Optional[str] = None


class ProductUpdateRequest(BaseModel):
    """Request model for updating a product"""
    product_key: Optional[str] = Field(default=None, min_length=1, max_length=100)
    notes: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    cost: Optional[Decimal] = Field(default=None, ge=0)
    price: Optional[Decimal] = Field(default=None, ge=0)
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    tax_name1: Optional[str] = None
    tax_rate1: Optional[Decimal] = Field(default=None, ge=0, le=100)
    tax_name2: Optional[str] = None
    tax_rate2: Optional[Decimal] = Field(default=None, ge=0, le=100)
    custom_value1: Optional[str] = None
    custom_value2: Optional[str] = None
    custom_value3: Optional[str] = None
    custom_value4: Optional[str] = None


# Helper Functions
async def get_cached_product(product_id: str) -> Optional[Dict[str, Any]]:
    """Get product from Redis cache"""
    try:
        redis = await get_redis()
        if redis is None:
            return None

        cache_key = f"{CACHE_PREFIX}:{product_id}"
        cached = await redis.get(cache_key)

        if cached:
            logger.debug(f"Cache HIT for product {product_id}")
            return json.loads(cached)

        logger.debug(f"Cache MISS for product {product_id}")
        return None
    except Exception as e:
        logger.error(f"Redis cache get error: {e}")
        return None


async def set_cached_product(product_id: str, product_data: Dict[str, Any]):
    """Set product in Redis cache"""
    try:
        redis = await get_redis()
        if redis is None:
            return

        cache_key = f"{CACHE_PREFIX}:{product_id}"
        await redis.setex(
            cache_key,
            CACHE_TTL,
            json.dumps(product_data, default=str)
        )
        logger.debug(f"Cached product {product_id} for {CACHE_TTL}s")
    except Exception as e:
        logger.error(f"Redis cache set error: {e}")


async def invalidate_product_cache(product_id: Optional[str] = None):
    """Invalidate product cache (specific product or entire list)"""
    try:
        redis = await get_redis()
        if redis is None:
            return

        if product_id:
            # Invalidate specific product
            cache_key = f"{CACHE_PREFIX}:{product_id}"
            await redis.delete(cache_key)
            logger.info(f"Invalidated cache for product {product_id}")

        # Always invalidate the list cache
        list_cache_key = f"{CACHE_PREFIX}:list"
        await redis.delete(list_cache_key)
        logger.info("Invalidated product list cache")
    except Exception as e:
        logger.error(f"Redis cache invalidation error: {e}")


def convert_product_to_response(product_data: Dict[str, Any]) -> ProductResponse:
    """Convert InvoiceNinja product data to response model"""
    return ProductResponse(
        id=product_data.get('id', ''),
        product_key=product_data.get('product_key', ''),
        notes=product_data.get('notes', ''),
        cost=Decimal(str(product_data.get('cost', 0))),
        price=Decimal(str(product_data.get('price', 0))),
        quantity=Decimal(str(product_data.get('quantity', 1.0))),
        tax_name1=product_data.get('tax_name1'),
        tax_rate1=Decimal(str(product_data['tax_rate1'])) if product_data.get('tax_rate1') else None,
        tax_name2=product_data.get('tax_name2'),
        tax_rate2=Decimal(str(product_data['tax_rate2'])) if product_data.get('tax_rate2') else None,
        custom_value1=product_data.get('custom_value1'),
        custom_value2=product_data.get('custom_value2'),
        custom_value3=product_data.get('custom_value3'),
        custom_value4=product_data.get('custom_value4'),
        is_deleted=product_data.get('is_deleted', False)
    )


# API Endpoints

@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=100),
    filter: Optional[str] = Query(default=None),
    is_deleted: bool = Query(default=False),
    current_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all products from InvoiceNinja with caching.

    Available to all authenticated users.
    """
    try:
        # Try to get from cache (only for default params)
        if page == 1 and per_page == 100 and not filter and not is_deleted:
            redis = await get_redis()
            if redis:
                cache_key = f"{CACHE_PREFIX}:list"
                cached = await redis.get(cache_key)
                if cached:
                    logger.info("Returning cached product list")
                    cached_data = json.loads(cached)
                    return ProductListResponse(**cached_data)

        # Fetch from InvoiceNinja
        invoiceninja = get_invoiceninja_client()
        result = await invoiceninja.list_products(
            page=page,
            per_page=per_page,
            filter=filter,
            is_deleted=is_deleted
        )

        products_data = result.get('data', [])
        meta = result.get('meta', {})

        products = [convert_product_to_response(p) for p in products_data]

        response = ProductListResponse(
            total=meta.get('total', len(products)),
            page=page,
            per_page=per_page,
            total_pages=meta.get('total_pages', 1),
            products=products
        )

        # Cache default list
        if page == 1 and per_page == 100 and not filter and not is_deleted:
            redis = await get_redis()
            if redis:
                cache_key = f"{CACHE_PREFIX}:list"
                await redis.setex(
                    cache_key,
                    CACHE_TTL,
                    json.dumps(response.dict(), default=str)
                )

        return response

    except Exception as e:
        logger.error(f"Error listing products: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single product by ID with caching.

    Available to all authenticated users.
    """
    try:
        # Check cache first
        cached_product = await get_cached_product(product_id)
        if cached_product:
            return convert_product_to_response(cached_product)

        # Fetch from InvoiceNinja
        invoiceninja = get_invoiceninja_client()
        product = await invoiceninja.get_product(product_id)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Convert to dict for caching
        product_dict = product.dict()

        # Cache the product
        await set_cached_product(product_id, product_dict)

        return convert_product_to_response(product_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get product: {str(e)}")


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    request: ProductCreateRequest,
    current_user: AuthUser = Depends(require_manager),  # Admin only
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product in InvoiceNinja.

    Admin only. Invalidates cache after creation.
    """
    try:
        invoiceninja = get_invoiceninja_client()

        product = await invoiceninja.create_product(
            product_key=request.product_key,
            notes=request.notes,
            cost=float(request.cost),
            price=float(request.price),
            quantity=float(request.quantity),
            tax_name1=request.tax_name1,
            tax_rate1=float(request.tax_rate1) if request.tax_rate1 else None,
            tax_name2=request.tax_name2,
            tax_rate2=float(request.tax_rate2) if request.tax_rate2 else None,
            custom_value1=request.custom_value1,
            custom_value2=request.custom_value2,
            custom_value3=request.custom_value3,
            custom_value4=request.custom_value4
        )

        if not product:
            raise HTTPException(status_code=500, detail="Failed to create product in InvoiceNinja")

        # Invalidate cache
        await invalidate_product_cache()

        logger.info(f"Created product {product.product_key} by user {current_user.get('email')}")

        return convert_product_to_response(product.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    request: ProductUpdateRequest,
    current_user: AuthUser = Depends(require_manager),  # Admin only
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing product in InvoiceNinja.

    Admin only. Invalidates cache after update.
    """
    try:
        invoiceninja = get_invoiceninja_client()

        # Build update dict (only include provided fields)
        update_data = {}
        if request.product_key is not None:
            update_data['product_key'] = request.product_key
        if request.notes is not None:
            update_data['notes'] = request.notes
        if request.cost is not None:
            update_data['cost'] = float(request.cost)
        if request.price is not None:
            update_data['price'] = float(request.price)
        if request.quantity is not None:
            update_data['quantity'] = float(request.quantity)
        if request.tax_name1 is not None:
            update_data['tax_name1'] = request.tax_name1
        if request.tax_rate1 is not None:
            update_data['tax_rate1'] = float(request.tax_rate1)
        if request.tax_name2 is not None:
            update_data['tax_name2'] = request.tax_name2
        if request.tax_rate2 is not None:
            update_data['tax_rate2'] = float(request.tax_rate2)
        if request.custom_value1 is not None:
            update_data['custom_value1'] = request.custom_value1
        if request.custom_value2 is not None:
            update_data['custom_value2'] = request.custom_value2
        if request.custom_value3 is not None:
            update_data['custom_value3'] = request.custom_value3
        if request.custom_value4 is not None:
            update_data['custom_value4'] = request.custom_value4

        product = await invoiceninja.update_product(product_id, **update_data)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found or update failed")

        # Invalidate cache
        await invalidate_product_cache(product_id)

        logger.info(f"Updated product {product_id} by user {current_user.get('email')}")

        return convert_product_to_response(product.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update product: {str(e)}")


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    current_user: AuthUser = Depends(require_manager),  # Admin only
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (soft delete) a product in InvoiceNinja.

    Admin only. Invalidates cache after deletion.
    """
    try:
        invoiceninja = get_invoiceninja_client()

        success = await invoiceninja.delete_product(product_id)

        if not success:
            raise HTTPException(status_code=404, detail="Product not found or delete failed")

        # Invalidate cache
        await invalidate_product_cache(product_id)

        logger.info(f"Deleted product {product_id} by user {current_user.get('email')}")

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {str(e)}")


@router.post("/sync", status_code=200)
async def force_cache_sync(
    current_user: AuthUser = Depends(require_manager),  # Admin only
    db: AsyncSession = Depends(get_db)
):
    """
    Force refresh of product cache.

    Admin only. Clears all product caches and returns fresh data.
    """
    try:
        redis = await get_redis()
        if redis:
            # Delete all product cache keys
            pattern = f"{CACHE_PREFIX}:*"
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await redis.delete(*keys)
                    deleted_count += len(keys)
                if cursor == 0:
                    break

            logger.info(f"Cache sync: deleted {deleted_count} cached items")

            return {
                "status": "success",
                "message": f"Cleared {deleted_count} cached product entries",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "warning",
                "message": "Redis not available, no cache to clear",
                "timestamp": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"Error syncing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync cache: {str(e)}")
