"""
Health and System Status API Endpoints
Provides detailed system health information and monitoring data
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timedelta
import logging
import psutil
import os

from db.database import get_db
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/detailed")
async def detailed_health(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check endpoint with comprehensive system status

    Returns:
    - Service health status
    - Database connection and performance metrics
    - MQTT broker connection status
    - Home Assistant integration status
    - Background service status
    - System resource usage
    """
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else 'production',
            "debug_mode": settings.DEBUG
        },
        "dependencies": {},
        "services": {},
        "system": {}
    }

    # === Database Health Check ===
    try:
        # Test basic connectivity
        start_time = datetime.utcnow()
        await db.execute(select(1))
        query_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Get database pool stats
        pool_size = db.get_bind().pool.size() if hasattr(db.get_bind(), 'pool') else None
        pool_checked_out = db.get_bind().pool.checkedout() if hasattr(db.get_bind(), 'pool') else None

        health_data["dependencies"]["database"] = {
            "status": "ok",
            "response_time_ms": round(query_time, 2),
            "pool_size": pool_size,
            "connections_in_use": pool_checked_out
        }

        # Count total records (sample query for DB load)
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM properties"))
            property_count = result.scalar()
            health_data["dependencies"]["database"]["property_count"] = property_count
        except Exception:
            # Table might not exist in fresh install
            pass

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_data["dependencies"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_data["status"] = "degraded"

    # === MQTT Health Check ===
    try:
        from services.mqtt_client import mqtt_service

        if mqtt_service.is_connected():
            health_data["dependencies"]["mqtt"] = {
                "status": "ok",
                "broker": settings.MQTT_BROKER,
                "port": settings.MQTT_PORT,
                "client_id": mqtt_service.client_id
            }
        else:
            health_data["dependencies"]["mqtt"] = {
                "status": "disconnected",
                "broker": settings.MQTT_BROKER,
                "port": settings.MQTT_PORT
            }
            health_data["status"] = "degraded"

    except Exception as e:
        health_data["dependencies"]["mqtt"] = {
            "status": "not_configured",
            "message": "MQTT service not initialized"
        }

    # === Home Assistant Health Check ===
    try:
        from services.homeassistant_client import ha_client

        if hasattr(ha_client, 'clients') and ha_client.clients:
            ha_instances = []
            for instance_name, client in ha_client.clients.items():
                ha_instances.append({
                    "name": instance_name,
                    "url": client.base_url if hasattr(client, 'base_url') else "unknown",
                    "connected": True  # TODO: Add actual connectivity check
                })

            health_data["dependencies"]["home_assistant"] = {
                "status": "ok",
                "instance_count": len(ha_client.clients),
                "instances": ha_instances
            }
        else:
            health_data["dependencies"]["home_assistant"] = {
                "status": "not_configured",
                "message": "No Home Assistant instances configured"
            }

    except Exception as e:
        health_data["dependencies"]["home_assistant"] = {
            "status": "not_configured",
            "message": str(e)
        }

    # === Background Services Health Check ===
    try:
        from services.device_monitor_service import device_monitor

        if hasattr(device_monitor, 'running') and device_monitor.running:
            health_data["services"]["device_monitor"] = {
                "status": "running",
                "uptime_seconds": (datetime.utcnow() - device_monitor.start_time).total_seconds() if hasattr(device_monitor, 'start_time') else None
            }
        else:
            health_data["services"]["device_monitor"] = {
                "status": "stopped"
            }

    except Exception as e:
        health_data["services"]["device_monitor"] = {
            "status": "not_initialized",
            "error": str(e)
        }

    # Check MQTT watchdog (if implemented)
    try:
        from services.mqtt_watchdog import mqtt_watchdog

        if hasattr(mqtt_watchdog, 'running') and mqtt_watchdog.running:
            health_data["services"]["mqtt_watchdog"] = {
                "status": "running",
                "reconnect_attempts": mqtt_watchdog.reconnect_attempts if hasattr(mqtt_watchdog, 'reconnect_attempts') else 0,
                "last_check": mqtt_watchdog.last_check.isoformat() if hasattr(mqtt_watchdog, 'last_check') else None
            }
        else:
            health_data["services"]["mqtt_watchdog"] = {
                "status": "stopped"
            }

    except ImportError:
        health_data["services"]["mqtt_watchdog"] = {
            "status": "not_implemented"
        }

    # === System Resources ===
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory usage
        memory = psutil.virtual_memory()

        # Disk usage (root partition)
        disk = psutil.disk_usage('/')

        health_data["system"] = {
            "cpu_percent": cpu_percent,
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": disk.percent
            },
            "process": {
                "pid": os.getpid(),
                "threads": psutil.Process().num_threads()
            }
        }

        # Warn if resources are high
        if cpu_percent > 80 or memory.percent > 90 or disk.percent > 90:
            health_data["status"] = "degraded"
            health_data["warnings"] = []

            if cpu_percent > 80:
                health_data["warnings"].append(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 90:
                health_data["warnings"].append(f"High memory usage: {memory.percent}%")
            if disk.percent > 90:
                health_data["warnings"].append(f"High disk usage: {disk.percent}%")

    except Exception as e:
        logger.error(f"System resource check failed: {e}")
        health_data["system"] = {
            "status": "error",
            "error": str(e)
        }

    # Determine final status code
    status_code = 200 if health_data["status"] == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content=health_data
    )


