"""Currency service with provider abstraction."""
from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import httpx
import logging

logger = logging.getLogger(__name__)


class CurrencyProvider(ABC):
    """Abstract base class for currency providers."""

    @abstractmethod
    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get exchange rate from one currency to another.
        
        Args:
            from_currency: Source currency code (e.g., "USD")
            to_currency: Destination currency code (e.g., "KES")
            
        Returns:
            Exchange rate as Decimal
            
        Raises:
            ValueError: If currencies are invalid
            Exception: If API call fails
        """
        pass

    @abstractmethod
    async def get_multiple_rates(
        self, from_currency: str, to_currencies: list[str]
    ) -> dict:
        """
        Get rates from one currency to multiple others.
        
        Returns:
            {to_currency: rate, ...}
        """
        pass


class ExchangeRateAPIProvider(CurrencyProvider):
    """Exchange rate provider using exchangerate-api.com."""

    def __init__(self, api_url: str = "https://api.exchangerate-api.com/v4/latest"):
        self.api_url = api_url
        self.supported_currencies = [
            "KES", "USD", "EUR", "GBP", "ZAR", "UGX", "TZS"
        ]

    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Get exchange rate."""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return Decimal(1)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_url}/{from_currency}")
                response.raise_for_status()
                data = response.json()

                if to_currency not in data.get("rates", {}):
                    raise ValueError(f"Currency {to_currency} not supported")

                rate = Decimal(str(data["rates"][to_currency]))
                return rate

        except httpx.HTTPError as e:
            logger.error(f"API error getting rate {from_currency}/{to_currency}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting rate: {e}")
            raise

    async def get_multiple_rates(
        self, from_currency: str, to_currencies: list[str]
    ) -> dict:
        """Get rates from one currency to multiple others."""
        from_currency = from_currency.upper()
        to_currencies = [c.upper() for c in to_currencies]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_url}/{from_currency}")
                response.raise_for_status()
                data = response.json()

                rates = {}
                for to_curr in to_currencies:
                    if to_curr in data.get("rates", {}):
                        rates[to_curr] = Decimal(str(data["rates"][to_curr]))
                    else:
                        logger.warning(f"Currency {to_curr} not found in API response")

                return rates

        except Exception as e:
            logger.error(f"Error getting multiple rates: {e}")
            raise


class MockCurrencyProvider(CurrencyProvider):
    """Mock provider for testing."""

    def __init__(self, rates: dict = None):
        """
        Initialize with predefined rates.
        
        rates: {"USD_KES": 130.0, "EUR_KES": 142.0, ...}
        """
        self.rates = rates or {
            "USD_KES": Decimal("130"),
            "USD_EUR": Decimal("0.92"),
            "EUR_KES": Decimal("142"),
            "GBP_KES": Decimal("165"),
            "ZAR_KES": Decimal("7.5"),
        }

    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Get mocked rate."""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return Decimal(1)

        key = f"{from_currency}_{to_currency}"
        if key in self.rates:
            return self.rates[key]

        # Try reverse
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in self.rates:
            return Decimal(1) / self.rates[reverse_key]

        raise ValueError(f"No rate found for {from_currency}/{to_currency}")

    async def get_multiple_rates(
        self, from_currency: str, to_currencies: list[str]
    ) -> dict:
        """Get multiple mocked rates."""
        rates = {}
        for to_curr in to_currencies:
            try:
                rates[to_curr] = await self.get_rate(from_currency, to_curr)
            except ValueError:
                pass
        return rates


class CachedCurrencyService:
    """Currency service with caching."""

    def __init__(
        self,
        provider: CurrencyProvider,
        cache_duration_minutes: int = 60,
    ):
        self.provider = provider
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self._cache: dict = {}  # {(from, to): (rate, timestamp)}
        self.last_update: dict = {}  # Track last update times

    async def get_rate(self, from_currency: str, to_currency: str) -> tuple[Decimal, bool]:
        """
        Get exchange rate with caching.
        
        Returns:
            (rate, is_cached): rate amount and whether it came from cache
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            self.last_update[f"{from_currency}/{to_currency}"] = datetime.now(timezone.utc)
            return Decimal(1), False

        key = (from_currency, to_currency)

        # Check cache
        if key in self._cache:
            rate, timestamp = self._cache[key]
            if datetime.now(timezone.utc) - timestamp < self.cache_duration:
                return rate, True

        # Fetch new rate
        try:
            rate = await self.provider.get_rate(from_currency, to_currency)
            self._cache[key] = (rate, datetime.now(timezone.utc))
            self.last_update[f"{from_currency}/{to_currency}"] = datetime.now(timezone.utc)
            return rate, False
        except Exception as e:
            # Fall back to cache if available, even if expired
            if key in self._cache:
                logger.warning(
                    f"API failed for {from_currency}/{to_currency}, using cached rate: {e}"
                )
                rate, _ = self._cache[key]
                return rate, True
            raise

    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """Convert amount from one currency to another."""
        rate, _ = await self.get_rate(from_currency, to_currency)
        return amount * rate

    def get_last_update(self, from_currency: str, to_currency: str) -> datetime:
        """Get when rate was last updated."""
        key = f"{from_currency.upper()}/{to_currency.upper()}"
        return self.last_update.get(key)

    def clear_cache(self):
        """Clear all cached rates."""
        self._cache.clear()
        self.last_update.clear()
