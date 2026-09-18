# Portfolio Tracker

A local-first personal finance and investment tracking app built with FastAPI, SQLAlchemy, Jinja2, and vanilla JavaScript.

## Features

- Portfolio tracking for holdings and asset categories
- Budget and expense analysis
- Emergency fund and savings-rate calculations
- Net worth and future projection calculators
- Multi-currency support with cached exchange rates
- Local-first browser storage for privacy and offline use
- Responsive dashboard and settings pages

## Project layout

```text
.
├── main.py
├── config.py
├── database.py
├── src/
│   ├── api/              # calculation and currency-pair endpoints
│   ├── models/ schemas/ services/
│   ├── static/           # CSS and browser-local IndexedDB client
│   └── templates/
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── tasks.md
├── todo.md
└── uv.lock
```

## Local development

```bash
cd portfolio-tracker
uv sync
uv run uvicorn main:app --reload
```

Then open http://127.0.0.1:8000

## Running tests

```bash
cd portfolio-tracker
uv run pytest -q
```

## Daily MMF updates

Schedule `uv run python -m src.workers.daily_market_update` once every 24 hours
(for example with cron or a systemd timer). It stores the latest PesaCalc yield
and accrues each matching MMF balance once per calendar day. Set `MANSA_API_KEY`
before refreshing server-side stock quotes.

## Notes

- Financial records live in browser IndexedDB by default. The backend receives
  calculation inputs and currency pairs only; it does not receive saved records.
- Currency totals require an available live or cached exchange rate. Original
  currency values remain visible in the ledger.
- The package is rooted at the project root so imports resolve as `portfolio_tracker.*` without requiring a `src` prefix.

## Portfolio architecture

- **Dashboard:** read-only summary metrics in the selected reporting currency.
- **Portfolio:** the single place to add, remove, refresh, and inspect holdings.
- **NSE catalogue:** bundled in the browser and backend as a ticker/name directory. Company names do not require a market-data request; price requests use the selected ticker only.
- **Currencies:** each position keeps its native currency while dashboard totals convert to the browser's reporting currency using the cached FX service.
- **MMF accruals:** an explicit investment date is stored. The daily worker uses the scraped yield for each completed valuation day and never substitutes an invented rate for a missing historical day.