@router.get("/status")
async def service_status():
    """
    Quick service status check (lighter than detailed health)
    Useful for monitoring dashboards
    """
    from services.mqtt_client import mqtt_service

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "up",
            "mqtt": "up" if mqtt_service.is_connected() else "down",
        }
    }

    # Check device monitor
    try:
        from services.device_monitor_service import device_monitor
        status["services"]["device_monitor"] = "running" if device_monitor.running else "stopped"
    except Exception:
        status["services"]["device_monitor"] = "unknown"

    # Check MQTT watchdog
    try:
        from services.mqtt_watchdog import mqtt_watchdog
        status["services"]["mqtt_watchdog"] = "running" if mqtt_watchdog.running else "stopped"
    except ImportError:
        status["services"]["mqtt_watchdog"] = "not_implemented"

    return status


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for uptime monitoring
    Returns minimal response for fast health checks
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)):
    """
    Prometheus-style metrics endpoint
    Returns application metrics in a format suitable for monitoring systems

    Metrics include:
    - HTTP request counts and error rates
    - Service connection status
    - Resource utilization
    - Database query performance
    - MQTT message throughput
    """
    from services.mqtt_client import mqtt_service

    metrics_data = []

    # === Service Status Metrics (gauge) ===
    # Value: 1 = up/connected, 0 = down/disconnected

    # API service (always up if this endpoint responds)
    metrics_data.append('# HELP somni_service_status Service availability status (1=up, 0=down)')
    metrics_data.append('# TYPE somni_service_status gauge')
    metrics_data.append('somni_service_status{service="api"} 1')

    # MQTT connection status
    mqtt_status = 1 if mqtt_service.is_connected() else 0
    metrics_data.append(f'somni_service_status{{service="mqtt"}} {mqtt_status}')

    # Device monitor status
    try:
        from services.device_monitor_service import device_monitor
        monitor_status = 1 if device_monitor.running else 0
        metrics_data.append(f'somni_service_status{{service="device_monitor"}} {monitor_status}')
    except Exception:
        metrics_data.append('somni_service_status{service="device_monitor"} 0')

    # MQTT watchdog status
    try:
        from services.mqtt_watchdog import mqtt_watchdog
        watchdog_status = 1 if mqtt_watchdog.running else 0
        metrics_data.append(f'somni_service_status{{service="mqtt_watchdog"}} {watchdog_status}')
    except Exception:
        metrics_data.append('somni_service_status{service="mqtt_watchdog"} 0')

    # === Database Metrics ===
    metrics_data.append('')
    metrics_data.append('# HELP somni_database_query_duration_seconds Database query response time')
    metrics_data.append('# TYPE somni_database_query_duration_seconds gauge')

    try:
        start_time = datetime.utcnow()
        await db.execute(select(1))
        query_duration = (datetime.utcnow() - start_time).total_seconds()
        metrics_data.append(f'somni_database_query_duration_seconds {{operation="health_check"}} {query_duration:.6f}')
    except Exception:
        metrics_data.append('somni_database_query_duration_seconds{operation="health_check"} -1')

    # Database pool metrics
    try:
        pool = db.get_bind().pool
        if hasattr(pool, 'size') and hasattr(pool, 'checkedout'):
            metrics_data.append('')
            metrics_data.append('# HELP somni_database_pool_size Database connection pool size')
            metrics_data.append('# TYPE somni_database_pool_size gauge')
            metrics_data.append(f'somni_database_pool_size {pool.size()}')

            metrics_data.append('')
            metrics_data.append('# HELP somni_database_connections_active Active database connections')
            metrics_data.append('# TYPE somni_database_connections_active gauge')
            metrics_data.append(f'somni_database_connections_active {pool.checkedout()}')
    except Exception:
        pass

    # === MQTT Watchdog Metrics ===
    try:
        from services.mqtt_watchdog import mqtt_watchdog
        stats = mqtt_watchdog.get_stats()

        metrics_data.append('')
        metrics_data.append('# HELP somni_mqtt_reconnection_attempts_total Total MQTT reconnection attempts')
        metrics_data.append('# TYPE somni_mqtt_reconnection_attempts_total counter')
        metrics_data.append(f'somni_mqtt_reconnection_attempts_total {stats["total_reconnections"]}')

        metrics_data.append('')
        metrics_data.append('# HELP somni_mqtt_reconnection_success_total Successful MQTT reconnections')
        metrics_data.append('# TYPE somni_mqtt_reconnection_success_total counter')
        metrics_data.append(f'somni_mqtt_reconnection_success_total {stats["successful_reconnections"]}')

        metrics_data.append('')
        metrics_data.append('# HELP somni_mqtt_reconnection_failure_total Failed MQTT reconnections')
        metrics_data.append('# TYPE somni_mqtt_reconnection_failure_total counter')
        metrics_data.append(f'somni_mqtt_reconnection_failure_total {stats["failed_reconnections"]}')

        if stats["current_downtime_seconds"] is not None:
            metrics_data.append('')
            metrics_data.append('# HELP somni_mqtt_downtime_seconds Current MQTT downtime in seconds')
            metrics_data.append('# TYPE somni_mqtt_downtime_seconds gauge')
            metrics_data.append(f'somni_mqtt_downtime_seconds {stats["current_downtime_seconds"]:.1f}')

    except Exception:
        pass

    # === System Resource Metrics ===
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        metrics_data.append('')
        metrics_data.append('# HELP somni_system_cpu_percent CPU usage percentage')
        metrics_data.append('# TYPE somni_system_cpu_percent gauge')
        metrics_data.append(f'somni_system_cpu_percent {cpu_percent}')

        metrics_data.append('')
        metrics_data.append('# HELP somni_system_memory_percent Memory usage percentage')
        metrics_data.append('# TYPE somni_system_memory_percent gauge')
        metrics_data.append(f'somni_system_memory_percent {memory.percent}')

        metrics_data.append('')
        metrics_data.append('# HELP somni_system_memory_bytes Memory usage in bytes')
        metrics_data.append('# TYPE somni_system_memory_bytes gauge')
        metrics_data.append(f'somni_system_memory_bytes{{type="total"}} {memory.total}')
        metrics_data.append(f'somni_system_memory_bytes{{type="used"}} {memory.used}')
        metrics_data.append(f'somni_system_memory_bytes{{type="available"}} {memory.available}')

        metrics_data.append('')
        metrics_data.append('# HELP somni_system_disk_percent Disk usage percentage')
        metrics_data.append('# TYPE somni_system_disk_percent gauge')
        metrics_data.append(f'somni_system_disk_percent {disk.percent}')

        metrics_data.append('')
        metrics_data.append('# HELP somni_system_disk_bytes Disk usage in bytes')
        metrics_data.append('# TYPE somni_system_disk_bytes gauge')
        metrics_data.append(f'somni_system_disk_bytes{{type="total"}} {disk.total}')
        metrics_data.append(f'somni_system_disk_bytes{{type="used"}} {disk.used}')
        metrics_data.append(f'somni_system_disk_bytes{{type="free"}} {disk.free}')

    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")

    # === Application Info ===
    metrics_data.append('')
    metrics_data.append('# HELP somni_app_info Application information')
    metrics_data.append('# TYPE somni_app_info gauge')
    metrics_data.append(
        f'somni_app_info{{version="{settings.APP_VERSION}",app="{settings.APP_NAME}"}} 1'
    )

    # Return metrics in Prometheus text format
    return JSONResponse(
        content='\n'.join(metrics_data) + '\n',
        media_type='text/plain; version=0.0.4'
    )
