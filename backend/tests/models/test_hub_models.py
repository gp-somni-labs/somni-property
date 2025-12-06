"""
Tests for Hub and Alert database models
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from db.models import PropertyEdgeNode, Alert


class TestPropertyEdgeNodeModel:
    """Test PropertyEdgeNode (Hub) model"""

    @pytest.mark.asyncio
    async def test_create_property_hub(self, db_session: AsyncSession):
        """Test creating a property hub"""
        hub = PropertyEdgeNode(
            name="Test Property Hub",
            location="Building A - Server Room",
            hub_type="property",
            status="online",
            ip_address="192.168.1.100",
            k3s_version="v1.28.5",
            home_assistant_version="2024.1.0"
        )
        
        db_session.add(hub)
        await db_session.commit()
        await db_session.refresh(hub)
        
        assert hub.id is not None
        assert hub.name == "Test Property Hub"
        assert hub.hub_type == "property"
        assert hub.status == "online"

    @pytest.mark.asyncio
    async def test_create_residential_hub(self, db_session: AsyncSession):
        """Test creating a residential hub"""
        hub = PropertyEdgeNode(
            name="Residential Hub 101",
            location="Unit 101",
            hub_type="residential",
            status="online",
            ip_address="192.168.1.101"
        )
        
        db_session.add(hub)
        await db_session.commit()
        await db_session.refresh(hub)
        
        assert hub.id is not None
        assert hub.hub_type == "residential"

    @pytest.mark.asyncio
    async def test_hub_alerts_relationship(self, db_session: AsyncSession):
        """Test Hub -> Alerts relationship"""
        # Create hub
        hub = PropertyEdgeNode(
            name="Hub with Alerts",
            location="Test Location",
            hub_type="property",
            status="online"
        )
        db_session.add(hub)
        await db_session.commit()
        await db_session.refresh(hub)
        
        # Create alerts for this hub
        for i in range(3):
            alert = Alert(
                hub_id=hub.id,
                severity="warning" if i < 2 else "critical",
                source="test_source",
                category="test_category",
                message=f"Test alert {i}",
                status="open"
            )
            db_session.add(alert)
        
        await db_session.commit()
        
        # Verify relationship
        result = await db_session.execute(
            select(PropertyEdgeNode).where(PropertyEdgeNode.id == hub.id)
        )
        fetched_hub = result.scalar_one()
        
        assert len(fetched_hub.alerts) == 3


class TestAlertModel:
    """Test Alert model and incident tracking"""

    @pytest.mark.asyncio
    async def test_create_alert(self, db_session: AsyncSession):
        """Test creating an alert"""
        # Create hub first
        hub = PropertyEdgeNode(
            name="Alert Test Hub",
            location="Alert Location",
            hub_type="property",
            status="online"
        )
        db_session.add(hub)
        await db_session.commit()
        await db_session.refresh(hub)
        
        # Create alert
        alert = Alert(
            hub_id=hub.id,
            severity="warning",
            source="home_assistant",
            category="device_offline",
            message="Smart thermostat offline",
            status="open"
        )
        
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.id is not None
        assert alert.severity == "warning"
        assert alert.status == "open"

    @pytest.mark.asyncio
    async def test_alert_severity_levels(self, db_session: AsyncSession):
        """Test different alert severity levels"""
        # Create hub
        hub = PropertyEdgeNode(
            name="Severity Test Hub",
            location="Severity Location",
            hub_type="residential",
            status="online"
        )
        db_session.add(hub)
        await db_session.commit()
        await db_session.refresh(hub)
        
        # Create alerts with different severities
        severities = ["info", "warning", "critical"]
        for severity in severities:
            alert = Alert(
                hub_id=hub.id,
                severity=severity,
                source="test",
                category="test",
                message=f"{severity} alert",
                status="open"
            )
            db_session.add(alert)
        
        await db_session.commit()
        
        # Verify all alerts were created
        result = await db_session.execute(
            select(Alert).where(Alert.hub_id == hub.id)
        )
        alerts = result.scalars().all()
        
        assert len(alerts) == 3
        assert {alert.severity for alert in alerts} == set(severities)

    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self, db_session: AsyncSession):
        """Test acknowledging an alert"""
        # Create hub and alert
        hub = PropertyEdgeNode(
            name="Ack Test Hub",
            location="Ack Location",
            hub_type="property",
            status="online"
        )
        db_session.add(hub)
        await db_session.commit()
        await db_session.refresh(hub)
        
        alert = Alert(
            hub_id=hub.id,
            severity="critical",
            source="kubernetes",
            category="deployment_failed",
            message="Pod deployment failed",
            status="open"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        # Acknowledge alert
        alert.status = "acknowledged"
        alert.acknowledged_by = "admin@example.com"
        alert.acknowledged_at = datetime.utcnow()
        
        await db_session.commit()
        await db_session.refresh(alert)
        
        assert alert.status == "acknowledged"
        assert alert.acknowledged_by == "admin@example.com"
        assert alert.acknowledged_at is not None

    @pytest.mark.asyncio
    async def test_alert_hub_relationship(self, db_session: AsyncSession):
        """Test Alert -> Hub relationship"""
        # Create hub and alert
        hub = PropertyEdgeNode(
            name="Relationship Hub",
            location="Relationship Location",
            hub_type="property",
            status="online"
        )
        db_session.add(hub)
        await db_session.commit()
        await db_session.refresh(hub)
        
        alert = Alert(
            hub_id=hub.id,
            severity="info",
            source="monitoring",
            category="system_update",
            message="System update available",
            status="open"
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        
        # Verify relationship
        result = await db_session.execute(
            select(Alert).where(Alert.id == alert.id)
        )
        fetched_alert = result.scalar_one()
        
        assert fetched_alert.hub.name == "Relationship Hub"
        assert fetched_alert.hub.hub_type == "property"
