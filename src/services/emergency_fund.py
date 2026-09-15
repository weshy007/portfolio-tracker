"""Emergency fund calculator service."""
from decimal import Decimal
from sqlalchemy.orm import Session
from src.models import Holding, Category


class EmergencyFundService:
    """Service for emergency fund calculations."""

    @staticmethod
    def calculate_emergency_fund_target(
        essential_monthly_expenses: Decimal,
        target_months: int = 6,
    ) -> Decimal:
        """
        Calculate emergency fund target.
        
        Args:
            essential_monthly_expenses: Monthly essential expenses
            target_months: Number of months to cover (default 6)
            
        Returns:
            Emergency fund target amount
        """
        if target_months < 0:
            raise ValueError("Target months cannot be negative")
        if essential_monthly_expenses < 0:
            raise ValueError("Essential expenses cannot be negative")
            
        return essential_monthly_expenses * Decimal(target_months)

    @staticmethod
    def get_current_emergency_fund(db: Session, base_currency: str = "KES") -> Decimal:
        """
        Get current emergency fund balance.
        
        Only counts holdings explicitly categorized as "Emergency Fund".
        """
        from src.services.portfolio import PortfolioService
        
        # Get emergency fund category
        emergency_fund_category = db.query(Category).filter(
            Category.name == "Emergency Fund"
        ).first()
        
        if not emergency_fund_category:
            return Decimal(0)
        
        # Sum holdings in emergency fund category with matching currency
        total = db.query(
            Holding.amount
        ).filter(
            Holding.category_id == emergency_fund_category.id,
            Holding.currency == base_currency,
        ).with_entities(
            db.func.sum(Holding.amount)
        ).scalar()
        
        return Decimal(total or 0)

    @staticmethod
    def calculate_emergency_fund_coverage(
        essential_monthly_expenses: Decimal | None = None,
        current_emergency_fund: Decimal | None = None,
        target: Decimal | None = None,
        **kwargs,
    ) -> dict:
        """
        Calculate emergency fund coverage.

        Supports both the current API shape and the legacy/older test shape:
        calculate_emergency_fund_coverage(
            essential_monthly_expenses=..., current_emergency_fund=...
        )
        and
        calculate_emergency_fund_coverage(target=..., current=..., essential_monthly_expenses=...)
        """
        if "current" in kwargs and current_emergency_fund is None:
            current_emergency_fund = kwargs["current"]
        if "target_months" in kwargs and target is None:
            target = kwargs["target_months"]

        if essential_monthly_expenses is None:
            essential_monthly_expenses = kwargs.get("essential_monthly_expenses", Decimal(0))
        if current_emergency_fund is None:
            current_emergency_fund = Decimal(0)

        if target is None:
            target = EmergencyFundService.calculate_emergency_fund_target(
                essential_monthly_expenses, 6
            )

        if essential_monthly_expenses < 0:
            raise ValueError("Essential expenses cannot be negative")
        if current_emergency_fund < 0:
            raise ValueError("Emergency fund cannot be negative")

        if essential_monthly_expenses == 0:
            return {
                "target": target,
                "current": current_emergency_fund,
                "remaining": Decimal(0),
                "percentage_complete": Decimal(100) if current_emergency_fund == 0 else Decimal(0),
                "months_covered": Decimal(0),
                "is_fully_funded": True,
                "excess": Decimal(0),
            }

        remaining = max(Decimal(0), target - current_emergency_fund)
        percentage = min(Decimal(100), (current_emergency_fund / target * Decimal(100))) if target > 0 else Decimal(0)
        months_covered = current_emergency_fund / essential_monthly_expenses if essential_monthly_expenses > 0 else Decimal(0)
        excess = max(Decimal(0), current_emergency_fund - target)
        is_fully_funded = current_emergency_fund >= target

        return {
            "target": target,
            "current": current_emergency_fund,
            "remaining": remaining,
            "percentage_complete": float(percentage),
            "months_covered": float(months_covered),
            "is_fully_funded": is_fully_funded,
            "excess": excess,
        }

    @staticmethod
    def calculate_emergency_fund_with_custom_target(
        essential_monthly_expenses: Decimal,
        target_months: int,
        current_emergency_fund: Decimal,
    ) -> dict:
        """
        Calculate emergency fund coverage with custom target months.
        """
        if target_months < 0:
            raise ValueError("Target months cannot be negative")
            
        target = EmergencyFundService.calculate_emergency_fund_target(
            essential_monthly_expenses, target_months
        )
        
        remaining = max(Decimal(0), target - current_emergency_fund)
        percentage = min(Decimal(100), (current_emergency_fund / target * Decimal(100))) if target > 0 else Decimal(0)
        months_covered = current_emergency_fund / essential_monthly_expenses if essential_monthly_expenses > 0 else Decimal(0)
        excess = max(Decimal(0), current_emergency_fund - target)
        is_fully_funded = current_emergency_fund >= target
        
        return {
            "target": target,
            "target_months": target_months,
            "current": current_emergency_fund,
            "remaining": remaining,
            "percentage_complete": float(percentage),
            "months_covered": float(months_covered),
            "is_fully_funded": is_fully_funded,
            "excess": excess,
        }
