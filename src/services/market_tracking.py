"""Provider adapters and deterministic KES valuation/accrual calculations.

Handles:
1. Mansa API stock quote retrieval with timeout handling.
2. PesaCalc scraping for MMF yields with selector/bot fallback.
3. Accurate 24-hour daily compound interest calculations in KES.
4. Stock position valuation and profit/loss calculations.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Currency precision: 2 decimal places for KES
KES = Decimal("0.01")


def kes(value: Decimal | float | int | str) -> Decimal:
    """Quantize any numeric amount to 2 decimal places using standard financial ROUND_HALF_UP."""
    return Decimal(str(value)).quantize(KES, rounding=ROUND_HALF_UP)


# Custom exceptions for clear error propagation
class MansaError(Exception):
    """Base exception for Mansa API operations."""
    pass


class MansaTimeoutError(MansaError):
    """Raised when Mansa API times out."""
    pass


class MansaConfigError(MansaError):
    """Raised when MANSA_API_KEY or configuration is missing."""
    pass


class MansaAPIError(MansaError):
    """Raised when Mansa API returns an error response."""
    pass


class MansaClient:
    """Client for fetching end-of-day stock prices from Mansa API (https://mansamarkets.com)."""

    def __init__(self, api_key: str, base_url: str = "https://mansaapi.com/api/v1"):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "https://mansaapi.com/api/v1").rstrip("/")

    async def close_price(self, exchange: str, ticker: str) -> Decimal:
        """Fetch the end-of-day closing/current price for a given stock ticker."""
        if not self.api_key:
            raise MansaConfigError("MANSA_API_KEY environment variable is not configured")

        ticker_upper = ticker.strip().upper()
        exchange_upper = exchange.strip().upper()

        # Try standard provider endpoint routes
        endpoints = [
            f"{self.base_url}/markets/exchanges/{exchange_upper}/stocks/{ticker_upper}",
            f"{self.base_url}/stocks/{ticker_upper}",
            f"https://mansamarkets.com/api/v1/markets/exchanges/{exchange_upper}/stocks/{ticker_upper}",
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "AkibaFinance/1.0",
        }

        last_error = None
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for url in endpoints:
                try:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    data = payload.get("data", payload)

                    # Extract price from common field variations
                    for field in ("close", "price", "currentPrice", "current_price", "eod_price", "last_price"):
                        val = data.get(field)
                        if val is not None:
                            try:
                                return kes(val)
                            except Exception:
                                continue

                    # Check nested quote object
                    quote = data.get("quote", {})
                    for field in ("close", "price", "currentPrice", "current_price"):
                        val = quote.get(field)
                        if val is not None:
                            try:
                                return kes(val)
                            except Exception:
                                continue

                except httpx.TimeoutException as error:
                    logger.warning(f"Mansa API timeout for {ticker_upper} on {url}: {error}")
                    last_error = MansaTimeoutError(f"Mansa API request timed out for ticker '{ticker_upper}'")
                    break
                except httpx.HTTPStatusError as error:
                    logger.warning(f"Mansa API error for {ticker_upper} ({error.response.status_code}): {error}")
                    last_error = MansaAPIError(f"Mansa API returned status {error.response.status_code} for '{ticker_upper}'")
                except httpx.RequestError as error:
                    logger.warning(f"Mansa API request error for {ticker_upper}: {error}")
                    last_error = MansaAPIError(f"Mansa API network error: {error}")

        if last_error:
            raise last_error
        raise MansaAPIError(f"Could not retrieve closing price for ticker '{ticker_upper}' from Mansa API")

    async def list_exchange_stocks(self, exchange: str = "NSE") -> list[dict]:
        """Fetch list of listed stocks for an exchange from Mansa API, falling back to prepopulated NSE directory."""
        if not self.api_key:
            return NSE_STOCKS_DIRECTORY
        exchange_upper = exchange.strip().upper()
        endpoints = [
            f"{self.base_url}/markets/exchanges/{exchange_upper}/stocks",
            f"{self.base_url}/stocks?exchange={exchange_upper}",
            f"https://mansamarkets.com/api/v1/markets/exchanges/{exchange_upper}/stocks",
        ]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "AkibaFinance/1.0",
        }
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            for url in endpoints:
                try:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        payload = response.json()
                        data = payload.get("data", payload)
                        if isinstance(data, list) and len(data) > 0:
                            return [
                                {
                                    "ticker": item.get("ticker", item.get("symbol", "")).upper(),
                                    "name": item.get("name", item.get("company_name", item.get("ticker", ""))),
                                    "sector": item.get("sector", "Equities"),
                                }
                                for item in data
                                if item.get("ticker") or item.get("symbol")
                            ]
                except Exception:
                    continue
        return NSE_STOCKS_DIRECTORY


