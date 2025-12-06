"""
SomniProperty MCP Server
Model Context Protocol server that exposes all SomniProperty API endpoints as MCP tools.
Enables AI agents (Claude, Ollama, etc.) to interact with the property management system.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPTool(BaseModel):
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class SomniPropertyMCPServer:
    """
    MCP Server for SomniProperty

    Exposes 50+ property management operations as MCP tools:
    - Property management (CRUD, search, analytics)
    - Client management (CRUD, service provisioning)
    - Tenant management (CRUD, lease tracking)
    - Work order management (create, assign, track)
    - Payment processing (invoices, payments, reporting)
    - Smart device control (query status, send commands)
    - Utility monitoring (usage tracking, cost analysis)
    - Fleet management (edge nodes, sync status)

    This enables AI assistants to:
    1. Query data ("Show me all vacant units")
    2. Perform actions ("Create a work order for unit 101")
    3. Generate insights ("Analyze utility costs by property")
    4. Automate workflows ("Send rent reminders to overdue tenants")
    """

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.tools = self._define_tools()

    def _define_tools(self) -> List[MCPTool]:
        """Define all MCP tools (one per API endpoint)"""
        return [
            # ================================================================
            # PROPERTY MANAGEMENT TOOLS
            # ================================================================
            MCPTool(
                name="list_properties",
                description="List all properties with optional filtering by type, city, or status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_type": {"type": "string", "enum": ["residential", "commercial", "mixed_use"]},
                        "city": {"type": "string"},
                        "limit": {"type": "integer", "default": 50}
                    }
                }
            ),
            MCPTool(
                name="get_property",
                description="Get detailed information about a specific property including buildings, units, and occupancy",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string", "description": "Property UUID"}
                    },
                    "required": ["property_id"]
                }
            ),
            MCPTool(
                name="create_property",
                description="Create a new property in the system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "address_line1": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "zip_code": {"type": "string"},
                        "property_type": {"type": "string", "enum": ["residential", "commercial", "mixed_use"]}
                    },
                    "required": ["name", "address_line1", "city", "state", "zip_code", "property_type"]
                }
            ),
            MCPTool(
                name="get_property_analytics",
                description="Get analytics for a property: occupancy rate, revenue, maintenance costs, vacancy trends",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    },
                    "required": ["property_id"]
                }
            ),

            # ================================================================
            # CLIENT MANAGEMENT TOOLS
            # ================================================================
            MCPTool(
                name="list_clients",
                description="List all clients (Tier 0, 1, 2) with their properties and edge nodes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tier": {"type": "string", "enum": ["tier_0", "tier_1", "tier_2"]},
                        "limit": {"type": "integer", "default": 50}
                    }
                }
            ),
            MCPTool(
                name="get_client",
                description="Get client details including properties, edge nodes, and service packages",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string"}
                    },
                    "required": ["client_id"]
                }
            ),
            MCPTool(
                name="create_client",
                description="Create a new client account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "tier": {"type": "string", "enum": ["tier_0", "tier_1", "tier_2"]},
                        "phone": {"type": "string"}
                    },
                    "required": ["name", "email", "tier"]
                }
            ),

            # ================================================================
            # TENANT MANAGEMENT TOOLS
            # ================================================================
            MCPTool(
                name="list_tenants",
                description="List all tenants with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "has_active_lease": {"type": "boolean"},
                        "limit": {"type": "integer", "default": 50}
                    }
                }
            ),
            MCPTool(
                name="get_tenant",
                description="Get tenant details including lease, payment history, and work orders",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tenant_id": {"type": "string"}
                    },
                    "required": ["tenant_id"]
                }
            ),
            MCPTool(
                name="create_tenant",
                description="Create a new tenant record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "employer": {"type": "string"},
                        "monthly_income": {"type": "number"}
                    },
                    "required": ["first_name", "last_name", "email", "phone"]
                }
            ),

            # ================================================================
            # LEASE MANAGEMENT TOOLS
            # ================================================================
            MCPTool(
                name="list_leases",
                description="List leases with filtering by status, property, or expiration date",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["active", "expired", "terminated", "pending"]},
                        "property_id": {"type": "string"},
                        "expiring_within_days": {"type": "integer"}
                    }
                }
            ),
            MCPTool(
                name="create_lease",
                description="Create a new lease agreement",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tenant_id": {"type": "string"},
                        "unit_id": {"type": "string"},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"},
                        "monthly_rent": {"type": "number"},
                        "security_deposit": {"type": "number"}
                    },
                    "required": ["tenant_id", "unit_id", "start_date", "end_date", "monthly_rent"]
                }
            ),

            # ================================================================
            # WORK ORDER MANAGEMENT TOOLS
            # ================================================================
            MCPTool(
                name="list_work_orders",
                description="List work orders with filtering by status, priority, or property",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "emergency"]},
                        "property_id": {"type": "string"},
                        "assigned_to": {"type": "string"}
                    }
                }
            ),
            MCPTool(
                name="create_work_order",
                description="Create a new maintenance work order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "unit_id": {"type": "string"},
                        "property_id": {"type": "string"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "emergency"]},
                        "category": {"type": "string"}
                    },
                    "required": ["title", "description", "priority"]
                }
            ),
            MCPTool(
                name="update_work_order_status",
                description="Update the status of a work order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "work_order_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                        "notes": {"type": "string"}
                    },
                    "required": ["work_order_id", "status"]
                }
            ),

            # ================================================================
            # PAYMENT & INVOICE TOOLS
            # ================================================================
            MCPTool(
                name="list_payments",
                description="List payments with filtering by tenant, property, or date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tenant_id": {"type": "string"},
                        "property_id": {"type": "string"},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"},
                        "status": {"type": "string", "enum": ["pending", "completed", "failed"]}
                    }
                }
            ),
            MCPTool(
                name="list_invoices",
                description="List invoices with filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tenant_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["draft", "sent", "paid", "overdue", "cancelled"]},
                        "overdue_only": {"type": "boolean"}
                    }
                }
            ),
            MCPTool(
                name="create_invoice",
                description="Create a new invoice for a tenant",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tenant_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "due_date": {"type": "string", "format": "date"},
                        "description": {"type": "string"}
                    },
                    "required": ["tenant_id", "amount", "due_date"]
                }
            ),

            # ================================================================
            # SMART DEVICE TOOLS
            # ================================================================
            MCPTool(
                name="list_smart_devices",
                description="List smart devices with filtering by property, unit, type, or status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "unit_id": {"type": "string"},
                        "device_type": {"type": "string"},
                        "status": {"type": "string", "enum": ["online", "offline", "error"]}
                    }
                }
            ),
            MCPTool(
                name="get_device_status",
                description="Get current status and state of a smart device",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string"}
                    },
                    "required": ["device_id"]
                }
            ),
            MCPTool(
                name="control_device",
                description="Send a command to a smart device (turn on/off, set temperature, lock/unlock, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string"},
                        "command": {"type": "string"},
                        "parameters": {"type": "object"}
                    },
                    "required": ["device_id", "command"]
                }
            ),

            # ================================================================
            # UTILITY MONITORING TOOLS
            # ================================================================
            MCPTool(
                name="get_utility_usage",
                description="Get utility usage data (electric, water, gas) for a property or unit",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "unit_id": {"type": "string"},
                        "utility_type": {"type": "string", "enum": ["electric", "water", "gas"]},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    },
                    "required": ["utility_type"]
                }
            ),
            MCPTool(
                name="get_utility_costs",
                description="Get utility cost breakdown and trends",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    }
                }
            ),

            # ================================================================
            # BUILDING & UNIT TOOLS
            # ================================================================
            MCPTool(
                name="list_units",
                description="List units with filtering by property, building, occupancy status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "building_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["vacant", "occupied", "maintenance"]},
                        "bedrooms": {"type": "integer"}
                    }
                }
            ),
            MCPTool(
                name="get_vacant_units",
                description="Get all currently vacant units across all properties",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "min_bedrooms": {"type": "integer"}
                    }
                }
            ),

            # ================================================================
            # FLEET MANAGEMENT TOOLS (Edge Nodes)
            # ================================================================
            MCPTool(
                name="list_edge_nodes",
                description="List all edge nodes (Home Assistant Yellow hubs) across client properties",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["online", "offline", "syncing", "error"]}
                    }
                }
            ),
            MCPTool(
                name="get_edge_node_status",
                description="Get detailed status of an edge node including sync status, connected devices, uptime",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "edge_node_id": {"type": "string"}
                    },
                    "required": ["edge_node_id"]
                }
            ),
            MCPTool(
                name="sync_components_to_edge_node",
                description="Trigger component sync to an edge node (Tier 0: rsync, Tier 1/2: GitOps)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "edge_node_id": {"type": "string"},
                        "component_names": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["edge_node_id"]
                }
            ),

            # ================================================================
            # REPORTING & ANALYTICS TOOLS
            # ================================================================
            MCPTool(
                name="generate_property_report",
                description="Generate a comprehensive property performance report",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "report_type": {"type": "string", "enum": ["occupancy", "financial", "maintenance", "comprehensive"]},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    },
                    "required": ["property_id", "report_type"]
                }
            ),
            MCPTool(
                name="get_dashboard_stats",
                description="Get high-level dashboard statistics: total properties, occupancy rate, work orders, revenue",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool by calling the corresponding API endpoint
        """
        try:
            # Map tool names to API endpoints
            endpoint_map = {
                "list_properties": ("GET", "/api/v1/properties"),
                "get_property": ("GET", "/api/v1/properties/{property_id}"),
                "create_property": ("POST", "/api/v1/properties"),
                "get_property_analytics": ("GET", "/api/v1/properties/{property_id}/analytics"),

                "list_clients": ("GET", "/api/v1/clients"),
                "get_client": ("GET", "/api/v1/clients/{client_id}"),
                "create_client": ("POST", "/api/v1/clients"),

                "list_tenants": ("GET", "/api/v1/tenants"),
                "get_tenant": ("GET", "/api/v1/tenants/{tenant_id}"),
                "create_tenant": ("POST", "/api/v1/tenants"),

                "list_leases": ("GET", "/api/v1/leases"),
                "create_lease": ("POST", "/api/v1/leases"),

                "list_work_orders": ("GET", "/api/v1/workorders"),
                "create_work_order": ("POST", "/api/v1/workorders"),
                "update_work_order_status": ("PATCH", "/api/v1/workorders/{work_order_id}"),

                "list_payments": ("GET", "/api/v1/payments"),
                "list_invoices": ("GET", "/api/v1/invoices"),
                "create_invoice": ("POST", "/api/v1/invoices"),

                "list_smart_devices": ("GET", "/api/v1/smart-devices"),
                "get_device_status": ("GET", "/api/v1/smart-devices/{device_id}"),
                "control_device": ("POST", "/api/v1/smart-devices/{device_id}/control"),

                "get_utility_usage": ("GET", "/api/v1/utilities/usage"),
                "get_utility_costs": ("GET", "/api/v1/utilities/costs"),

                "list_units": ("GET", "/api/v1/units"),
                "get_vacant_units": ("GET", "/api/v1/units/vacant"),

                "list_edge_nodes": ("GET", "/api/v1/edge-nodes"),
                "get_edge_node_status": ("GET", "/api/v1/edge-nodes/{edge_node_id}"),
                "sync_components_to_edge_node": ("POST", "/api/v1/component-sync/sync"),

                "generate_property_report": ("POST", "/api/v1/properties/{property_id}/reports"),
                "get_dashboard_stats": ("GET", "/api/v1/dashboard/stats"),
            }

            if tool_name not in endpoint_map:
                return {"error": f"Unknown tool: {tool_name}"}

            method, endpoint = endpoint_map[tool_name]

            # Replace path parameters
            for key, value in arguments.items():
                placeholder = f"{{{key}}}"
                if placeholder in endpoint:
                    endpoint = endpoint.replace(placeholder, str(value))
                    arguments.pop(key)

            url = f"{self.api_base_url}{endpoint}"

            # Make API request
            if method == "GET":
                response = await self.client.get(url, params=arguments)
            elif method == "POST":
                response = await self.client.post(url, json=arguments)
            elif method == "PATCH":
                response = await self.client.patch(url, json=arguments)
            elif method == "DELETE":
                response = await self.client.delete(url)

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Tool execution error: {tool_name} - {str(e)}")
            return {"error": str(e), "tool": tool_name}

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """Get MCP tools manifest for AI clients"""
        return [tool.dict() for tool in self.tools]

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance
somniproperty_mcp = SomniPropertyMCPServer()
