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


@router.post("/{account_id}/accrue-today")
def accrue_today(account_id: str, db: Session = Depends(get_db)):
    account = db.get(MMFAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="MMF account not found")
    today = date.today()
    if account.last_accrued_on == today:
        return {"id": account.id, "interest_added": 0.0, "current_balance": float(account.current_balance), "accrued_on": today.isoformat()}

    matched = match_institution_yield(account.fund_name, _latest_yields(db))
    annual_yield = matched["yield_decimal"]
    current = Decimal(str(account.current_balance))
    interest = accrue_daily(current, annual_yield)
    account.current_balance = current + interest
    account.total_interest_accrued = Decimal(str(account.total_interest_accrued or 0)) + interest
    account.last_accrued_on = today
    db.commit()
    db.refresh(account)
    return {"id": account.id, "interest_added": float(interest), "current_balance": float(account.current_balance), "accrued_on": today.isoformat()}
