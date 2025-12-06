"""
Project Phase Service
Handles phased project planning, deposit management, and progress tracking
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models_quotes import Quote, QuoteLineItem
from db.models_project_phases import (
    ProjectPhase, ProjectPhaseLineItem, ProjectPhaseMilestone,
    ProjectDeposit, ProjectTimeline
)

logger = logging.getLogger(__name__)


class ProjectPhaseService:
    """
    Service for managing phased project planning

    Enables large smart home/building projects to be broken into phases
    with incremental deposit-based unlocking
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_phases_from_quote(
        self,
        quote_id: UUID,
        number_of_phases: int = 3,
        phase_strategy: str = 'even',
        deposit_percentage: Decimal = Decimal('50.00'),
        include_timeline: bool = True,
        average_days_per_phase: Optional[int] = 30
    ) -> Dict:
        """
        Auto-generate project phases from an existing quote

        Args:
            quote_id: Quote to generate phases for
            number_of_phases: How many phases to create (1-10)
            phase_strategy: 'even' (equal cost), 'priority_based', or 'custom'
            deposit_percentage: % of phase cost required as deposit
            include_timeline: Create project timeline
            average_days_per_phase: Estimated days for each phase

        Returns:
            Dict with phases created and timeline
        """

        # Load quote
        query = select(Quote).where(Quote.id == quote_id)
        result = await self.db.execute(query)
        quote = result.scalar_one_or_none()

        if not quote:
            raise ValueError(f"Quote {quote_id} not found")

        # Calculate total project value
        total_value = quote.monthly_total  # This will need to be adapted based on project type
        if quote.hardware_costs:
            total_value += quote.hardware_costs
        if quote.setup_fees:
            total_value += quote.setup_fees

        phases_created = []

        if phase_strategy == 'even':
            # Divide project evenly across phases
            phases_created = await self._generate_even_phases(
                quote=quote,
                number_of_phases=number_of_phases,
                total_value=total_value,
                deposit_percentage=deposit_percentage,
                average_days_per_phase=average_days_per_phase
            )
        elif phase_strategy == 'priority_based':
            # Create phases based on priority (foundation first, enhancements later)
            phases_created = await self._generate_priority_based_phases(
                quote=quote,
                number_of_phases=number_of_phases,
                total_value=total_value,
                deposit_percentage=deposit_percentage,
                average_days_per_phase=average_days_per_phase
            )

        # Create project timeline if requested
        timeline = None
        if include_timeline:
            timeline = await self._create_project_timeline(
                quote=quote,
                phases=phases_created,
                total_value=total_value
            )

        return {
            'quote_id': quote_id,
            'phases_created': len(phases_created),
            'total_project_value': total_value,
            'total_deposits_required': sum(p.deposit_required for p in phases_created),
            'estimated_total_duration_days': sum(p.estimated_duration_days or 0 for p in phases_created),
            'phases': phases_created,
            'timeline': timeline
        }

    async def _generate_even_phases(
        self,
        quote: Quote,
        number_of_phases: int,
        total_value: Decimal,
        deposit_percentage: Decimal,
        average_days_per_phase: Optional[int]
    ) -> List[ProjectPhase]:
        """Generate phases with even cost distribution"""

        phase_cost = total_value / number_of_phases
        phases = []

        phase_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        phase_names = [
            'Foundation',
            'Enhancement',
            'Premium',
            'Advanced',
            'Enterprise',
            'Ultimate',
            'Elite',
            'Professional',
            'Expert',
            'Master'
        ]

        start_date = datetime.utcnow() + timedelta(days=7)  # Start in 1 week

        for i in range(number_of_phases):
            phase_number = i + 1
            phase_letter = phase_letters[i] if i < len(phase_letters) else f"P{i+1}"
            phase_name = f"Phase {phase_letter}: {phase_names[i]}" if i < len(phase_names) else f"Phase {phase_letter}"

            deposit_required = (phase_cost * deposit_percentage) / 100

            # Calculate timeline
            estimated_start = start_date + timedelta(days=i * (average_days_per_phase or 30))
            estimated_completion = estimated_start + timedelta(days=average_days_per_phase or 30)

            phase = ProjectPhase(
                quote_id=quote.id,
                phase_name=phase_name,
                phase_letter=phase_letter,
                phase_number=phase_number,
                description=f"Phase {phase_number} of {number_of_phases} - {phase_name.split(': ')[1]}",
                deliverables=[
                    f"Deliverable 1 for {phase_name}",
                    f"Deliverable 2 for {phase_name}",
                    f"Deliverable 3 for {phase_name}"
                ],
                phase_cost=phase_cost.quantize(Decimal('0.01')),
                deposit_required=deposit_required.quantize(Decimal('0.01')),
                deposit_percentage=deposit_percentage,
                hardware_cost=Decimal('0.00'),
                installation_cost=Decimal('0.00'),
                monthly_service_cost=Decimal('0.00'),
                estimated_duration_days=average_days_per_phase or 30,
                estimated_start_date=estimated_start,
                estimated_completion_date=estimated_completion,
                depends_on_phase_id=phases[-1].id if phases else None,  # Depends on previous phase
                can_start_after_days=0,
                status='planned',
                is_required=True,
                is_milestone=i == 0 or i == number_of_phases - 1,  # First and last are milestones
                priority_level=10 - i,  # Higher priority for earlier phases
                payment_terms=f"{deposit_percentage}% deposit, balance on completion"
            )

            self.db.add(phase)
            await self.db.flush()  # Get ID for next phase dependency

            phases.append(phase)

        await self.db.commit()

        return phases

    async def _generate_priority_based_phases(
        self,
        quote: Quote,
        number_of_phases: int,
        total_value: Decimal,
        deposit_percentage: Decimal,
        average_days_per_phase: Optional[int]
    ) -> List[ProjectPhase]:
        """
        Generate phases based on priority

        Foundation phase gets more budget, enhancement phases get less
        """

        # Distribution: Foundation (40%), Enhancement (30%), Premium (20%), Advanced (10%)
        distributions = {
            1: [Decimal('100.00')],
            2: [Decimal('60.00'), Decimal('40.00')],
            3: [Decimal('40.00'), Decimal('35.00'), Decimal('25.00')],
            4: [Decimal('40.00'), Decimal('30.00'), Decimal('20.00'), Decimal('10.00')],
            5: [Decimal('30.00'), Decimal('25.00'), Decimal('20.00'), Decimal('15.00'), Decimal('10.00')],
        }

        # Default to even distribution if not in predefined
        distribution = distributions.get(number_of_phases)
        if not distribution:
            distribution = [Decimal('100.00') / number_of_phases] * number_of_phases

        phases = []
        phase_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        phase_names = [
            'Foundation',
            'Enhancement',
            'Premium',
            'Advanced',
            'Enterprise',
        ]

        start_date = datetime.utcnow() + timedelta(days=7)

        for i in range(number_of_phases):
            phase_number = i + 1
            phase_letter = phase_letters[i] if i < len(phase_letters) else f"P{i+1}"
            phase_name = f"Phase {phase_letter}: {phase_names[i]}" if i < len(phase_names) else f"Phase {phase_letter}"

            # Calculate cost based on distribution
            phase_percentage = distribution[i]
            phase_cost = (total_value * phase_percentage) / 100
            deposit_required = (phase_cost * deposit_percentage) / 100

            # Timeline
            estimated_start = start_date + timedelta(days=i * (average_days_per_phase or 30))
            estimated_completion = estimated_start + timedelta(days=average_days_per_phase or 30)

            phase = ProjectPhase(
                quote_id=quote.id,
                phase_name=phase_name,
                phase_letter=phase_letter,
                phase_number=phase_number,
                description=f"Phase {phase_number} - {phase_percentage}% of total project value",
                deliverables=[
                    f"Core deliverable for {phase_name}",
                    f"Secondary deliverable for {phase_name}"
                ],
                phase_cost=phase_cost.quantize(Decimal('0.01')),
                deposit_required=deposit_required.quantize(Decimal('0.01')),
                deposit_percentage=deposit_percentage,
                estimated_duration_days=average_days_per_phase or 30,
                estimated_start_date=estimated_start,
                estimated_completion_date=estimated_completion,
                depends_on_phase_id=phases[-1].id if phases else None,
                status='planned',
                is_required=i == 0,  # Only first phase is required
                is_milestone=i == 0,
                priority_level=10 - i,
                payment_terms=f"{deposit_percentage}% deposit, balance on completion"
            )

            self.db.add(phase)
            await self.db.flush()

            phases.append(phase)

        await self.db.commit()

        return phases

    async def _create_project_timeline(
        self,
        quote: Quote,
        phases: List[ProjectPhase],
        total_value: Decimal
    ) -> ProjectTimeline:
        """Create project timeline from phases"""

        total_deposits = sum(p.deposit_required for p in phases)
        total_duration = sum(p.estimated_duration_days or 0 for p in phases)

        # Get first and last phase dates
        planned_start = min(p.estimated_start_date for p in phases if p.estimated_start_date)
        planned_completion = max(p.estimated_completion_date for p in phases if p.estimated_completion_date)

        timeline = ProjectTimeline(
            quote_id=quote.id,
            project_name=f"Smart Home Project - {quote.customer_name}",
            project_description=f"Phased smart home deployment with {len(phases)} phases",
            planned_start_date=planned_start,
            planned_completion_date=planned_completion,
            total_estimated_days=total_duration,
            status='planning',
            completion_percentage=0,
            total_project_value=total_value,
            total_deposits_required=total_deposits,
            total_deposits_received=Decimal('0.00'),
            total_paid=Decimal('0.00'),
            balance_remaining=total_value,
            total_phases=len(phases),
            phases_unlocked=0,
            phases_completed=0,
            customer_contact_name=quote.customer_name,
            customer_contact_email=quote.customer_email,
            customer_contact_phone=quote.customer_phone
        )

        self.db.add(timeline)
        await self.db.commit()

        return timeline

    async def apply_deposit(
        self,
        quote_id: UUID,
        phase_id: UUID,
        deposit_amount: Decimal,
        payment_method: str,
        payment_reference: Optional[str] = None
    ) -> Dict:
        """
        Apply a deposit to unlock a phase

        Args:
            quote_id: Quote ID
            phase_id: Phase to unlock
            deposit_amount: Amount deposited
            payment_method: How it was paid
            payment_reference: Transaction reference

        Returns:
            Dict with deposit details and phase unlock status
        """

        # Load phase
        query = select(ProjectPhase).where(
            ProjectPhase.id == phase_id,
            ProjectPhase.quote_id == quote_id
        )
        result = await self.db.execute(query)
        phase = result.scalar_one_or_none()

        if not phase:
            raise ValueError(f"Phase {phase_id} not found for quote {quote_id}")

        # Check if deposit is sufficient
        unlocks_phase = deposit_amount >= phase.deposit_required

        # Generate deposit number
        deposit_number = await self._generate_deposit_number()

        # Create deposit record
        deposit = ProjectDeposit(
            quote_id=quote_id,
            phase_id=phase_id,
            deposit_number=deposit_number,
            deposit_amount=deposit_amount,
            payment_method=payment_method,
            payment_reference=payment_reference,
            payment_status='completed',
            cleared_date=datetime.utcnow(),
            unlocks_phase=unlocks_phase,
            phase_unlocked_at=datetime.utcnow() if unlocks_phase else None,
            allocated_amount=deposit_amount
        )

        self.db.add(deposit)

        # Update phase if unlocked
        if unlocks_phase:
            phase.deposit_paid = True
            phase.deposit_paid_at = datetime.utcnow()
            phase.deposit_amount_paid = deposit_amount
            phase.total_paid += deposit_amount
            phase.status = 'unlocked'
            phase.balance_remaining = phase.phase_cost - phase.total_paid

        # Update timeline
        timeline_query = select(ProjectTimeline).where(ProjectTimeline.quote_id == quote_id)
        timeline_result = await self.db.execute(timeline_query)
        timeline = timeline_result.scalar_one_or_none()

        if timeline:
            timeline.total_deposits_received += deposit_amount
            timeline.total_paid += deposit_amount
            timeline.balance_remaining = timeline.total_project_value - timeline.total_paid

            if unlocks_phase:
                timeline.phases_unlocked += 1

                # Update status if first deposit
                if timeline.status == 'planning':
                    timeline.status = 'awaiting_deposit'
                if timeline.phases_unlocked > 0:
                    timeline.status = 'in_progress'

        await self.db.commit()

        # Find next phase
        next_phase_query = select(ProjectPhase).where(
            ProjectPhase.quote_id == quote_id,
            ProjectPhase.phase_number == phase.phase_number + 1
        )
        next_phase_result = await self.db.execute(next_phase_query)
        next_phase = next_phase_result.scalar_one_or_none()

        return {
            'deposit_id': deposit.id,
            'deposit_number': deposit_number,
            'phase_unlocked': unlocks_phase,
            'phase_id': phase_id,
            'phase_name': phase.phase_name,
            'amount_applied': deposit_amount,
            'balance_remaining': phase.balance_remaining,
            'next_phase_id': next_phase.id if next_phase else None,
            'next_phase_deposit_required': next_phase.deposit_required if next_phase else None
        }

    async def _generate_deposit_number(self) -> str:
        """Generate unique deposit number"""
        # Format: DEP-YYYY-NNNN
        now = datetime.utcnow()
        year = now.year

        # In production, query for max number this year
        # For now, use timestamp-based
        number = int(now.timestamp()) % 10000

        return f"DEP-{year}-{number:04d}"

    async def get_project_progress(self, quote_id: UUID) -> Dict:
        """
        Get comprehensive project progress summary

        Args:
            quote_id: Quote ID

        Returns:
            Dict with financial status, phase progress, and timeline
        """

        # Load quote
        quote_query = select(Quote).where(Quote.id == quote_id)
        quote_result = await self.db.execute(quote_query)
        quote = quote_result.scalar_one_or_none()

        if not quote:
            raise ValueError(f"Quote {quote_id} not found")

        # Load phases
        phases_query = select(ProjectPhase).where(
            ProjectPhase.quote_id == quote_id
        ).order_by(ProjectPhase.phase_number)
        phases_result = await self.db.execute(phases_query)
        phases = list(phases_result.scalars().all())

        # Load timeline
        timeline_query = select(ProjectTimeline).where(ProjectTimeline.quote_id == quote_id)
        timeline_result = await self.db.execute(timeline_query)
        timeline = timeline_result.scalar_one_or_none()

        # Calculate summary statistics
        total_value = sum(p.phase_cost for p in phases)
        total_paid = sum(p.total_paid for p in phases)
        total_remaining = total_value - total_paid

        phases_by_status = {
            'planned': sum(1 for p in phases if p.status == 'planned'),
            'unlocked': sum(1 for p in phases if p.status == 'unlocked'),
            'in_progress': sum(1 for p in phases if p.status == 'in_progress'),
            'completed': sum(1 for p in phases if p.status == 'completed'),
        }

        # Find next phase needing deposit
        next_phase = next((p for p in phases if not p.deposit_paid), None)

        return {
            'quote_id': quote_id,
            'project_name': timeline.project_name if timeline else quote.customer_name,
            'total_project_value': total_value,
            'total_paid': total_paid,
            'total_remaining': total_remaining,
            'payment_percentage': (total_paid / total_value * 100) if total_value > 0 else 0,
            'total_phases': len(phases),
            'phases_planned': phases_by_status['planned'],
            'phases_unlocked': phases_by_status['unlocked'],
            'phases_in_progress': phases_by_status['in_progress'],
            'phases_completed': phases_by_status['completed'],
            'project_status': timeline.status if timeline else 'planning',
            'completion_percentage': timeline.completion_percentage if timeline else 0,
            'planned_start_date': timeline.planned_start_date if timeline else None,
            'planned_completion_date': timeline.planned_completion_date if timeline else None,
            'next_deposit_required': next_phase.deposit_required if next_phase else None,
            'next_phase_name': next_phase.phase_name if next_phase else None,
            'phases': phases
        }
