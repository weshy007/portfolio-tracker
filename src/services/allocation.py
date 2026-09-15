"""Planned allocation service for managing planned monthly allocations."""
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import PlannedAllocation, AllocationType
from src.schemas import PlannedAllocationCreate, PlannedAllocationUpdate


class PlannedAllocationService:
    """Service for managing planned allocations."""

    @staticmethod
    def create_allocation(
        db: Session, allocation_data: PlannedAllocationCreate
    ) -> PlannedAllocation:
        """Create a new planned allocation."""
        allocation = PlannedAllocation(
            id=str(uuid4()),
            name=allocation_data.name,
            allocation_type=allocation_data.allocation_type,
            category_id=allocation_data.category_id,
            amount=allocation_data.amount,
            currency=allocation_data.currency,
            frequency=allocation_data.frequency,
            active=allocation_data.active,
            notes=allocation_data.notes,
        )
        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        return allocation

    @staticmethod
    def get_allocation(db: Session, allocation_id: str) -> PlannedAllocation:
        """Get a planned allocation by ID."""
        return db.query(PlannedAllocation).filter(
            PlannedAllocation.id == allocation_id
        ).first()

    @staticmethod
    def get_all_allocations(db: Session) -> list[PlannedAllocation]:
        """Get all planned allocations."""
        return db.query(PlannedAllocation).all()

    @staticmethod
    def get_active_allocations(db: Session) -> list[PlannedAllocation]:
        """Get active planned allocations."""
        return db.query(PlannedAllocation).filter(
            PlannedAllocation.active == True
        ).all()

    @staticmethod
    def get_allocations_by_type(
        db: Session, allocation_type: AllocationType
    ) -> list[PlannedAllocation]:
        """Get allocations by type."""
        return db.query(PlannedAllocation).filter(
            PlannedAllocation.allocation_type == allocation_type,
            PlannedAllocation.active == True,
        ).all()

    @staticmethod
    def update_allocation(
        db: Session, allocation_id: str, allocation_data: PlannedAllocationUpdate
    ) -> PlannedAllocation:
        """Update a planned allocation."""
        allocation = PlannedAllocationService.get_allocation(db, allocation_id)
        if not allocation:
            return None

        if allocation_data.name:
            allocation.name = allocation_data.name
        if allocation_data.allocation_type:
            allocation.allocation_type = allocation_data.allocation_type
        if allocation_data.category_id is not None:
            allocation.category_id = allocation_data.category_id
        if allocation_data.amount is not None:
            allocation.amount = allocation_data.amount
        if allocation_data.currency:
            allocation.currency = allocation_data.currency
        if allocation_data.frequency:
            allocation.frequency = allocation_data.frequency
        if allocation_data.active is not None:
            allocation.active = allocation_data.active
        if allocation_data.notes is not None:
            allocation.notes = allocation_data.notes

        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        return allocation

    @staticmethod
    def delete_allocation(db: Session, allocation_id: str) -> bool:
        """Delete a planned allocation."""
        allocation = PlannedAllocationService.get_allocation(db, allocation_id)
        if not allocation:
            return False

        db.delete(allocation)
        db.commit()
        return True

    @staticmethod
    def get_total_planned_allocation(db: Session, base_currency: str = "KES") -> Decimal:
        """Get total planned allocation amount."""
        result = db.query(
            func.sum(PlannedAllocation.amount)
        ).filter(
            PlannedAllocation.active == True,
            PlannedAllocation.currency == base_currency,
        ).scalar()

        return Decimal(result or 0)

    @staticmethod
    def get_allocation_by_type_total(
        db: Session, allocation_type: AllocationType, base_currency: str = "KES"
    ) -> Decimal:
        """Get total allocation amount by type."""
        result = db.query(
            func.sum(PlannedAllocation.amount)
        ).filter(
            PlannedAllocation.active == True,
            PlannedAllocation.allocation_type == allocation_type,
            PlannedAllocation.currency == base_currency,
        ).scalar()

        return Decimal(result or 0)

    @staticmethod
    def get_allocation_summary(db: Session, base_currency: str = "KES") -> dict:
        """Get summary of planned allocations."""
        total = PlannedAllocationService.get_total_planned_allocation(
            db, base_currency
        )
        expenses = PlannedAllocationService.get_allocation_by_type_total(
            db, AllocationType.EXPENSE, base_currency
        )
        savings = PlannedAllocationService.get_allocation_by_type_total(
            db, AllocationType.SAVING, base_currency
        )
        investments = PlannedAllocationService.get_allocation_by_type_total(
            db, AllocationType.INVESTMENT, base_currency
        )
        debt = PlannedAllocationService.get_allocation_by_type_total(
            db, AllocationType.DEBT, base_currency
        )
        other = PlannedAllocationService.get_allocation_by_type_total(
            db, AllocationType.OTHER, base_currency
        )

        return {
            "total_allocated": total,
            "expenses": expenses,
            "savings": savings,
            "investments": investments,
            "debt": debt,
            "other": other,
            "currency": base_currency,
        }
