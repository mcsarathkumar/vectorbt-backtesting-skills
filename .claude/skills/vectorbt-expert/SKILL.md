---
name: vectorbt-expert
description: VectorBT backtesting expert. Use when user asks to backtest strategies, create entry/exit signals, analyze portfolio performance, optimize parameters, fetch historical data, use VectorBT/vectorbt, compare strategies, position sizing, equity curves, drawdown charts, or trade analysis. Also triggers for signal helpers (exrem, crossover, crossunder, flip, donchian, supertrend) and TA-Lib / pandas-ta / vectorbt indicators.
user-invocable: false
---

# VectorBT Backtesting Expert Skill

## Environment

- Python with vectorbt, pandas, numpy, plotly
- Data sources: **local Parquet candle store** for Indian markets (`/Users/mcsarathkumar/Workspace/indian-market-data/data/candles`, no API), yfinance (US/Global), CCXT (Crypto), custom providers
- API keys (CCXT, custom providers) loaded from single root `.env` via `python-dotenv` + `find_dotenv()` — never hardcode keys
- Technical indicators: **TA-Lib** (DEFAULT - `import talib`). Use **pandas-ta** or **vectorbt** indicators (`vbt.talib(...)`, `vbt.MA`) when TA-Lib lacks the indicator (Supertrend, Ichimoku, HMA ...), for parameter sweeps, or when the user asks.
- Signal helpers (exrem, crossover, crossunder, flip, donchian, supertrend): `market_lib.py` in `backtesting/` (template in `rules/assets/market_lib.py`)
- Fee model: Indian market standard (STT + statutory charges + Rs 20/order)
- Benchmark: NIFTYBEES (Nifty 50 ETF, daily) from the local candle store by default
- Charts: Plotly with `template="plotly_dark"`
- Scripts go in `backtesting/{strategy_name}/` directories (created on-demand, not pre-created)
- Never use icons/emojis in code or logger output

## Critical Rules

1. **Default to TA-Lib** (`import talib`) for standard indicators (EMA, SMA, RSI, MACD, BBANDS, ATR, ADX, STDDEV, MOM). TA-Lib takes/returns `pd.Series`, index preserved.
2. **Use pandas-ta** for indicators TA-Lib lacks (Ichimoku, HMA, ALMA, VWMA, Keltner ...) and **vectorbt indicators** (`vbt.talib("EMA")`, `vbt.MA`) for multi-parameter sweeps, or whenever the user asks for either. See [ta-helpers](rules/ta-helpers.md).
3. **Use `market_lib`** for data and signal utilities: `load_candles()`, `exrem()`, `crossover()`, `crossunder()`, `flip()`, `donchian()`, `supertrend()`.
4. **Always clean signals** with `exrem()` after generating raw buy/sell signals. Always `.fillna(False)` before exrem.
5. **Market-specific fees**: India ([indian-market-costs](rules/indian-market-costs.md)), US ([us-market-costs](rules/us-market-costs.md)), Crypto ([crypto-market-costs](rules/crypto-market-costs.md)). Auto-select based on user's market.
6. **Default benchmarks**: India=NIFTYBEES from the local candle store, US=S&P 500 (`^GSPC`), Crypto=Bitcoin (`BTC-USD`). See [data-fetching](rules/data-fetching.md) Market Selection Guide.
7. **Always produce** a Strategy vs Benchmark comparison table after every backtest.
8. **Always explain** the backtest report in plain language so even normal traders understand risk and strength.
9. **Plotly candlestick charts** must use `xaxis type="category"` to avoid weekend gaps.
10. **Whole shares**: Always set `min_size=1, size_granularity=1` for equities.
11. **Check data coverage first**: most symbols have daily candles only; intraday exists for large caps. `ls` the symbol folder before backtesting and tell the user if the requested symbol/interval is missing. See [data-fetching](rules/data-fetching.md).

## Modular Rule Files

Detailed reference for each topic is in `rules/`:

| Rule File | Topic |
|-----------|-------|
| [data-fetching](rules/data-fetching.md) | Local candle store (India), yfinance (US), CCXT (Crypto), custom providers, .env setup |
| [simulation-modes](rules/simulation-modes.md) | from_signals, from_orders, from_holding, direction types |
| [position-sizing](rules/position-sizing.md) | Amount/Value/Percent/TargetPercent sizing |
| [indicators-signals](rules/indicators-signals.md) | TA-Lib (default) strategy snippets, pandas-ta extras, signal generation |
| [ta-helpers](rules/ta-helpers.md) | TA-Lib / pandas-ta / vectorbt mapping; market_lib signal helpers (exrem, crossover, flip, Donchian, Supertrend) |
| [stop-loss-take-profit](rules/stop-loss-take-profit.md) | Fixed SL, TP, trailing stop |
| [parameter-optimization](rules/parameter-optimization.md) | Broadcasting and loop-based optimization |
| [performance-analysis](rules/performance-analysis.md) | Stats, metrics, benchmark comparison, CAGR |
| [plotting](rules/plotting.md) | Candlestick (category x-axis), VectorBT plots, custom Plotly |
| [indian-market-costs](rules/indian-market-costs.md) | Indian market fee model by segment |
| [us-market-costs](rules/us-market-costs.md) | US market fee model (stocks, options, futures) |
| [crypto-market-costs](rules/crypto-market-costs.md) | Crypto fee model (spot, USDT-M, COIN-M futures) |
| [futures-backtesting](rules/futures-backtesting.md) | Lot sizes (SEBI revised Dec 2025), value sizing |
| [long-short-trading](rules/long-short-trading.md) | Simultaneous long/short, direction comparison |
| [csv-data-resampling](rules/csv-data-resampling.md) | Loading CSV, resampling with Indian market alignment |
| [walk-forward](rules/walk-forward.md) | Walk-forward analysis, WFE ratio |
| [robustness-testing](rules/robustness-testing.md) | Monte Carlo, noise test, parameter sensitivity, delay test |
| [pitfalls](rules/pitfalls.md) | Common mistakes and checklist before going live |
| [strategy-catalog](rules/strategy-catalog.md) | Strategy reference with code snippets |
| [openstatz-tearsheet](rules/openstatz-tearsheet.md) | OpenStatz interactive offline dashboard, metrics, Monte Carlo (replaces QuantStats) |

