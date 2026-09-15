"""Budget and income allocation calculator service."""
from decimal import Decimal
from sqlalchemy.orm import Session
from src.models import AllocationType


class BudgetService:
    """Service for budget calculations."""

    @staticmethod
    def calculate_surplus(
        total_income: Decimal | None = None,
        total_expenses: Decimal | None = None,
        **kwargs,
    ) -> Decimal:
        """Calculate monthly surplus (income - expenses)."""
        if total_income is None:
            total_income = kwargs.get("income", Decimal(0))
        if total_expenses is None:
            total_expenses = kwargs.get("expenses", Decimal(0))
        return total_income - total_expenses

    @staticmethod
    def calculate_savings_rate(
        savings_amount: Decimal | None = None,
        total_income: Decimal | None = None,
        **kwargs,
    ) -> float:
        """
        Calculate savings rate.

        savings_rate = savings / income * 100

        Returns:
            Percentage (0-100+)
        """
        if savings_amount is None:
            savings_amount = kwargs.get("savings", Decimal(0))
        if total_income is None:
            total_income = kwargs.get("income", Decimal(0))
        if total_income == 0:
            return 0.0

        return float((savings_amount / total_income) * Decimal(100))

    @staticmethod
    def calculate_investment_rate(
        investment_amount: Decimal | None = None,
        total_income: Decimal | None = None,
        **kwargs,
    ) -> float:
        """
        Calculate investment rate.

        investment_rate = investments / income * 100
        """
        if investment_amount is None:
            investment_amount = kwargs.get("investments", Decimal(0))
        if total_income is None:
            total_income = kwargs.get("income", Decimal(0))
        if total_income == 0:
            return 0.0

        return float((investment_amount / total_income) * Decimal(100))

    @staticmethod
    def calculate_expense_ratio(
        total_expenses: Decimal | None = None,
        total_income: Decimal | None = None,
        **kwargs,
    ) -> float:
        """
        Calculate expense ratio.

        expense_ratio = expenses / income * 100
        """
        if total_expenses is None:
            total_expenses = kwargs.get("expenses", Decimal(0))
        if total_income is None:
            total_income = kwargs.get("income", Decimal(0))
        if total_income == 0:
            return 0.0

        return float((total_expenses / total_income) * Decimal(100))

    @staticmethod
    def calculate_allocation_allocation_summary(
        total_income: Decimal | None = None,
        allocation_totals: dict | None = None,
        **kwargs,
    ) -> dict:
        """
        Calculate allocation percentages.
        
        Args:
            total_income: Total monthly income
            allocation_totals: {
                "expenses": amount,
                "savings": amount,
                "investments": amount,
                "debt": amount,
                "other": amount
            }
        
        Returns:
            Allocation summary with percentages and remaining
        """
        if total_income is None:
            total_income = kwargs.get("income", None)
        if allocation_totals is None:
            allocation_totals = kwargs.get("allocation_totals", {})

        if not allocation_totals:
            return {
                "total_income": Decimal(0),
                "total_allocated": Decimal(0),
                "unallocated": Decimal(0),
                "overallocated": Decimal(0),
                "percentage_allocated": 0.0,
                "allocations": {},
                "percentages": {},
            }

        if total_income is None:
            total_income = sum(allocation_totals.values())

        total_allocated = sum(allocation_totals.values())
        unallocated = max(Decimal(0), total_income - total_allocated)
        overallocated = max(Decimal(0), total_allocated - total_income)
        percentage_allocated = (total_allocated / total_income) * Decimal(100) if total_income > 0 else Decimal(0)
        
        percentages = {
            key: float((value / total_income * Decimal(100))) if total_income > 0 else 0.0
            for key, value in allocation_totals.items()
        }
        
        return {
            "total_income": total_income,
            "total_allocated": total_allocated,
            "unallocated": unallocated,
            "overallocated": overallocated,
            "percentage_allocated": float(percentage_allocated),
            "allocations": allocation_totals,
            "percentages": percentages,
        }

    @staticmethod
    def validate_income_allocation(
        total_income: Decimal | None = None,
        allocations: list | None = None,
        **kwargs,
    ) -> dict:
        """
        Validate that income allocation doesn't exceed income.

        Returns:
            {
                "is_valid": boolean,
                "total_allocated": amount,
                "surplus": amount,
                "deficit": amount,
                "message": string
            }
        """
        if total_income is None:
            total_income = kwargs.get("income", Decimal(0))
        if allocations is None:
            allocations = kwargs.get("allocations", [])
        if "total_allocated" in kwargs and not allocations:
            total_allocated = kwargs["total_allocated"]
            surplus = total_income - total_allocated
            return {
                "is_valid": total_allocated <= total_income,
                "total_allocated": total_allocated,
                "surplus": max(Decimal(0), surplus),
                "deficit": max(Decimal(0), -surplus),
                "message": (
                    f"Allocated {total_allocated} from {total_income}"
                    if surplus >= 0
                    else f"Over-allocated by {-surplus}"
                ),
            }

        total_allocated = sum(Decimal(a.get("amount", 0)) for a in allocations)
        surplus = total_income - total_allocated

        return {
            "is_valid": total_allocated <= total_income,
            "total_allocated": total_allocated,
            "surplus": max(Decimal(0), surplus),
            "deficit": max(Decimal(0), -surplus),
            "message": (
                f"Allocated {total_allocated} from {total_income}"
                if surplus >= 0
                else f"Over-allocated by {-surplus}"
            ),
        }
