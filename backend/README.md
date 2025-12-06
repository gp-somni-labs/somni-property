# SomniProperty Backend

FastAPI backend for multi-unit property management with building automation integration.

## Overview

SomniProperty is an enterprise-grade property management system designed for multi-unit residential properties with integrated IoT and building automation. It provides comprehensive tenant management, lease tracking, payment processing, work order management, and AI-powered assistance.

## Architecture

### Tech Stack
- **Framework**: FastAPI 0.104+ (async Python web framework)
- **Database**: PostgreSQL 15+ with AsyncPG driver
- **ORM**: SQLAlchemy 2.0+ (async mode)
- **Migrations**: Alembic
- **Authentication**: Authelia SSO via forwarded headers
- **Message Broker**: EMQX MQTT (optional)
- **Container Runtime**: Kubernetes (K3s)

### Key Features
- ✅ **96 Secured API Endpoints** - All routes protected with Authelia SSO
- ✅ **Rate Limiting** - 100 requests/minute per user (configurable)
- ✅ **Audit Logging** - All API operations logged with user context
- ✅ **Request Tracing** - Unique request IDs for distributed tracing
- ✅ **Custom Exceptions** - 8 business logic exception classes
- ✅ **Invoice Ninja Integration** - Professional invoicing and billing
- ✅ **IoT Device Management** - MQTT-based sensor and automation control
- ✅ **AI Assistant** - Ollama-powered chatbot for property management
- ✅ **Document Management** - Paperless-ngx integration with OCR

## Project Structure

```
backend/
├── main.py                     # Application entry point
├── core/
│   ├── config.py              # Environment configuration
│   ├── security.py            # Authentication helpers
│   └── exceptions/            # Custom exception classes
│       └── __init__.py        # 8 business logic exceptions
├── middleware/
│   ├── __init__.py            # Middleware exports
│   ├── rate_limiter.py        # 100 req/min rate limiting
│   ├── audit_logger.py        # Audit trail logging
│   ├── request_id.py          # Request ID tracking
│   └── error_handler.py       # Global error handling
├── db/
│   ├── database.py            # Async database connection
│   └── models.py              # SQLAlchemy ORM models
├── api/
│   └── v1/                    # API version 1 endpoints
│       ├── properties.py      # Property management (5 endpoints)
│       ├── buildings.py       # Building management (5 endpoints)
│       ├── units.py           # Unit management (7 endpoints)
│       ├── tenants.py         # Tenant management (7 endpoints)
│       ├── leases.py          # Lease management (9 endpoints)
│       ├── payments.py        # Payment processing (9 endpoints)
│       ├── workorders.py      # Work order tracking (11 endpoints)
│       ├── utilities.py       # Utility bill management (11 endpoints)
│       ├── iot.py             # IoT device control (12 endpoints)
│       ├── ai_chat.py         # AI assistant endpoints (7 endpoints)
│       ├── websocket.py       # Real-time WebSocket (2 endpoints)
│       ├── documents.py       # Document management (3 endpoints)
│       └── invoices.py        # Invoice Ninja integration (10 endpoints)
├── services/
│   ├── mqtt_client.py         # EMQX MQTT client
│   ├── invoice_ninja.py       # Invoice Ninja API client
│   ├── stripe_client.py       # Stripe payment processing
│   ├── docuseal_client.py     # Document signing service
│   ├── minio_client.py        # Object storage client
│   ├── paperless_client.py    # Document OCR integration
│   ├── home_assistant.py      # Home Assistant integration (TODO)
│   ├── gotify_client.py       # Push notification service
│   ├── firefly_client.py      # Financial management
│   ├── ntfy_client.py         # NTFY push notifications
│   └── ollama_client.py       # AI/LLM inference service
├── schemas/
│   └── *.py                   # Pydantic models for validation
├── alembic/
│   ├── env.py                 # Alembic configuration
│   └── versions/              # Database migrations
├── tests/
│   ├── test_auth.py           # Authentication tests
│   ├── test_properties.py     # Property endpoint tests
│   ├── test_tenants.py        # Tenant endpoint tests
│   └── test_leases.py         # Lease endpoint tests
├── utils/                     # Utility functions (TODO)
├── Dockerfile                 # Production container image
└── requirements.txt           # Python dependencies
```

