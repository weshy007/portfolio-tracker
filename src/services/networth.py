"""Net worth service for managing assets and liabilities."""
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import Asset, Liability
from src.schemas import AssetCreate, AssetUpdate, LiabilityCreate, LiabilityUpdate


class AssetService:
    """Service for managing assets."""

    @staticmethod
    def create_asset(db: Session, asset_data: AssetCreate) -> Asset:
        """Create a new asset."""
        asset = Asset(
            id=str(uuid4()),
            name=asset_data.name,
            category=asset_data.category,
            amount=asset_data.amount,
            currency=asset_data.currency,
            notes=asset_data.notes,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def get_asset(db: Session, asset_id: str) -> Asset:
        """Get an asset by ID."""
        return db.query(Asset).filter(Asset.id == asset_id).first()

    @staticmethod
    def get_all_assets(db: Session) -> list[Asset]:
        """Get all assets."""
        return db.query(Asset).all()

    @staticmethod
    def update_asset(
        db: Session, asset_id: str, asset_data: AssetUpdate
    ) -> Asset:
        """Update an asset."""
        asset = AssetService.get_asset(db, asset_id)
        if not asset:
            return None

        if asset_data.name:
            asset.name = asset_data.name
        if asset_data.category:
            asset.category = asset_data.category
        if asset_data.amount is not None:
            asset.amount = asset_data.amount
        if asset_data.currency:
            asset.currency = asset_data.currency
        if asset_data.notes is not None:
            asset.notes = asset_data.notes

        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def delete_asset(db: Session, asset_id: str) -> bool:
        """Delete an asset."""
        asset = AssetService.get_asset(db, asset_id)
        if not asset:
            return False

        db.delete(asset)
        db.commit()
        return True

    @staticmethod
    def get_total_assets(db: Session, base_currency: str = "KES") -> Decimal:
        """Get total asset value."""
        result = db.query(
            func.sum(Asset.amount)
        ).filter(
            Asset.currency == base_currency
        ).scalar()

        return Decimal(result or 0)


class LiabilityService:
    """Service for managing liabilities."""

    @staticmethod
    def create_liability(db: Session, liability_data: LiabilityCreate) -> Liability:
        """Create a new liability."""
        liability = Liability(
            id=str(uuid4()),
            name=liability_data.name,
            category=liability_data.category,
            amount=liability_data.amount,
            currency=liability_data.currency,
            interest_rate=liability_data.interest_rate,
            notes=liability_data.notes,
        )
        db.add(liability)
        db.commit()
        db.refresh(liability)
        return liability

    @staticmethod
    def get_liability(db: Session, liability_id: str) -> Liability:
        """Get a liability by ID."""
        return db.query(Liability).filter(Liability.id == liability_id).first()

    @staticmethod
    def get_all_liabilities(db: Session) -> list[Liability]:
        """Get all liabilities."""
        return db.query(Liability).all()

    @staticmethod
    def update_liability(
        db: Session, liability_id: str, liability_data: LiabilityUpdate
    ) -> Liability:
        """Update a liability."""
        liability = LiabilityService.get_liability(db, liability_id)
        if not liability:
            return None

        if liability_data.name:
            liability.name = liability_data.name
        if liability_data.category:
            liability.category = liability_data.category
        if liability_data.amount is not None:
            liability.amount = liability_data.amount
        if liability_data.currency:
            liability.currency = liability_data.currency
        if liability_data.interest_rate is not None:
            liability.interest_rate = liability_data.interest_rate
        if liability_data.notes is not None:
            liability.notes = liability_data.notes

        db.add(liability)
        db.commit()
        db.refresh(liability)
        return liability

    @staticmethod
    def delete_liability(db: Session, liability_id: str) -> bool:
        """Delete a liability."""
        liability = LiabilityService.get_liability(db, liability_id)
        if not liability:
            return False

        db.delete(liability)
        db.commit()
        return True

    @staticmethod
    def get_total_liabilities(db: Session, base_currency: str = "KES") -> Decimal:
        """Get total liability value."""
        result = db.query(
            func.sum(Liability.amount)
        ).filter(
            Liability.currency == base_currency
        ).scalar()

        return Decimal(result or 0)


class NetWorthService:
    """Service for calculating net worth."""

    @staticmethod
    def calculate_net_worth(db: Session, base_currency: str = "KES") -> dict:
        """Calculate net worth."""
        total_assets = AssetService.get_total_assets(db, base_currency)
        total_liabilities = LiabilityService.get_total_liabilities(db, base_currency)
        net_worth = total_assets - total_liabilities

        return {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
            "currency": base_currency,
        }
