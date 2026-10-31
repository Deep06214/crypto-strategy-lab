"""
Everything the bot remembers lives in one SQLite file (trading_bot.db).
No separate database server to install -- it's just a file next to the code.
"""
import sqlite3
import time
from contextlib import contextmanager

import config


@contextmanager
def get_conn():
    # The dashboard (Streamlit) and the background scanner thread both hit
    # this file. WAL mode + a busy timeout let reads and writes overlap
    # instead of throwing "database is locked".
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_at REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                strategy TEXT,
                direction TEXT,        -- LONG or SHORT
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                size REAL,             -- position size in units of the asset
                status TEXT,           -- OPEN, CLOSED_WIN, CLOSED_LOSS
                opened_at REAL,
                closed_at REAL,
                close_price REAL,
                pnl REAL,
                pnl_pct REAL,
                reasoning TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS strategy_balance (
                strategy TEXT PRIMARY KEY,
                balance REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL,
                message TEXT
            )
        """)
        # seed default watchlist only if the table is empty (first run)
        c.execute("SELECT COUNT(*) FROM watchlist")
        if c.fetchone()[0] == 0:
            for sym in config.DEFAULT_SYMBOLS:
                c.execute(
                    "INSERT OR IGNORE INTO watchlist (symbol, added_at) VALUES (?, ?)",
                    (sym, time.time()),
                )


def ensure_strategy_balance(strategy):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM strategy_balance WHERE strategy=?", (strategy,))
        row = c.fetchone()
        if row is None:
            c.execute(
                "INSERT INTO strategy_balance (strategy, balance) VALUES (?, ?)",
                (strategy, config.STARTING_BALANCE_PER_STRATEGY),
            )
            return config.STARTING_BALANCE_PER_STRATEGY
        return row["balance"]


def get_strategy_balance(strategy):
    return ensure_strategy_balance(strategy)


def set_strategy_balance(strategy, new_balance):
    with get_conn() as conn:
        conn.execute(
            "UPDATE strategy_balance SET balance=? WHERE strategy=?",
            (new_balance, strategy),
        )


# ---------- watchlist ----------

def get_watchlist():
    with get_conn() as conn:
        rows = conn.execute("SELECT symbol FROM watchlist ORDER BY symbol").fetchall()
        return [r["symbol"] for r in rows]


def add_symbol(symbol):
    symbol = symbol.strip().upper()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (symbol, added_at) VALUES (?, ?)",
            (symbol, time.time()),
        )


def remove_symbol(symbol):
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE symbol=?", (symbol,))


# ---------- trades ----------

def has_open_trade(symbol, strategy):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM trades WHERE symbol=? AND strategy=? AND status='OPEN'",
            (symbol, strategy),
        ).fetchone()
        return row is not None


def open_trade(symbol, strategy, direction, entry_price, stop_loss, take_profit, size, reasoning):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO trades
            (symbol, strategy, direction, entry_price, stop_loss, take_profit,
             size, status, opened_at, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
        """, (symbol, strategy, direction, entry_price, stop_loss, take_profit,
              size, time.time(), reasoning))


def close_trade(trade_id, close_price, status, pnl, pnl_pct):
    with get_conn() as conn:
        conn.execute("""
            UPDATE trades SET status=?, close_price=?, closed_at=?, pnl=?, pnl_pct=?
            WHERE id=?
        """, (status, close_price, time.time(), pnl, pnl_pct, trade_id))


def get_open_trades():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM trades WHERE status='OPEN' ORDER BY opened_at DESC"
        ).fetchall()]


def get_trade_history(limit=200):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM trades WHERE status != 'OPEN' ORDER BY closed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()]


def get_strategy_stats():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT strategy,
                   COUNT(*) as trades,
                   SUM(CASE WHEN status='CLOSED_WIN' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN status='CLOSED_LOSS' THEN 1 ELSE 0 END) as losses,
                   SUM(pnl) as total_pnl
            FROM trades
            WHERE status != 'OPEN'
            GROUP BY strategy
        """).fetchall()
        stats = {}
        for r in rows:
            total = r["trades"] or 0
            wins = r["wins"] or 0
            stats[r["strategy"]] = {
                "trades": total,
                "wins": wins,
                "losses": r["losses"] or 0,
                "win_rate": round(100 * wins / total, 1) if total else 0.0,
                "total_pnl": round(r["total_pnl"] or 0.0, 2),
                "balance": round(get_strategy_balance(r["strategy"]), 2),
            }
        return stats


# ---------- scan log ----------

def log_scan(message):
    with get_conn() as conn:
        conn.execute("INSERT INTO scan_log (ts, message) VALUES (?, ?)", (time.time(), message))
        # keep the log from growing forever
        conn.execute("""
            DELETE FROM scan_log WHERE id NOT IN (
                SELECT id FROM scan_log ORDER BY ts DESC LIMIT 200
            )
        """)


def get_recent_logs(limit=25):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM scan_log ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()]
