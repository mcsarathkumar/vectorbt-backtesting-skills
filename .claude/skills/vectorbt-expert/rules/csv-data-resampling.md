---
name: csv-data-resampling
description: Loading CSV market data and resampling to different timeframes
metadata:
  tags: csv, data, resample, timeframe, ohlcv, minute, daily, hourly
---

# CSV Data Loading & Resampling

## Load Minute-Level CSV Data

```python
import pandas as pd
from pathlib import Path

csv_file = Path("data") / "NIFTYF.csv"
df = pd.read_csv(
    csv_file,
    usecols=["Ticker", "Date", "Time", "Open", "High", "Low", "Close", "Volume"]
)

# Build datetime index
df["datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
df = df.set_index("datetime").sort_index()
df = df.drop(columns=["Date", "Time", "Ticker"])
```

## Resample to Different Timeframes

```python
def resample_df(df, tf="D"):
    if tf == "D":
        return df.resample("D").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
        }).dropna()
    elif tf == "H":
        # 60-min bars aligned to Indian market open (09:15)
        return df.resample("60min", origin="start_day", offset="9h15min").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
        }).dropna()
    elif tf == "5min":
        return df.resample("5min", origin="start_day", offset="9h15min",
                           label="right", closed="right").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
        }).dropna()
    else:
        raise ValueError("Unsupported timeframe")

timeframe = "H"
df_resampled = resample_df(df, tf=timeframe)
close = df_resampled["Close"]
```

## Best Practices

- Always use `origin="start_day"` with `offset="9h15min"` for Indian market bar alignment
- Use `label="right", closed="right"` for intraday bars (a 9:15-9:20 bar is labeled 9:20)
- Apply `.dropna()` after resampling to remove empty bars (weekends, holidays)
- Verify bar count after resampling matches expected trading sessions

## Load from the Local Candle Store and Resample

`load_candles()` (see [data-fetching](./data-fetching.md)) already resamples from 1-minute data when an interval is not stored. For custom bar sizes (2h, 4h, 45min) use `resample_ohlcv()` from `market_lib`:

```python
from market_lib import load_candles, resample_ohlcv

df_1m = load_candles("RELIANCE", "NSE", "1m", start="2025-01-01")
df_45m = resample_ohlcv(df_1m, "45min")       # anchored to the 09:15 open
close = df_45m["close"]
```

