"""
market_lib - shared helpers for the backtest templates.

* load_candles(): reads the local Parquet candle store (indian-market-data).
* Signal helpers (exrem, crossover, crossunder, flip, donchian, supertrend) that
  TA-Lib / pandas-ta / vectorbt do not ship as one-liners.

Indicators themselves come from TA-Lib (default), pandas-ta or vectorbt.
Setup copies this file to backtesting/market_lib.py; scripts find it by walking up.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

CANDLES_ROOT = Path(os.getenv(
    "CANDLES_DIR", "/Users/mcsarathkumar/Workspace/indian-market-data/data/candles"))

# Script interval -> folder on disk (the store holds no 2m/4m/1h-native bars)
INTERVAL_FOLDERS = {
    "1m": "1minute", "3m": "3minute", "5m": "5minute", "10m": "10minute",
    "15m": "15minute", "30m": "30minute", "1h": "60minute",
    "D": "1day", "W": "1week",
}
# pandas freq string per interval, for vbt `freq=`
INTERVAL_FREQ = {"1m": "1min", "3m": "3min", "5m": "5min", "10m": "10min",
                 "15m": "15min", "30m": "30min", "1h": "1h", "D": "1D", "W": "1W"}
INDEX_ALIASES = {"NIFTY": "Nifty 50"}   # index folders hold only 1minute/1second bars


def _symbol_dir(symbol, exchange):
    d = CANDLES_ROOT / exchange / INDEX_ALIASES.get(symbol, symbol)
    if not d.exists() and exchange == "NSE" and (CANDLES_ROOT / exchange / f"{symbol}-EQ").exists():
        d = CANDLES_ROOT / exchange / f"{symbol}-EQ"       # SBIN -> SBIN-EQ
    return d


def _read(folder, start, end):
    """Concatenate parquet files under folder, skipping years outside [start, end]."""
    lo = pd.Timestamp(start).year if start else None
    hi = pd.Timestamp(end).year if end else None
    files = []
    for f in sorted(folder.rglob("*.parquet")):
        year = f.stem if f.stem.isdigit() and len(f.stem) == 4 else f.relative_to(folder).parts[0]
        if year.isdigit() and ((lo and int(year) < lo) or (hi and int(year) > hi)):
            continue
        files.append(f)
    if not files:
        return None
    df = pd.concat(pd.read_parquet(f) for f in files).set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.index = df.index.tz_localize(None)       # IST wall-clock time
    return df


def resample_ohlcv(df, rule):
    """Resample to a coarser bar (e.g. '5min', '2h'), anchored to the 09:15 open."""
    out = df.resample(rule, origin="start_day", offset="9h15min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return out.dropna(subset=["close"])


def load_candles(symbol, exchange="NSE", interval="D", start=None, end=None):
    """Return a tz-naive (IST) OHLCV DataFrame for symbol/interval.

    If the interval is not stored for this symbol (e.g. 5m, 15m), it is resampled
    from the 1minute candles instead.
    """
    base = _symbol_dir(symbol, exchange)
    df = _read(base / INTERVAL_FOLDERS.get(interval, interval), start, end)
    if df is None and interval in INTERVAL_FREQ and interval not in ("D", "W"):
        raw = _read(base / "1minute", start, end)
        if raw is not None:
            df = resample_ohlcv(raw, INTERVAL_FREQ[interval])
    if df is None:
        raise FileNotFoundError(
            f"No {interval} candles under {base} - check symbol (e.g. SBIN-EQ), exchange and interval")
    return df.loc[start:end, ["open", "high", "low", "close", "volume"]]


# --- Signal helpers (pandas in, pandas out) ---------------------------------
def crossover(a, b):
    """True on the bar where a crosses above b."""
    a, b = pd.Series(a), pd.Series(b, index=pd.Series(a).index) if np.isscalar(b) else pd.Series(b)
    return ((a > b) & (a.shift(1) <= b.shift(1))).fillna(False)


def crossunder(a, b):
    """True on the bar where a crosses below b."""
    a, b = pd.Series(a), pd.Series(b, index=pd.Series(a).index) if np.isscalar(b) else pd.Series(b)
    return ((a < b) & (a.shift(1) >= b.shift(1))).fillna(False)


def exrem(signal, opposite):
    """Drop repeated `signal` bars until `opposite` fires (excess-signal removal)."""
    sig = np.asarray(signal, dtype=bool)
    opp = np.asarray(opposite, dtype=bool)
    out = np.zeros(len(sig), dtype=bool)
    active = False
    for i in range(len(sig)):
        if sig[i] and not active:
            out[i], active = True, True
        elif opp[i]:
            active = False
    return pd.Series(out, index=getattr(signal, "index", None))


def flip(on, off):
    """Regime flag: True from an `on` bar until the next `off` bar."""
    index = getattr(on, "index", None)
    on, off = np.asarray(on, dtype=bool), np.asarray(off, dtype=bool)
    state, out = False, np.zeros(len(on), dtype=bool)
    for i in range(len(on)):
        if on[i]:
            state = True
        elif off[i]:
            state = False
        out[i] = state
    return pd.Series(out, index=index)


def donchian(high, low, period=20):
    """(upper, middle, lower) rolling channel."""
    upper = high.rolling(period).max()
    lower = low.rolling(period).min()
    return upper, (upper + lower) / 2, lower


def supertrend(high, low, close, period=10, multiplier=3.0):
    """(line, direction) with direction = 1 uptrend / -1 downtrend. ATR from TA-Lib."""
    import talib
    atr = talib.ATR(high.values, low.values, close.values, timeperiod=period)
    hl2 = ((high + low) / 2).values
    c = close.values
    upper, lower = hl2 + multiplier * atr, hl2 - multiplier * atr
    n = len(c)
    fu, fl = upper.copy(), lower.copy()
    direction = np.ones(n, dtype=int)
    line = np.full(n, np.nan)
    for i in range(1, n):
        if np.isnan(atr[i]):
            continue
        if i == 1 or np.isnan(fu[i - 1]):
            pass
        else:
            if not (upper[i] < fu[i - 1] or c[i - 1] > fu[i - 1]):
                fu[i] = fu[i - 1]
            if not (lower[i] > fl[i - 1] or c[i - 1] < fl[i - 1]):
                fl[i] = fl[i - 1]
        if c[i] > fu[i - 1]:
            direction[i] = 1
        elif c[i] < fl[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
        line[i] = fl[i] if direction[i] == 1 else fu[i]
    return pd.Series(line, index=close.index), pd.Series(direction, index=close.index)
