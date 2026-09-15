"""Income service for managing income sources."""
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import IncomeSource, AllocationFrequency
from src.schemas import IncomeSourceCreate, IncomeSourceUpdate


class IncomeService:
    """Service for managing income sources."""

    @staticmethod
    def create_income_source(db: Session, income_data: IncomeSourceCreate) -> IncomeSource:
        """Create a new income source."""
        income = IncomeSource(
            id=str(uuid4()),
            name=income_data.name,
            amount=income_data.amount,
            currency=income_data.currency,
            frequency=income_data.frequency,
            active=income_data.active,
            notes=income_data.notes,
        )
        db.add(income)
        db.commit()
        db.refresh(income)
        return income

    @staticmethod
    def get_income_source(db: Session, income_id: str) -> IncomeSource:
        """Get an income source by ID."""
        return db.query(IncomeSource).filter(IncomeSource.id == income_id).first()

    @staticmethod
    def get_all_income_sources(db: Session) -> list[IncomeSource]:
        """Get all income sources."""
        return db.query(IncomeSource).all()

    @staticmethod
    def get_active_income_sources(db: Session) -> list[IncomeSource]:
        """Get active income sources."""
        return db.query(IncomeSource).filter(IncomeSource.active == True).all()

    @staticmethod
    def update_income_source(
        db: Session, income_id: str, income_data: IncomeSourceUpdate
    ) -> IncomeSource:
        """Update an income source."""
        income = IncomeService.get_income_source(db, income_id)
        if not income:
            return None

        if income_data.name:
            income.name = income_data.name
        if income_data.amount is not None:
            income.amount = income_data.amount
        if income_data.currency:
            income.currency = income_data.currency
        if income_data.frequency:
            income.frequency = income_data.frequency
        if income_data.active is not None:
            income.active = income_data.active
        if income_data.notes is not None:
            income.notes = income_data.notes

        db.add(income)
        db.commit()
        db.refresh(income)
        return income

    @staticmethod
    def delete_income_source(db: Session, income_id: str) -> bool:
        """Delete an income source."""
        income = IncomeService.get_income_source(db, income_id)
        if not income:
            return False

        db.delete(income)
        db.commit()
        return True

    @staticmethod
    def get_total_monthly_income(db: Session, base_currency: str = "KES") -> Decimal:
        """
        Get total monthly income from active sources.
        Note: Assumes frequency conversion will be handled separately.
        For now, only returns active monthly sources.
        """
        result = db.query(
            func.sum(IncomeSource.amount)
        ).filter(
            IncomeSource.active == True,
            IncomeSource.frequency == AllocationFrequency.MONTHLY,
            IncomeSource.currency == base_currency,
        ).scalar()

        return Decimal(result or 0)

    @staticmethod
    def get_income_summary(db: Session, base_currency: str = "KES") -> dict:
        """Get summary of income sources."""
        all_sources = IncomeService.get_all_income_sources(db)
        active_sources = IncomeService.get_active_income_sources(db)

        monthly_income = IncomeService.get_total_monthly_income(db, base_currency)

        return {
            "total_sources": len(all_sources),
            "active_sources": len(active_sources),
            "total_monthly_income": monthly_income,
            "currency": base_currency,
        }
