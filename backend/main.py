"""
Somni Property Manager - Main Application
FastAPI backend for multi-unit property management with building automation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from core.config import settings
from middleware import (
    RateLimitMiddleware,
    AuditLogMiddleware,
    RequestIDMiddleware,
    ErrorHandlerMiddleware
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    redirect_slashes=False  # Disable automatic redirects to prevent mixed content errors
)

# Add custom middleware (order matters - first added = last executed)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
app.add_middleware(RequestIDMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Validate critical security settings
    if not settings.CUSTOMER_PORTAL_SECRET_KEY:
        logger.error("❌ CUSTOMER_PORTAL_SECRET_KEY is not set!")
        logger.error("   This is required for customer quote portal security.")
        logger.error("   Generate a secure key with: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
        logger.error("   Then set CUSTOMER_PORTAL_SECRET_KEY in your environment or .env file")
        raise RuntimeError("CUSTOMER_PORTAL_SECRET_KEY environment variable is required")
    logger.info("✅ Customer portal security validated")

    # Import all models to ensure SQLAlchemy knows about all relationships
    # This must happen before any database operations
    # IMPORTANT: Import order matters! Import models that are referenced by others first
    import db.models_maintenance  # Maintenance scheduling models (referenced by Property)
    import db.models_project_phases  # Project phase models (required by quotes)
    import db.models  # Main property management models
    import db.family_models  # SomniFamily MSP models
    import db.models_ai  # AI assistant models
    import db.models_approval  # Approval workflow models
    import db.models_comms  # Communication models
    import db.models_quotes  # Quote and pricing models
    import db.models_leads  # Lead management models (NoteCaptureMCP integration)
    import db.models_ha_instance  # Home Assistant instance models (Flutter app)
    logger.info("✅ All database models imported")

    # Initialize database connection pool
    from db.database import init_db
    await init_db()

    # Initialize MQTT client connection (optional)
    mqtt_enabled = settings.MQTT_USERNAME is not None or settings.DEBUG
    if mqtt_enabled:
        try:
            from services.mqtt_client import mqtt_service
            await mqtt_service.connect()
            logger.info("✅ MQTT client connected")
        except Exception as e:
            logger.warning(f"⚠️  MQTT connection failed: {e}")
            logger.info("Application will continue without MQTT functionality")
    else:
        logger.info("⏭️  MQTT disabled (no credentials configured)")

    # Initialize Home Assistant connections (optional)
    ha_enabled = len(settings.HA_INSTANCES) > 0 if hasattr(settings, 'HA_INSTANCES') else False
    if ha_enabled:
        try:
            from services.homeassistant_client import ha_client
            # HA client initializes in __init__, just verify it's ready
            logger.info(f"✅ Home Assistant client initialized with {len(settings.HA_INSTANCES)} instances")
        except Exception as e:
            logger.warning(f"⚠️  Home Assistant initialization failed: {e}")
            logger.info("Application will continue without Home Assistant functionality")
    else:
        logger.info("⏭️  Home Assistant disabled (no instances configured)")

    # Start proactive ticket scheduler (background tasks)
    try:
        from services.proactive_ticket_scheduler import scheduler
        await scheduler.start()
        logger.info("✅ Proactive ticket scheduler started")
    except Exception as e:
        logger.warning(f"⚠️  Proactive scheduler failed to start: {e}")
        logger.info("Application will continue without proactive ticket creation")

    # Start device monitoring service (if MQTT is enabled)
    if mqtt_enabled:
        try:
            from services.device_monitor_service import device_monitor
            await device_monitor.start()
            logger.info("✅ Device monitoring service started")
        except Exception as e:
            logger.warning(f"⚠️  Device monitoring service failed to start: {e}")
            logger.info("Application will continue without device monitoring")

    # Start MQTT watchdog (monitors MQTT connection health)
    if mqtt_enabled:
        try:
            from services.mqtt_watchdog import mqtt_watchdog
            await mqtt_watchdog.start()
            logger.info("✅ MQTT watchdog started")
        except Exception as e:
            logger.warning(f"⚠️  MQTT watchdog failed to start: {e}")
            logger.info("Application will continue without MQTT watchdog")

    # Start MQTT-WebSocket bridge (real-time IoT updates to frontend)
    if mqtt_enabled:
        try:
            from services.mqtt_websocket_bridge import mqtt_ws_bridge
            await mqtt_ws_bridge.start()
            logger.info("✅ MQTT-WebSocket bridge started")
        except Exception as e:
            logger.warning(f"⚠️  MQTT-WebSocket bridge failed to start: {e}")
            logger.info("Application will continue without real-time IoT updates")

    logger.info("✅ Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down application...")

    # Stop proactive ticket scheduler
    try:
        from services.proactive_ticket_scheduler import scheduler
        await scheduler.stop()
        logger.info("✅ Proactive ticket scheduler stopped")
    except Exception as e:
        logger.debug(f"Proactive scheduler stop: {e}")

    # Close database connections
    from db.database import close_db
    await close_db()

    # Close MQTT connection (if enabled)
    try:
        from services.mqtt_client import mqtt_service
        if mqtt_service.is_connected():
            await mqtt_service.disconnect()
            logger.info("✅ MQTT client disconnected")
    except Exception as e:
        logger.debug(f"MQTT disconnect: {e}")

    # Close Home Assistant connections (if enabled)
    try:
        from services.homeassistant_client import ha_client
        if ha_client.clients:
            await ha_client.close()
            logger.info("✅ Home Assistant clients disconnected")
    except Exception as e:
        logger.debug(f"Home Assistant disconnect: {e}")

    # Stop device monitoring service
    try:
        from services.device_monitor_service import device_monitor
        if device_monitor.running:
            await device_monitor.stop()
            logger.info("✅ Device monitoring service stopped")
    except Exception as e:
        logger.debug(f"Device monitor stop: {e}")

    # Stop MQTT watchdog
    try:
        from services.mqtt_watchdog import mqtt_watchdog
        if mqtt_watchdog.running:
            await mqtt_watchdog.stop()
            logger.info("✅ MQTT watchdog stopped")
    except Exception as e:
        logger.debug(f"MQTT watchdog stop: {e}")

    # Stop MQTT-WebSocket bridge
    try:
        from services.mqtt_websocket_bridge import mqtt_ws_bridge
        if mqtt_ws_bridge.running:
            await mqtt_ws_bridge.stop()
            logger.info("✅ MQTT-WebSocket bridge stopped")
    except Exception as e:
        logger.debug(f"MQTT-WebSocket bridge stop: {e}")

    # Close Redis connection
    try:
        from services.redis_service import close_redis
        await close_redis()
    except Exception as e:
        logger.debug(f"Redis disconnect: {e}")

    logger.info("✅ Application shutdown complete")


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with dependency status"""
    from datetime import datetime
    from sqlalchemy import select

    health_status = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {}
    }

    # Check database
    try:
        from db.database import get_db
        async for db in get_db():
            await db.execute(select(1))
            health_status["dependencies"]["database"] = "ok"
            break
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["dependencies"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check MQTT (only mark degraded if credentials are configured but connection failed)
    try:
        from services.mqtt_client import mqtt_service
        if mqtt_service.is_connected():
            health_status["dependencies"]["mqtt"] = "ok"
        elif settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            # MQTT credentials configured but not connected - degraded
            health_status["dependencies"]["mqtt"] = "disconnected"
            health_status["status"] = "degraded"
        else:
            # MQTT not configured - not degraded, just disabled
            health_status["dependencies"]["mqtt"] = "disabled"
    except Exception as e:
        health_status["dependencies"]["mqtt"] = "not_configured"

    # Check Home Assistant (if enabled)
    try:
        from services.homeassistant_client import ha_client
        if hasattr(ha_client, 'clients') and ha_client.clients:
            health_status["dependencies"]["home_assistant"] = f"ok ({len(ha_client.clients)} instances)"
        else:
            health_status["dependencies"]["home_assistant"] = "not_configured"
    except Exception as e:
        health_status["dependencies"]["home_assistant"] = "not_configured"

    # Determine HTTP status code based on health
    status_code = 200 if health_status["status"] == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content=health_status
    )


