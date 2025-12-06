"""
Simplified SomniProperty Backend - For Quick Deployment
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

# Create FastAPI application
app = FastAPI(
    title="SomniProperty API",
    description="Property Management System",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "SomniProperty API",
        "version": "1.0.0",
        "status": "running",
        "database": os.getenv("DATABASE_URL", "not_configured")[:50],
        "mqtt_broker": os.getenv("MQTT_BROKER", "not_configured")
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/properties")
async def get_properties():
    return {
        "properties": [
            {
                "id": 1,
                "name": "Sample Property",
                "address": "123 Main St",
                "units": 4,
                "status": "active"
            }
        ]
    }

@app.get("/api/dashboard")
async def get_dashboard():
    return {
        "total_properties": 1,
        "total_units": 4,
        "occupied_units": 3,
        "maintenance_requests": 2,
        "recent_activity": [
            {"type": "maintenance", "message": "Work order #123 completed"},
            {"type": "rent", "message": "Rent payment received - Unit 2A"}
        ]
    }