## Database Schema

The application uses PostgreSQL with 15 tables:

### Core Tables
- **properties** - Property information (address, units, owner)
- **buildings** - Building details within properties
- **units** - Individual rental units
- **tenants** - Tenant information
- **leases** - Lease agreements and terms

### Operations Tables
- **rent_payments** - Payment tracking and history
- **work_orders** - Maintenance request management
- **utility_bills** - Utility bill tracking
- **documents** - Document metadata and storage
- **contractors** - Contractor management

### IoT & Automation Tables
- **iot_devices** - Smart devices and sensors
- **sensor_readings** - Time-series sensor data
- **automation_rules** - Automation rule definitions

### System Tables
- **access_logs** - Audit trail for access control
- **alembic_version** - Database migration version

## API Endpoints

### Properties API (`/api/v1/properties`)
- `GET /` - List all properties (with filters)
- `POST /` - Create new property
- `GET /{id}` - Get property details
- `PUT /{id}` - Update property
- `DELETE /{id}` - Delete property

### Buildings API (`/api/v1/buildings`)
- `GET /` - List buildings
- `POST /` - Create building
- `GET /{id}` - Get building details
- `PUT /{id}` - Update building
- `DELETE /{id}` - Delete building

### Units API (`/api/v1/units`)
- `GET /` - List units (with availability filter)
- `POST /` - Create unit
- `GET /{id}` - Get unit details
- `PUT /{id}` - Update unit
- `DELETE /{id}` - Delete unit
- `GET /{id}/history` - Get unit rental history
- `GET /available` - List available units

### Tenants API (`/api/v1/tenants`)
- `GET /` - List tenants
- `POST /` - Create tenant
- `GET /{id}` - Get tenant details
- `PUT /{id}` - Update tenant
- `DELETE /{id}` - Delete tenant
- `GET /{id}/leases` - Get tenant lease history
- `GET /{id}/payments` - Get tenant payment history

### Leases API (`/api/v1/leases`)
- `GET /` - List leases (with status filter)
- `POST /` - Create lease
- `GET /{id}` - Get lease details
- `PUT /{id}` - Update lease
- `DELETE /{id}` - Delete lease
- `POST /{id}/renew` - Renew lease
- `POST /{id}/terminate` - Terminate lease
- `GET /expiring` - List expiring leases
- `GET /active` - List active leases

### Payments API (`/api/v1/payments`)
- `GET /` - List payments
- `POST /` - Record payment
- `GET /{id}` - Get payment details
- `PUT /{id}` - Update payment
- `DELETE /{id}` - Delete payment
- `GET /overdue` - List overdue payments
- `GET /tenant/{tenant_id}` - Get tenant payments
- `POST /{id}/refund` - Process refund
- `GET /reports/summary` - Payment summary report

### Work Orders API (`/api/v1/workorders`)
- `GET /` - List work orders (with status filter)
- `POST /` - Create work order
- `GET /{id}` - Get work order details
- `PUT /{id}` - Update work order
- `DELETE /{id}` - Delete work order
- `POST /{id}/assign` - Assign to contractor
- `POST /{id}/complete` - Mark complete
- `POST /{id}/comment` - Add comment
- `GET /urgent` - List urgent work orders
- `GET /unit/{unit_id}` - Get unit work orders
- `GET /stats` - Work order statistics

