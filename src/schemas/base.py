"""Pydantic schemas for request/response validation."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models import AllocationFrequency, AllocationType, CategoryType


class CategoryBase(BaseModel):
    """Base schema for Category."""

    name: str = Field(..., min_length=1, max_length=255)
    category_type: CategoryType = Field(default=CategoryType.OTHER)
    is_default: bool = False


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""

    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category_type: Optional[CategoryType] = None


class CategoryResponse(CategoryBase):
    """Schema for category response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class HoldingBase(BaseModel):
    """Base schema for Holding."""

    name: str = Field(..., min_length=1, max_length=255)
    category_id: str
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v


class HoldingCreate(HoldingBase):
    """Schema for creating a holding."""

    pass


class HoldingUpdate(BaseModel):
    """Schema for updating a holding."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category_id: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    notes: Optional[str] = Field(None, max_length=1000)


class HoldingResponse(HoldingBase):
    """Schema for holding response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class IncomeSourceBase(BaseModel):
    """Base schema for IncomeSource."""

    name: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    frequency: AllocationFrequency = Field(default=AllocationFrequency.MONTHLY)
    active: bool = True
    notes: Optional[str] = Field(None, max_length=1000)


class IncomeSourceCreate(IncomeSourceBase):
    """Schema for creating an income source."""

    pass


class IncomeSourceUpdate(BaseModel):
    """Schema for updating an income source."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    frequency: Optional[AllocationFrequency] = None
    active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)


class IncomeSourceResponse(IncomeSourceBase):
    """Schema for income source response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ExpenseBase(BaseModel):
    """Base schema for Expense."""

    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    essential: bool = False
    active: bool = True
    notes: Optional[str] = Field(None, max_length=1000)


class ExpenseCreate(ExpenseBase):
    """Schema for creating an expense."""

    pass


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    essential: Optional[bool] = None
    active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)


class ExpenseResponse(ExpenseBase):
    """Schema for expense response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class PlannedAllocationBase(BaseModel):
    """Base schema for PlannedAllocation."""

    name: str = Field(..., min_length=1, max_length=255)
    allocation_type: AllocationType
    category_id: Optional[str] = None
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    frequency: AllocationFrequency = Field(default=AllocationFrequency.MONTHLY)
    active: bool = True
    notes: Optional[str] = Field(None, max_length=1000)


class PlannedAllocationCreate(PlannedAllocationBase):
    """Schema for creating a planned allocation."""

    pass


class PlannedAllocationUpdate(BaseModel):
    """Schema for updating a planned allocation."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    allocation_type: Optional[AllocationType] = None
    category_id: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    frequency: Optional[AllocationFrequency] = None
    active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)


class PlannedAllocationResponse(PlannedAllocationBase):
    """Schema for planned allocation response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class AssetBase(BaseModel):
    """Base schema for Asset."""

    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    notes: Optional[str] = Field(None, max_length=1000)


class AssetCreate(AssetBase):
    """Schema for creating an asset."""

    pass


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    notes: Optional[str] = Field(None, max_length=1000)


class AssetResponse(AssetBase):
    """Schema for asset response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class LiabilityBase(BaseModel):
    """Base schema for Liability."""

    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=1000)


class LiabilityCreate(LiabilityBase):
    """Schema for creating a liability."""

    pass


class LiabilityUpdate(BaseModel):
    """Schema for updating a liability."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=1000)


class LiabilityResponse(LiabilityBase):
    """Schema for liability response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


# Health check responses


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    app: str
    environment: str
