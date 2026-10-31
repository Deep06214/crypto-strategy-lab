"""
This is the ONE command you run: `streamlit run dashboard.py`

It does two jobs at once:
  1. Starts the scanner running in the background (once per server, no
     matter how many browser tabs or devices connect to it).
  2. Shows you everything the scanner is doing: live watchlist, open
     paper trades, the full journal, and which strategy is winning.
"""
import threading
import time
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import config
import data_feed
import db
import scanner

st.set_page_config(page_title="Crypto Strategy Lab", layout="wide")


@st.cache_resource
def start_engine_once():
    db.init_db()
    thread = threading.Thread(target=scanner.run_forever, daemon=True)
    thread.start()
    return thread


start_engine_once()
st_autorefresh(interval=15_000, key="auto_refresh")  # repaint every 15s

st.title("Crypto strategy lab")
st.caption(
    "Paper trading only \u2014 no real money, no exchange account connected. "
    "This is a tool for testing strategies, not financial advice."
)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Asset selector")
    new_symbol = st.text_input("Add a symbol (Binance format, e.g. BTCUSDT)")
    if st.button("Add") and new_symbol.strip():
        db.add_symbol(new_symbol)
        st.rerun()

    st.write("**Currently watching:**")
    for sym in db.get_watchlist():
        c1, c2 = st.columns([3, 1])
        c1.write(sym)
        if c2.button("Remove", key=f"remove_{sym}"):
            db.remove_symbol(sym)
            st.rerun()

    st.divider()
    st.header("Settings")
    st.write(f"Candle size: `{config.CANDLE_INTERVAL}`")
    st.write(f"Scan every: `{config.SCAN_INTERVAL_SECONDS}s`")
    st.write(f"Risk per trade: `{config.RISK_PER_TRADE_PCT*100:.1f}%` of that strategy's balance")
    st.write(f"Reward:risk target: `{config.REWARD_RISK_RATIO}:1`")
    st.write(f"Starting balance per strategy: `${config.STARTING_BALANCE_PER_STRATEGY:,.0f}`")

    st.divider()
    logs = db.get_recent_logs(1)
    if logs:
        seconds_ago = time.time() - logs[0]["ts"]
        status = "\U0001F7E2 live" if seconds_ago < config.SCAN_INTERVAL_SECONDS * 2 else "\U0001F7E1 stalled?"
        st.write(f"Engine status: {status}")
        st.caption(f"Last scan activity {int(seconds_ago)}s ago")
    else:
        st.write("Engine status: starting up...")

# ---------------------------------------------------------------- data for this render
watchlist = db.get_watchlist()
open_trades = db.get_open_trades()
symbols_needed = set(watchlist) | {t["symbol"] for t in open_trades}
current_prices = {s: data_feed.get_current_price(s) for s in symbols_needed}

tab_scanner, tab_positions, tab_journal, tab_leaderboard = st.tabs(
    ["Live scanner", "Open positions", "Journal", "Strategy leaderboard"]
)

# ---------------------------------------------------------------- live scanner
with tab_scanner:
    st.subheader("Watchlist")
    if not watchlist:
        st.info("Nothing on the watchlist yet \u2014 add a symbol from the sidebar.")
    else:
        rows = [{"Symbol": s, "Last price": current_prices.get(s)} for s in watchlist]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Recent activity")
    recent = db.get_recent_logs(20)
    if recent:
        for entry in recent:
            ts = datetime.fromtimestamp(entry["ts"]).strftime("%H:%M:%S")
            st.text(f"[{ts}] {entry['message']}")
    else:
        st.caption("No activity logged yet.")

# ---------------------------------------------------------------- open positions
with tab_positions:
    st.subheader(f"Open paper trades ({len(open_trades)})")
    if not open_trades:
        st.info("No open positions right now.")
    else:
        rows = []
        for t in open_trades:
            price = current_prices.get(t["symbol"])
            unrealized = None
            if price is not None:
                mult = 1 if t["direction"] == "LONG" else -1
                unrealized = (price - t["entry_price"]) * t["size"] * mult
            rows.append({
                "Symbol": t["symbol"], "Strategy": t["strategy"], "Direction": t["direction"],
                "Entry": round(t["entry_price"], 4), "Stop loss": round(t["stop_loss"], 4),
                "Target": round(t["take_profit"], 4), "Current price": price,
                "Unrealized P&L": round(unrealized, 2) if unrealized is not None else None,
                "Why": t["reasoning"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- journal
with tab_journal:
    st.subheader("Trade journal")
    history = db.get_trade_history()
    if not history:
        st.info("No closed trades yet. This fills in automatically as paper trades close.")
    else:
        rows = []
        for t in history:
            rows.append({
                "Closed": datetime.fromtimestamp(t["closed_at"]).strftime("%Y-%m-%d %H:%M") if t["closed_at"] else "",
                "Symbol": t["symbol"], "Strategy": t["strategy"], "Direction": t["direction"],
                "Result": t["status"].replace("CLOSED_", ""),
                "Entry": round(t["entry_price"], 4), "Exit": round(t["close_price"], 4) if t["close_price"] else None,
                "P&L": round(t["pnl"], 2) if t["pnl"] is not None else None,
                "P&L %": round(t["pnl_pct"], 2) if t["pnl_pct"] is not None else None,
                "Setup conditions": t["reasoning"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- leaderboard
with tab_leaderboard:
    st.subheader("Which strategy is actually working")
    stats = db.get_strategy_stats()
    if not stats:
        st.info("No closed trades yet \u2014 the leaderboard fills in as strategies close trades.")
    else:
        rows = []
        for name, s in stats.items():
            rows.append({
                "Strategy": name, "Trades": s["trades"], "Win rate": f"{s['win_rate']}%",
                "Total P&L": s["total_pnl"], "Current balance": s["balance"],
            })
        df_stats = pd.DataFrame(rows).sort_values("Total P&L", ascending=False)
        st.dataframe(df_stats, use_container_width=True, hide_index=True)
        st.bar_chart(df_stats.set_index("Strategy")["Total P&L"])
