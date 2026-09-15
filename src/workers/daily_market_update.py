"""Background worker executing the 24-hour daily update cadence:

1. Scrapes daily effective annual yields from PesaCalc (https://pesacalc.co.ke).
2. Saves the daily yields into the 'daily_mmf_yields' table tracking fund_name, yield_decimal, and yield_date.
3. Implements the daily compound interest math engine:
   Today's Interest = Current Balance * (Daily Yield / 365.25)
   Accrues this interest into user's balance column once every 24 hours.

Can be run via cron / systemd:
    uv run python -m src.workers.daily_market_update
Or invoked programmatically by API endpoints.
"""
import asyncio
from datetime import date
from decimal import Decimal
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import get_db_context
from src.models import DailyMMFYield, MMFAccount, StockPosition
from src.services.market_tracking import (
    PesaCalcYieldScraper,
    MansaClient,
    accrue_daily,
    kes,
)

logger = logging.getLogger(__name__)


def find_matching_yield(fund_name: str, yield_map: dict[str, Decimal]) -> Optional[Decimal]:
    """Fuzzy-match an MMF account fund name against the scraped yield dictionary."""
    fund_lower = fund_name.casefold().strip()

    # Exact match
    if fund_lower in yield_map:
        return yield_map[fund_lower]

    # Keyword / prefix match
    clean_target = fund_lower.replace("money market fund", "").replace("mmf", "").strip()
    for name, rate in yield_map.items():
        clean_name = name.casefold().replace("money market fund", "").replace("mmf", "").strip()
        if clean_target and (clean_target in clean_name or clean_name in clean_target):
            return rate

    # Fallback to average of available yields if no specific match
    if yield_map:
        rates = list(yield_map.values())
        return sum(rates) / Decimal(len(rates))

    return None


async def run_daily_update() -> dict:
    """Execute the full 24-hour update cycle for MMF yields, accruals, and stock prices."""
    today = date.today()
    scraper = PesaCalcYieldScraper(settings.pesacalc_mmf_url)
    yields = await scraper.fetch()
    yield_map = {name.casefold().strip(): rate for name, rate in yields}

    yields_saved = 0
    accounts_accrued = 0
    total_interest_added = Decimal("0.00")

    with get_db_context() as db:
        # 1. Save yields into daily_mmf_yields table
        for fund_name, annual_yield in yields:
            existing = db.scalar(
                select(DailyMMFYield).where(
                    DailyMMFYield.fund_name == fund_name,
                    DailyMMFYield.yield_date == today,
                )
            )
            if not existing:
                db.add(
                    DailyMMFYield(
                        fund_name=fund_name,
                        yield_decimal=annual_yield,
                        yield_date=today,
                    )
                )
                yields_saved += 1
            else:
                existing.yield_decimal = annual_yield
        db.commit()

        # 2. Accrue daily compound interest into MMFAccount balances
        accounts = db.scalars(select(MMFAccount)).all()
        for account in accounts:
            if account.last_accrued_on == today:
                continue  # Already accrued for today

            annual_yield = find_matching_yield(account.fund_name, yield_map)
            if annual_yield is None:
                continue

            current_bal = Decimal(str(account.current_balance))
            interest = accrue_daily(current_bal, annual_yield)

            account.current_balance = current_bal + interest
            account.total_interest_accrued = Decimal(str(account.total_interest_accrued or 0)) + interest
            account.last_accrued_on = today

            accounts_accrued += 1
            total_interest_added += interest

        db.commit()

        # 3. Optionally refresh stock prices if MANSA_API_KEY is configured
        stocks_refreshed = 0
        if settings.mansa_api_key:
            client = MansaClient(settings.mansa_api_key, settings.mansa_api_url)
            from src.models.base import utc_now
            for stock in db.scalars(select(StockPosition)).all():
                try:
                    price = await client.close_price(stock.exchange or "NSE", stock.ticker)
                    stock.current_price = price
                    stock.price_updated_at = utc_now()
                    stocks_refreshed += 1
                except Exception as e:
                    logger.warning(f"Could not refresh stock {stock.ticker}: {e}")
            db.commit()

    summary = {
        "date": today.isoformat(),
        "yields_saved": yields_saved,
        "accounts_accrued": accounts_accrued,
        "total_interest_added": float(kes(total_interest_added)),
        "stocks_refreshed": stocks_refreshed,
    }
    logger.info(f"Daily update completed: {summary}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_daily_update())
    print("Daily market update finished:", result)
