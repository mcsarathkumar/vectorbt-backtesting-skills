---
name: data-fetching
description: Loading historical market data - local Parquet candle store (India), yfinance (US/Global), CCXT (Crypto)
metadata:
  tags: data, candles, parquet, yfinance, ccxt, history, intervals, exchanges, dotenv, env
---

# Data Fetching

## Environment Setup (All Markets)

API keys (CCXT, Alpaca, ...) live in the single root `.env`, loaded with `python-dotenv` + `find_dotenv()`. Never hardcode keys. Indian-market backtests need no keys: they read local Parquet files.

```python
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

script_dir = Path(__file__).resolve().parent
load_dotenv(find_dotenv(), override=False)   # only needed for CCXT / custom providers
```

---

## 1. Indian Markets - Local Candle Store (Primary)

Data comes from the `indian-market-data` Parquet store - no API, no rate limit:

```
/Users/mcsarathkumar/Workspace/indian-market-data/data/candles   (override with env CANDLES_DIR)
  <EXCHANGE>/<SYMBOL>/<interval>/...parquet
```

Use `load_candles()` from `market_lib.py` (template: `rules/assets/market_lib.py`, copied to `backtesting/market_lib.py` by `/setup`):

```python
import sys
from pathlib import Path
for _p in Path(__file__).resolve().parents:       # find backtesting/market_lib.py
    if (_p / "market_lib.py").exists():
        sys.path.insert(0, str(_p)); break
from market_lib import load_candles

df = load_candles("SBIN", "NSE", "D", start="2023-01-01", end="2026-10-19")
close = df["close"]          # tz-naive IST index; columns: open high low close volume
```

`load_candles(symbol, exchange="NSE", interval="D", start=None, end=None)`:
- `SBIN` resolves to the folder `SBIN-EQ` automatically; `NIFTY` resolves to the `Nifty 50` index folder.
- Returns a sorted, de-duplicated, tz-naive DataFrame (IST wall-clock; candle **start** time).
- If the requested intraday interval is not stored for that symbol, it is resampled from `1minute` candles (anchored to the 09:15 open).

### Store Layout

| Interval arg | Folder | File layout |
|--------------|--------|-------------|
| `1m` | `1minute` | one file per day: `<yyyy>/<mm>/<dd>.parquet` |
| `3m`, `5m`, `10m`, `15m`, `30m`, `1h` | `3minute` ... `60minute` | one file per month: `<yyyy>/<mm>.parquet` |
| `D` | `1day` | one file per year: `<yyyy>.parquet` |
| `W` | `1week` | one file per year |

Columns: `timestamp` (tz `Asia/Kolkata`), `open`, `high`, `low`, `close`, `volume`. Prices are rounded to 2 decimals; bad rows are dropped at ingest.

### Check What Exists Before You Backtest

Coverage is **not uniform** - most symbols have `1day` only; intraday exists for large caps and a few ETFs. List before assuming:

```bash
ls /Users/mcsarathkumar/Workspace/indian-market-data/data/candles/NSE/SBIN-EQ        # intervals available
ls /Users/mcsarathkumar/Workspace/indian-market-data/data/candles/NSE | grep -i "^RELI"  # find the symbol folder
```

Known gaps: index folders (`Nifty 50`) have `1minute`/`1second` only (no daily); `NIFTYBEES-EQ` and `GOLDBEES-EQ` have daily only. If `load_candles` raises `FileNotFoundError`, tell the user which interval/symbol is missing instead of falling back to another source silently.

### Exchanges and Symbols

| Exchange | Folder | Symbol format |
|----------|--------|---------------|
| NSE equities / ETFs | `candles/NSE/<SYMBOL>-EQ` | `SBIN-EQ`, `NIFTYBEES-EQ` (bare `SBIN` accepted) |
| NSE indices | `candles/NSE/Nifty 50` | 1-minute only |
| BSE equities | `candles/BSE/<SCRIPCODE-or-ticker>` | 1day only, e.g. `KMEW` |
| NSE F&O | `data/fno_candles/NFO/<UNDERLYING>/<CONTRACT>/1minute/<yyyy>/...` | e.g. `BANKNIFTY22APR31700CE`; extra `open_interest` column |

F&O sits in a separate root (`.../indian-market-data/data/fno_candles`); read those files with `pd.read_parquet` over the contract folder (see [futures-backtesting](./futures-backtesting.md)).

### Indian Market Benchmarks

| Benchmark | Source | Symbol |
|-----------|--------|--------|
| Nifty 50 (daily, primary) | local store | `NIFTYBEES` (ETF proxy; index has no daily bars) |
| Nifty 50 (intraday) | local store | `NIFTY` (index, 1-minute, resample as needed) |
| Nifty 50 (fallback) | yfinance | `^NSEI` |

---

## 2. US Markets — yfinance (No API Key Needed)

