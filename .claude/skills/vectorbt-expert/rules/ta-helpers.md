---
name: ta-helpers
description: Signal helpers (exrem, crossover, crossunder, flip, donchian, supertrend) in market_lib, plus the TA-Lib / pandas-ta / vectorbt indicator cheat sheet
metadata:
  tags: ta-lib, talib, pandas-ta, vectorbt, exrem, crossover, crossunder, flip, donchian, supertrend, indicators
---

# Indicator Libraries & Signal Helpers

Three indicator sources are allowed. **TA-Lib is the default**; use the others when TA-Lib lacks the indicator or the user asks for them.

| Library | Import | Use when |
|---------|--------|----------|
| **TA-Lib** (default) | `import talib` | EMA, SMA, WMA, RSI, MACD, BBANDS, ATR, ADX, STOCH, CCI, MOM, STDDEV, OBV, SAR ... |
| **pandas-ta** | `import pandas_ta as pta` | Indicators TA-Lib lacks: Supertrend, Donchian, Ichimoku, HMA, ALMA, VWMA, KC, ... or the user asks for pandas-ta |
| **vectorbt** | `vbt.talib("EMA")`, `vbt.MA`, `vbt.BBANDS` ... | Parameter sweeps over many windows at once (see [parameter-optimization](./parameter-optimization.md)), or the user asks for vectorbt indicators |

TA-Lib accepts a `pd.Series` and returns a `pd.Series` on the same index, so no re-wrapping is needed. `High/Low/Close` indicators take the series positionally.

```python
import talib
ema = talib.EMA(close, timeperiod=20)
rsi = talib.RSI(close, timeperiod=14)
macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
atr = talib.ATR(high, low, close, timeperiod=14)
adx = talib.ADX(high, low, close, timeperiod=14)
slowk, slowd = talib.STOCH(high, low, close)
```

## Quick Mapping

| Indicator | TA-Lib | pandas-ta | vectorbt |
|-----------|--------|-----------|----------|
| EMA | `talib.EMA(close, timeperiod=n)` | `pta.ema(close, n)` | `vbt.talib("EMA").run(close, timeperiod=n).real` |
| SMA | `talib.SMA(close, timeperiod=n)` | `pta.sma(close, n)` | `vbt.MA.run(close, n).ma` |
| RSI (Wilder) | `talib.RSI(close, timeperiod=n)` | `pta.rsi(close, n)` | `vbt.talib("RSI").run(close, timeperiod=n).real` |
| MACD | `talib.MACD(close, 12, 26, 9)` | `pta.macd(close, 12, 26, 9)` (DataFrame) | `vbt.MACD.run(close).macd` |
| Bollinger | `talib.BBANDS(close, 20, 2, 2)` | `pta.bbands(close, 20, 2)` (DataFrame) | `vbt.BBANDS.run(close).upper` |
| ATR | `talib.ATR(h, l, c, n)` | `pta.atr(h, l, c, n)` | `vbt.ATR.run(h, l, c, n).atr` |
| Momentum | `talib.MOM(close, n)` | `pta.mom(close, n)` | - |
| Supertrend | `market_lib.supertrend(h, l, c, n, mult)` | `pta.supertrend(h, l, c, length=n, multiplier=m)` | - |
| Donchian | `market_lib.donchian(h, l, n)` | `pta.donchian(h, l, n, n)` | - |

Caveats:
- `vbt.RSI.run()` uses a simple moving average by default, so it does **not** match Wilder RSI (`talib.RSI`). Use `vbt.talib("RSI")` when you need the standard value.
- pandas-ta returns DataFrames for multi-output indicators (column names like `SUPERT_10_3.0`, `DCU_20_20`); pick columns explicitly.
- Never mix libraries for the *same* indicator inside one comparison - results differ slightly in warm-up and smoothing.

## Signal Helpers (`market_lib.py`)

TA-Lib, pandas-ta and vectorbt do not ship signal-cleaning one-liners, so the project keeps them in `backtesting/market_lib.py` (template: `rules/assets/market_lib.py`, copied by `/setup`):

```python
from market_lib import exrem, crossover, crossunder, flip, donchian, supertrend
```

### exrem - Remove Excess Signals (CRITICAL)

Keeps only the first entry before an exit, and the first exit before an entry.

```python
entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))
```

**Before exrem:** `BUY BUY BUY SELL SELL BUY`
**After exrem:**  `BUY --- --- SELL ---- BUY`

### crossover / crossunder

```python
cross_up = crossover(close, upper_band)      # a crosses above b (b may be a scalar)
cross_down = crossunder(close, lower_band)
```

### flip - Regime Detection

True from the `on` bar until the `off` bar:

```python
bull_regime = flip(bull_trigger, bear_trigger)
bear_regime = flip(bear_trigger, bull_trigger)
```

### donchian / supertrend

```python
upper, middle, lower = donchian(high, low, period=20)
upper_shifted = upper.shift(1)                      # ALWAYS shift by 1 - avoids lookahead

st_line, st_direction = supertrend(high, low, close, period=10, multiplier=3.0)
# st_direction: 1 = uptrend (bullish), -1 = downtrend (bearish); ATR comes from TA-Lib
```

## Common Signal Pipeline

```python
import talib
from market_lib import exrem

ema_fast = talib.EMA(close, timeperiod=10)
ema_slow = talib.EMA(close, timeperiod=20)

buy_raw = ((ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))).fillna(False)
sell_raw = ((ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))).fillna(False)

entries = exrem(buy_raw, sell_raw)
exits = exrem(sell_raw, buy_raw)
```

## NEVER Do This

- Never skip `exrem()` - duplicate signals corrupt position sizing
- Never forget `.fillna(False)` before `exrem()` - NaN values propagate incorrectly
- Never use channel values (Donchian etc.) without `.shift(1)` - that is lookahead bias
