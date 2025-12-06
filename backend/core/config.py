"""
Somni Property Manager - Configuration
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import json
import os


def clean_secret(value: Optional[str]) -> Optional[str]:
    """Clean Infisical secrets that may have JSON quotes and newlines"""
    if value is None:
        return None
    # Remove JSON quotes and newlines
    return value.strip().strip('"').strip('\n').strip()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Somni Property Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database (read from Infisical-synced secret or fallback to old secret)
    DATABASE_URL: str = clean_secret(
        os.getenv("somniproperty_somniproperty-postgres-secret_DATABASE_URL")
    ) or "postgresql+asyncpg://somniproperty:somni-postgres-secure-password-change-me@somniproperty-postgres:5432/somniproperty"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # MQTT (EMQX) - will be added to Infisical in Phase 2
    MQTT_BROKER: str = "emqx.core.svc.cluster.local"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = clean_secret(
        os.getenv("somniproperty_mqtt_username_MQTT_USERNAME") or
        os.getenv("MQTT_USERNAME") or
        os.getenv("USERNAME")
    )
    MQTT_PASSWORD: Optional[str] = clean_secret(
        os.getenv("somniproperty_mqtt_password_MQTT_PASSWORD") or
        os.getenv("MQTT_PASSWORD") or
        os.getenv("PASSWORD")
    )
    MQTT_KEEPALIVE: int = 60
    MQTT_TOPIC_PREFIX: str = "somni/property-manager"

    # Home Assistant Instances (JSON string in env)
    # Format: [{"id": "oak-street", "url": "http://...", "token": "..."}]
    HA_INSTANCES_JSON: str = "[]"

    @property
    def HA_INSTANCES(self) -> List[dict]:
        """Parse HA instances from JSON"""
        try:
            return json.loads(self.HA_INSTANCES_JSON)
        except:
            return []

    # Invoice Ninja Integration
    INVOICE_NINJA_URL: str = "http://invoiceninja.utilities.svc.cluster.local"
    INVOICE_NINJA_TOKEN: Optional[str] = None
    INVOICE_NINJA_AUTO_GENERATE: bool = True  # Auto-generate invoices for rent payments

    # Firefly III Integration
    FIREFLY_III_URL: str = "https://finances.home.lan"
    FIREFLY_III_TOKEN: Optional[str] = None

    # Paperless-ngx Integration
    PAPERLESS_URL: str = "http://paperless-ngx.storage.svc.cluster.local:8000"
    PAPERLESS_TOKEN: Optional[str] = None
    PAPERLESS_AUTO_OCR: bool = True  # Automatically send documents to Paperless for OCR

    # Homebox Integration
    HOMEBOX_URL: str = "https://homebox.home.lan"

    # Notifications
    GOTIFY_URL: str = "https://gotify.home.lan"
    GOTIFY_TOKEN: Optional[str] = None
    NTFY_URL: str = "https://ntfy.home.lan"

    # Authelia Integration
    AUTHELIA_URL: str = "https://auth.home.lan"

    # Stripe Payment Integration (read from Infisical)
    STRIPE_SECRET_KEY: Optional[str] = clean_secret(
        os.getenv("somniproperty_stripe_STRIPE_SECRET_KEY_STRIPE_SECRET_KEY") or
        os.getenv("STRIPE_SECRET_KEY")
    )
    STRIPE_PUBLISHABLE_KEY: Optional[str] = clean_secret(
        os.getenv("somniproperty_stripe_STRIPE_PUBLISHABLE_KEY_STRIPE_PUBLISHABLE_KEY") or
        os.getenv("STRIPE_PUBLISHABLE_KEY")
    )
    STRIPE_WEBHOOK_SECRET: Optional[str] = clean_secret(
        os.getenv("somniproperty_stripe_STRIPE_WEBHOOK_SECRET_STRIPE_WEBHOOK_SECRET") or
        os.getenv("STRIPE_WEBHOOK_SECRET")
    )
    STRIPE_CURRENCY: str = os.getenv("STRIPE_CURRENCY", "usd")
    STRIPE_ENABLE_PAYMENT_LINKS: bool = os.getenv("STRIPE_ENABLE_PAYMENT_LINKS", "true").lower() == "true"

    # DocuSeal Document Signing
    DOCUSEAL_URL: str = "http://docuseal.utilities.svc.cluster.local"
    DOCUSEAL_API_KEY: Optional[str] = None
    DOCUSEAL_LEASE_TEMPLATE_ID: Optional[int] = None
    DOCUSEAL_WORK_ORDER_TEMPLATE_ID: Optional[int] = None
    DOCUSEAL_MOVE_IN_TEMPLATE_ID: Optional[int] = None
    DOCUSEAL_MOVE_OUT_TEMPLATE_ID: Optional[int] = None

    # MinIO Object Storage
    MINIO_ENDPOINT: str = "minio.storage.svc.cluster.local:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "somniproperty-documents"
    MINIO_SECURE: bool = False  # Use HTTPS (False for internal cluster communication)

    # Security (will use Infisical-synced secret in Phase 2)
    SECRET_KEY: str = clean_secret(
        os.getenv("somniproperty_backend_secret-key_SECRET_KEY") or
        os.getenv("SECRET-KEY") or
        os.getenv("SECRET_KEY")
    ) or "f71ba1cfb9b3d7b7c84a746529cc6a9179f2c8da4bcf96e47f62baef6aac717c"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: List[str] = [
        "https://property.home.lan",
        "https://tenant.home.lan",
        "https://employee.home.lan",  # Employee Flutter app
        "https://employee.tail58c8e4.ts.net",  # Employee via Tailscale
        "http://localhost:3000",  # Development
        "http://localhost:8080",
    ]

    # Support Ticket SLA Configuration (in hours)
    SLA_CRITICAL_HOURS: int = 2
    SLA_HIGH_HOURS: int = 4
    SLA_MEDIUM_HOURS: int = 24
    SLA_LOW_HOURS: int = 72

    # Monitoring (optional)
    SENTRY_DSN: Optional[str] = None

    # SMTP / Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "postfix.somniproperty.svc.cluster.local")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "25"))
    SMTP_USERNAME: Optional[str] = clean_secret(os.getenv("SMTP_USERNAME"))
    SMTP_PASSWORD: Optional[str] = clean_secret(os.getenv("SMTP_PASSWORD"))
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() == "true"

    # Customer Notifications
    NOTIFICATIONS_FROM_EMAIL: str = os.getenv("NOTIFICATIONS_FROM_EMAIL", "notifications@somni.property")
    NOTIFICATIONS_FROM_NAME: str = os.getenv("NOTIFICATIONS_FROM_NAME", "SomniProperty")
    CUSTOMER_PORTAL_BASE_URL: str = os.getenv("CUSTOMER_PORTAL_BASE_URL", "https://property.home.lan")

    # JWT for Customer Portal Tokens
    JWT_SECRET_KEY: str = clean_secret(
        os.getenv("JWT_SECRET_KEY") or
        os.getenv("SECRET_KEY")
    ) or "your-secret-key-change-in-production"

    # Customer Portal Token Secret Key (REQUIRED for security)
    # This key is used to sign HMAC tokens for the customer quote portal
    # MUST be set to a secure random value in production
    CUSTOMER_PORTAL_SECRET_KEY: str = clean_secret(
        os.getenv("CUSTOMER_PORTAL_SECRET_KEY")
    ) or ""

    # Twilio SMS Configuration (optional)
    TWILIO_ACCOUNT_SID: Optional[str] = clean_secret(os.getenv("TWILIO_ACCOUNT_SID"))
    TWILIO_AUTH_TOKEN: Optional[str] = clean_secret(os.getenv("TWILIO_AUTH_TOKEN"))
    TWILIO_PHONE_NUMBER: Optional[str] = os.getenv("TWILIO_PHONE_NUMBER")

    # Cal.com Scheduling Integration
    CALCOM_URL: str = os.getenv("CALCOM_URL", "https://cal.home.lan")
    CALCOM_API_KEY: Optional[str] = clean_secret(os.getenv("CALCOM_API_KEY"))
    CALCOM_DEFAULT_EVENT_TYPE_ID: Optional[int] = int(os.getenv("CALCOM_DEFAULT_EVENT_TYPE_ID", "0")) or None

    # Kubernetes Cluster Management
    K8S_IN_CLUSTER: bool = os.getenv("K8S_IN_CLUSTER", "true").lower() == "true"
    K8S_KUBECONFIG_PATH: Optional[str] = os.getenv("KUBECONFIG")
    ARGOCD_URL: str = os.getenv("ARGOCD_URL", "https://argocd.home.lan")
    ARGOCD_TOKEN: Optional[str] = clean_secret(os.getenv("ARGOCD_TOKEN"))

    # VPN Authentication (for secure VPN access without Authelia)
    VPN_AUTH_TOKEN: Optional[str] = clean_secret(os.getenv("VPN_AUTH_TOKEN"))

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
