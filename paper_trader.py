"""
No real money, no real exchange account -- this just simulates fills
against live prices so you can see how a strategy would have done.
"""
import config
import db


def process_signal(signal, symbol):
    """Open a paper trade from a strategy's signal, sized by % risk of
    that strategy's current virtual balance. Skips if that strategy
    already has an open position on this symbol (no stacking)."""
    if db.has_open_trade(symbol, signal.strategy):
        return False

    balance = db.get_strategy_balance(signal.strategy)
    risk_amount = balance * config.RISK_PER_TRADE_PCT
    stop_distance = abs(signal.entry - signal.stop_loss)
    if stop_distance <= 0:
        return False

    size = risk_amount / stop_distance  # units of the asset

    db.open_trade(
        symbol=symbol,
        strategy=signal.strategy,
        direction=signal.direction,
        entry_price=signal.entry,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        size=size,
        reasoning=signal.reasoning,
    )
    db.log_scan(
        f"OPENED {signal.direction} {symbol} via {signal.strategy} @ {signal.entry:.4f} "
        f"(SL {signal.stop_loss:.4f} / TP {signal.take_profit:.4f})"
    )
    return True


def check_open_trades(current_prices):
    """current_prices: dict of symbol -> latest price. Closes any trade
    that has hit its stop loss or take profit."""
    for trade in db.get_open_trades():
        price = current_prices.get(trade["symbol"])
        if price is None:
            continue

        hit_sl = hit_tp = False
        if trade["direction"] == "LONG":
            hit_sl = price <= trade["stop_loss"]
            hit_tp = price >= trade["take_profit"]
        else:  # SHORT
            hit_sl = price >= trade["stop_loss"]
            hit_tp = price <= trade["take_profit"]

        if not (hit_sl or hit_tp):
            continue

        close_price = trade["stop_loss"] if hit_sl else trade["take_profit"]
        direction_mult = 1 if trade["direction"] == "LONG" else -1
        pnl = (close_price - trade["entry_price"]) * trade["size"] * direction_mult
        pnl_pct = (pnl / (trade["entry_price"] * trade["size"])) * 100 if trade["size"] else 0
        status = "CLOSED_WIN" if hit_tp else "CLOSED_LOSS"

        db.close_trade(trade["id"], close_price, status, pnl, pnl_pct)

        new_balance = db.get_strategy_balance(trade["strategy"]) + pnl
        db.set_strategy_balance(trade["strategy"], new_balance)

        db.log_scan(
            f"CLOSED {trade['direction']} {trade['symbol']} via {trade['strategy']} "
            f"-> {status} (P&L {pnl:+.2f})"
        )
