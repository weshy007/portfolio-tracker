"""Tests for Pydantic schemas."""
from decimal import Decimal

import pytest

from src.api.calculations import (
    AllocationRequest,
    EmergencyFundRequest,
    ProjectionRequest,
)
from src.schemas.base import CategoryCreate, ExpenseCreate, HoldingCreate, IncomeSourceCreate


class TestCategorySchema:
    """Test Category schemas."""

    def test_valid_category_create(self):
        """Test creating valid category."""
        schema = CategoryCreate(name="Test Category")
        assert schema.name == "Test Category"

    def test_category_name_too_long(self):
        """Test category name length validation."""
        with pytest.raises(ValueError):
            CategoryCreate(name="A" * 300)


class TestHoldingSchema:
    """Test Holding schemas."""

    def test_valid_holding_create(self):
        """Test creating valid holding."""
        schema = HoldingCreate(
            name="Test Holding",
            category_id="test-id",
            amount=Decimal("10000"),
            currency="KES",
        )
        assert schema.amount == Decimal("10000")

    def test_negative_amount_invalid(self):
        """Test that negative amounts are rejected."""
        with pytest.raises(ValueError):
            HoldingCreate(
                name="Test",
                category_id="id",
                amount=Decimal("-100"),
                currency="KES",
            )

    def test_currency_length(self):
        """Test currency code length."""
        # Valid 3-letter code
        schema = HoldingCreate(
            name="Test",
            category_id="id",
            amount=Decimal("100"),
            currency="KES",
        )
        assert schema.currency == "KES"


class TestIncomeSourceSchema:
    """Test IncomeSource schemas."""

    def test_valid_income_create(self):
        """Test creating valid income source."""
        schema = IncomeSourceCreate(
            name="Salary",
            amount=Decimal("50000"),
            currency="KES",
        )
        assert schema.name == "Salary"
        assert schema.amount == Decimal("50000")

    def test_negative_income_invalid(self):
        """Test that negative income is rejected."""
        with pytest.raises(ValueError):
            IncomeSourceCreate(
                name="Salary",
                amount=Decimal("-50000"),
                currency="KES",
            )


class TestExpenseSchema:
    """Test Expense schemas."""

    def test_valid_expense_create(self):
        """Test creating valid expense."""
        schema = ExpenseCreate(
            name="Rent",
            amount=Decimal("25000"),
            category="Housing",
            essential=True,
        )
        assert schema.essential is True

    def test_expense_without_essential(self):
        """Test expense without essential flag."""
        schema = ExpenseCreate(
            name="Food",
            amount=Decimal("10000"),
            category="Food",
        )
        # Should default to False
        assert schema.essential is False


class TestCalculationSchemas:
    """Test calculation request/response schemas."""

    def test_emergency_fund_request(self):
        """Test emergency fund request schema."""
        schema = EmergencyFundRequest(
            essential_monthly_expenses=Decimal("30000"),
            target_months=6,
        )
        assert schema.target_months == 6

    def test_emergency_fund_custom_target(self):
        """Test emergency fund with custom target months."""
        schema = EmergencyFundRequest(
            essential_monthly_expenses=Decimal("30000"),
            target_months=12,
        )
        assert schema.target_months == 12

    def test_allocation_request(self):
        """Test allocation request schema."""
        schema = AllocationRequest(
            total_income=Decimal("100000"),
            expenses=Decimal("40000"),
            savings=Decimal("30000"),
            investments=Decimal("20000"),
        )
        assert schema.total_income == Decimal("100000")

    def test_projection_request(self):
        """Test projection request schema."""
        schema = ProjectionRequest(
            monthly_contribution=Decimal("10000"),
            annual_return_percent=12,
            years=5,
        )
        assert schema.years == 5

    def test_projection_zero_return(self):
        """Test projection with default zero return."""
        schema = ProjectionRequest(
            monthly_contribution=Decimal("10000"),
            years=1,
        )
        assert schema.annual_return_percent == 0
