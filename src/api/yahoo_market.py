"""Yahoo Finance market-data endpoints for US-listed stock positions."""

import asyncio
from datetime import timezone
from decimal import Decimal

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from src.models import StockPosition, utc_now
from src.services.market_tracking import stock_summary

router = APIRouter(prefix="/api/us-market", tags=["US market"])


class USStockCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    shares_owned: Decimal = Field(gt=0)
    average_buy_price: Decimal = Field(gt=0)


def _quote_sync(ticker: str) -> float:
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Ticker is required")
    ticker_obj = yf.Ticker(symbol)
    price = None
    try:
        price = ticker_obj.fast_info.get("last_price")
    except Exception:
        price = None
    if price is None:
        history = ticker_obj.history(period="1d")
        if history.empty or "Close" not in history:
            raise ValueError(f"No market data found for {symbol}")
        closes = history["Close"].dropna()
        if closes.empty:
            raise ValueError(f"No closing price found for {symbol}")
        price = closes.iloc[-1]
    price = float(price)
    if price <= 0:
        raise ValueError(f"Invalid market price returned for {symbol}")
    return price


async def get_quote(ticker: str) -> float:
    return await asyncio.to_thread(_quote_sync, ticker)


def _position_response(position: StockPosition) -> dict:
    summary = stock_summary(
        Decimal(str(position.shares_owned)),
        Decimal(str(position.average_buy_price)),
        Decimal(str(position.current_price or position.average_buy_price)),
    )
    return {
        "id": position.id,
        "ticker": position.ticker,
        "exchange": position.exchange,
        "currency": "USD",
        **{k: float(v) if isinstance(v, Decimal) else v for k, v in summary.items()},
        "price_updated_at": position.price_updated_at.isoformat() if position.price_updated_at else None,
    }


@router.get("/quote")
async def quote(ticker: str = Query(..., min_length=1, max_length=32)):
    symbol = ticker.strip().upper()
    try:
        price = await get_quote(symbol)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "ticker": symbol,
        "exchange": "US",
        "currency": "USD",
        "current_price": price,
        "price_updated_at": utc_now().isoformat(),
    }


@router.post("/stocks")
async def create_us_stock(payload: USStockCreate, db: Session = Depends(get_db)):
    symbol = payload.ticker.strip().upper()
    try:
        current_price = await get_quote(symbol)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    position = StockPosition(
        ticker=symbol,
        exchange="US",
        shares_owned=payload.shares_owned,
        average_buy_price=payload.average_buy_price,
        current_price=Decimal(str(current_price)),
        price_updated_at=utc_now(),
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return _position_response(position)


@router.post("/stocks/{position_id}/refresh")
async def refresh_us_stock(position_id: str, db: Session = Depends(get_db)):
    position = db.get(StockPosition, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Stock position not found")
    if position.exchange != "US":
        raise HTTPException(status_code=400, detail="Position is not a US stock")

    try:
        price = await get_quote(position.ticker)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    position.current_price = Decimal(str(price))
    position.price_updated_at = utc_now()
    db.commit()
    db.refresh(position)
    return _position_response(position)


@router.post("/stocks/refresh-all")
async def refresh_all_us_stocks(db: Session = Depends(get_db)):
    positions = db.scalars(
        select(StockPosition).where(StockPosition.exchange == "US")
    ).all()
    refreshed = []
    for position in positions:
        try:
            price = await get_quote(position.ticker)
            position.current_price = Decimal(str(price))
            position.price_updated_at = utc_now()
            refreshed.append(position)
        except Exception:
            continue
    db.commit()
    for position in refreshed:
        db.refresh(position)
    return {"count": len(refreshed), "stocks": [_position_response(p) for p in refreshed]}
