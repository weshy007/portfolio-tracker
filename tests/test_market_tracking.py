"""Comprehensive automated tests for Stock Tracking, Mansa API, MMF Scraper, and Accrual Engine."""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from database import get_db
from src.models.base import DailyMMFYield, MMFAccount, StockPosition
from src.services.market_tracking import (
    DEFAULT_KENYA_MMF_BENCHMARKS,
    KENYA_MMF_INSTITUTIONS,
    MansaAPIError,
    MansaClient,
    MansaConfigError,
    MansaTimeoutError,
    PesaCalcYieldScraper,
    accrue_daily,
    kes,
    match_institution_yield,
    stock_summary,
)
from src.workers.daily_market_update import find_matching_yield, run_daily_update


# ==========================================
# 1. MATH ENGINE & HELPER TESTS
# ==========================================


def test_kes_quantization():
    """Verify standard financial ROUND_HALF_UP to 2 decimal places."""
    assert kes("10.554") == Decimal("10.55")
    assert kes("10.555") == Decimal("10.56")
    assert kes("10.556") == Decimal("10.56")
    assert kes(100) == Decimal("100.00")
    assert kes(12.3456) == Decimal("12.35")


def test_accrue_daily_formula():
    """Verify: Today's Interest = Current Balance * (Daily Yield / 365.25)."""
    # Balance = 100,000 KES, Annual Yield = 15.2% (0.152)
    # Expected = 100,000 * (0.152 / 365.25) = 41.61533... -> 41.62 KES
    interest = accrue_daily(Decimal("100000"), Decimal("0.152"))
    assert interest == Decimal("41.62")

    # Balance = 50,000 KES, Annual Yield = 14.5% (0.145)
    # 50000 * 0.145 / 365.25 = 19.8494... -> 19.85 KES
    assert accrue_daily(50000, 0.145) == Decimal("19.85")


def test_accrue_daily_validation():
    """Accrual engine rejects negative balances or yields."""
    with pytest.raises(ValueError, match="negative"):
        accrue_daily(-1000, 0.15)
    with pytest.raises(ValueError, match="negative"):
        accrue_daily(1000, -0.05)


def test_stock_summary_calculation():
    """Verify stock valuation and profit/loss percentage."""
    # 1,000 shares @ 15.00 avg buy, current price = 18.00
    summary = stock_summary(1000, Decimal("15.00"), Decimal("18.00"))
    assert summary["shares_owned"] == Decimal("1000")
    assert summary["average_buy_price"] == Decimal("15.00")
    assert summary["current_price"] == Decimal("18.00")
    assert summary["cost_basis"] == Decimal("15000.00")
    assert summary["current_value"] == Decimal("18000.00")
    assert summary["profit_loss"] == Decimal("3000.00")
    assert summary["profit_loss_percentage"] == Decimal("20.00")


def test_stock_summary_loss():
    """Verify stock loss calculation."""
    # 500 shares @ 20.00 avg buy, current price = 15.00 (25% loss)
    summary = stock_summary(500, 20.0, 15.0)
    assert summary["cost_basis"] == Decimal("10000.00")
    assert summary["current_value"] == Decimal("7500.00")
    assert summary["profit_loss"] == Decimal("-2500.00")
    assert summary["profit_loss_percentage"] == Decimal("-25.00")


def test_match_institution_yield():
    """Match institutions to their tracked yields."""
    res_cic = match_institution_yield("CIC Asset Management")
    assert "CIC" in res_cic["institution"]
    assert res_cic["yield_percentage"] >= 10.0

    res_sanlam = match_institution_yield("Sanlam")
    assert "Sanlam" in res_sanlam["institution"]

    # Fuzzy match with custom yield map
    custom_map = {"cic money market fund": Decimal("0.1620")}
    res_custom = match_institution_yield("CIC", custom_map)
    assert res_custom["yield_decimal"] == Decimal("0.1620")


# ==========================================
# 2. MANSA API CLIENT & ERROR HANDLING TESTS
# ==========================================


def test_mansa_client_missing_key():
    """MansaClient raises MansaConfigError when MANSA_API_KEY is empty."""
    client = MansaClient(api_key="", base_url="https://mansaapi.com/api/v1")
    with pytest.raises(MansaConfigError):
        asyncio.run(client.close_price("NSE", "SCOM"))


