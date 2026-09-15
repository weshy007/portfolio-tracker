"""Portfolio service for managing holdings and portfolio calculations."""
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import Holding, Category
from src.schemas import HoldingCreate, HoldingUpdate


class PortfolioService:
    """Service for managing holdings and portfolio calculations."""

    @staticmethod
    def create_holding(db: Session, holding_data: HoldingCreate) -> Holding:
        """Create a new holding."""
        holding = Holding(
            id=str(uuid4()),
            name=holding_data.name,
            category_id=holding_data.category_id,
            amount=holding_data.amount,
            currency=holding_data.currency,
            notes=holding_data.notes,
        )
        db.add(holding)
        db.commit()
        db.refresh(holding)
        return holding

    @staticmethod
    def get_holding(db: Session, holding_id: str) -> Holding:
        """Get a holding by ID."""
        return db.query(Holding).filter(Holding.id == holding_id).first()

    @staticmethod
    def get_all_holdings(db: Session) -> list[Holding]:
        """Get all holdings."""
        return db.query(Holding).all()

    @staticmethod
    def get_holdings_by_category(db: Session, category_id: str) -> list[Holding]:
        """Get holdings by category."""
        return db.query(Holding).filter(Holding.category_id == category_id).all()

    @staticmethod
    def get_holdings_by_currency(db: Session, currency: str) -> list[Holding]:
        """Get holdings by currency."""
        return db.query(Holding).filter(Holding.currency == currency).all()

    @staticmethod
    def update_holding(
        db: Session, holding_id: str, holding_data: HoldingUpdate
    ) -> Holding:
        """Update a holding."""
        holding = PortfolioService.get_holding(db, holding_id)
        if not holding:
            return None

        if holding_data.name:
            holding.name = holding_data.name
        if holding_data.category_id:
            holding.category_id = holding_data.category_id
        if holding_data.amount is not None:
            holding.amount = holding_data.amount
        if holding_data.currency:
            holding.currency = holding_data.currency
        if holding_data.notes is not None:
            holding.notes = holding_data.notes

        db.add(holding)
        db.commit()
        db.refresh(holding)
        return holding

    @staticmethod
    def delete_holding(db: Session, holding_id: str) -> bool:
        """Delete a holding."""
        holding = PortfolioService.get_holding(db, holding_id)
        if not holding:
            return False

        db.delete(holding)
        db.commit()
        return True

    @staticmethod
    def get_total_portfolio_value(db: Session, base_currency: str = "KES") -> Decimal:
        """
        Get total portfolio value in base currency.
        Note: For now, only handles same-currency holdings.
        Currency conversion will be handled by CurrencyService.
        """
        result = db.query(
            func.sum(Holding.amount)
        ).filter(
            Holding.currency == base_currency
        ).scalar()

        return Decimal(result or 0)

    @staticmethod
    def get_portfolio_allocation(db: Session, base_currency: str = "KES") -> dict:
        """
        Get portfolio allocation by category.
        Returns dict with category info and percentages.
        """
        total_value = PortfolioService.get_total_portfolio_value(db, base_currency)

        if total_value == 0:
            return {
                "total_value": Decimal(0),
                "allocations": [],
                "has_holdings": False,
            }

        # Get allocations by category
        allocations = db.query(
            Category.id,
            Category.name,
            Category.category_type,
            func.sum(Holding.amount).label("amount"),
        ).join(
            Holding, Category.id == Holding.category_id
        ).filter(
            Holding.currency == base_currency
        ).group_by(
            Category.id, Category.name, Category.category_type
        ).order_by(
            func.sum(Holding.amount).desc()
        ).all()

        allocation_list = []
        for category_id, category_name, category_type, amount in allocations:
            percentage = (amount / total_value * 100) if total_value > 0 else 0
            allocation_list.append({
                "category_id": category_id,
                "category_name": category_name,
                "category_type": category_type,
                "amount": Decimal(amount or 0),
                "percentage": float(percentage),
            })

        return {
            "total_value": total_value,
            "allocations": allocation_list,
            "has_holdings": len(allocation_list) > 0,
        }

    @staticmethod
    def get_holdings_summary(db: Session) -> dict:
        """Get summary statistics about holdings."""
        total_holdings = db.query(Holding).count()
        unique_categories = db.query(Category).filter(
            Category.id.in_(
                db.query(Holding.category_id).distinct()
            )
        ).count()
        unique_currencies = db.query(
            func.distinct(Holding.currency)
        ).count()

        return {
            "total_holdings": total_holdings,
            "unique_categories": unique_categories,
            "unique_currencies": unique_currencies,
        }
