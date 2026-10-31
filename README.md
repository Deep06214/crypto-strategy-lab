# Crypto Strategy Lab

A bot that watches a list of crypto pairs, runs several independent strategies
against them every minute, paper-trades (virtual money only) whatever setups
actually form, and journals every trade with the exact conditions that caused
it — so you can see which strategy is actually working before ever risking
real money.

**This trades nothing real.** No exchange account, no API keys, no withdrawal
permissions, ever. It reads public price data and simulates fills.

---

## 1. Install Python (skip if you already have it)

1. Go to **python.org/downloads** and download Python 3.11 or newer.
2. Run the installer.
   - **Windows:** on the first screen, tick **"Add python.exe to PATH"** before
     clicking Install. This step is easy to miss and causes most setup
     problems if skipped.
   - **Mac:** the default installer is fine.
3. Confirm it worked: open a terminal (Windows: search "Command Prompt" or
   "PowerShell"; Mac: search "Terminal") and type:
   ```
   python --version
   ```
   You should see something like `Python 3.11.x`. (On Mac, if that doesn't
   work, try `python3 --version` instead — then use `python3` and `pip3`
   everywhere below instead of `python`/`pip`.)

## 2. Get the project folder and install dependencies

1. Unzip the folder you downloaded somewhere you'll remember, e.g. your
   Desktop.
2. Open a terminal **in that folder**:
   - Windows: open the folder in File Explorer, click the address bar, type
     `cmd`, press Enter.
   - Mac: right-click the folder → "New Terminal at Folder" (or open
     Terminal and type `cd ` followed by dragging the folder in).
3. Install the dependencies (one line, copy-paste it exactly):
   ```
   pip install -r requirements.txt
   ```
   This downloads Streamlit and a handful of small libraries. Takes a minute
   or two.

## 3. Run it

Still in that same terminal:
```
streamlit run dashboard.py
```
Your browser should open automatically to `http://localhost:8501`. If it
doesn't, open that address manually. **Leave the terminal window open** —
closing it stops the bot.

That's it — it's already scanning BTCUSDT, ETHUSDT and SOLUSDT with three
strategies, paper trading with a virtual $10,000 per strategy.

---

## 4. Using the dashboard

- **Live scanner** — your watchlist, last prices, and a running feed of what
  the engine is doing every scan cycle.
- **Open positions** — every paper trade currently open, with entry, stop
  loss, target, and live unrealized P&L.
- **Journal** — every *closed* trade, permanently, with a "Setup conditions"
  column explaining exactly why the bot took it. This is your trading journal,
  written automatically.
- **Strategy leaderboard** — win rate and total P&L per strategy, so you can
  see which one is actually earning its keep instead of guessing.
- **Sidebar** — add or remove symbols (use Binance's format, e.g. `BTCUSDT`,
  `ETHUSDT`, `DOGEUSDT` — no slash), and see engine status / settings.

Signals aren't forced — if nothing meets a strategy's conditions, nothing
happens that cycle. That's intentional: it's meant to replace emotional
entries with patience, not create new noise.

---

## 5. Using it from your phone

### Option A — same WiFi as your laptop (free, instant)
1. On your laptop, find its local IP address:
   - Windows: `ipconfig` in a terminal, look for "IPv4 Address" (e.g.
     `192.168.1.42`)
   - Mac: System Settings → Network, or run `ipconfig getifaddr en0` in
     Terminal
2. Run the app so it's reachable from other devices on the network:
   ```
   streamlit run dashboard.py --server.address 0.0.0.0
   ```
3. On your phone (same WiFi), open `http://<that-ip>:8501` in your browser.

This only works while your laptop is on, awake, and on the same WiFi as your
phone — the engine runs on the laptop, the phone is just viewing it.

### Option B — away from home, laptop off (free, with a caveat)
To check it from anywhere without your laptop running, the engine needs to
live somewhere that's on 24/7. The easiest free way to try this:

1. Create a free account at **share.streamlit.io** (Streamlit Community
   Cloud).
2. Push this folder to a GitHub repository (GitHub has a simple "upload
   files" button in the browser if you don't want to use git directly).
3. In Streamlit Community Cloud, click "New app", point it at your repo and
   `dashboard.py`, and deploy.
4. You'll get a public URL you can open from your phone, anywhere.

**Honest caveat:** free hosting like this can go to sleep after a period of
no visitors, and background threads on a free container aren't guaranteed to
run forever uninterrupted. It's a genuinely good zero-cost way to get
phone access without your laptop. If you later want *guaranteed* every-minute
scanning even when nobody's looking at the dashboard for days, the reliable
upgrade is a small always-on server (~$5–6/month, e.g. DigitalOcean or
Linode) — ask me when you're ready and I'll walk you through that deploy
too.

---

## 6. What's simplified (read this before trusting any signal)

- **The SMC/ICT detection (`smc.py`) is a homemade, simplified version** of
  fair value gaps, break of structure, and order blocks — not a full
  reproduction of ICT theory, and real ICT/SMC trading involves a lot of
  discretionary judgment that doesn't reduce cleanly to code. Treat its
  signals as one input, not gospel. If you want a more complete version
  later, there's an open-source library called `smartmoneyconcepts` on PyPI
  worth trying.
- **There's no economic calendar yet.** The bot doesn't currently know about
  high-impact news events. For crypto this matters less than for forex, but
  macro events (CPI, FOMC) do move BTC. This is a natural next addition.
- **No "auto-discover strategies from GitHub" module.** That was deliberately
  left out of the first build — automatically pulling and running
  unreviewed code is a real security risk, and "automatically find a better
  strategy" is a hard problem even for well-funded trading firms. A
  human-reviewed research-assistant version is a reasonable later addition,
  but it should never auto-run without you approving it first.
- **This is paper trading only.** A strategy that looks good here can behave
  differently with real slippage, spread, and real money on the line. Treat
  strong paper results as a filter for what's worth studying further, not a
  guarantee.
- Not financial advice — this is a tool for testing ideas systematically,
  not a signal that should be followed blindly.

## 7. Adding your own strategy

Every strategy is just a function in `strategies.py` that takes the recent
candles and returns a `Signal` or `None`. Copy the shape of any existing one
(e.g. `rsi_reversion_strategy`), write your own condition, and add your
function to the `STRATEGIES` list at the bottom of the file. It'll
automatically get its own virtual balance and show up on the leaderboard
next to the others.

## Project files

| File | What it does |
|---|---|
| `config.py` | All the settings in one place (watchlist, risk, timeframe) |
| `data_feed.py` | Pulls live candles/prices from Binance's public API |
| `indicators.py` | EMA, RSI, ATR |
| `smc.py` | Simplified swing/FVG/BOS/order-block detection |
| `strategies.py` | The 3 strategies — add more here |
| `paper_trader.py` | Virtual portfolio: sizing, opening, closing trades |
| `db.py` | SQLite storage: watchlist, trades, journal, logs |
| `scanner.py` | The main loop that ties it all together |
| `dashboard.py` | The web app you actually run |