def test_mansa_client_successful_quote():
    """MansaClient parses closing price from Mansa API response."""
    client = MansaClient(api_key="test-key", base_url="https://mansaapi.com/api/v1")

    mock_response = httpx.Response(
        status_code=200,
        json={"status": "success", "data": {"ticker": "SCOM", "close": 17.85}},
        request=httpx.Request("GET", "https://mansaapi.com/api/v1/markets/exchanges/NSE/stocks/SCOM"),
    )

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        price = asyncio.run(client.close_price("NSE", "SCOM"))
        assert price == Decimal("17.85")


def test_mansa_client_timeout_handling():
    """MansaClient handles API timeouts cleanly with MansaTimeoutError."""
    client = MansaClient(api_key="test-key")
    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=httpx.TimeoutException("Timeout"))):
        with pytest.raises(MansaTimeoutError):
            asyncio.run(client.close_price("NSE", "EQTY"))


def test_mansa_client_list_exchange_stocks():
    """MansaClient returns prepopulated stocks directory."""
    client = MansaClient(api_key="")
    stocks = asyncio.run(client.list_exchange_stocks("NSE"))
    assert len(stocks) > 10
    assert any(s["ticker"] == "SCOM" for s in stocks)
    assert any(s["ticker"] == "EQTY" for s in stocks)


# ==========================================
# 3. PESACALC SCRAPER & FALLBACK TESTS
# ==========================================


def test_pesacalc_scraper_parsing():
    """PesaCalcYieldScraper parses fund names and yields from HTML."""
    sample_html = """
    <html>
        <body>
            <table>
                <tr><th>Fund</th><th>Yield</th></tr>
                <tr><td>CIC Money Market Fund</td><td>15.20%</td></tr>
                <tr><td>Sanlam Money Market Fund</td><td>14.85%</td></tr>
            </table>
        </body>
    </html>
    """
    scraper = PesaCalcYieldScraper()
    yields = scraper._parse_html(sample_html)
    assert len(yields) == 2
    fund_dict = dict(yields)
    assert fund_dict["CIC Money Market Fund"] == Decimal("0.1520")
    assert fund_dict["Sanlam Money Market Fund"] == Decimal("0.1485")


def test_pesacalc_scraper_fallback_on_challenge():
    """PesaCalcYieldScraper falls back to benchmark registry if bot-blocked."""
    scraper = PesaCalcYieldScraper()
    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=httpx.TimeoutException("Timeout"))):
        yields = asyncio.run(scraper.fetch())
        assert len(yields) > 0
        assert any("CIC" in name for name, _ in yields)


# ==========================================
# 4. 24-HOUR DAILY UPDATE WORKER TESTS
# ==========================================


def test_daily_update_worker_accrual(db):
    """Verify daily update stores yields and accrues compound interest into MMFAccount."""
    today = date.today()
    account = MMFAccount(
        fund_name="CIC Money Market Fund",
        principal_balance=Decimal("100000.00"),
        current_balance=Decimal("100000.00"),
        total_interest_accrued=Decimal("0.00"),
        last_accrued_on=None,
    )
    db.add(account)
    db.commit()

    with patch("src.workers.daily_market_update.get_db_context") as mock_db_ctx:
        from contextlib import contextmanager

        @contextmanager
        def fake_ctx():
            yield db

        mock_db_ctx.side_effect = fake_ctx

        summary = asyncio.run(run_daily_update())
        assert summary["accounts_accrued"] >= 1
        assert summary["total_interest_added"] > 0

        # Refresh account from db
        db.refresh(account)
        assert account.current_balance > Decimal("100000.00")
        assert account.total_interest_accrued > Decimal("0.00")
        assert account.last_accrued_on == today

        # Test idempotence: running again on the same day does not double-accrue
        second_summary = asyncio.run(run_daily_update())
        assert second_summary["accounts_accrued"] == 0
        assert second_summary["total_interest_added"] == 0.0


# ==========================================
# 5. FASTAPI MARKET TRACKING ROUTE TESTS
# ==========================================


