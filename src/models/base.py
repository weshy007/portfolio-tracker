"""Database models for Portfolio Tracker using SQLAlchemy 2.x."""
import enum
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Date,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def utc_now():
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class CategoryType(str, enum.Enum):
    """Category types for investments/savings."""

    SAFETY = "Safety"
    CASH = "Cash"
    FIXED_INCOME = "Fixed Income"
    EQUITIES = "Equities"
    REAL_ESTATE = "Real Estate"
    RETIREMENT = "Retirement"
    BUSINESS = "Business"
    ALTERNATIVE = "Alternative"
    OTHER = "Other"


class AllocationFrequency(str, enum.Enum):
    """Frequency of allocations."""

    MONTHLY = "Monthly"
    WEEKLY = "Weekly"
    YEARLY = "Yearly"
    ONE_TIME = "One Time"


class AllocationType(str, enum.Enum):
    """Type of allocation."""

    EXPENSE = "Expense"
    SAVING = "Saving"
    INVESTMENT = "Investment"
    DEBT = "Debt"
    OTHER = "Other"


class Category(Base):
    """Investment/Savings categories."""

    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, index=True)
    category_type = Column(SQLEnum(CategoryType), nullable=False, default=CategoryType.OTHER)
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        timestamp = utc_now()
        if self.created_at is None:
            self.created_at = timestamp
        if self.updated_at is None:
            self.updated_at = timestamp

    # Relationships
    holdings = relationship("Holding", back_populates="category", cascade="all, delete-orphan")
    planned_allocations = relationship("PlannedAllocation", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"


class Holding(Base):
    """Current investments/holdings."""

    __tablename__ = "holdings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, index=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)  # Amount in the specified currency
    currency = Column(String(3), nullable=False, default="KES", index=True)
    notes = Column(String(1000))
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="holdings")

    def __repr__(self):
        return f"<Holding {self.name} {self.amount} {self.currency}>"


class IncomeSource(Base):
    """Income sources."""

    __tablename__ = "income_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="KES", index=True)
    frequency = Column(SQLEnum(AllocationFrequency), nullable=False, default=AllocationFrequency.MONTHLY)
    active = Column(Boolean, default=True, index=True)
    notes = Column(String(1000))
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self):
        return f"<IncomeSource {self.name} {self.amount} {self.currency}>"


class Expense(Base):
    """Monthly expenses."""

    __tablename__ = "expenses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(255), nullable=False, index=True)  # Expense category (not FK)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="KES", index=True)
    essential = Column(Boolean, default=False, index=True)  # True if essential
    active = Column(Boolean, default=True, index=True)
    notes = Column(String(1000))
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self):
        return f"<Expense {self.name} {self.amount} {self.currency}>"


class PlannedAllocation(Base):
    """Planned monthly allocations."""

    __tablename__ = "planned_allocations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, index=True)
    allocation_type = Column(SQLEnum(AllocationType), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)  # Optional FK
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="KES", index=True)
    frequency = Column(SQLEnum(AllocationFrequency), nullable=False, default=AllocationFrequency.MONTHLY)
    active = Column(Boolean, default=True, index=True)
    notes = Column(String(1000))
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="planned_allocations")

    def __repr__(self):
        return f"<PlannedAllocation {self.name} {self.amount} {self.currency}>"


class Asset(Base):
    """Net worth assets."""

    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(255), nullable=False, index=True)  # Asset category (Property, Car, etc.)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="KES", index=True)
    notes = Column(String(1000))
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self):
        return f"<Asset {self.name} {self.amount} {self.currency}>"


class Liability(Base):
    """Net worth liabilities (debts)."""

    __tablename__ = "liabilities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(255), nullable=False, index=True)  # Loan, Credit Card, etc.
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="KES", index=True)
    interest_rate = Column(Numeric(5, 2), nullable=True)  # Optional annual interest rate
    notes = Column(String(1000))
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self):
        return f"<Liability {self.name} {self.amount} {self.currency}>"


class StockPosition(Base):
    """A locally owned equity position, valued from the latest provider close."""
    __tablename__ = "stock_positions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ticker = Column(String(32), nullable=False, index=True)
    exchange = Column(String(12), nullable=False, default="NSE")
    shares_owned = Column(Numeric(18, 6), nullable=False)
    average_buy_price = Column(Numeric(18, 4), nullable=False)
    current_price = Column(Numeric(18, 4), nullable=True)
    price_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class MMFAccount(Base):
    """MMF balance; daily accruals are recorded in KES to two decimal places."""
    __tablename__ = "mmf_accounts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    fund_name = Column(String(255), nullable=False, index=True)
    principal_balance = Column(Numeric(18, 2), nullable=False)
    current_balance = Column(Numeric(18, 2), nullable=False)
    total_interest_accrued = Column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    investment_date = Column(Date, nullable=True)
    last_accrued_on = Column(Date, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class DailyMMFYield(Base):
    """One scraped effective annual yield per fund and valuation date."""
    __tablename__ = "daily_mmf_yields"
    __table_args__ = (UniqueConstraint("fund_name", "yield_date", name="uq_mmf_yield_fund_date"),)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    fund_name = Column(String(255), nullable=False, index=True)
    yield_decimal = Column(Numeric(10, 8), nullable=False)
    yield_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