### Utilities API (`/api/v1/utilities`)
- `GET /bills` - List utility bills
- `POST /bills` - Create bill
- `GET /bills/{id}` - Get bill details
- `PUT /bills/{id}` - Update bill
- `DELETE /bills/{id}` - Delete bill
- `GET /bills/property/{property_id}` - Get property bills
- `GET /bills/overdue` - List overdue bills
- `POST /bills/{id}/pay` - Mark bill as paid
- `GET /usage/analytics` - Usage analytics
- `GET /costs/forecast` - Cost forecasting
- `GET /providers` - List utility providers

### IoT API (`/api/v1/iot`)
- `GET /devices` - List IoT devices
- `POST /devices` - Register device
- `GET /devices/{id}` - Get device details
- `PUT /devices/{id}` - Update device
- `DELETE /devices/{id}` - Remove device
- `POST /devices/{id}/command` - Send command
- `GET /devices/{id}/readings` - Get sensor readings
- `GET /sensors/readings` - List all readings
- `POST /sensors/readings` - Record reading
- `GET /automation/rules` - List automation rules
- `POST /automation/rules` - Create rule
- `GET /devices/unit/{unit_id}` - Get unit devices

### AI Chat API (`/api/v1/chat`)
- `POST /message` - Send chat message
- `GET /history` - Get chat history
- `DELETE /history` - Clear history
- `GET /suggestions` - Get AI suggestions
- `POST /analyze/property` - Analyze property
- `POST /analyze/tenant` - Analyze tenant
- `GET /insights` - Get AI insights

### WebSocket API (`/api/v1/ws`)
- `WS /{client_id}` - Real-time updates connection
- `GET /active-connections` - List active connections

### Documents API (`/api/v1/documents`)
- `POST /upload` - Upload document
- `GET /{id}` - Download document
- `GET /` - List documents (with filters)

### Invoices API (`/api/v1/invoices`)
- `GET /` - List invoices
- `POST /` - Create invoice
- `GET /{id}` - Get invoice details
- `PUT /{id}` - Update invoice
- `DELETE /{id}` - Delete invoice
- `POST /{id}/send` - Send invoice to tenant
- `POST /{id}/pay` - Record payment
- `GET /tenant/{tenant_id}` - Get tenant invoices
- `GET /overdue` - List overdue invoices
- `GET /sync` - Sync with Invoice Ninja

## Middleware Pipeline

Requests flow through middleware in this order (first added = last executed):

1. **CORS Middleware** - Cross-origin resource sharing
2. **Request ID Middleware** - Adds unique `X-Request-ID` header
3. **Rate Limit Middleware** - Enforces 100 req/min per user
4. **Audit Log Middleware** - Logs all requests with user context
5. **Error Handler Middleware** - Catches unhandled exceptions

### Rate Limiting
- Default: 100 requests per minute per user
- Tracks by `X-Forwarded-User` header or IP address
- Returns `429 Too Many Requests` when exceeded
- Adds `X-RateLimit-Limit` header to responses

### Audit Logging
Logs include:
- Timestamp
- User (from `X-Forwarded-User` header)
- User email (from `X-Forwarded-Email` header)
- HTTP method and path
- Status code
- Response time in milliseconds
- Request body (for POST/PUT/PATCH/DELETE, max 1000 chars)

### Error Handling
All unhandled exceptions are caught and return:
```json
{
  "detail": "An internal server error occurred",
  "request_id": "uuid-here",
  "type": "InternalServerError"
}
```

## Authentication

Authentication is handled by **Authelia SSO** via Traefik ingress. All requests must include:

- `X-Forwarded-User`: Username (required)
- `X-Forwarded-Email`: User email (optional)
- `X-Forwarded-Groups`: User groups (optional)

The `core/security.py` module provides helper functions:
```python
from core.security import get_current_user

@app.get("/api/v1/properties")
async def list_properties(current_user: dict = Depends(get_current_user)):
    # current_user contains: username, email, groups
    pass
```

## Environment Configuration

Configuration is managed in `core/config.py` and loaded from environment variables:

### Required Variables
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Security
SECRET_KEY=your-256-bit-secret-key-here

