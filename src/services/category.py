"""Category service for managing investment categories."""
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models import Category, CategoryType, Holding
from src.schemas import CategoryCreate, CategoryUpdate


DEFAULT_CATEGORIES = [
    ("Emergency Fund", CategoryType.SAFETY),
    ("Cash", CategoryType.CASH),
    ("Money Market Fund", CategoryType.FIXED_INCOME),
    ("Treasury Bills", CategoryType.FIXED_INCOME),
    ("Government Bonds", CategoryType.FIXED_INCOME),
    ("NSE Stocks", CategoryType.EQUITIES),
    ("US Stocks", CategoryType.EQUITIES),
    ("International Stocks", CategoryType.EQUITIES),
    ("REITs", CategoryType.REAL_ESTATE),
    ("SACCO", CategoryType.RETIREMENT),
    ("Pension", CategoryType.RETIREMENT),
    ("Business", CategoryType.BUSINESS),
    ("Crypto", CategoryType.ALTERNATIVE),
    ("Other", CategoryType.OTHER),
]


class CategoryService:
    """Service for managing investment categories."""

    @staticmethod
    def create_default_categories(db: Session) -> list[Category]:
        """Create default categories if they don't exist."""
        categories = []
        for name, category_type in DEFAULT_CATEGORIES:
            existing = db.query(Category).filter(
                Category.name == name,
                Category.is_default == True
            ).first()
            if not existing:
                category = Category(
                    id=str(uuid4()),
                    name=name,
                    category_type=category_type,
                    is_default=True,
                )
                db.add(category)
                categories.append(category)
        if categories:
            db.commit()
        return categories

    @staticmethod
    def create_category(db: Session, category_data: CategoryCreate) -> Category:
        """Create a new category."""
        category = Category(
            id=str(uuid4()),
            name=category_data.name,
            category_type=category_data.category_type,
            is_default=False,  # User-created categories are never default
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def get_category(db: Session, category_id: str) -> Category:
        """Get a category by ID."""
        return db.query(Category).filter(Category.id == category_id).first()

    @staticmethod
    def get_all_categories(db: Session) -> list[Category]:
        """Get all categories."""
        return db.query(Category).all()

    @staticmethod
    def update_category(
        db: Session, category_id: str, category_data: CategoryUpdate
    ) -> Category:
        """Update a category."""
        category = CategoryService.get_category(db, category_id)
        if not category:
            return None

        # Prevent updating default categories if needed
        if category_data.name:
            category.name = category_data.name
        if category_data.category_type:
            category.category_type = category_data.category_type

        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def delete_category(db: Session, category_id: str) -> bool:
        """Delete a category if it has no holdings."""
        category = CategoryService.get_category(db, category_id)
        if not category:
            return False

        # Check if category has any holdings
        holdings_count = db.query(Holding).filter(
            Holding.category_id == category_id
        ).count()

        if holdings_count > 0:
            raise ValueError(f"Cannot delete category with {holdings_count} holding(s)")

        db.delete(category)
        db.commit()
        return True

    @staticmethod
    def get_categories_by_type(
        db: Session, category_type: CategoryType
    ) -> list[Category]:
        """Get categories by type."""
        return db.query(Category).filter(
            Category.category_type == category_type
        ).all()
