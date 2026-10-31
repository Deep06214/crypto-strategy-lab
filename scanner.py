"""
This is the part that runs continuously in the background. The Streamlit
dashboard starts this in a thread when it launches -- you don't run this
file directly.
"""
import time
import traceback

import config
import data_feed
import db
import paper_trader
from strategies import STRATEGIES


def run_scan_cycle():
    symbols = db.get_watchlist()
    if not symbols:
        db.log_scan("Watchlist is empty -- add a symbol from the dashboard.")
        return

    signals_found = 0
    current_prices = {}

    for symbol in symbols:
        df = data_feed.get_klines(symbol)
        if df is None or len(df) < 30:
            db.log_scan(f"Could not fetch data for {symbol} -- skipping this cycle.")
            continue

        current_prices[symbol] = float(df["close"].iloc[-1])

        for strategy_fn in STRATEGIES:
            try:
                signal = strategy_fn(df)
            except Exception as e:
                db.log_scan(f"Strategy {strategy_fn.__name__} errored on {symbol}: {e}")
                continue
            if signal is not None:
                opened = paper_trader.process_signal(signal, symbol)
                if opened:
                    signals_found += 1

    # also grab live prices for any open trades whose symbol wasn't in the
    # loop above for some reason (e.g. it was just removed from the watchlist)
    for trade in db.get_open_trades():
        if trade["symbol"] not in current_prices:
            price = data_feed.get_current_price(trade["symbol"])
            if price is not None:
                current_prices[trade["symbol"]] = price

    paper_trader.check_open_trades(current_prices)

    if signals_found == 0:
        db.log_scan(f"Scanned {len(symbols)} symbol(s). No new setups this cycle.")


def run_forever(interval_seconds=None):
    interval_seconds = interval_seconds or config.SCAN_INTERVAL_SECONDS
    db.init_db()
    db.log_scan("Engine started.")
    while True:
        try:
            run_scan_cycle()
        except Exception:
            # one bad cycle should never kill the whole bot
            db.log_scan("Scan cycle error:\n" + traceback.format_exc()[-500:])
        time.sleep(interval_seconds)