# Application
APP_NAME=SomniProperty Manager
APP_VERSION=1.0.0
DEBUG=false
```

### Optional Variables
```bash
# CORS
CORS_ORIGINS=["http://localhost:3000","https://property.home.lan"]

# MQTT (optional)
MQTT_BROKER=emqx.core.svc.cluster.local
MQTT_PORT=1883
MQTT_USERNAME=somniproperty
MQTT_PASSWORD=your-mqtt-password
MQTT_CLIENT_ID=somniproperty-backend

# External Services
INVOICE_NINJA_URL=https://invoices.home.lan
INVOICE_NINJA_TOKEN=your-token-here
STRIPE_API_KEY=sk_test_...
DOCUSEAL_API_URL=https://docuseal.home.lan
MINIO_ENDPOINT=minio.storage.svc.cluster.local:9000
PAPERLESS_URL=https://paperless.home.lan
PAPERLESS_TOKEN=your-token-here
HOME_ASSISTANT_URL=http://homeassistant.default.svc.cluster.local:8123
HOME_ASSISTANT_TOKEN=your-token-here
GOTIFY_URL=https://gotify.home.lan
GOTIFY_TOKEN=your-token-here
FIREFLY_URL=https://firefly.home.lan
FIREFLY_TOKEN=your-token-here
NTFY_URL=https://ntfy.sh
OLLAMA_URL=http://ollama.ai.svc.cluster.local:11434
```

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Poetry or pip

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/somniproperty"
export SECRET_KEY="your-secret-key-here"
export DEBUG=true

# Run database migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests
```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster (K3s/K8s)
- PostgreSQL database deployed
- Authelia SSO configured
- Traefik ingress controller

### Deployment Steps

1. **Create namespace** (if not exists):
```bash
kubectl create namespace somniproperty
```

2. **Create secrets**:
```bash
kubectl create secret generic somniproperty-secrets \
  --from-literal=database-url='postgresql+asyncpg://user:pass@somniproperty-postgres:5432/somniproperty' \
  --from-literal=secret-key='your-256-bit-secret-key' \
  -n somniproperty
```

3. **Build and push image**:
```bash
# Build image
docker build -t somniproperty-backend:latest .

# Load into K3s (for local cluster)
docker save somniproperty-backend:latest | sudo k3s ctr images import -

# Or push to registry
docker push your-registry/somniproperty-backend:latest
```

4. **Deploy application**:
```bash
kubectl apply -f manifests/utilities/somniproperty-production.yaml
```

5. **Verify deployment**:
```bash
# Check pods
kubectl get pods -n somniproperty

# Check logs
kubectl logs -n somniproperty deployment/somniproperty-backend --tail=50

# Check service
kubectl get svc -n somniproperty somniproperty-backend
```

### Database Migrations

Migrations run automatically via init container in Kubernetes deployment. To run manually:

```bash
# Get pod name
POD=$(kubectl get pods -n somniproperty -l component=backend -o jsonpath='{.items[0].metadata.name}')

# Run migration
kubectl exec -n somniproperty $POD -- alembic upgrade head

# Check current version
kubectl exec -n somniproperty $POD -- alembic current

# Create new migration
kubectl exec -n somniproperty $POD -- alembic revision --autogenerate -m "Description"
```

### Health Checks

The application exposes health check endpoints:

- `GET /health` - Kubernetes liveness/readiness probe
- `GET /` - Root endpoint with API information
- `GET /api/docs` - Interactive API documentation (Swagger UI)
- `GET /api/redoc` - Alternative API documentation (ReDoc)
- `GET /api/openapi.json` - OpenAPI schema

## Troubleshooting

### Database Connection Issues
```bash
# Check database pod
kubectl get pods -n somniproperty -l app=postgres

# Test connection from backend pod
kubectl exec -n somniproperty deployment/somniproperty-backend -- \
  python -c "from core.config import settings; print(settings.DATABASE_URL)"

# Check database tables
kubectl exec -n somniproperty deployment/somniproperty-postgres -- \
  psql -U somniproperty -d somniproperty -c "\dt"
```

