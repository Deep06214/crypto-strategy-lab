"""
Each strategy is a plain function: (df) -> Signal or None.
They know nothing about each other and don't wait for one another --
the scanner runs all of them every cycle and acts on whichever actually
has a real setup. Add a new strategy by writing a new function and
adding it to STRATEGIES at the bottom.
"""
from dataclasses import dataclass

import config
import indicators as ind
import smc


@dataclass
class Signal:
    strategy: str
    direction: str  # "LONG" or "SHORT"
    entry: float
    stop_loss: float
    take_profit: float
    reasoning: str


def fmt(p):
    return f"{p:,.2f}" if p >= 10 else f"{p:,.5f}"


def _rr_take_profit(entry, stop_loss, direction):
    risk = abs(entry - stop_loss)
    if direction == "LONG":
        return entry + config.REWARD_RISK_RATIO * risk
    return entry - config.REWARD_RISK_RATIO * risk


# ---------------------------------------------------------------- strategy 1
def ema_trend_strategy(df):
    """Classic trend-following: EMA9/EMA21 cross, filtered by EMA50 trend."""
    if len(df) < 60:
        return None
    close = df["close"]
    ema9, ema21, ema50 = ind.ema(close, 9), ind.ema(close, 21), ind.ema(close, 50)

    prev_diff = ema9.iloc[-2] - ema21.iloc[-2]
    curr_diff = ema9.iloc[-1] - ema21.iloc[-1]
    price = close.iloc[-1]

    crossed_up = prev_diff <= 0 and curr_diff > 0
    crossed_down = prev_diff >= 0 and curr_diff < 0

    swings = smc.find_swings(df)

    if crossed_up and price > ema50.iloc[-1]:
        sl_row = smc.last_swing_low(swings)
        stop = sl_row["low"] if sl_row is not None else price * 0.985
        tp = _rr_take_profit(price, stop, "LONG")
        reasoning = (
            f"EMA9 crossed above EMA21 ({fmt(ema9.iloc[-1])} / {fmt(ema21.iloc[-1])}) "
            f"while price ({fmt(price)}) is above EMA50 ({fmt(ema50.iloc[-1])}), confirming uptrend."
        )
        return Signal("ema_trend", "LONG", price, stop, tp, reasoning)

    if crossed_down and price < ema50.iloc[-1]:
        sh_row = smc.last_swing_high(swings)
        stop = sh_row["high"] if sh_row is not None else price * 1.015
        tp = _rr_take_profit(price, stop, "SHORT")
        reasoning = (
            f"EMA9 crossed below EMA21 ({fmt(ema9.iloc[-1])} / {fmt(ema21.iloc[-1])}) "
            f"while price ({fmt(price)}) is below EMA50 ({fmt(ema50.iloc[-1])}), confirming downtrend."
        )
        return Signal("ema_trend", "SHORT", price, stop, tp, reasoning)

    return None


# ---------------------------------------------------------------- strategy 2
def rsi_reversion_strategy(df):
    """Oversold/overbought bounce, confirmed by the candle actually turning."""
    if len(df) < 30:
        return None
    close = df["close"]
    rsi = ind.rsi(close, 14)
    last = df.iloc[-1]
    bullish_candle = last["close"] > last["open"]
    bearish_candle = last["close"] < last["open"]
    price = close.iloc[-1]

    swings = smc.find_swings(df)

    crossed_up_from_oversold = rsi.iloc[-2] < 30 and rsi.iloc[-1] >= 30
    crossed_down_from_overbought = rsi.iloc[-2] > 70 and rsi.iloc[-1] <= 70

    if crossed_up_from_oversold and bullish_candle:
        sl_row = smc.last_swing_low(swings)
        stop = sl_row["low"] if sl_row is not None else price * 0.98
        tp = _rr_take_profit(price, stop, "LONG")
        reasoning = (
            f"RSI(14) rose back above 30 from oversold ({rsi.iloc[-2]:.1f} -> {rsi.iloc[-1]:.1f}) "
            f"with a bullish confirmation candle."
        )
        return Signal("rsi_reversion", "LONG", price, stop, tp, reasoning)

    if crossed_down_from_overbought and bearish_candle:
        sh_row = smc.last_swing_high(swings)
        stop = sh_row["high"] if sh_row is not None else price * 1.02
        tp = _rr_take_profit(price, stop, "SHORT")
        reasoning = (
            f"RSI(14) dropped back below 70 from overbought ({rsi.iloc[-2]:.1f} -> {rsi.iloc[-1]:.1f}) "
            f"with a bearish confirmation candle."
        )
        return Signal("rsi_reversion", "SHORT", price, stop, tp, reasoning)

    return None


# ---------------------------------------------------------------- strategy 3
def smc_strategy(df):
    """Break of structure, then wait for price to retrace into an
    unmitigated fair value gap before entering -- the classic ICT
    'confirm direction, then enter on the pullback' sequence."""
    if len(df) < 40:
        return None
    bos_dir, sh, sl = smc.detect_bos(df)
    if bos_dir is None:
        return None

    price = df["close"].iloc[-1]
    fvgs = [f for f in smc.detect_fvgs(df) if f["direction"] == bos_dir]
    if not fvgs:
        return None

    # most recent matching FVG that current price is actually sitting inside
    touched = [f for f in fvgs if smc.price_in_fvg(price, f)]
    if not touched:
        return None
    fvg = touched[-1]

    ob = smc.find_order_block(df, bos_dir, fvg["index"])
    ob_note = ""
    if ob is not None:
        ob_level = ob["low"] if bos_dir == "bullish" else ob["high"]
        ob_note = f", aligned with an order block near {fmt(ob_level)}"

    if bos_dir == "bullish":
        stop = fvg["bottom"] * 0.999
        tp = _rr_take_profit(price, stop, "LONG")
        reasoning = (
            f"Bullish break of structure above the prior swing high ({fmt(sh['high'])}), "
            f"price retraced into an unmitigated bullish FVG ({fmt(fvg['bottom'])}-{fmt(fvg['top'])})"
            f"{ob_note}."
        )
        return Signal("smc_ict", "LONG", price, stop, tp, reasoning)
    else:
        stop = fvg["top"] * 1.001
        tp = _rr_take_profit(price, stop, "SHORT")
        reasoning = (
            f"Bearish break of structure below the prior swing low ({fmt(sl['low'])}), "
            f"price retraced into an unmitigated bearish FVG ({fmt(fvg['bottom'])}-{fmt(fvg['top'])})"
            f"{ob_note}."
        )
        return Signal("smc_ict", "SHORT", price, stop, tp, reasoning)


STRATEGIES = [ema_trend_strategy, rsi_reversion_strategy, smc_strategy]
