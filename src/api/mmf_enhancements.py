from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from database import get_db
from src.models import DailyMMFYield, MMFAccount
from src.services.market_tracking import DEFAULT_KENYA_MMF_BENCHMARKS, accrue_daily, match_institution_yield

router = APIRouter(prefix="/api/mmf", tags=["MMF enhancements"])


def _latest_yields(db: Session):
    records = db.scalars(select(DailyMMFYield).order_by(desc(DailyMMFYield.yield_date))).all()
    if records:
        seen = set()
        result = {}
        for record in records:
            key = record.fund_name.casefold().strip()
            if key not in seen:
                seen.add(key)
                result[key] = Decimal(str(record.yield_decimal))
        return result
    return {name.casefold().strip(): rate for name, rate in DEFAULT_KENYA_MMF_BENCHMARKS}


def _latest_rate_record(db: Session, fund_name: str):
    records = db.scalars(select(DailyMMFYield).order_by(desc(DailyMMFYield.yield_date))).all()
    target = fund_name.casefold().strip()
    clean_target = target.replace("money market fund", "").replace("mmf", "").strip()
    for record in records:
        candidate = record.fund_name.casefold().strip()
        clean_candidate = candidate.replace("money market fund", "").replace("mmf", "").strip()
        if candidate == target or (clean_target and (clean_target in clean_candidate or clean_candidate in clean_target)):
            return record
    return None


@router.post("/{account_id}/accrue-today")
def accrue_today(account_id: str, db: Session = Depends(get_db)):
    """Compatibility endpoint for a single manual completed-day accrual."""
    account = db.get(MMFAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="MMF account not found")
    today = date.today()
    if account.last_accrued_on == today:
        return {"id": account.id, "interest_added": 0.0, "current_balance": float(account.current_balance), "accrued_on": today.isoformat()}

    matched = match_institution_yield(account.fund_name, _latest_yields(db))
    current = Decimal(str(account.current_balance))
    interest = accrue_daily(current, matched["yield_decimal"])
    account.current_balance = current + interest
    account.total_interest_accrued = Decimal(str(account.total_interest_accrued or 0)) + interest
    account.last_accrued_on = today
    db.commit()
    db.refresh(account)
    return {"id": account.id, "interest_added": float(interest), "current_balance": float(account.current_balance), "accrued_on": today.isoformat()}


@router.get("/rate-status")
def rate_status(db: Session = Depends(get_db)):
    """Expose the worker-fetched MMF rate and its source date to the UI."""
    result = []
    for account in db.scalars(select(MMFAccount)).all():
        record = _latest_rate_record(db, account.fund_name)
        result.append({
            "account_id": account.id,
            "fund_name": account.fund_name,
            "source": "worker" if record else "benchmark",
            "rate_date": record.yield_date.isoformat() if record else None,
            "annual_yield_percentage": round(float(record.yield_decimal) * 100, 2) if record else None,
        })
    return result