### MQTT Connection Issues
```bash
# Check MQTT broker
kubectl get pods -n core -l app=emqx

# Test MQTT from backend pod
kubectl exec -n somniproperty deployment/somniproperty-backend -- \
  python -c "from services.mqtt_client import mqtt_service; print(mqtt_service)"
```

### Authentication Issues
```bash
# Check if headers are being forwarded
kubectl logs -n somniproperty deployment/somniproperty-backend | grep "X-Forwarded-User"

# Check Authelia middleware
kubectl get middleware -n network authelia -o yaml
```

### Rate Limit Issues
```bash
# Check rate limit headers in response
curl -I https://property.home.lan/api/v1/properties

# Increase rate limit (edit main.py)
app.add_middleware(RateLimitMiddleware, requests_per_minute=200)
```

## External Service Integration

### Invoice Ninja Setup
1. Create API token in Invoice Ninja dashboard
2. Set environment variable: `INVOICE_NINJA_TOKEN=your-token`
3. Test connection: `GET /api/v1/invoices/sync`

### Stripe Payment Processing
1. Get API key from Stripe dashboard
2. Set environment variable: `STRIPE_API_KEY=sk_test_...`
3. Test with payment endpoint: `POST /api/v1/payments`

### Paperless Document Management
1. Create API token in Paperless settings
2. Set environment variables:
   ```bash
   PAPERLESS_URL=https://paperless.home.lan
   PAPERLESS_TOKEN=your-token
   ```
3. Upload document: `POST /api/v1/documents/upload`

### Ollama AI Assistant
1. Deploy Ollama in `ai` namespace
2. Set environment variable: `OLLAMA_URL=http://ollama.ai.svc.cluster.local:11434`
3. Test chat: `POST /api/v1/chat/message`

## API Documentation

Once deployed, access interactive API documentation:

- **Swagger UI**: `https://property.home.lan/api/docs`
- **ReDoc**: `https://property.home.lan/api/redoc`
- **OpenAPI JSON**: `https://property.home.lan/api/openapi.json`

## Performance Considerations

### Database Optimization
- All database queries use async operations (AsyncPG)
- Connection pooling configured in `db/database.py`
- Indexes on foreign keys and frequently queried fields

### Caching Strategy
- Rate limiter uses in-memory cache (consider Redis for multi-pod deployments)
- Static responses can be cached at Traefik level

### Scaling
- Stateless design allows horizontal pod scaling
- WebSocket connections require sticky sessions
- MQTT client uses shared subscriptions for load balancing

## Security Best Practices

1. **Never commit secrets** - Use Kubernetes secrets or environment variables
2. **Rotate SECRET_KEY** - Generate new key periodically: `openssl rand -hex 32`
3. **Use TLS** - Always deploy behind HTTPS ingress
4. **Validate input** - All endpoints use Pydantic validation
5. **Rate limiting** - Adjust limits based on usage patterns
6. **Audit logs** - Monitor for suspicious activity
7. **Update dependencies** - Regular security updates

## Contributing

### Code Style
- Follow PEP 8 guidelines
- Use type hints for all functions
- Document all public APIs with docstrings

### Adding New Endpoints
1. Create endpoint in `api/v1/your_module.py`
2. Create Pydantic schema in `schemas/your_module.py`
3. Add database model if needed in `db/models.py`
4. Write tests in `tests/test_your_module.py`
5. Update this README

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Add your_table"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head
```

## License

Proprietary - SomniProperty Manager

## Support

For issues or questions:
- Check logs: `kubectl logs -n somniproperty deployment/somniproperty-backend`
- Review API docs: `https://property.home.lan/api/docs`
- Check database: Verify tables exist and migrations applied
