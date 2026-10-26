---
name: strategy-catalog
description: Complete strategy implementations - EMA, Donchian, Momentum, MACD, SDA2, Supertrend, Dual Momentum
metadata:
  tags: strategies, ema-crossover, donchian, momentum, macd, sda2, supertrend, dual-momentum
---

# Strategy Catalog

All strategies use TA-Lib for indicators (default) and `market_lib` for signal cleaning and helpers. Use pandas-ta or vectorbt indicators if TA-Lib lacks the indicator or the user asks for them - see [indicators-signals](./indicators-signals.md). Each strategy has a production-ready template in the `assets/` directory.

## 1. EMA Crossover

Fast/slow EMA crossover with `exrem()` signal cleaning.

Template: [assets/ema_crossover/backtest.py](./assets/ema_crossover/backtest.py)

```python
import talib
from market_lib import exrem

ema_fast = talib.EMA(close, timeperiod=10)
ema_slow = talib.EMA(close, timeperiod=20)

buy_raw = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
sell_raw = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))
```

## 2. Donchian Channel Breakout

Price breaks above/below the N-period high/low channel.

Template: [assets/donchian/backtest.py](./assets/donchian/backtest.py)

```python
from market_lib import crossover, crossunder, donchian

upper, middle, lower = donchian(df["high"], df["low"], period=20)

# Shift to avoid lookahead
upper_shifted = upper.shift(1)
lower_shifted = lower.shift(1)

entries = crossover(df["close"], upper_shifted)
exits = crossunder(df["close"], lower_shifted)
```

## 3. Momentum (Double MOM)

Uses MOM + MOM-of-MOM for directional confirmation with next-bar fill.

Template: [assets/momentum/backtest.py](./assets/momentum/backtest.py)

```python
import talib
from market_lib import exrem

LENGTH = 12
mom0 = talib.MOM(close, timeperiod=LENGTH)
mom1 = talib.MOM(mom0, timeperiod=1)

cond_long = (mom0 > 0) & (mom1 > 0)
cond_short = (mom0 < 0) & (mom1 < 0)

prev_high = high.shift(1)
prev_low = low.shift(1)
MINTICK = 0.05

entries_long = (cond_long.shift(1) & (high >= (prev_high + MINTICK))).fillna(False)
entries_short = (cond_short.shift(1) & (low <= (prev_low - MINTICK))).fillna(False)

entries_long = exrem(entries_long, entries_short)
entries_short = exrem(entries_short, entries_long)

exits_long = entries_short
exits_short = entries_long
```

## 4. MACD Signal-Candle Breakout

MACD zero-line defines regimes; entry on breakout of signal candle.

Template: [assets/macd/backtest.py](./assets/macd/backtest.py)

```python
import talib
from market_lib import exrem, crossover, crossunder, flip

macd_series, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
zero = pd.Series(0.0, index=close.index)

bull_flip = crossover(macd_series, zero)
bear_flip = crossunder(macd_series, zero)

bull_regime = flip(bull_flip, bear_flip)
bear_regime = flip(bear_flip, bull_flip)

sig_high = high.where(bull_flip).ffill()
sig_low = low.where(bear_flip).ffill()

long_entry_raw = crossover(high, sig_high) & bull_regime
short_entry_raw = crossunder(low, sig_low) & bear_regime

entries_long = exrem(long_entry_raw, bear_flip)
entries_short = exrem(short_entry_raw, bull_flip)

exits_long = exrem(bear_flip, entries_long)
exits_short = exrem(bull_flip, entries_short)
```

## 5. SDA2 Trend Following System

WMA-based channel with STDDEV and ATR bands.

Template: [assets/sda2/backtest.py](./assets/sda2/backtest.py)

```python
import talib
from market_lib import exrem

base = ((high + low) / 2.0) + (df["open"] - close)
derived = talib.WMA(base, timeperiod=3)

sd7 = talib.STDDEV(derived, timeperiod=7)
atr2 = talib.ATR(high, low, close, timeperiod=2)

upper = derived + sd7 + (atr2 / 1.5)
lower = derived - sd7 - (atr2 / 1.0)

entries = (close > upper) & (close.shift(1) <= upper.shift(1))
exits = (lower > close) & (lower.shift(1) <= close.shift(1))

entries = exrem(entries.fillna(False), exits.fillna(False))
exits = exrem(exits.fillna(False), entries)
```

## 6. Supertrend (Intraday with Time-Based Exit)

Supertrend crossover with Indian market session-aware entry/exit windows.

Template: [assets/supertrend/backtest.py](./assets/supertrend/backtest.py)

```python
from market_lib import supertrend
from datetime import time

st_line, st_direction = supertrend(df["high"], df["low"], df["close"],
                                       period=10, multiplier=3.0)

close = df["close"]
t = df.index.time

cross_up = (close > st_line) & (close.shift(1) <= st_line.shift(1))
cross_down = (close < st_line) & (close.shift(1) >= st_line.shift(1))

# Indian market session windows
entry_window = (t >= time(9, 30)) & (t <= time(15, 0))
at_1515 = (t == time(15, 15))

long_entries = cross_up & entry_window
long_exits = cross_down | at_1515
short_entries = cross_down & entry_window
short_exits = cross_up | at_1515
```

## 7. Dual Momentum (ETF Rotation)

Quarterly momentum rotation between two ETFs.

Template: [assets/dual_momentum/backtest.py](./assets/dual_momentum/backtest.py)

See the template for the full implementation including quarterly returns calculation, winner selection with lookahead prevention, and target-weight portfolio construction.
