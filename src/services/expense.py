"""Expense service for managing expenses."""
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import Expense
from src.schemas import ExpenseCreate, ExpenseUpdate


class ExpenseService:
    """Service for managing expenses."""

    @staticmethod
    def create_expense(db: Session, expense_data: ExpenseCreate) -> Expense:
        """Create a new expense."""
        expense = Expense(
            id=str(uuid4()),
            name=expense_data.name,
            category=expense_data.category,
            amount=expense_data.amount,
            currency=expense_data.currency,
            essential=expense_data.essential,
            active=expense_data.active,
            notes=expense_data.notes,
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)
        return expense

    @staticmethod
    def get_expense(db: Session, expense_id: str) -> Expense:
        """Get an expense by ID."""
        return db.query(Expense).filter(Expense.id == expense_id).first()

    @staticmethod
    def get_all_expenses(db: Session) -> list[Expense]:
        """Get all expenses."""
        return db.query(Expense).all()

    @staticmethod
    def get_active_expenses(db: Session) -> list[Expense]:
        """Get active expenses."""
        return db.query(Expense).filter(Expense.active == True).all()

    @staticmethod
    def get_essential_expenses(db: Session) -> list[Expense]:
        """Get essential expenses."""
        return db.query(Expense).filter(
            Expense.essential == True,
            Expense.active == True,
        ).all()

    @staticmethod
    def get_non_essential_expenses(db: Session) -> list[Expense]:
        """Get non-essential expenses."""
        return db.query(Expense).filter(
            Expense.essential == False,
            Expense.active == True,
        ).all()

    @staticmethod
    def update_expense(
        db: Session, expense_id: str, expense_data: ExpenseUpdate
    ) -> Expense:
        """Update an expense."""
        expense = ExpenseService.get_expense(db, expense_id)
        if not expense:
            return None

        if expense_data.name:
            expense.name = expense_data.name
        if expense_data.category:
            expense.category = expense_data.category
        if expense_data.amount is not None:
            expense.amount = expense_data.amount
        if expense_data.currency:
            expense.currency = expense_data.currency
        if expense_data.essential is not None:
            expense.essential = expense_data.essential
        if expense_data.active is not None:
            expense.active = expense_data.active
        if expense_data.notes is not None:
            expense.notes = expense_data.notes

        db.add(expense)
        db.commit()
        db.refresh(expense)
        return expense

    @staticmethod
    def delete_expense(db: Session, expense_id: str) -> bool:
        """Delete an expense."""
        expense = ExpenseService.get_expense(db, expense_id)
        if not expense:
            return False

        db.delete(expense)
        db.commit()
        return True

    @staticmethod
    def get_total_monthly_expenses(db: Session, base_currency: str = "KES") -> Decimal:
        """Get total monthly expenses."""
        result = db.query(
            func.sum(Expense.amount)
        ).filter(
            Expense.active == True,
            Expense.currency == base_currency,
        ).scalar()

        return Decimal(result or 0)

    @staticmethod
    def get_total_essential_expenses(db: Session, base_currency: str = "KES") -> Decimal:
        """Get total essential monthly expenses."""
        result = db.query(
            func.sum(Expense.amount)
        ).filter(
            Expense.active == True,
            Expense.essential == True,
            Expense.currency == base_currency,
        ).scalar()

        return Decimal(result or 0)

    @staticmethod
    def get_total_non_essential_expenses(db: Session, base_currency: str = "KES") -> Decimal:
        """Get total non-essential monthly expenses."""
        result = db.query(
            func.sum(Expense.amount)
        ).filter(
            Expense.active == True,
            Expense.essential == False,
            Expense.currency == base_currency,
        ).scalar()

        return Decimal(result or 0)

    @staticmethod
    def get_expense_summary(db: Session, base_currency: str = "KES") -> dict:
        """Get expense summary."""
        total = ExpenseService.get_total_monthly_expenses(db, base_currency)
        essential = ExpenseService.get_total_essential_expenses(db, base_currency)
        non_essential = ExpenseService.get_total_non_essential_expenses(db, base_currency)

        return {
            "total_monthly_expenses": total,
            "essential_expenses": essential,
            "non_essential_expenses": non_essential,
            "percentage_essential": float(
                (essential / total * 100) if total > 0 else 0
            ),
            "currency": base_currency,
        }
