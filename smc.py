"""
A lightweight, homemade implementation of the ICT / Smart Money Concepts
building blocks: swing points, fair value gaps, break of structure, and a
simplified order block finder.

This is NOT a faithful reproduction of ICT theory -- it's a reasonable,
readable approximation so the strategy engine has something concrete to
work with. There's a more complete open-source library called
`smartmoneyconcepts` on PyPI if you want to go deeper later; this module
is written to be easy to read and extend rather than exhaustive.
"""


def find_swings(df, lookback=3):
    """Marks confirmed swing highs/lows (a swing needs `lookback` candles
    on both sides, so the most recent few candles can't be swings yet)."""
    df = df.copy()
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    swing_high = [False] * n
    swing_low = [False] * n
    for i in range(lookback, n - lookback):
        window_high = highs[i - lookback: i + lookback + 1]
        window_low = lows[i - lookback: i + lookback + 1]
        if highs[i] == window_high.max():
            swing_high[i] = True
        if lows[i] == window_low.min():
            swing_low[i] = True
    df["swing_high"] = swing_high
    df["swing_low"] = swing_low
    return df


def last_swing_high(swings_df, before_index=None):
    sub = swings_df if before_index is None else swings_df.iloc[:before_index]
    rows = sub[sub["swing_high"]]
    return rows.iloc[-1] if len(rows) else None


def last_swing_low(swings_df, before_index=None):
    sub = swings_df if before_index is None else swings_df.iloc[:before_index]
    rows = sub[sub["swing_low"]]
    return rows.iloc[-1] if len(rows) else None


def detect_bos(df, lookback=3):
    """Break of structure on the most recent closed candle.
    Returns ('bullish' | 'bearish' | None, swing_high_row, swing_low_row)."""
    swings = find_swings(df, lookback=lookback)
    last_close = swings["close"].iloc[-1]
    before = len(swings) - 1
    sh = last_swing_high(swings, before_index=before)
    sl = last_swing_low(swings, before_index=before)

    broke_up = sh is not None and last_close > sh["high"]
    broke_down = sl is not None and last_close < sl["low"]

    if broke_up and not broke_down:
        return "bullish", sh, sl
    if broke_down and not broke_up:
        return "bearish", sh, sl
    if broke_up and broke_down:
        # both technically true (rare) -- whichever swing is more recent wins
        return ("bullish" if sh.name > sl.name else "bearish"), sh, sl
    return None, sh, sl


def detect_fvgs(df, max_lookback=50):
    """Unmitigated fair value gaps (3-candle imbalance) in the recent window."""
    n = len(df)
    start = max(2, n - max_lookback)
    found = []
    for i in range(start, n):
        c0 = df.iloc[i - 2]
        c2 = df.iloc[i]
        if c2["low"] > c0["high"]:
            found.append({"direction": "bullish", "top": c2["low"], "bottom": c0["high"], "index": i})
        elif c2["high"] < c0["low"]:
            found.append({"direction": "bearish", "top": c0["low"], "bottom": c2["high"], "index": i})

    # A gap counts as mitigated only once price trades all the way THROUGH
    # it (closes the far side) -- not the moment price first dips back in.
    # That first dip back in is the retracement we actually want to trade,
    # so it must stay classified as "unmitigated" or the strategy would
    # never be able to enter on it.
    unmitigated = []
    for fvg in found:
        mitigated = False
        for j in range(fvg["index"] + 1, n):
            if fvg["direction"] == "bullish" and df["low"].iloc[j] <= fvg["bottom"]:
                mitigated = True
                break
            if fvg["direction"] == "bearish" and df["high"].iloc[j] >= fvg["top"]:
                mitigated = True
                break
        if not mitigated:
            unmitigated.append(fvg)
    return unmitigated


def price_in_fvg(price, fvg):
    return fvg["bottom"] <= price <= fvg["top"]


def find_order_block(df, direction, before_index, max_search=15):
    """Simplified order block: the last opposite-colored candle before the
    move, searching backward from `before_index`."""
    start = before_index - 1
    end = max(before_index - max_search, 0)
    for i in range(start, end, -1):
        row = df.iloc[i]
        is_bullish_candle = row["close"] > row["open"]
        if direction == "bullish" and not is_bullish_candle:
            return row
        if direction == "bearish" and is_bullish_candle:
            return row
    return None