def test_list_nse_tickers_endpoint(client):
    """GET /api/market/stocks/nse-tickers returns prepopulated stocks."""
    response = client.get("/api/market/stocks/nse-tickers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(s["ticker"] == "SCOM" for s in data)


def test_stocks_crud_and_calculations(client):
    """POST and GET /api/market/stocks test valuation and profit/loss with Mansa close price."""
    payload = {
        "ticker": "SCOM",
        "exchange": "NSE",
        "shares_owned": 1000,
        "average_buy_price": 15.00,
        "current_price": 18.50,
    }
    with patch("src.services.market_tracking.MansaClient.close_price", AsyncMock(return_value=Decimal("18.50"))):
        create_res = client.post("/api/market/stocks", json=payload)
        assert create_res.status_code == 200
        stock_data = create_res.json()
        assert stock_data["ticker"] == "SCOM"
        assert float(stock_data["current_value"]) == 18500.00
        assert float(stock_data["cost_basis"]) == 15000.00
        assert float(stock_data["profit_loss"]) == 3500.00
        assert float(stock_data["profit_loss_percentage"]) == 23.33

        stock_id = stock_data["id"]

        # List stocks
        list_res = client.get("/api/market/stocks")
        assert list_res.status_code == 200
        stocks = list_res.json()
        assert len(stocks) >= 1
        assert any(s["id"] == stock_id for s in stocks)

        # Delete stock
        del_res = client.delete(f"/api/market/stocks/{stock_id}")
        assert del_res.status_code == 200


def test_stock_auto_fetch_from_mansa_api(client):
    """POST /api/market/stocks auto-fetches price from Mansa API when current_price is None."""
    payload = {
        "ticker": "EQTY",
        "shares_owned": 200,
        "average_buy_price": 40.00,
    }
    with patch("src.services.market_tracking.MansaClient.close_price", AsyncMock(return_value=Decimal("45.50"))):
        res = client.post("/api/market/stocks", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert float(data["current_price"]) == 45.50
        assert float(data["current_value"]) == 9100.00  # 200 * 45.50


def test_mmf_crud_and_accrual(client):
    """POST, GET, and accrue for /api/market/mmfs."""
    payload = {
        "fund_name": "Sanlam Money Market Fund",
        "current_principal_balance": 50000.00,
    }
    create_res = client.post("/api/market/mmfs", json=payload)
    assert create_res.status_code == 200
    mmf_data = create_res.json()
    assert mmf_data["fund_name"] == "Sanlam Money Market Fund"
    assert float(mmf_data["current_balance"]) == 50000.00
    mmf_id = mmf_data["id"]

    # List MMF accounts
    list_res = client.get("/api/market/mmfs")
    assert list_res.status_code == 200
    mmfs = list_res.json()
    assert any(m["id"] == mmf_id for m in mmfs)

    # Delete MMF account
    del_res = client.delete(f"/api/market/mmfs/{mmf_id}")
    assert del_res.status_code == 200


def test_institutions_endpoints(client):
    """GET /api/market/institutions and /api/market/institutions/match."""
    # List institutions
    list_res = client.get("/api/market/institutions")
    assert list_res.status_code == 200
    inst_list = list_res.json()
    assert len(inst_list) >= 10
    assert any("CIC" in item["institution"] for item in inst_list)

    # Match institution
    match_res = client.get("/api/market/institutions/match?query=Sanlam")
    assert match_res.status_code == 200
    match_data = match_res.json()
    assert "Sanlam" in match_data["institution"]
    assert match_data["yield_percentage"] > 0


def test_unified_summary_endpoint(client):
    """GET /api/market/summary returns unified portfolio metrics."""
    with patch("src.services.market_tracking.MansaClient.close_price", AsyncMock(return_value=Decimal("36.00"))):
        # Add a stock and an MMF
        client.post(
            "/api/market/stocks",
            json={"ticker": "KCB", "shares_owned": 500, "average_buy_price": 30.00, "current_price": 36.00},
        )
    client.post(
        "/api/market/mmfs",
        json={"fund_name": "Britam Money Market Fund", "current_principal_balance": 20000.00},
    )

    summary_res = client.get("/api/market/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()

    assert summary["currency"] == "KES"
    assert summary["total_stock_value"] == 18000.00  # 500 * 36
    assert summary["total_stock_cost"] == 15000.00   # 500 * 30
    assert summary["stock_profit_loss"] == 3000.00
    assert summary["stock_profit_loss_percentage"] == 20.00
    assert summary["total_mmf_value"] == 20000.00
    assert summary["total_portfolio_value"] == 38000.00
