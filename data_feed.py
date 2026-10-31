"""
Live market data, read-only, no account or API key required.
Uses Binance's public REST endpoints (these are the same endpoints
Binance's own charts pull from -- nothing exotic or unofficial).
"""
import pandas as pd
import requests

import config

COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
]


def get_klines(symbol, interval=None, limit=None):
    """Returns a DataFrame of recent candles, oldest first, or None on failure."""
    interval = interval or config.CANDLE_INTERVAL
    limit = limit or config.CANDLES_TO_FETCH
    try:
        resp = requests.get(
            config.BINANCE_KLINES_URL,
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json()
        if not raw:
            return None
        df = pd.DataFrame(raw, columns=COLUMNS)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        return df[["open_time", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
    except Exception as e:
        return None


def get_current_price(symbol):
    """Lightweight single price check, used to test open trades against SL/TP."""
    try:
        resp = requests.get(
            config.BINANCE_PRICE_URL, params={"symbol": symbol}, timeout=10
        )
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception:
        return None
