from datetime import date
from decimal import Decimal

from src.services.market_tracking import accrue_daily
from src.workers.daily_market_update import find_matching_yield


def test_find_matching_yield_does_not_fabricate_rate():
    assert find_matching_yield("Unknown Fund", {"cic money market fund": Decimal("0.15")}) is None


def test_daily_interest_uses_the_supplied_day_rate():
    interest = accrue_daily(Decimal("100000"), Decimal("0.1460"))
    assert interest == Decimal("39.97")


def test_mmf_account_keeps_explicit_investment_date(client):
    response = client.post(
        "/api/market/mmfs",
        json={
            "fund_name": "CIC Money Market Fund",
            "current_principal_balance": 100000,
            "investment_date": "2026-09-01",
        },
    )
    assert response.status_code == 200
    assert response.json()["investment_date"] == date(2026, 9, 1).isoformat()
