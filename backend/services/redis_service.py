"""
Redis Service for Caching

Provides Redis connection and caching utilities for SomniProperty backend.

Features:
- Connection pooling
- Graceful degradation (app works without Redis)
- Async operations with aioredis
- Automatic reconnection
"""

import logging
import os
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """
    Get Redis client instance.

    Returns None if Redis is not configured or unavailable.
    Application should gracefully handle None by skipping caching.
    """
    global _redis_client

    # Return existing client if available
    if _redis_client is not None:
        try:
            # Test connection
            await _redis_client.ping()
            return _redis_client
        except Exception as e:
            logger.warning(f"Redis connection lost: {e}")
            _redis_client = None

    # Try to create new connection
    try:
        redis_host = os.getenv('REDIS_HOST', 'redis.core.svc.cluster.local')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_db = int(os.getenv('REDIS_DB', '0'))
        redis_password = os.getenv('REDIS_PASSWORD')

        logger.info(f"Connecting to Redis at {redis_host}:{redis_port}/{redis_db}")

        _redis_client = aioredis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,  # Auto-decode bytes to strings
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )

        # Test connection
        await _redis_client.ping()
        logger.info("Redis connection established successfully")

        return _redis_client

    except Exception as e:
        logger.warning(f"Redis unavailable: {e}. Caching disabled.")
        _redis_client = None
        return None


async def close_redis():
    """Close Redis connection on application shutdown"""
    global _redis_client

    if _redis_client is not None:
        try:
            await _redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None