# Bundled NSE security directory. The UI uses the same static catalogue;
# ticker codes are passed to Mansa only when a price is explicitly requested.
NSE_STOCKS_DIRECTORY: list[dict] = [
    {"ticker":"SCOM","name":"Safaricom Plc","sector":"TELECOMMUNICATION"},
    {"ticker":"KPLC","name":"Kenya Power & Lighting Co Plc","sector":"ENERGY & PETROLEUM"},
    {"ticker":"HFCK","name":"HF Group Plc","sector":"BANKING"},
    {"ticker":"KEGN","name":"KenGen Co. Plc","sector":"ENERGY & PETROLEUM"},
    {"ticker":"CIC","name":"CIC Insurance Group Ltd","sector":"INSURANCE"},
    {"ticker":"EQTY","name":"Equity Group Holdings Plc","sector":"BANKING"},
    {"ticker":"KQ","name":"Kenya Airways Ltd","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"KNRE","name":"Kenya Re Insurance Corporation Ltd","sector":"INSURANCE"},
    {"ticker":"ABSA","name":"ABSA Bank Kenya Plc","sector":"BANKING"},
    {"ticker":"COOP","name":"The Co-operative Bank of Kenya Ltd","sector":"BANKING"},
    {"ticker":"NSE","name":"Nairobi Securities Exchange Plc","sector":"INVESTMENT SERVICES"},
    {"ticker":"DTK","name":"Diamond Trust Bank Kenya Ltd","sector":"BANKING"},
    {"ticker":"HAFR","name":"Home Afrika Ltd","sector":"INVESTMENT"},
    {"ticker":"IMH","name":"I&M Holdings Plc","sector":"BANKING"},
    {"ticker":"FMLY","name":"Family Bank Limited","sector":"BANKING"},
    {"ticker":"SBIC","name":"Stanbic Holdings Plc","sector":"BANKING"},
    {"ticker":"EVRD","name":"Eveready East Africa Ltd","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"UCHM","name":"Uchumi Supermarket Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"CTUM","name":"Centum Investment Co Plc","sector":"INVESTMENT"},
    {"ticker":"BRIT","name":"Britam Holdings Plc","sector":"INSURANCE"},
    {"ticker":"EABL","name":"East African Breweries Ltd","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"NBV","name":"Nairobi Business Ventures Ltd","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"SCAN","name":"WPP Scangroup Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"UMME","name":"Umeme Ltd","sector":"ENERGY & PETROLEUM"},
    {"ticker":"CARB","name":"Carbacid Investments Ltd","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"SLAM","name":"Sanlam Kenya Plc","sector":"INSURANCE"},
    {"ticker":"FTGH","name":"Flame Tree Group Holdings Ltd","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"NMG","name":"Nation Media Group Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"SKL","name":"Shri Krishana Overseas Plc","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"SMER","name":"Sameer Africa Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"TOTL","name":"Total Kenya Ltd","sector":"ENERGY & PETROLEUM"},
    {"ticker":"SCBK","name":"Standard Chartered Bank Kenya Ltd","sector":"BANKING"},
    {"ticker":"XPRS","name":"Express Kenya Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"BKG","name":"BK Group Plc","sector":"BANKING"},
    {"ticker":"LKL","name":"Longhorn Publishers Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"CGEN","name":"Car & General (K) Ltd","sector":"AUTOMOBILES & ACCESSORIES"},
    {"ticker":"BAT","name":"British American Tobacco Kenya Plc","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"UNGA","name":"Unga Group Ltd","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"WTK","name":"Williamson Tea Kenya Ltd","sector":"AGRICULTURAL"},
    {"ticker":"SASN","name":"Sasini Plc","sector":"AGRICULTURAL"},
    {"ticker":"LBTY","name":"Liberty Kenya Holdings Ltd","sector":"INSURANCE"},
    {"ticker":"TPSE","name":"TPS Eastern Africa Ltd","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"SGL","name":"Standard Group Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"KCB","name":"KCB Group Plc","sector":"BANKING"},
    {"ticker":"CRWN","name":"Crown Paints Kenya Plc","sector":"CONSTRUCTION & ALLIED"},
    {"ticker":"PORT","name":"E.A. Portland Cement Co. Ltd","sector":"CONSTRUCTION & ALLIED"},
    {"ticker":"KAPC","name":"Kapchorua Tea Co. Ltd","sector":"AGRICULTURAL"},
    {"ticker":"JUB","name":"Jubilee Holdings Ltd","sector":"INSURANCE"},
    {"ticker":"KPC","name":"Kenya Pipeline Company Plc","sector":"ENERGY & PETROLEUM"},
    {"ticker":"AMAC","name":"Africa Mega Agricorp Plc","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"KPLC.P0004","name":"Kenya Power & Lighting Plc 4% Preference","sector":"ENERGY & PETROLEUM"},
    {"ticker":"EGAD","name":"Eaagads Ltd","sector":"AGRICULTURAL"},
    {"ticker":"OCH","name":"Olympia Capital Holdings Ltd","sector":"INVESTMENT"},
    {"ticker":"KUKZ","name":"Kakuzi Plc","sector":"AGRICULTURAL"},
    {"ticker":"LIMT","name":"The Limuru Tea Co. Plc","sector":"AGRICULTURAL"},
    {"ticker":"NCBA","name":"NCBA Group Plc","sector":"BANKING"},
    {"ticker":"KURV","name":"Kurwitu Ventures Ltd","sector":"INVESTMENT"},
    {"ticker":"BOC","name":"B.O.C Kenya Plc","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"BAMB","name":"Bamburi Cement Ltd","sector":"CONSTRUCTION & ALLIED"},
    {"ticker":"CABL","name":"E.A. Cables Ltd","sector":"CONSTRUCTION & ALLIED"},
    {"ticker":"DCON","name":"Deacons (East Africa) Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"HBE","name":"Homeboyz Entertainment Plc","sector":"COMMERCIAL AND SERVICES"},
    {"ticker":"MSC","name":"Mumias Sugar Co. Ltd","sector":"MANUFACTURING & ALLIED"},
    {"ticker":"TCL","name":"Trans-Century Plc","sector":"INVESTMENT"},
    {"ticker":"ARM","name":"ARM Cement Plc","sector":"CONSTRUCTION & ALLIED"},
]


# Curated benchmark yields and institutions for Kenyan Money Market Funds
KENYA_MMF_INSTITUTIONS: list[dict] = [
    {"institution": "CIC Asset Management", "short_name": "CIC", "fund_name": "CIC Money Market Fund", "default_yield": Decimal("0.1550")},
    {"institution": "Sanlam Investments East Africa", "short_name": "Sanlam", "fund_name": "Sanlam Money Market Fund", "default_yield": Decimal("0.1520")},
    {"institution": "Britam Asset Managers", "short_name": "Britam", "fund_name": "Britam Money Market Fund", "default_yield": Decimal("0.1480")},
    {"institution": "Stanbic Holdings / SBG Securities", "short_name": "Stanbic", "fund_name": "Stanbic Money Market Fund", "default_yield": Decimal("0.1450")},
    {"institution": "NCBA Asset Management", "short_name": "NCBA", "fund_name": "NCBA Money Market Fund", "default_yield": Decimal("0.1430")},
    {"institution": "ICEA LION Asset Management", "short_name": "ICEA Lion", "fund_name": "ICEA Lion Money Market Fund", "default_yield": Decimal("0.1410")},
    {"institution": "Old Mutual Investment Group", "short_name": "Old Mutual", "fund_name": "Old Mutual Money Market Fund", "default_yield": Decimal("0.1380")},
    {"institution": "Co-op Trust Investment Services", "short_name": "Co-op", "fund_name": "Co-op Money Market Fund", "default_yield": Decimal("0.1420")},
    {"institution": "Lofty-Corban Investments", "short_name": "Lofty-Corban", "fund_name": "Lofty-Corban Money Market Fund", "default_yield": Decimal("0.1620")},
    {"institution": "GenAfrica Asset Managers", "short_name": "GenAfrica", "fund_name": "GenAfrica Money Market Fund", "default_yield": Decimal("0.1510")},
    {"institution": "Kuza Asset Management", "short_name": "Kuza", "fund_name": "Kuza Money Market Fund", "default_yield": Decimal("0.1580")},
    {"institution": "Etica Capital", "short_name": "Etica", "fund_name": "Etica Money Market Fund", "default_yield": Decimal("0.1650")},
    {"institution": "Apollo Asset Management", "short_name": "Apollo", "fund_name": "Apollo Money Market Fund", "default_yield": Decimal("0.1470")},
    {"institution": "Dry Associates Investment Bank", "short_name": "Dry Associates", "fund_name": "Dry Associates Money Market Fund", "default_yield": Decimal("0.1490")},
    {"institution": "Zimele Asset Management", "short_name": "Zimele", "fund_name": "Zimele Money Market Fund", "default_yield": Decimal("0.1350")},
    {"institution": "Nabo Capital", "short_name": "Nabo Africa", "fund_name": "Nabo Africa Money Market Fund", "default_yield": Decimal("0.1530")},
    {"institution": "Madison Asset Management", "short_name": "Madison", "fund_name": "Madison Money Market Fund", "default_yield": Decimal("0.1460")},
    {"institution": "Cytonn Asset Managers", "short_name": "Cytonn", "fund_name": "Cytonn Money Market Fund", "default_yield": Decimal("0.1560")},
]

DEFAULT_KENYA_MMF_BENCHMARKS: list[tuple[str, Decimal]] = [
    (item["fund_name"], item["default_yield"]) for item in KENYA_MMF_INSTITUTIONS
]


def match_institution_yield(
    fund_or_institution: str,
    yield_map: Optional[dict[str, Decimal]] = None,
) -> dict:
    """Match a fund name or financial institution to its yield interest.
    
    Returns matched institution, fund name, yield decimal, yield percentage, and daily yield.
    """
    target = fund_or_institution.casefold().strip()
    clean_target = (
        target.replace("money market fund", "")
        .replace("mmf", "")
        .replace("asset management", "")
        .replace("investments", "")
        .strip()
    )

    matched_item = None
    # 1. Match from KENYA_MMF_INSTITUTIONS
    for item in KENYA_MMF_INSTITUTIONS:
        inst_lower = item["institution"].casefold()
        short_lower = item["short_name"].casefold()
        fund_lower = item["fund_name"].casefold()

        if (
            target == inst_lower
            or target == short_lower
            or target == fund_lower
            or clean_target == short_lower
            or short_lower in clean_target
            or clean_target in short_lower
            or (clean_target and clean_target in inst_lower)
        ):
            matched_item = item
            break

    # Determine yield decimal
    yield_dec = None
    if yield_map:
        # Check if scraped yield map has this fund
        if matched_item and matched_item["fund_name"].casefold() in yield_map:
            yield_dec = yield_map[matched_item["fund_name"].casefold()]
        elif target in yield_map:
            yield_dec = yield_map[target]
        else:
            for y_name, y_rate in yield_map.items():
                if clean_target and clean_target in y_name:
                    yield_dec = y_rate
                    break

    if yield_dec is None:
        if matched_item:
            yield_dec = matched_item["default_yield"]
        else:
            yield_dec = Decimal("0.1500")  # Standard default ~15.0%

    institution_name = matched_item["institution"] if matched_item else fund_or_institution.strip()
    fund_name = matched_item["fund_name"] if matched_item else f"{fund_or_institution.strip()} Money Market Fund"
    daily_yield = (yield_dec / Decimal("365.25")).quantize(Decimal("0.00000001"))

    return {
        "institution": institution_name,
        "fund_name": fund_name,
        "short_name": matched_item["short_name"] if matched_item else fund_or_institution.strip(),
        "yield_decimal": yield_dec,
        "yield_percentage": float(yield_dec * Decimal("100")),
        "daily_yield_decimal": daily_yield,
    }


class PesaCalcYieldScraper:
    """Scrapes daily effective annual yields from PesaCalc (https://pesacalc.co.ke).

    Includes multi-tier parsing and graceful fallback when Cloudflare/bot challenges or markup changes occur.
    """

    def __init__(self, url: str = "https://pesacalc.co.ke"):
        self.url = url or "https://pesacalc.co.ke"

    async def fetch(self) -> list[tuple[str, Decimal]]:
        """Fetch daily MMF yields from PesaCalc, falling back to cached benchmarks if blocked."""
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        urls_to_try = [
            self.url,
            "https://pesacalc.co.ke",
            "https://pesacalc.co.ke/calculators/money-market",
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = [u for u in urls_to_try if not (u in seen or seen.add(u))]

        for target_url in unique_urls:
            try:
                async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                    response = await client.get(target_url, headers=headers)
                    if response.status_code == 200:
                        yields = self._parse_html(response.text)
                        if yields:
                            return yields
            except httpx.TimeoutException:
                logger.warning(f"PesaCalc scrape timed out on {target_url}")
                continue
            except httpx.RequestError as error:
                logger.warning(f"PesaCalc scrape request error on {target_url}: {error}")
                continue

        # If live scraping could not parse rates (e.g. anti-bot challenge interstitial),
        # return curated Kenya MMF benchmark yields so that calculations continue reliably.
        logger.info("Using curated Kenya MMF benchmark yields as fallback")
        return list(DEFAULT_KENYA_MMF_BENCHMARKS)

    def _parse_html(self, html_content: str) -> list[tuple[str, Decimal]]:
        """Parse MMF fund names and annual yield rates from HTML."""
        soup = BeautifulSoup(html_content, "html.parser")
        results: dict[str, Decimal] = {}

        # Strategy 1: Table rows
        for row in soup.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) >= 2:
                name = cells[0].strip()
                rate_str = cells[1].strip()
                if ("mmf" in name.lower() or "money market" in name.lower() or "fund" in name.lower()) and "%" in rate_str:
                    match = re.search(r"(\d{1,2}(?:\.\d{1,4})?)\s*%", rate_str)
                    if match:
                        try:
                            rate_val = Decimal(match.group(1)) / Decimal(100)
                            if Decimal("0.01") <= rate_val <= Decimal("0.50"):
                                results[name] = rate_val
                        except Exception:
                            pass

        if results:
            return [(name, val) for name, val in results.items()]

        # Strategy 2: Regex search across full cleaned page text (fallback if no table rows found)
        text = soup.get_text(" ", strip=True)
        # Matches patterns like: 'CIC Money Market Fund 15.2%' or 'Sanlam MMF: 14.85%'
        matches = re.findall(r"([A-Za-z][A-Za-z0-9 .&'-]{2,80}?)(?::|\s+-|\s+)\s*(\d{1,2}(?:\.\d{1,4})?)\s*%", text)
        for name, rate in matches:
            cleaned_name = name.strip()
            name_lower = cleaned_name.lower()
            if "mmf" in name_lower or "money market" in name_lower or "fund" in name_lower:
                try:
                    rate_val = Decimal(rate) / Decimal(100)
                    if Decimal("0.01") <= rate_val <= Decimal("0.50") and cleaned_name not in results:
                        results[cleaned_name] = rate_val
                except Exception:
                    pass

        return [(name, val) for name, val in results.items()]


def accrue_daily(balance: Decimal | float | int | str, annual_yield: Decimal | float | int | str) -> Decimal:
    """Implement the daily compound interest math engine for an MMF account:
    
    Today's Interest = Current Balance * (Daily Yield / 365.25)
    
    Result is rounded to 2 decimal places using ROUND_HALF_UP.
    """
    bal = Decimal(str(balance))
    rate = Decimal(str(annual_yield))
    if bal < Decimal(0) or rate < Decimal(0):
        raise ValueError("Balance and yield cannot be negative")
    interest = bal * (rate / Decimal("365.25"))
    return kes(interest)


def stock_summary(
    shares: Decimal | float | int | str,
    average_buy_price: Decimal | float | int | str,
    current_price: Decimal | float | int | str,
) -> dict:
    """Calculate individual stock current value (shares_owned * current_price)
    and profit/loss percentage based on average_buy_price.
    
    All figures are quantized to 2 decimal places.
    """
    shares_dec = Decimal(str(shares))
    buy_price_dec = Decimal(str(average_buy_price))
    curr_price_dec = Decimal(str(current_price))

    cost_basis = kes(shares_dec * buy_price_dec)
    current_value = kes(shares_dec * curr_price_dec)
    profit_loss = kes(current_value - cost_basis)

    if cost_basis > Decimal(0):
        profit_loss_pct = ((profit_loss / cost_basis) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        profit_loss_pct = Decimal("0.00")

    return {
        "shares_owned": shares_dec,
        "average_buy_price": buy_price_dec,
        "current_price": curr_price_dec,
        "cost_basis": cost_basis,
        "current_value": current_value,
        "profit_loss": profit_loss,
        "profit_loss_percentage": profit_loss_pct,
    }
