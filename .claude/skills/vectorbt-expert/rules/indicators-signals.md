---
name: indicators-signals
description: Creating technical indicators and entry/exit signals - TA-Lib by default, pandas-ta or vectorbt indicators when TA-Lib lacks them or the user asks
metadata:
  tags: indicators, signals, rsi, ema, sma, macd, crossover, entries, exits, talib, pandas-ta, vectorbt
---

# Creating Indicators & Signals

## Rule: TA-Lib by Default; pandas-ta or vectorbt When Needed

- **Default to `talib`** for standard indicators (EMA, SMA, RSI, MACD, BBANDS, ATR, ADX, STOCH, CCI, MOM, STDDEV).
- **Use pandas-ta** for indicators TA-Lib lacks (Supertrend, Ichimoku, HMA, ALMA, VWMA, Keltner ...), or when the user asks for it.
- **Use vectorbt indicators** (`vbt.talib("EMA")`, `vbt.MA`, `vbt.BBANDS` ...) for multi-parameter sweeps, or when the user asks for them. See [parameter-optimization](./parameter-optimization.md).
- Signal helpers (`exrem`, `crossover`, `crossunder`, `flip`, `donchian`, `supertrend`) come from `market_lib`. Full reference and a TA-Lib / pandas-ta / vectorbt mapping table: [ta-helpers](./ta-helpers.md).

TA-Lib takes and returns `pd.Series` (index preserved), so no wrapping is needed.

## EMA Crossover Strategy

```python
import talib
from market_lib import exrem

ema_fast = talib.EMA(close, timeperiod=10)
ema_slow = talib.EMA(close, timeperiod=20)

buy_raw = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
sell_raw = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

# ALWAYS clean signals with exrem()
entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))
```

## SMA Crossover Strategy

```python
fast_sma = talib.SMA(close, timeperiod=10)
slow_sma = talib.SMA(close, timeperiod=20)

buy_raw = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
sell_raw = (fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))
```

## RSI Strategy

```python
rsi = talib.RSI(close, timeperiod=14)

buy_raw = (rsi < 30) & (rsi.shift(1) >= 30)      # RSI crosses below 30 (oversold)
sell_raw = (rsi > 70) & (rsi.shift(1) <= 70)      # RSI crosses above 70 (overbought)

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))
```

## MACD Strategy

```python
macd_line, signal_line, histogram = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)

buy_raw = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
sell_raw = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))
```

## Bollinger Bands Strategy

```python
upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)

buy_raw = (close < lower) & (close.shift(1) >= lower.shift(1))   # Price touches lower band
sell_raw = (close > upper) & (close.shift(1) <= upper.shift(1))   # Price touches upper band

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))
```

## ATR (Average True Range)

```python
atr = talib.ATR(high, low, close, timeperiod=14)
```

## Indicators Beyond TA-Lib (pandas-ta)

```python
import pandas_ta as pta

hma = pta.hma(close, length=21)
kc = pta.kc(high, low, close, length=20)                          # Keltner channels (DataFrame)
st = pta.supertrend(high, low, close, length=10, multiplier=3.0)  # columns SUPERT_10_3.0, SUPERTd_10_3.0 ...
```

## Signal Cleaning: Why exrem() Matters

Raw crossover signals can produce consecutive buy signals without an intervening sell. `exrem()` keeps only the FIRST entry before an exit and vice versa:

```
Raw:    BUY  BUY  BUY  SELL  SELL  BUY
Clean:  BUY  ---  ---  SELL  ----  BUY
```

Always apply `exrem()` after generating raw signals, whichever library computed the indicator.

## NEVER Do This

- Never use `vbt.RSI.run()` expecting Wilder RSI (it defaults to a simple average) - use `talib.RSI` or `vbt.talib("RSI")`
- Never generate signals using future data (lookahead bias)
- Never skip `exrem()` signal cleaning - duplicate signals cause incorrect position sizing
- Never use `close[i]` in Python loops when vectorized operations exist
- Never forget `.fillna(False)` on boolean signal series - NaN signals cause silent errors