@app.get("/api/health")
async def api_health_check():
    """
    Health check endpoint at /api/health for frontend compatibility
    This is a lightweight proxy to the main health check
    """
    from datetime import datetime
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/health",
        "api_prefix": settings.API_V1_PREFIX,
    }


# ============================================================================
# API ROUTERS
# ============================================================================

# Import API v1 routers
from api.v1 import (
    auth,  # Employee authentication (Infisical-backed)
    properties, buildings, units, tenants, leases, payments, workorders,
    websocket, documents, invoices,
    # Smart Home Service modules
    service_packages, service_contracts, smart_devices, edge_nodes,
    # 3-Tier Architecture modules
    sync, fleet,
    # Client Management
    clients, client_media, client_onboarding, client_notes,
    # Component Sync
    component_sync,
    # AI Assistant
    ai_chat,
    # Family Mode (MSP)
    family,
    # Property Mode Cluster Management
    clusters,
    # Dashboard statistics
    dashboard,
    # Intelligent Summary (Multi-service aggregation)
    intelligent_summary,
    # Alerts and Incidents
    alerts,
    # Support Tickets (Proactive Outreach)
    support_tickets,
    # Health and Monitoring
    health,
    # Contractors
    contractors,
    # Maintenance Scheduling
    maintenance,
    # Quotes (Sales)
    quotes,
    public_quotes,
    quote_tiers,
    labor,  # Labor pricing and estimation
    labor_config,  # Labor configuration (rates, installation times, materials)
    # Communications
    communications,
    # New SOMNI Internal Ops features
    scheduling,
    deployments,
    # Customer Portal (Public - No Auth)
    customer_portal,
    # Analytics (MRR/Subscription Metrics)
    analytics,
    # Stripe Webhooks (Payment Events)
    stripe_webhooks,
    # InvoiceNinja Products Integration
    products,  # InvoiceNinja products proxy with caching
    # MQTT Testing
    mqtt_test,  # MQTT connectivity testing endpoints
    # Contractor Labor (Mobile App - GPS time tracking, photos, materials, notes)
    contractor_labor,  # Full contractor mobile workflow with labor item management
    # Leads (NoteCaptureMCP integration)
    leads,  # Lead management and NoteCaptureMCP business opportunity capture
    # HA Instance Management (Flutter App)
    ha_instances,  # Home Assistant instance management for unified Flutter app
    ha_terminal  # SSH terminal WebSocket for HA instances
)

