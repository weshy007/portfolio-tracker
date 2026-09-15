"""Projection calculator service."""
from decimal import Decimal, ROUND_HALF_UP


class ProjectionService:
    """Service for financial projections."""

    @staticmethod
    def calculate_future_value(
        monthly_contribution: Decimal,
        annual_return_percent: Decimal,
        years: int,
    ) -> Decimal:
        """
        Calculate future value using compound interest formula.
        
        FV = P × ((1 + r)^n - 1) / r
        
        where:
            P = monthly contribution
            r = monthly return rate
            n = number of months
        
        Args:
            monthly_contribution: Monthly contribution amount
            annual_return_percent: Expected annual return as percentage (e.g., 12 for 12%)
            years: Number of years for projection
            
        Returns:
            Projected future value
        """
        if monthly_contribution < 0:
            raise ValueError("Monthly contribution cannot be negative")
        if years < 0:
            raise ValueError("Years cannot be negative")
        
        if years == 0:
            return Decimal(0)
        
        # Handle 0% return
        if annual_return_percent == 0:
            return monthly_contribution * Decimal(years * 12)
        
        # Convert annual return to monthly (decimal form)
        annual_rate = annual_return_percent / Decimal(100)
        monthly_rate = annual_rate / Decimal(12)
        
        # Number of months
        n = years * 12
        
        # Decimal arithmetic prevents binary floating-point drift in money values.
        factor = (Decimal(1) + monthly_rate) ** int(n)
        fv = monthly_contribution * ((factor - Decimal(1)) / monthly_rate)
        return fv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_contribution_only_projection(
        current_value: Decimal,
        monthly_contribution: Decimal,
        months: int,
    ) -> Decimal:
        """
        Calculate projected value with only contributions (no returns).
        
        Used when investment returns are not factored in.
        """
        if current_value < 0:
            raise ValueError("Current value cannot be negative")
        if monthly_contribution < 0:
            raise ValueError("Monthly contribution cannot be negative")
        if months < 0:
            raise ValueError("Months cannot be negative")
        
        return current_value + (monthly_contribution * Decimal(months))

    @staticmethod
    def calculate_monthly_contribution_needed(
        target_value: Decimal | None = None,
        current_value: Decimal = Decimal(0),
        annual_return_percent: Decimal = Decimal(0),
        months: int | None = None,
        **kwargs,
    ) -> Decimal:
        """
        Calculate monthly contribution needed to reach a target.

        Reverse of FV formula to solve for P.
        Supports both the newer and legacy parameter names.
        """
        if target_value is None:
            target_value = kwargs.get("target_amount", Decimal(0))
        if months is None:
            months = kwargs.get("years", 0) * 12
        if "target_amount" in kwargs and target_value is None:
            target_value = kwargs["target_amount"]
        if target_value < current_value:
            return Decimal(0)

        if months <= 0:
            raise ValueError("Months must be positive")

        if annual_return_percent == 0:
            remaining = target_value - current_value
            return (remaining / Decimal(months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        annual_rate = annual_return_percent / Decimal(100)
        monthly_rate = annual_rate / Decimal(12)
        current_fv = current_value * ((Decimal(1) + monthly_rate) ** int(months))
        additional_needed = target_value - current_fv

        if additional_needed <= 0:
            return Decimal(0)

        multiplier = ((Decimal(1) + monthly_rate) ** int(months) - Decimal(1)) / monthly_rate

        if multiplier == 0:
            return Decimal(0)

        contribution = additional_needed / multiplier
        return contribution.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_breakeven_return_rate(
        current_value: Decimal,
        monthly_contribution: Decimal,
        target_value: Decimal,
        years: int,
    ) -> float:
        """
        Calculate the annual return rate needed to reach target (approximation).
        
        Returns rate as percentage (0-50 for realistic estimates).
        Uses iterative approach.
        """
        if target_value <= current_value:
            return 0.0
        
        if years <= 0:
            return 0.0
        
        months = years * 12
        
        # Binary search for the rate
        low, high = Decimal(0), Decimal(50)
        epsilon = Decimal("0.01")  # Precision
        
        for _ in range(100):  # Max iterations
            mid = (low + high) / Decimal(2)
            
            fv = ProjectionService.calculate_future_value(
                monthly_contribution, mid, years
            )
            fv_with_current = current_value * (
                Decimal(1) + (mid / Decimal(100) / Decimal(12))
            ) ** Decimal(months) + fv
            
            if fv_with_current < target_value:
                low = mid
            else:
                high = mid
            
            if high - low < epsilon:
                break
        
        return float((low + high) / Decimal(2))
