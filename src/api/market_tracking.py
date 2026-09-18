"""Database-backed stock/MMF endpoints; provider keys stay server-side."""
from datetime import date
from decimal import Decimal
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from src.models import DailyMMFYield, MMFAccount, StockPosition, utc_now
from src.services.market_tracking import (
    DEFAULT_KENYA_MMF_BENCHMARKS,
    MansaAPIError,
    MansaClient,
    MansaConfigError,
    MansaTimeoutError,
    PesaCalcYieldScraper,
    accrue_daily,
    kes,
    stock_summary,
)
from src.workers.daily_market_update import find_matching_yield, run_daily_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market tracking"])


# Request Schemas
class StockCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    exchange: str = Field(default="NSE", min_length=2, max_length=12)
    shares_owned: Decimal = Field(gt=0)
    average_buy_price: Decimal = Field(gt=0)
    current_price: Optional[Decimal] = Field(default=None, gt=0)


class MMFCreate(BaseModel):
    fund_name: str = Field(min_length=2, max_length=255)
    current_principal_balance: Decimal = Field(gt=0)
    investment_date: Optional[date] = None


# ==========================================
# 1. STOCK TRACKING ENDPOINTS (Mansa API)
# ==========================================


@router.get("/stocks/price")
async def get_stock_price(
    ticker: str = Query(..., min_length=1, max_length=32, description="Stock ticker symbol (e.g. SCOM, EQTY)"),
    exchange: str = Query("NSE", min_length=2, max_length=12, description="Exchange code"),
):
    """Fetch end-of-day stock closing price from Mansa API using MANSA_API_KEY."""
    client = MansaClient(settings.mansa_api_key, settings.mansa_api_url)
    try:
        price = await client.close_price(exchange, ticker)
        return {
            "ticker": ticker.upper(),
            "exchange": exchange.upper(),
            "price": float(price),
            "currency": "KES",
            "fetched_at": utc_now().isoformat(),
        }
    except MansaConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except MansaTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except MansaAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error querying Mansa API: {e}",
        )


@router.get("/stocks/nse-tickers")
async def list_nse_tickers(exchange: str = Query("NSE", description="Exchange code")):
    """Return the bundled NSE directory; no market-data request is needed for names."""
    from fastapi.responses import JSONResponse
    from src.services.market_tracking import NSE_STOCKS_DIRECTORY
    if exchange.strip().upper() != "NSE":
        return []
    return JSONResponse(
        content=NSE_STOCKS_DIRECTORY,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/stocks")
def list_stocks(db: Session = Depends(get_db)):
    """List all stock holdings with current value, cost basis, and profit/loss calculated."""
    positions = db.scalars(select(StockPosition).order_by(desc(StockPosition.created_at))).all()
    results = []

    for pos in positions:
        shares = Decimal(str(pos.shares_owned))
        buy_price = Decimal(str(pos.average_buy_price))
        curr_price = Decimal(str(pos.current_price if pos.current_price is not None else buy_price))

        summary = stock_summary(shares, buy_price, curr_price)
        results.append({
            "id": pos.id,
            "ticker": pos.ticker,
            "exchange": pos.exchange,
            "currency": "USD" if pos.exchange == "US" else "KES",
            "shares_owned": float(summary["shares_owned"]),
            "average_buy_price": float(summary["average_buy_price"]),
            "current_price": float(summary["current_price"]),
            "cost_basis": float(summary["cost_basis"]),
            "current_value": float(summary["current_value"]),
            "profit_loss": float(summary["profit_loss"]),
            "profit_loss_percentage": float(summary["profit_loss_percentage"]),
            "price_updated_at": pos.price_updated_at.isoformat() if pos.price_updated_at else None,
            "created_at": pos.created_at.isoformat() if pos.created_at else None,
        })

    return results


@router.post("/stocks")
async def create_stock(payload: StockCreate, db: Session = Depends(get_db)):
    """Create a new stock position.
    
    Per requirements, automatically fetches the current price from Mansa API if MANSA_API_KEY
    is set, falling back to user provided price or average buy price.
    """
    ticker_upper = payload.ticker.strip().upper()
    exchange_upper = payload.exchange.strip().upper()

    current_price = payload.current_price
    price_updated_at = None

    # Fetch live/EOD price from Mansa API
    if settings.mansa_api_key:
        try:
            client = MansaClient(settings.mansa_api_key, settings.mansa_api_url)
            price = await client.close_price(exchange_upper, ticker_upper)
            current_price = price
            price_updated_at = utc_now()
        except Exception as e:
            logger.warning(f"Could not auto-fetch Mansa price for {ticker_upper}: {e}")

    # If still not set, fallback to average_buy_price
    if current_price is None:
        current_price = payload.average_buy_price

    position = StockPosition(
        ticker=ticker_upper,
        exchange=exchange_upper,
        shares_owned=payload.shares_owned,
        average_buy_price=payload.average_buy_price,
        current_price=current_price,
        price_updated_at=price_updated_at,
    )
    db.add(position)
    db.commit()
    db.refresh(position)

    summary = stock_summary(
        Decimal(str(position.shares_owned)),
        Decimal(str(position.average_buy_price)),
        Decimal(str(position.current_price)),
    )

    return {
        "id": position.id,
        "ticker": position.ticker,
        "exchange": position.exchange,
        **{k: float(v) if isinstance(v, Decimal) else v for k, v in summary.items()},
    }


@router.post("/stocks/{position_id}/refresh")
async def refresh_stock(position_id: str, db: Session = Depends(get_db)):
    """Refresh a stock's closing price from Mansa API and update calculation metrics."""
    position = db.get(StockPosition, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Stock position not found")

    client = MansaClient(settings.mansa_api_key, settings.mansa_api_url)
    try:
        price = await client.close_price(position.exchange or "NSE", position.ticker)
    except MansaConfigError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MansaTimeoutError as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e))
    except MansaAPIError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error))

    position.current_price = price
    position.price_updated_at = utc_now()
    db.commit()

    summary = stock_summary(
        Decimal(str(position.shares_owned)),
        Decimal(str(position.average_buy_price)),
        price,
    )
    return {
        "id": position.id,
        "ticker": position.ticker,
        **{k: float(v) if isinstance(v, Decimal) else v for k, v in summary.items()},
    }


