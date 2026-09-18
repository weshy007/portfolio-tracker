"""Background worker for daily MMF yields, accruals, and market prices."""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
import logging
from typing import Optional

from sqlalchemy import select

from config import settings
from database import get_db_context
from src.models import DailyMMFYield, MMFAccount, StockPosition
from src.services.market_tracking import PesaCalcYieldScraper, MansaClient, accrue_daily, kes

logger = logging.getLogger(__name__)


def find_matching_yield(fund_name: str, yield_map: dict[str, Decimal]) -> Optional[Decimal]:
    """Fuzzy-match an MMF account fund name against a yield dictionary."""
    fund_lower = fund_name.casefold().strip()
    if fund_lower in yield_map:
        return yield_map[fund_lower]

    clean_target = fund_lower.replace("money market fund", "").replace("mmf", "").strip()
    for name, rate in yield_map.items():
        clean_name = name.casefold().replace("money market fund", "").replace("mmf", "").strip()
        if clean_target and (clean_target in clean_name or clean_name in clean_target):
            return rate

    return None


def _yield_for_date(db, fund_name: str, valuation_date: date) -> Optional[Decimal]:
    """Return the latest known scraped annual yield for one fund.

    Prefer the latest yield available on or before the valuation date. If the
    fund was first scraped after that date, use its latest available yield
    instead of inventing a historical rate or skipping the investment day.
    """
    records = db.scalars(select(DailyMMFYield).order_by(DailyMMFYield.yield_date.desc())).all()
    if not records:
        return None

    latest_all: dict[str, Decimal] = {}
    latest_before: dict[str, Decimal] = {}
    for record in records:
        key = record.fund_name.casefold().strip()
        value = Decimal(str(record.yield_decimal))
        if key not in latest_all:
            latest_all[key] = value
        if record.yield_date <= valuation_date and key not in latest_before:
            latest_before[key] = value

    return find_matching_yield(fund_name, latest_before) or find_matching_yield(fund_name, latest_all)


async def run_daily_update() -> dict:
    """Fetch today's rates, then compound each MMF from its investment day through today.

    The daily rate is annual_yield / 365 and is applied to the current balance.
    If a historical day's scrape is missing, the latest available scraped yield is used.
    """
    today = date.today()
    valuation_date = today
    scraper = PesaCalcYieldScraper(settings.pesacalc_mmf_url)
    yields = await scraper.fetch()

    yields_saved = 0
    accounts_accrued = 0
    total_interest_added = Decimal("0.00")

    with get_db_context() as db:
        # Worker-owned rate history. The UI reads this table; it does not scrape rates.
        for fund_name, annual_yield in yields:
            existing = db.scalar(
                select(DailyMMFYield).where(
                    DailyMMFYield.fund_name == fund_name,
                    DailyMMFYield.yield_date == today,
                )
            )
            if existing:
                existing.yield_decimal = annual_yield
            else:
                db.add(DailyMMFYield(fund_name=fund_name, yield_decimal=annual_yield, yield_date=today))
                yields_saved += 1
        db.flush()

        for account in db.scalars(select(MMFAccount)).all():
            investment_day = account.investment_date or (account.created_at.date() if account.created_at else today)
            first_unaccrued = account.last_accrued_on + timedelta(days=1) if account.last_accrued_on else investment_day
            accrual_day = max(first_unaccrued, investment_day)

            # Compound every investment day through the current valuation day.
                annual_yield = _yield_for_date(db, account.fund_name, accrual_day)
                if annual_yield is None:
                    # Do not advance past a day for which no worker-fetched rate exists.
                    break

                current_balance = Decimal(str(account.current_balance))
                interest = accrue_daily(current_balance, annual_yield)
                account.current_balance = current_balance + interest
                account.total_interest_accrued = Decimal(str(account.total_interest_accrued or 0)) + interest
                account.last_accrued_on = accrual_day
                accounts_accrued += 1
                total_interest_added += interest
                accrual_day += timedelta(days=1)

        db.commit()

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
                except Exception as error:
                    logger.warning("Could not refresh stock %s: %s", stock.ticker, error)
            db.commit()

    summary = {
        "date": today.isoformat(),
        "valuation_date": valuation_date.isoformat(),
        "yields_saved": yields_saved,
        "accounts_accrued": accounts_accrued,
        "total_interest_added": float(kes(total_interest_added)),
        "stocks_refreshed": stocks_refreshed,
    }
    logger.info("Daily update completed: %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_daily_update())
    print("Daily market update finished:", result)
