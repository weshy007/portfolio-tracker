"""Tests for service layer."""
import pytest
from decimal import Decimal
from src.services.emergency_fund import EmergencyFundService
from src.services.budget import BudgetService
from src.services.projection import ProjectionService
from src.models.base import Category, CategoryType


class TestEmergencyFundService:
    """Test emergency fund calculations."""

    def test_calculate_target(self):
        """Test calculating emergency fund target."""
        target = EmergencyFundService.calculate_emergency_fund_target(
            essential_monthly_expenses=Decimal("30000"),
            target_months=6,
        )
        assert target == Decimal("180000")

    def test_calculate_target_zero_expenses(self):
        """Test target with zero expenses."""
        target = EmergencyFundService.calculate_emergency_fund_target(
            essential_monthly_expenses=Decimal("0"),
            target_months=6,
        )
        assert target == Decimal("0")

    def test_calculate_coverage(self):
        """Test calculating emergency fund coverage."""
        coverage = EmergencyFundService.calculate_emergency_fund_coverage(
            target=Decimal("180000"),
            current=Decimal("90000"),
            essential_monthly_expenses=Decimal("30000"),
        )
        
        assert coverage["target"] == Decimal("180000")
        assert coverage["current"] == Decimal("90000")
        assert coverage["remaining"] == Decimal("90000")
        assert coverage["percentage_complete"] == 50.0
        assert coverage["months_covered"] == 3.0
        assert coverage["is_fully_funded"] is False

    def test_calculate_coverage_fully_funded(self):
        """Test coverage when fully funded."""
        coverage = EmergencyFundService.calculate_emergency_fund_coverage(
            target=Decimal("120000"),
            current=Decimal("120000"),
            essential_monthly_expenses=Decimal("20000"),
        )
        
        assert coverage["is_fully_funded"] is True
        assert coverage["excess"] == Decimal("0")


class TestBudgetService:
    """Test budget calculations."""

    def test_calculate_surplus(self):
        """Test calculating surplus."""
        surplus = BudgetService.calculate_surplus(
            income=Decimal("100000"),
            expenses=Decimal("60000"),
        )
        assert surplus == Decimal("40000")

    def test_calculate_surplus_negative(self):
        """Test deficit calculation."""
        surplus = BudgetService.calculate_surplus(
            income=Decimal("50000"),
            expenses=Decimal("60000"),
        )
        assert surplus == Decimal("-10000")

    def test_calculate_savings_rate(self):
        """Test savings rate calculation."""
        rate = BudgetService.calculate_savings_rate(
            savings=Decimal("30000"),
            income=Decimal("100000"),
        )
        assert rate == Decimal("30")

    def test_calculate_savings_rate_zero_income(self):
        """Test savings rate with zero income."""
        rate = BudgetService.calculate_savings_rate(
            savings=Decimal("10000"),
            income=Decimal("0"),
        )
        assert rate == Decimal("0")

    def test_calculate_investment_rate(self):
        """Test investment rate calculation."""
        rate = BudgetService.calculate_investment_rate(
            investments=Decimal("20000"),
            income=Decimal("100000"),
        )
        assert rate == Decimal("20")

    def test_calculate_expense_ratio(self):
        """Test expense ratio calculation."""
        ratio = BudgetService.calculate_expense_ratio(
            expenses=Decimal("60000"),
            income=Decimal("100000"),
        )
        assert ratio == Decimal("60")

    def test_allocation_allocation_summary(self):
        """Test allocation allocation summary."""
        summary = BudgetService.calculate_allocation_allocation_summary(
            allocation_totals={
                "Expense": Decimal("40000"),
                "Saving": Decimal("30000"),
                "Investment": Decimal("20000"),
            },
        )
        
        assert summary["total_allocated"] == Decimal("90000")
        assert summary["unallocated"] == Decimal("0")  # No income provided
        assert summary["overallocated"] == Decimal("0")

    def test_validate_income_allocation_valid(self):
        """Test valid income allocation."""
        validation = BudgetService.validate_income_allocation(
            total_allocated=Decimal("90000"),
            income=Decimal("100000"),
        )
        
        assert validation["is_valid"] is True
        assert validation["surplus"] == Decimal("10000")


class TestProjectionService:
    """Test projection calculations."""

    def test_future_value_zero_return(self):
        """Test FV calculation with 0% return."""
        fv = ProjectionService.calculate_future_value(
            monthly_contribution=Decimal("10000"),
            annual_return_percent=0,
            years=1,
        )
        # Should be 10000 * 12 = 120000
        assert fv == Decimal("120000.00")

    def test_future_value_with_return(self):
        """Test FV calculation with positive return."""
        fv = ProjectionService.calculate_future_value(
            monthly_contribution=Decimal("10000"),
            annual_return_percent=12,
            years=5,
        )
        # Should be greater than 600000 (contributions only)
        assert fv > Decimal("600000")

    def test_contribution_only_projection(self):
        """Test contribution-only projection."""
        projection = ProjectionService.calculate_contribution_only_projection(
            current_value=Decimal("100000"),
            monthly_contribution=Decimal("10000"),
            months=12,
        )
        # 100000 + (10000 * 12) = 220000
        assert projection == Decimal("220000")

    def test_monthly_contribution_needed(self):
        """Test calculating required monthly contribution."""
        contribution = ProjectionService.calculate_monthly_contribution_needed(
            target_amount=Decimal("600000"),
            years=5,
            annual_return_percent=0,
        )
        # 600000 / 60 = 10000
        assert contribution == Decimal("10000.00")
