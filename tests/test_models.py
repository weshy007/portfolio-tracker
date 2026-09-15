"""Tests for database models and schemas."""
from decimal import Decimal

import pytest

from src.models.base import (
    AllocationFrequency,
    AllocationType,
    Asset,
    Category,
    CategoryType,
    Expense,
    Holding,
    IncomeSource,
    Liability,
    PlannedAllocation,
)


class TestCategoryModel:
    """Test Category model."""

    def test_create_category(self, db):
        """Test creating a category."""
        category = Category(
            name="Emergency Fund",
            category_type=CategoryType.SAFETY,
            is_default=True,
        )
        db.add(category)
        db.commit()

        assert category.id is not None
        assert category.name == "Emergency Fund"
        assert category.category_type == CategoryType.SAFETY
        assert category.is_default is True
        assert category.created_at is not None

    def test_category_timestamps(self, db):
        """Test that timestamps are set correctly."""
        category = Category(
            name="Test",
            category_type=CategoryType.OTHER,
        )
        db.add(category)
        db.commit()

        assert category.created_at is not None
        assert category.updated_at is not None
        assert category.created_at == category.updated_at


class TestHoldingModel:
    """Test Holding model."""

    def test_create_holding(self, db, default_category):
        """Test creating a holding."""
        holding = Holding(
            name="Kenya Power Shares",
            category_id=default_category.id,
            amount=Decimal("50000.50"),
            currency="KES",
            notes="Blue chip stock",
        )
        db.add(holding)
        db.commit()

        assert holding.id is not None
        assert holding.name == "Kenya Power Shares"
        assert holding.amount == Decimal("50000.50")
        assert holding.currency == "KES"
        assert holding.category_id == default_category.id

    def test_holding_decimal_precision(self, db, default_category):
        """Test Decimal precision in holdings."""
        holding = Holding(
            name="Investment",
            category_id=default_category.id,
            amount=Decimal("1234.56"),
            currency="KES",
        )
        db.add(holding)
        db.commit()
        db.refresh(holding)

        assert holding.amount == Decimal("1234.56")


class TestIncomeSourceModel:
    """Test IncomeSource model."""

    def test_create_income_source(self, db):
        """Test creating an income source."""
        income = IncomeSource(
            name="Salary",
            amount=Decimal("100000"),
            currency="KES",
            frequency=AllocationFrequency.MONTHLY,
            active=True,
        )
        db.add(income)
        db.commit()

        assert income.id is not None
        assert income.name == "Salary"
        assert income.frequency == AllocationFrequency.MONTHLY
        assert income.active is True


class TestExpenseModel:
    """Test Expense model."""

    def test_create_essential_expense(self, db):
        """Test creating an essential expense."""
        expense = Expense(
            name="Rent",
            amount=Decimal("30000"),
            currency="KES",
            category="Housing",
            essential=True,
            active=True,
        )
        db.add(expense)
        db.commit()

        assert expense.id is not None
        assert expense.essential is True

    def test_create_non_essential_expense(self, db):
        """Test creating a non-essential expense."""
        expense = Expense(
            name="Entertainment",
            amount=Decimal("5000"),
            currency="KES",
            category="Leisure",
            essential=False,
            active=True,
        )
        db.add(expense)
        db.commit()

        assert expense.essential is False


class TestPlannedAllocationModel:
    """Test PlannedAllocation model."""

    def test_create_allocation(self, db):
        """Test creating a planned allocation."""
        allocation = PlannedAllocation(
            name="Monthly Savings",
            allocation_type=AllocationType.SAVING,
            amount=Decimal("20000"),
            currency="KES",
            frequency=AllocationFrequency.MONTHLY,
            active=True,
        )
        db.add(allocation)
        db.commit()

        assert allocation.id is not None
        assert allocation.allocation_type == AllocationType.SAVING


class TestAssetModel:
    """Test Asset model."""

    def test_create_asset(self, db):
        """Test creating an asset."""
        asset = Asset(
            name="House",
            category="Real Estate",
            amount=Decimal("5000000"),
            currency="KES",
        )
        db.add(asset)
        db.commit()

        assert asset.id is not None
        assert asset.name == "House"


class TestLiabilityModel:
    """Test Liability model."""

    def test_create_liability(self, db):
        """Test creating a liability."""
        liability = Liability(
            name="Mortgage",
            category="Housing",
            amount=Decimal("3000000"),
            currency="KES",
            interest_rate=Decimal("8.5"),
        )
        db.add(liability)
        db.commit()

        assert liability.id is not None
        assert liability.interest_rate == Decimal("8.5")

    def test_liability_without_interest(self, db):
        """Test creating liability without interest rate."""
        liability = Liability(
            name="Personal Loan",
            category="Debt",
            amount=Decimal("100000"),
            currency="KES",
            interest_rate=None,
        )
        db.add(liability)
        db.commit()

        assert liability.interest_rate is None