# Include routers

# Auth router (for employee mobile app)
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["auth"]
)

app.include_router(
    properties.router,
    prefix=f"{settings.API_V1_PREFIX}/properties",
    tags=["properties"]
)
app.include_router(
    buildings.router,
    prefix=f"{settings.API_V1_PREFIX}/buildings",
    tags=["buildings"]
)
app.include_router(
    units.router,
    prefix=f"{settings.API_V1_PREFIX}/units",
    tags=["units"]
)
app.include_router(
    tenants.router,
    prefix=f"{settings.API_V1_PREFIX}/tenants",
    tags=["tenants"]
)

app.include_router(
    clients.router,
    prefix=f"{settings.API_V1_PREFIX}/clients",
    tags=["clients"]
)

app.include_router(
    client_media.router,
    prefix=f"{settings.API_V1_PREFIX}/clients",
    tags=["client media"]
)

app.include_router(
    client_onboarding.router,
    prefix=f"{settings.API_V1_PREFIX}/clients",
    tags=["client onboarding"]
)

app.include_router(
    client_notes.router,
    prefix=f"{settings.API_V1_PREFIX}/clients",
    tags=["client notes"]
)

app.include_router(
    leases.router,
    prefix=f"{settings.API_V1_PREFIX}/leases",
    tags=["leases"]
)