@router.post("/stocks/refresh-all")
async def refresh_all_stocks(db: Session = Depends(get_db)):
    """Refresh all stock positions with closing prices from Mansa API."""
    if not settings.mansa_api_key:
        raise HTTPException(status_code=400, detail="MANSA_API_KEY is not configured")

    client = MansaClient(settings.mansa_api_key, settings.mansa_api_url)
    positions = db.scalars(select(StockPosition)).all()
    refreshed = 0
    errors = []

    for pos in positions:
        try:
            price = await client.close_price(pos.exchange or "NSE", pos.ticker)
            pos.current_price = price
            pos.price_updated_at = utc_now()
            refreshed += 1
        except Exception as e:
            errors.append({"ticker": pos.ticker, "error": str(e)})

    db.commit()
    return {"refreshed": refreshed, "total": len(positions), "errors": errors}


@router.delete("/stocks/{position_id}")
def delete_stock(position_id: str, db: Session = Depends(get_db)):
    """Delete a stock position from portfolio."""
    position = db.get(StockPosition, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Stock position not found")
    db.delete(position)
    db.commit()
    return {"message": f"Deleted position {position.ticker}"}


# ==========================================
# 2. MMF TRACKING & ESTIMATED VALUE ENGINE
# ==========================================


@router.get("/mmfs")
def list_mmfs(db: Session = Depends(get_db)):
    """List all MMF accounts with principal, current balance, interest, and yield."""
    accounts = db.scalars(select(MMFAccount).order_by(desc(MMFAccount.created_at))).all()

    # Load latest yields
    yield_records = db.scalars(
        select(DailyMMFYield).order_by(desc(DailyMMFYield.yield_date))
    ).all()
    yield_map = {}
    for record in yield_records:
        key = record.fund_name.casefold().strip()
        if key not in yield_map:
            yield_map[key] = Decimal(str(record.yield_decimal))

    if not yield_map:
        yield_map = {name.casefold().strip(): rate for name, rate in DEFAULT_KENYA_MMF_BENCHMARKS}

    from src.services.market_tracking import match_institution_yield

    results = []
    for acc in accounts:
        curr_bal = Decimal(str(acc.current_balance))
        principal = Decimal(str(acc.principal_balance))
        interest_accrued = Decimal(str(acc.total_interest_accrued or 0))

        matched = match_institution_yield(acc.fund_name, yield_map)
        annual_yield = matched["yield_decimal"]
        yield_pct = matched["yield_percentage"]
        today_est_interest = float(accrue_daily(curr_bal, annual_yield))

        results.append({
            "id": acc.id,
            "fund_name": acc.fund_name,
            "institution": matched["institution"],
            "currency": "KES",
            "investment_date": acc.investment_date.isoformat() if acc.investment_date else None,
            "short_name": matched["short_name"],
            "principal_balance": float(kes(principal)),
            "current_balance": float(kes(curr_bal)),
            "total_interest_accrued": float(kes(interest_accrued)),
            "annual_yield_percentage": round(yield_pct, 2),
            "daily_yield_percentage": round(float(matched["daily_yield_decimal"]) * 100, 4),
            "today_estimated_interest": today_est_interest,
            "last_accrued_on": acc.last_accrued_on.isoformat() if acc.last_accrued_on else None,
            "created_at": acc.created_at.isoformat() if acc.created_at else None,
        })

    return results


@router.post("/mmfs")
def create_mmf(payload: MMFCreate, db: Session = Depends(get_db)):
    """Create a new MMF account with initial principal balance."""
    account = MMFAccount(
        fund_name=payload.fund_name.strip(),
        principal_balance=payload.current_principal_balance,
        current_balance=payload.current_principal_balance,
        total_interest_accrued=Decimal("0.00"),
        investment_date=payload.investment_date or date.today(),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {
        "id": account.id,
        "fund_name": account.fund_name,
        "principal_balance": float(account.principal_balance),
        "current_balance": float(account.current_balance),
        "investment_date": account.investment_date.isoformat() if account.investment_date else None,
    }


@router.post("/mmfs/accrue")
async def accrue_mmf_interest(db: Session = Depends(get_db)):
    """Trigger the daily compound interest accrual for all MMF accounts."""
    result = await run_daily_update()
    return result


@router.delete("/mmfs/{account_id}")
def delete_mmf(account_id: str, db: Session = Depends(get_db)):
    """Delete an MMF account."""
    account = db.get(MMFAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="MMF account not found")
    db.delete(account)
    db.commit()
    return {"message": f"Deleted MMF account {account.fund_name}"}


# ==========================================
# 3. YIELD SCRAPING & TRACKED FUNDS
# ==========================================


@router.get("/yields")
def list_yields(db: Session = Depends(get_db)):
    """Get latest effective annual yields for tracked Money Market Funds."""
    today = date.today()
    latest_yields = db.scalars(
        select(DailyMMFYield).order_by(desc(DailyMMFYield.yield_date), DailyMMFYield.fund_name)
    ).all()

    if latest_yields:
        # Group by fund name, take latest
        seen = set()
        unique = []
        for r in latest_yields:
            if r.fund_name not in seen:
                seen.add(r.fund_name)
                unique.append({
                    "fund_name": r.fund_name,
                    "yield_decimal": float(r.yield_decimal),
                    "yield_percentage": round(float(r.yield_decimal) * 100, 2),
                    "date": r.yield_date.isoformat(),
                })
        return unique

    # Fallback to defaults
    return [
        {
            "fund_name": name,
            "yield_decimal": float(rate),
            "yield_percentage": round(float(rate) * 100, 2),
            "date": today.isoformat(),
        }
        for name, rate in DEFAULT_KENYA_MMF_BENCHMARKS
    ]


@router.post("/yields/scrape")
async def scrape_yields(db: Session = Depends(get_db)):
    """Trigger the PesaCalc yield scraper and persist the daily rates into daily_mmf_yields."""
    scraper = PesaCalcYieldScraper(settings.pesacalc_mmf_url)
    yields = await scraper.fetch()
    today = date.today()
    saved = 0

    for fund_name, annual_yield in yields:
        existing = db.scalar(
            select(DailyMMFYield).where(
                DailyMMFYield.fund_name == fund_name,
                DailyMMFYield.yield_date == today,
            )
        )
        if not existing:
            db.add(DailyMMFYield(fund_name=fund_name, yield_decimal=annual_yield, yield_date=today))
            saved += 1
        else:
            existing.yield_decimal = annual_yield
    return {"status": "success", "yields_scraped": len(yields), "yields_saved": saved, "date": today.isoformat()}


@router.get("/institutions")
def list_institutions(db: Session = Depends(get_db)):
    """List all tracked financial institutions with their funds and matched current yields."""
    from src.services.market_tracking import KENYA_MMF_INSTITUTIONS, match_institution_yield

    # Load latest yields from db
    yield_records = db.scalars(select(DailyMMFYield).order_by(desc(DailyMMFYield.yield_date))).all()
    yield_map = {r.fund_name.casefold().strip(): Decimal(str(r.yield_decimal)) for r in yield_records}

    results = []
    for item in KENYA_MMF_INSTITUTIONS:
        matched = match_institution_yield(item["institution"], yield_map)
        results.append({
            "institution": item["institution"],
            "short_name": item["short_name"],
            "fund_name": item["fund_name"],
            "yield_decimal": float(matched["yield_decimal"]),
            "yield_percentage": round(matched["yield_percentage"], 2),
            "daily_yield_decimal": float(matched["daily_yield_decimal"]),
        })

    return results


@router.get("/institutions/match")
def match_institution(query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Match an institution or fund name to its current yield interest."""
    from src.services.market_tracking import match_institution_yield

    yield_records = db.scalars(select(DailyMMFYield).order_by(desc(DailyMMFYield.yield_date))).all()
    yield_map = {r.fund_name.casefold().strip(): Decimal(str(r.yield_decimal)) for r in yield_records}

    matched = match_institution_yield(query, yield_map)
    return {
        "institution": matched["institution"],
        "short_name": matched["short_name"],
        "fund_name": matched["fund_name"],
        "yield_decimal": float(matched["yield_decimal"]),
        "yield_percentage": round(matched["yield_percentage"], 2),
        "daily_yield_decimal": float(matched["daily_yield_decimal"]),
    }


# ==========================================
# 4. UNIFIED FINANCIAL SUMMARY
# ==========================================


@router.get("/summary")
def get_unified_summary(db: Session = Depends(get_db)):
    """Return native-currency summary data without mixing KES and USD."""
    stocks = db.scalars(select(StockPosition)).all()
    mmfs = db.scalars(select(MMFAccount)).all()

    totals_by_currency: dict[str, dict[str, Decimal]] = {}
    for s in stocks:
        currency = "USD" if s.exchange == "US" else "KES"
        shares = Decimal(str(s.shares_owned))
        buy_price = Decimal(str(s.average_buy_price))
        curr_price = Decimal(str(s.current_price if s.current_price is not None else buy_price))
        bucket = totals_by_currency.setdefault(currency, {"value": Decimal("0.00"), "cost": Decimal("0.00")})
        bucket["cost"] += shares * buy_price
        bucket["value"] += shares * curr_price

    kes_bucket = totals_by_currency.get("KES", {"value": Decimal("0.00"), "cost": Decimal("0.00")})
    total_stock_value = kes_bucket["value"]
    total_stock_cost = kes_bucket["cost"]
    stock_profit_loss = total_stock_value - total_stock_cost
    stock_profit_loss_pct = (
        ((stock_profit_loss / total_stock_cost) * Decimal("100")).quantize(Decimal("0.01"))
        if total_stock_cost > 0
        else Decimal("0.00")
    )

    total_mmf_value = Decimal("0.00")
    total_mmf_principal = Decimal("0.00")
    total_mmf_interest_accrued = Decimal("0.00")

    for m in mmfs:
        total_mmf_principal += Decimal(str(m.principal_balance))
        total_mmf_value += Decimal(str(m.current_balance))
        total_mmf_interest_accrued += Decimal(str(m.total_interest_accrued or 0))

    return {
        "currency": "KES",
        "currency_totals": {
            currency: {
                "current_value": float(kes(bucket["value"])),
                "cost_basis": float(kes(bucket["cost"])),
            }
            for currency, bucket in totals_by_currency.items()
        },
        "total_portfolio_value": float(kes(total_stock_value + total_mmf_value)),
        "total_stock_value": float(kes(total_stock_value)),
        "total_stock_cost": float(kes(total_stock_cost)),
        "stock_profit_loss": float(kes(stock_profit_loss)),
        "stock_profit_loss_percentage": float(stock_profit_loss_pct),
        "stock_positions_count": len(stocks),
        "total_mmf_value": float(kes(total_mmf_value)),
        "total_mmf_principal": float(kes(total_mmf_principal)),
        "total_mmf_interest_accrued": float(kes(total_mmf_interest_accrued)),
        "mmf_accounts_count": len(mmfs),
    }