yfinance uses public Yahoo Finance data. No API key or `.env` config required.

```python
import yfinance as yf

# US Stock
df = yf.download("AAPL", start="2022-01-01", end="2025-01-01",
                  interval="1d", auto_adjust=True, multi_level_index=False)
close = df["Close"]

# US ETF
df = yf.download("SPY", start="2022-01-01", end="2025-01-01",
                  interval="1d", auto_adjust=True, multi_level_index=False)
```

### yfinance Ticker Format

| Asset | Ticker | Example |
|-------|--------|---------|
| US Stock | `AAPL`, `MSFT`, `TSLA` | Direct ticker |
| US ETF | `SPY`, `QQQ`, `IWM` | Direct ticker |
| Indian Stock | `RELIANCE.NS`, `SBIN.NS` | Ticker + `.NS` (NSE) or `.BO` (BSE) |
| Crypto | `BTC-USD`, `ETH-USD` | Symbol + `-USD` |
| US Index | `^GSPC` (S&P 500), `^NDX` (NASDAQ 100) | `^` prefix |
| Indian Index | `^NSEI` (NIFTY 50), `^BSESN` (Sensex) | `^` prefix |

### yfinance Intervals

| Interval | Code | Max History |
|----------|------|-------------|
| 1 minute | `1m` | 7 days |
| 2 minutes | `2m` | 60 days |
| 5 minutes | `5m` | 60 days |
| 15 minutes | `15m` | 60 days |
| 30 minutes | `30m` | 60 days |
| 1 hour | `1h` | 730 days |
| 1 day | `1d` | Unlimited |
| 1 week | `1wk` | Unlimited |
| 1 month | `1mo` | Unlimited |

### US Market Benchmarks

| Benchmark | Ticker | Description |
|-----------|--------|-------------|
| S&P 500 (index) | `^GSPC` | Broad US market |
| S&P 500 (ETF) | `SPY` | Tradeable ETF |
| NASDAQ 100 | `^NDX` or `QQQ` | Tech-heavy |
| Dow Jones | `^DJI` or `DIA` | Blue chips |
| Russell 2000 | `^RUT` or `IWM` | Small caps |

### Multi-Asset US Data Fetch

```python
import yfinance as yf
import pandas as pd

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
df = yf.download(tickers, start="2022-01-01", end="2025-01-01",
                 interval="1d", auto_adjust=True, multi_level_index=False)
# For multi-ticker, columns are multi-level: ("Close", "AAPL"), etc.
# With multi_level_index=False on single ticker it flattens
```

---

## 3. Crypto Markets — yfinance or CCXT

### yfinance (Simple — No API Key)

```python
import yfinance as yf

# Bitcoin daily
df = yf.download("BTC-USD", start="2022-01-01", end="2025-01-01",
                  interval="1d", auto_adjust=True, multi_level_index=False)
close = df["Close"]

# Ethereum daily
df = yf.download("ETH-USD", start="2022-01-01", end="2025-01-01",
                  interval="1d", auto_adjust=True, multi_level_index=False)
```

### CCXT (Higher Resolution — Optional API Key)

For intraday crypto data or exchange-specific pairs. Public OHLCV data does NOT require API keys. Only private endpoints (account, orders) need keys.

```python
# pip install ccxt
import ccxt
import pandas as pd

# Public data - no API key needed
exchange = ccxt.binance()

# Fetch OHLCV
ohlcv = exchange.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=1000)
df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
df = df.set_index("timestamp")
close = df["close"]
```

For authenticated CCXT (account data):

```python
# Authenticated — requires CRYPTO_API_KEY and CRYPTO_SECRET_KEY in .env
exchange = ccxt.binance({
    "apiKey": os.getenv("CRYPTO_API_KEY"),
    "secret": os.getenv("CRYPTO_SECRET_KEY"),
})
```

### Crypto Tickers

| Pair | yfinance | CCXT |
|------|----------|----------------|
| BTC/USD | `BTC-USD` | `BTC/USDT` |
| ETH/USD | `ETH-USD` | `ETH/USDT` |
| SOL/USD | `SOL-USD` | `SOL/USDT` |
| BNB/USD | `BNB-USD` | `BNB/USDT` |

### Crypto Benchmarks

| Benchmark | Ticker | Source |
|-----------|--------|--------|
| Bitcoin | `BTC-USD` | yfinance |
| Ethereum | `ETH-USD` | yfinance |

---

## Data Normalization (yfinance / CCXT / custom)

`load_candles()` already returns a clean frame. For other sources, normalize:

```python
df = df.sort_index()
if df.index.tz is not None:
    df.index = df.index.tz_convert(None)   # VectorBT works best with tz-naive
df.columns = df.columns.str.lower()        # yfinance: Close -> close
close = df["close"]
```

## Multiple Timeframe Data Load

