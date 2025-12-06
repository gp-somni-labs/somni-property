"""
Contractor & Staff Management Service

Intelligent resource allocation for work orders:
1. Check in-house staff availability
2. Check approved contractor list
3. Trigger automated quote gathering if neither available

Integrates with:
- Quote lookup service for automated contractor discovery
- n8n for email/API quote requests
- Yelp/Google APIs for contractor discovery
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel, EmailStr
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class StaffMember(BaseModel):
    """In-house staff member"""
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str]
    position: str
    department: Optional[str]
    skills: List[str] = []
    hourly_rate: Optional[Decimal]
    available: bool = True
    current_workload: int = 0
    max_concurrent_jobs: int = 5
    average_rating: Optional[Decimal]


class Contractor(BaseModel):
    """Approved contractor/vendor"""
    id: uuid.UUID
    company_name: str
    contact_name: Optional[str]
    email: Optional[EmailStr]
    phone: str
    categories: List[str] = []
    hourly_rate: Optional[Decimal]
    emergency_rate: Optional[Decimal]
    approval_status: str
    available: bool = True
    average_rating: Optional[Decimal]
    total_jobs_completed: int = 0
    on_time_rate: Optional[Decimal]
    response_time_hours: Optional[int]


class ContractorQuote(BaseModel):
    """Quote from contractor for work"""
    id: uuid.UUID
    contractor_name: str
    contractor_email: Optional[str]
    contractor_phone: Optional[str]
    quoted_amount: Optional[Decimal]
    quote_breakdown: Optional[Dict]
    availability_date: Optional[date]
    estimated_completion_date: Optional[date]
    status: str
    ai_recommendation: Optional[Dict]


class ResourceMatch(BaseModel):
    """Matched resource for work order"""
    resource_type: str  # 'staff', 'contractor'
    resource_id: uuid.UUID
    resource_name: str
    categories: List[str]
    hourly_rate: Optional[Decimal]
    availability_score: float  # 0.0 - 1.0
    match_score: float  # 0.0 - 1.0 based on skills, rating, workload
    estimated_cost: Optional[Decimal]
    estimated_response_time_hours: Optional[int]
    reason: str  # Why this resource was selected


# ============================================================================
# CONTRACTOR MANAGER SERVICE
# ============================================================================

class ContractorManagerService:
    """
    Main service for managing staff, contractors, and work order assignments
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # INTELLIGENT RESOURCE MATCHING
    # ========================================================================

    async def find_best_resource(
        self,
        service_category: str,
        property_id: Optional[uuid.UUID] = None,
        urgency: str = 'normal',
        estimated_hours: Optional[Decimal] = None,
        max_budget: Optional[Decimal] = None,
        prefer_staff: bool = True
    ) -> Optional[ResourceMatch]:
        """
        Find the best available resource (staff or contractor) for a work order

        Priority:
        1. Available in-house staff with matching skills
        2. Approved contractors with matching categories
        3. If none found, return None (trigger auto-quote gathering)

        Scoring factors:
        - Skill/category match
        - Current workload (staff only)
        - Average rating
        - Cost
        - Response time
        - Past performance with this property
        """
        matches: List[ResourceMatch] = []

        # Step 1: Check in-house staff (if preferred)
        if prefer_staff:
            staff_matches = await self._find_available_staff(
                service_category=service_category,
                property_id=property_id,
                urgency=urgency,
                estimated_hours=estimated_hours,
                max_budget=max_budget
            )
            matches.extend(staff_matches)

        # Step 2: Check approved contractors
        contractor_matches = await self._find_available_contractors(
            service_category=service_category,
            property_id=property_id,
            urgency=urgency,
            estimated_hours=estimated_hours,
            max_budget=max_budget
        )
        matches.extend(contractor_matches)

        if not matches:
            logger.warning(f"No available resources found for category '{service_category}' - will trigger auto-quote")
            return None

        # Sort by match score (highest first)
        matches.sort(key=lambda x: x.match_score, reverse=True)

        # Return best match
        best_match = matches[0]
        logger.info(
            f"Best resource match: {best_match.resource_type} '{best_match.resource_name}' "
            f"(score: {best_match.match_score:.2f})"
        )

        return best_match

    async def _find_available_staff(
        self,
        service_category: str,
        property_id: Optional[uuid.UUID],
        urgency: str,
        estimated_hours: Optional[Decimal],
        max_budget: Optional[Decimal]
    ) -> List[ResourceMatch]:
        """Find available in-house staff members"""
        # This would query the staff table - simplified here
        # In production, use actual SQLAlchemy query

        matches = []

        # TODO: Implement actual database query
        # Example logic:
        # SELECT * FROM staff
        # WHERE available = true
        # AND employment_status = 'active'
        # AND skills @> '["plumbing"]'  -- JSONB contains operator
        # AND current_workload < max_concurrent_jobs
        # ORDER BY average_rating DESC, current_workload ASC

        logger.info(f"Checking in-house staff for category: {service_category}")

        # Placeholder - would be replaced with real query results
        return matches

    async def _find_available_contractors(
        self,
        service_category: str,
        property_id: Optional[uuid.UUID],
        urgency: str,
        estimated_hours: Optional[Decimal],
        max_budget: Optional[Decimal]
    ) -> List[ResourceMatch]:
        """Find available approved contractors"""
        matches = []

        # TODO: Implement actual database query
        # Example logic:
        # SELECT * FROM contractors
        # WHERE available = true
        # AND approval_status = 'approved'
        # AND categories @> '["plumbing"]'  -- JSONB contains operator
        # ORDER BY average_rating DESC, total_jobs_completed DESC

        logger.info(f"Checking approved contractors for category: {service_category}")

        # Placeholder - would be replaced with real query results
        return matches

    # ========================================================================
    # STAFF MANAGEMENT
    # ========================================================================

    async def create_staff_member(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str],
        position: str,
        department: Optional[str],
        skills: List[str],
        hourly_rate: Optional[Decimal] = None
    ) -> uuid.UUID:
        """Create new staff member"""
        # TODO: Implement database insert
        logger.info(f"Creating staff member: {first_name} {last_name}")
        return uuid.uuid4()  # Placeholder

    async def update_staff_availability(
        self,
        staff_id: uuid.UUID,
        available: bool,
        reason: Optional[str] = None
    ) -> bool:
        """Update staff availability status"""
        # TODO: Implement database update
        logger.info(f"Updating staff {staff_id} availability to: {available}")
        return True

    async def get_staff_workload(self, staff_id: uuid.UUID) -> Dict[str, Any]:
        """Get staff member's current workload and assignments"""
        # TODO: Implement query for active assignments
        return {
            'staff_id': str(staff_id),
            'current_workload': 0,
            'active_assignments': [],
            'completed_this_week': 0,
            'average_completion_time': None
        }

    # ========================================================================
    # CONTRACTOR MANAGEMENT
    # ========================================================================

    async def create_contractor(
        self,
        company_name: str,
        contact_name: Optional[str],
        email: Optional[str],
        phone: str,
        categories: List[str],
        hourly_rate: Optional[Decimal] = None,
        source: str = 'manual_entry'
    ) -> uuid.UUID:
        """Create new contractor (pending approval)"""
        # TODO: Implement database insert
        logger.info(f"Creating contractor: {company_name} (source: {source})")
        return uuid.uuid4()  # Placeholder

    async def approve_contractor(
        self,
        contractor_id: uuid.UUID,
        approver_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> bool:
        """Approve a pending contractor"""
        # TODO: Implement database update
        logger.info(f"Approving contractor {contractor_id} by {approver_id}")
        return True

    async def update_contractor_rating(
        self,
        contractor_id: uuid.UUID,
        rating: int,
        review_text: Optional[str] = None,
        work_order_id: Optional[uuid.UUID] = None,
        reviewer_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Add review for contractor (triggers rating recalculation)"""
        # TODO: Implement insert into contractor_reviews table
        logger.info(f"Adding review for contractor {contractor_id}: {rating}/5 stars")
        return True

    # ========================================================================
    # WORK ORDER ASSIGNMENT
    # ========================================================================

    async def assign_work_order(
        self,
        work_order_id: uuid.UUID,
        resource_type: str,  # 'staff' or 'contractor'
        resource_id: uuid.UUID,
        assigned_by: uuid.UUID,
        estimated_hours: Optional[Decimal] = None,
        estimated_cost: Optional[Decimal] = None,
        assignment_method: str = 'auto_assigned'
    ) -> uuid.UUID:
        """
        Assign work order to staff or contractor

        Returns: assignment_id
        """
        # TODO: Implement database insert into work_order_assignments
        logger.info(
            f"Assigning work order {work_order_id} to {resource_type} {resource_id} "
            f"(method: {assignment_method})"
        )

        assignment_id = uuid.uuid4()

        # TODO: Send notification to assignee
        # - Staff: Email + in-app notification
        # - Contractor: Email + SMS

        return assignment_id

    async def update_assignment_status(
        self,
        assignment_id: uuid.UUID,
        status: str,  # 'accepted', 'declined', 'in_progress', 'completed'
        notes: Optional[str] = None
    ) -> bool:
        """Update work order assignment status"""
        # TODO: Implement database update
        logger.info(f"Updating assignment {assignment_id} status to: {status}")

        # If completed, collect completion metrics
        if status == 'completed':
            # TODO: Request rating/review
            pass

        return True

    # ========================================================================
    # QUOTE MANAGEMENT
    # ========================================================================

    async def request_quotes(
        self,
        work_order_id: uuid.UUID,
        service_category: str,
        service_description: str,
        property_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        urgency: str = 'normal',
        target_quote_count: int = 3,
        deadline_hours: int = 48
    ) -> uuid.UUID:
        """
        Trigger automated quote gathering campaign

        Will:
        1. Search for contractors via Yelp/Google APIs
        2. Check existing contractor database
        3. Send quote requests via n8n workflow (email/API)
        4. Track responses
        5. Present quotes for approval when ready

        Returns: campaign_id
        """
        from services.quote_lookup_service import get_quote_lookup_service

        logger.info(
            f"Starting quote request campaign for work order {work_order_id} "
            f"(target: {target_quote_count} quotes)"
        )

        # Create campaign
        campaign_id = uuid.uuid4()

        # TODO: Insert into quote_request_campaigns table

        # Trigger quote lookup service
        quote_service = get_quote_lookup_service(self.db)
        await quote_service.start_quote_campaign(
            campaign_id=campaign_id,
            work_order_id=work_order_id,
            service_category=service_category,
            service_description=service_description,
            property_id=property_id,
            unit_id=unit_id,
            urgency=urgency,
            target_quote_count=target_quote_count,
            deadline_hours=deadline_hours
        )

        return campaign_id

    async def get_quotes_for_work_order(
        self,
        work_order_id: uuid.UUID
    ) -> List[ContractorQuote]:
        """Get all quotes received for a work order"""
        # TODO: Query contractor_quotes table
        quotes = []

        logger.info(f"Retrieved {len(quotes)} quotes for work order {work_order_id}")

        return quotes

    async def select_quote(
        self,
        quote_id: uuid.UUID,
        selected_by: uuid.UUID,
        selection_reason: Optional[str] = None
    ) -> Tuple[bool, Optional[uuid.UUID]]:
        """
        Select a quote and assign work order to contractor

        Returns: (success, assignment_id)
        """
        # TODO: Implement quote selection logic
        # 1. Mark quote as selected
        # 2. Create contractor if not in system
        # 3. Assign work order to contractor
        # 4. Notify contractor of selection
        # 5. Notify other contractors of rejection

        logger.info(f"Selecting quote {quote_id} by {selected_by}")

        return (True, uuid.uuid4())

    # ========================================================================
    # PERFORMANCE ANALYTICS
    # ========================================================================

    async def get_contractor_performance(
        self,
        contractor_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get detailed performance metrics for contractor"""
        # TODO: Query multiple tables for comprehensive metrics
        return {
            'contractor_id': str(contractor_id),
            'total_jobs': 0,
            'completion_rate': 0.0,
            'average_rating': 0.0,
            'on_time_rate': 0.0,
            'response_time_avg_hours': 0.0,
            'recent_reviews': [],
            'jobs_by_category': {},
            'revenue_total': 0.0
        }

    async def get_staff_performance(
        self,
        staff_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get detailed performance metrics for staff member"""
        # TODO: Query work_order_assignments for metrics
        return {
            'staff_id': str(staff_id),
            'total_jobs': 0,
            'average_rating': 0.0,
            'average_completion_time_hours': 0.0,
            'jobs_this_month': 0,
            'efficiency_score': 0.0
        }

    async def get_resource_utilization(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get resource utilization metrics across all staff and contractors"""
        return {
            'period': {'start': str(start_date), 'end': str(end_date)},
            'total_jobs': 0,
            'staff_jobs': 0,
            'contractor_jobs': 0,
            'staff_utilization_rate': 0.0,
            'average_cost_per_job': 0.0,
            'in_house_vs_contractor_cost_ratio': 0.0
        }


# ============================================================================
# SINGLETON HELPER
# ============================================================================

_contractor_manager_instance = None

def get_contractor_manager(db: AsyncSession) -> ContractorManagerService:
    """Get singleton instance of ContractorManagerService"""
    global _contractor_manager_instance
    if _contractor_manager_instance is None:
        _contractor_manager_instance = ContractorManagerService(db)
    return _contractor_manager_instance