app.include_router(
    payments.router,
    prefix=f"{settings.API_V1_PREFIX}/payments",
    tags=["payments"]
)

app.include_router(
    workorders.router,
    prefix=f"{settings.API_V1_PREFIX}/workorders",
    tags=["work orders"]
)

app.include_router(
    websocket.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["websocket"]
)

app.include_router(
    documents.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["documents"]
)

app.include_router(
    invoices.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["invoices"]
)

# Smart Home Service routers
app.include_router(
    service_packages.router,
    prefix=f"{settings.API_V1_PREFIX}/service-packages",
    tags=["smart home services", "service packages"]
)

app.include_router(
    service_contracts.router,
    prefix=f"{settings.API_V1_PREFIX}/service-contracts",
    tags=["smart home services", "service contracts"]
)

app.include_router(
    smart_devices.router,
    prefix=f"{settings.API_V1_PREFIX}/smart-devices",
    tags=["smart home services", "devices"]
)

app.include_router(
    edge_nodes.router,
    prefix=f"{settings.API_V1_PREFIX}/edge-nodes",
    tags=["smart home services", "edge nodes"]
)

# 3-Tier Architecture routers
app.include_router(
    sync.router,
    prefix=f"{settings.API_V1_PREFIX}/sync",
    tags=["3-tier architecture", "device sync"]
)

app.include_router(
    fleet.router,
    prefix=f"{settings.API_V1_PREFIX}/fleet",
    tags=["3-tier architecture", "fleet management"]
)

# Client Management routers
app.include_router(
    clients.router,
    prefix=f"{settings.API_V1_PREFIX}/clients",
    tags=["client management"]
)

app.include_router(
    client_media.router,
    prefix=f"{settings.API_V1_PREFIX}/clients",
    tags=["client management", "media"]
)

app.include_router(
    client_onboarding.router,
    prefix=f"{settings.API_V1_PREFIX}/clients",
    tags=["client management", "onboarding"]
)

app.include_router(
    client_notes.router,
    prefix=f"{settings.API_V1_PREFIX}/clients",
    tags=["client management", "notes"]
)

# Communications router
app.include_router(
    communications.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["communications", "email", "sms"]
)

# Component Sync routers
app.include_router(
    component_sync.router,
    prefix=f"{settings.API_V1_PREFIX}/component-sync",
    tags=["component sync", "somni intelligence"]
)

# AI Assistant routers
app.include_router(
    ai_chat.router,
    prefix=f"{settings.API_V1_PREFIX}/ai",
    tags=["ai assistant", "somni intelligence"]
)

# Family Mode routers (MSP)
app.include_router(
    family.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["family mode", "msp"]
)

# Property Mode Cluster Management routers
app.include_router(
    clusters.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["property mode", "cluster management", "kubernetes"]
)

# Dashboard statistics
app.include_router(
    dashboard.router,
    prefix=f"{settings.API_V1_PREFIX}/dashboard",
    tags=["dashboard", "statistics"]
)

# Intelligent Summary (Multi-service aggregation)
app.include_router(
    intelligent_summary.router,
    tags=["intelligent summary", "aggregation"]
)

# Alerts and Incidents
app.include_router(
    alerts.router,
    prefix=f"{settings.API_V1_PREFIX}/alerts",
    tags=["alerts", "incidents", "monitoring"]
)

# Support Tickets (Proactive Outreach)
app.include_router(
    support_tickets.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["support tickets", "proactive outreach", "family mode"]
)

# Health and Monitoring
app.include_router(
    health.router,
    prefix=f"{settings.API_V1_PREFIX}/health",
    tags=["health", "monitoring", "observability"]
)

# Contractors
app.include_router(
    contractors.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["contractors"]
)

# Maintenance Scheduling
app.include_router(
    maintenance.router,
    prefix=f"{settings.API_V1_PREFIX}/maintenance",
    tags=["maintenance", "property management"]
)

# Quotes (Sales)
app.include_router(
    quotes.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["quotes", "sales"]
)

