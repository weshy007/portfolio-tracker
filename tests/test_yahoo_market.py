from src.api.yahoo_market import _quote_sync


def test_quote_uses_fast_info(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            assert symbol == "AAPL"
            self.fast_info = {"last_price": 231.45}

    monkeypatch.setattr("src.api.yahoo_market.yf.Ticker", FakeTicker)
    assert _quote_sync("aapl") == 231.45