```python
df_daily = load_candles("RELIANCE", "NSE", "D", start="2024-01-01")
df_5m = load_candles("RELIANCE", "NSE", "5m", start="2025-02-01")   # resampled from 1minute if not stored
df_4h = resample_ohlcv(load_candles("RELIANCE", "NSE", "1h"), "4h")  # from market_lib
```

## Multi-Asset Data Load

```python
symbols = ["RELIANCE", "HDFCBANK", "INFY", "TCS"]
dfs = {sym: load_candles(sym, "NSE", "D", start="2024-01-01") for sym in symbols}
close_prices = pd.DataFrame({sym: dfs[sym]["close"] for sym in symbols})
```

## Market Selection Guide

| If the user says... | Market | Data Source | Fee Model |
|---------------------|--------|-------------|-----------|
| NSE, BSE, NIFTY, BANKNIFTY, Indian stock names | India | Local candle store | [indian-market-costs](./indian-market-costs.md) |
| AAPL, SPY, S&P 500, NASDAQ, US stock names | US | yfinance | [us-market-costs](./us-market-costs.md) |
| BTC, ETH, crypto, USDT | Crypto | yfinance or CCXT | [crypto-market-costs](./crypto-market-costs.md) |

## 4. Custom Data Provider (Extensible)

Users can plug in any data source as long as it returns a pandas DataFrame with a DatetimeIndex and OHLCV columns. Follow this pattern:

### Adding a Custom Data Provider

1. **Add API key(s) to `.env`:**

```
# Custom data provider
CUSTOM_API_KEY=your_key_here
CUSTOM_API_URL=https://api.example.com
```

2. **Create a fetch function** that returns a normalized DataFrame:

```python
import os
import requests
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from pathlib import Path

script_dir = Path(__file__).resolve().parent
load_dotenv(find_dotenv(), override=False)

def fetch_custom_data(symbol, start_date, end_date, interval="1d"):
    """Fetch data from a custom provider.

    Must return a DataFrame with:
    - DatetimeIndex (tz-naive)
    - Columns: open, high, low, close, volume (lowercase)
    """
    api_key = os.getenv("CUSTOM_API_KEY")
    base_url = os.getenv("CUSTOM_API_URL")

    # --- Replace this block with your provider's API call ---
    response = requests.get(f"{base_url}/history", params={
        "symbol": symbol,
        "from": start_date,
        "to": end_date,
        "interval": interval,
        "apikey": api_key,
    })
    data = response.json()
    df = pd.DataFrame(data)
    # --- End custom block ---

    # Normalize to standard format
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    if df.index.tz is not None:
        df.index = df.index.tz_convert(None)
    df.columns = df.columns.str.lower()

    return df
```

3. **Use it in backtest scripts** the same way as any other source:

```python
df = fetch_custom_data("AAPL", "2022-01-01", "2025-01-01")
close = df["close"]
```

### Custom Provider Checklist

- [ ] API keys loaded from `.env` via `python-dotenv` (never hardcoded)
- [ ] Returns DataFrame with DatetimeIndex (tz-naive)
- [ ] Columns lowercase: `open`, `high`, `low`, `close`, `volume`
- [ ] Data sorted by index (`df.sort_index()`)
- [ ] Timezone stripped (`tz_convert(None)`)
- [ ] Add your provider's API key variable to `.env.sample`

### Example: Alpaca Markets

```python
import os
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from pathlib import Path

# pip install alpaca-trade-api
from alpaca_trade_api.rest import REST

script_dir = Path(__file__).resolve().parent
load_dotenv(find_dotenv(), override=False)

alpaca = REST(
    key_id=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    base_url=os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
)

bars = alpaca.get_bars("AAPL", "1Day", start="2022-01-01", end="2025-01-01").df
bars.columns = bars.columns.str.lower()
bars.index = bars.index.tz_convert(None)
close = bars["close"]
```

### Example: Twelve Data

```python
import os
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from pathlib import Path

# pip install twelvedata
from twelvedata import TDClient

script_dir = Path(__file__).resolve().parent
load_dotenv(find_dotenv(), override=False)

td = TDClient(apikey=os.getenv("TWELVEDATA_API_KEY"))
ts = td.time_series(symbol="AAPL", interval="1day", start_date="2022-01-01",
                    end_date="2025-01-01", outputsize=5000).as_pandas()
ts = ts.sort_index()
ts.columns = ts.columns.str.lower()
close = ts["close"]
```

---

## NEVER Do This

- Never hardcode API keys in scripts — always use `.env` + `python-dotenv`
- Never fetch Indian market data from a broker/API when the local candle store has it
- Never hardcode dates without making them configurable
- Never skip `sort_index()` — data must be chronologically ordered
- Never ignore timezone handling — mismatch causes silent alignment errors
- Never fetch more intraday data than the source provides (see interval tables above)
- Never use yfinance for Indian market backtests when the local candle store has the symbol
