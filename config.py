"""
All the knobs you might want to turn live here, in one place.
Nothing else in the project should hardcode these values.
"""

# Starting watchlist (Binance symbol format: BASEQUOTE, e.g. BTCUSDT).
# You can add/remove symbols from the dashboard later -- this is just
# what the bot watches before you've touched anything.
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

# Candle size the strategies analyze. 15-minute candles are a deliberate
# choice: 1-minute candles are extremely noisy and would generate way too
# many low-quality signals -- exactly the kind of overtrading this bot is
# meant to prevent. Change this if you know what you're doing.
CANDLE_INTERVAL = "15m"
CANDLES_TO_FETCH = 150  # how much history to pull each cycle

# How often the engine wakes up to check prices / look for new signals.
# This is the "scans the market every minute" part -- it checks on this
# schedule even though the candles themselves are 15 minutes.
SCAN_INTERVAL_SECONDS = 60

# Each strategy gets its own virtual bankroll, so you can fairly compare
# which strategy actually performs best instead of them fighting over one
# shared balance.
STARTING_BALANCE_PER_STRATEGY = 10_000.0

# Risk management: how much of a strategy's CURRENT balance it risks on
# any single trade, and the reward target as a multiple of that risk.
RISK_PER_TRADE_PCT = 0.01   # 1%
REWARD_RISK_RATIO = 2.0     # take-profit set at 2x the stop distance

# Binance's public, unrestricted market-data mirror. No API key needed, no
# account needed -- this is read-only price data, nothing is ever traded
# for real. Deliberately using data-api.binance.vision instead of
# api.binance.com: the main domain blocks requests from a list of
# "restricted locations" (HTTP 451), and most free cloud hosts -- including
# Streamlit Community Cloud -- run on servers in one of those locations
# regardless of which region you pick. This mirror serves the identical
# public endpoints without that restriction, so it works the same whether
# the bot is running on your laptop or in the cloud.
BINANCE_KLINES_URL = "https://data-api.binance.vision/api/v3/klines"
BINANCE_PRICE_URL = "https://data-api.binance.vision/api/v3/ticker/price"

DB_PATH = "trading_bot.db"
