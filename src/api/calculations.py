"""API routes for financial calculations."""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from config import settings
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from src.schemas import HealthResponse
from src.services import (
    BudgetService,
    EmergencyFundService,
    ExpenseService,
    IncomeService,
    NetWorthService,
    PortfolioService,
    ProjectionService,
    CachedCurrencyService,
    ExchangeRateAPIProvider,
)


router = APIRouter(prefix="/api", tags=["calculations"])
currency_service = CachedCurrencyService(
    ExchangeRateAPIProvider(settings.currency_api_url), settings.currency_cache_minutes
)


# Request/Response models for calculations


class EmergencyFundRequest(BaseModel):
    """Request for emergency fund calculation."""

    essential_monthly_expenses: Decimal = Field(
        ..., ge=0, description="Essential monthly expenses"
    )
    target_months: Optional[int] = Field(
        6, ge=0, le=24, description="Target months of coverage"
    )
    current_emergency_fund: Optional[Decimal] = Field(
        0, ge=0, description="Current emergency fund balance"
    )


class EmergencyFundResponse(BaseModel):
    """Emergency fund calculation response."""

    target: Decimal
    current: Decimal
    remaining: Decimal
    percentage_complete: float
    months_covered: float
    is_fully_funded: bool
    excess: float
    target_months: Optional[int] = None


class AllocationRequest(BaseModel):
    """Request for allocation calculation."""

    total_income: Decimal = Field(..., ge=0, description="Total monthly income")
    expenses: Decimal = Field(0, ge=0, description="Total expenses")
    savings: Decimal = Field(0, ge=0, description="Total savings")
    investments: Decimal = Field(0, ge=0, description="Total investments")
    debt: Decimal = Field(0, ge=0, description="Total debt payments")
    other: Decimal = Field(0, ge=0, description="Other allocations")


class AllocationResponse(BaseModel):
    """Allocation calculation response."""

    total_income: Decimal
    total_allocated: Decimal
    unallocated: Decimal
    overallocated: Decimal
    percentage_allocated: float
    allocations: dict
    percentages: dict


class ProjectionRequest(BaseModel):
    """Request for financial projection."""

    monthly_contribution: Decimal = Field(..., ge=0, description="Monthly contribution")
    annual_return_percent: Decimal = Field(
        0, ge=0, le=100, description="Expected annual return %"
    )
    years: int = Field(..., ge=0, le=50, description="Projection period in years")
    current_value: Optional[Decimal] = Field(
        0, ge=0, description="Current investment value"
    )


class ProjectionResponse(BaseModel):
    """Projection calculation response."""

    projected_value: Decimal
    total_contributions: Decimal
    total_returns: Decimal
    monthly_contribution: Decimal
    annual_return_percent: Decimal
    years: int


class SavingsRateRequest(BaseModel):
    """Request for savings rate calculation."""

    savings_amount: Decimal = Field(..., ge=0, description="Savings amount")
    total_income: Decimal = Field(..., ge=0, description="Total income")


class SavingsRateResponse(BaseModel):
    """Savings rate response."""

    savings_amount: Decimal
    total_income: Decimal
    savings_rate_percent: float


class NetWorthRequest(BaseModel):
    """Request for net worth calculation."""

    total_assets: Decimal = Field(..., ge=0, description="Total assets")
    total_liabilities: Decimal = Field(..., ge=0, description="Total liabilities")


class NetWorthResponse(BaseModel):
    """Net worth response."""

    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal


class CurrencyRateResponse(BaseModel):
    from_currency: str
    to_currency: str
    rate: Decimal
    cached: bool
    last_updated: str | None


# Endpoints


@router.post("/calculate/emergency-fund", response_model=EmergencyFundResponse)
async def calculate_emergency_fund(request: EmergencyFundRequest):
    """Calculate emergency fund target and coverage."""
    try:
        result = EmergencyFundService.calculate_emergency_fund_with_custom_target(
            request.essential_monthly_expenses,
            request.target_months or 6,
            request.current_emergency_fund or 0,
        )

        return EmergencyFundResponse(
            target=result["target"],
            current=result["current"],
            remaining=result["remaining"],
            percentage_complete=result["percentage_complete"],
            months_covered=result["months_covered"],
            is_fully_funded=result["is_fully_funded"],
            excess=float(result["excess"]),
            target_months=result.get("target_months"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/allocation", response_model=AllocationResponse)
async def calculate_allocation(request: AllocationRequest):
    """Calculate income allocation."""
    try:
        allocations = {
            "expenses": request.expenses,
            "savings": request.savings,
            "investments": request.investments,
            "debt": request.debt,
            "other": request.other,
        }

        result = BudgetService.calculate_allocation_allocation_summary(
            request.total_income, allocations
        )

        return AllocationResponse(
            total_income=result["total_income"],
            total_allocated=result["total_allocated"],
            unallocated=result["unallocated"],
            overallocated=result["overallocated"],
            percentage_allocated=result["percentage_allocated"],
            allocations=result["allocations"],
            percentages=result["percentages"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/projection", response_model=ProjectionResponse)
async def calculate_projection(request: ProjectionRequest):
    """Calculate financial projection."""
    try:
        fv = ProjectionService.calculate_future_value(
            request.monthly_contribution,
            request.annual_return_percent,
            request.years,
        )

        total_contributions = request.monthly_contribution * Decimal(request.years * 12)
        total_returns = fv - total_contributions

        return ProjectionResponse(
            projected_value=fv,
            total_contributions=total_contributions,
            total_returns=total_returns,
            monthly_contribution=request.monthly_contribution,
            annual_return_percent=request.annual_return_percent,
            years=request.years,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/savings-rate", response_model=SavingsRateResponse)
async def calculate_savings_rate(request: SavingsRateRequest):
    """Calculate savings rate."""
    try:
        rate = BudgetService.calculate_savings_rate(
            request.savings_amount, request.total_income
        )

        return SavingsRateResponse(
            savings_amount=request.savings_amount,
            total_income=request.total_income,
            savings_rate_percent=rate,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/net-worth", response_model=NetWorthResponse)
async def calculate_net_worth(request: NetWorthRequest):
    """Calculate net worth."""
    try:
        net_worth = request.total_assets - request.total_liabilities

        return NetWorthResponse(
            total_assets=request.total_assets,
            total_liabilities=request.total_liabilities,
            net_worth=net_worth,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/currency/rate", response_model=CurrencyRateResponse)
async def get_currency_rate(
    from_currency: str = Query(..., min_length=3, max_length=3),
    to_currency: str = Query(..., min_length=3, max_length=3),
):
    """Return a currency pair only. Amounts and personal financial records are never accepted."""
    try:
        source, destination = from_currency.upper(), to_currency.upper()
        rate, cached = await currency_service.get_rate(source, destination)
        updated = currency_service.get_last_update(source, destination)
        return CurrencyRateResponse(
            from_currency=source, to_currency=destination, rate=rate, cached=cached,
            last_updated=updated.isoformat() if updated else None,
        )
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="No live or cached exchange rate is available for this pair.") from error