# Public Quotes (Customer Portal - No Auth)
app.include_router(
    public_quotes.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["public-quotes", "customer-portal"]
)

# Quote Tiers (Subscription tiers and product catalog)
app.include_router(
    quote_tiers.router,
    prefix=f"{settings.API_V1_PREFIX}/quote-tiers",
    tags=["quotes", "subscription-tiers", "product-catalog"]
)

# Labor Pricing (Labor estimation and management)
app.include_router(
    labor.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["labor", "quotes", "estimation"]
)

# Labor Configuration (Labor rates, installation times, materials)
app.include_router(
    labor_config.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["labor-config", "configuration", "pricing"]
)

# Scheduling (Cal.com Integration)
app.include_router(
    scheduling.router,
    prefix=f"{settings.API_V1_PREFIX}/scheduling",
    tags=["scheduling", "calendar", "cal.com"]
)

# Deployments (GitOps Orchestration)
app.include_router(
    deployments.router,
    prefix=f"{settings.API_V1_PREFIX}/deployments",
    tags=["deployments", "gitops", "argocd"]
)

# Customer Portal (Public - No Auth Required)
app.include_router(
    customer_portal.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["customer-portal", "public"]
)

# Analytics (MRR/Subscription Metrics)
app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["analytics", "mrr", "metrics"]
)

# Stripe Webhooks (Payment Events - Public endpoint)
app.include_router(
    stripe_webhooks.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["stripe", "webhooks", "payments"]
)

# InvoiceNinja Products (Integration with InvoiceNinja for product catalog)
app.include_router(
    products.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["products", "invoiceninja", "invoicing"]
)

# MQTT Testing (For verifying MQTT connectivity and message flow)
app.include_router(
    mqtt_test.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["mqtt", "testing", "iot"]
)

# Contractor Labor (somni-employee mobile app integration)
# GPS-verified time tracking, photo uploads, materials, notes, dashboard
app.include_router(
    contractor_labor.router,
    prefix=f"{settings.API_V1_PREFIX}/contractor-labor",
    tags=["contractor-labor", "mobile", "time-tracking", "photos", "somni-employee"]
)

# Alias mount for somni-employee backward compatibility
# somni-employee calls /contractor/dashboard/* instead of /contractor-labor/dashboard/*
app.include_router(
    contractor_labor.router,
    prefix=f"{settings.API_V1_PREFIX}/contractor",
    tags=["contractor", "somni-employee-alias"],
    include_in_schema=False  # Hide from OpenAPI docs (use main prefix in docs)
)

# Leads (NoteCaptureMCP integration and business opportunity management)
app.include_router(
    leads.router,
    prefix=f"{settings.API_V1_PREFIX}/leads",
    tags=["leads", "notecapture", "sales"]
)

# HA Instance Management (Flutter App)
app.include_router(
    ha_instances.router,
    prefix=f"{settings.API_V1_PREFIX}/ha-instances",
    tags=["ha-instances", "home-assistant", "flutter-app"]
)

# HA Terminal WebSocket (SSH Terminal for Flutter App)
app.include_router(
    ha_terminal.router,
    prefix=f"{settings.API_V1_PREFIX}/ha-instances",
    tags=["ha-terminal", "ssh", "websocket", "flutter-app"]
)

# TODO: Add more routers as we build them
# Note: utilities, staff, approvals, communications routers exist but
# are missing required database models and service implementations
# from api.v1 import iot
# app.include_router(iot.router, prefix=f"{settings.API_V1_PREFIX}/iot", tags=["iot"])


# ============================================================================
# STATIC FILE SERVING
# ============================================================================
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Mount static file directory for visual quote assets
storage_path = Path("/app/storage/visual-assets")
storage_path.mkdir(parents=True, exist_ok=True)

app.mount(
    "/storage/visual-assets",
    StaticFiles(directory=str(storage_path)),
    name="visual-assets"
)
logger.info(f"✅ Static file serving enabled for visual assets at {storage_path}")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