## Strategy Templates (in rules/assets/)

Production-ready scripts with realistic fees, NIFTY benchmark, comparison table, and plain-language report:

| Template | Path | Description |
|----------|------|-------------|
| EMA Crossover | `assets/ema_crossover/backtest.py` | EMA 10/20 crossover |
| RSI | `assets/rsi/backtest.py` | RSI(14) oversold/overbought |
| Donchian | `assets/donchian/backtest.py` | Donchian channel breakout |
| Supertrend | `assets/supertrend/backtest.py` | Supertrend with intraday sessions |
| MACD | `assets/macd/backtest.py` | MACD signal-candle breakout |
| SDA2 | `assets/sda2/backtest.py` | SDA2 trend following |
| Momentum | `assets/momentum/backtest.py` | Double momentum (MOM + MOM-of-MOM) |
| Dual Momentum | `assets/dual_momentum/backtest.py` | Quarterly ETF rotation |
| Buy & Hold | `assets/buy_hold/backtest.py` | Static multi-asset allocation |
| RSI Accumulation | `assets/rsi_accumulation/backtest.py` | Weekly RSI slab-wise accumulation |
| Walk-Forward | `assets/walk_forward/template.py` | Walk-forward analysis template |
| Realistic Costs | `assets/realistic_costs/template.py` | Transaction cost impact comparison |

## Quick Template: Standard Backtest Script

```python
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt
import talib

# market_lib.py lives in backtesting/ (copied by the setup skill)
for _p in Path(__file__).resolve().parents:
    if (_p / "market_lib.py").exists():
        sys.path.insert(0, str(_p))
        break
from market_lib import load_candles, exrem

# --- Config ---
script_dir = Path(__file__).resolve().parent

SYMBOL = "SBIN"
EXCHANGE = "NSE"
INTERVAL = "D"
INIT_CASH = 1_000_000
FEES = 0.00111              # Indian delivery equity (STT + statutory)
FIXED_FEES = 20             # Rs 20 per order
ALLOCATION = 0.75
BENCHMARK_SYMBOL = "NIFTYBEES"   # Nifty 50 ETF (index has no daily bars locally)
BENCHMARK_EXCHANGE = "NSE"

# --- Load Data (local Parquet candles) ---
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365 * 3)

df = load_candles(SYMBOL, EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))
close = df["close"]

# --- Strategy: EMA Crossover (TA-Lib - default indicator library) ---
ema_fast = talib.EMA(close, timeperiod=10)
ema_slow = talib.EMA(close, timeperiod=20)

buy_raw = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
sell_raw = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))

# --- Backtest ---
pf = vbt.Portfolio.from_signals(
    close, entries, exits,
    init_cash=INIT_CASH, size=ALLOCATION, size_type="percent",
    fees=FEES, fixed_fees=FIXED_FEES, direction="longonly",
    min_size=1, size_granularity=1, freq="1D",
)

# --- Benchmark ---
df_bench = load_candles(BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE, INTERVAL,
                        start=str(start_date), end=str(end_date))
bench_close = df_bench["close"].reindex(close.index).ffill().bfill()
pf_bench = vbt.Portfolio.from_holding(bench_close, init_cash=INIT_CASH, fees=FEES, freq="1D")

# --- Results ---
print(pf.stats())

# --- Strategy vs Benchmark ---
comparison = pd.DataFrame({
    "Strategy": [
        f"{pf.total_return() * 100:.2f}%", f"{pf.sharpe_ratio():.2f}",
        f"{pf.sortino_ratio():.2f}", f"{pf.max_drawdown() * 100:.2f}%",
        f"{pf.trades.win_rate() * 100:.1f}%", f"{pf.trades.count()}",
        f"{pf.trades.profit_factor():.2f}",
    ],
    f"Benchmark ({BENCHMARK_SYMBOL})": [
        f"{pf_bench.total_return() * 100:.2f}%", f"{pf_bench.sharpe_ratio():.2f}",
        f"{pf_bench.sortino_ratio():.2f}", f"{pf_bench.max_drawdown() * 100:.2f}%",
        "-", "-", "-",
    ],
}, index=["Total Return", "Sharpe Ratio", "Sortino Ratio", "Max Drawdown",
          "Win Rate", "Total Trades", "Profit Factor"])
print(comparison.to_string())

# --- Explain ---
print(f"* Total Return: {pf.total_return() * 100:.2f}% vs NIFTY {pf_bench.total_return() * 100:.2f}%")
print(f"* Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
print(f"  -> On Rs {INIT_CASH:,}, worst temporary loss = Rs {abs(pf.max_drawdown()) * INIT_CASH:,.0f}")

# --- Plot ---
fig = pf.plot(subplots=['value', 'underwater', 'cum_returns'], template="plotly_dark")
fig.show()

# --- Export ---
pf.positions.records_readable.to_csv(script_dir / f"{SYMBOL}_trades.csv", index=False)
```
