"""
EMA Crossover Backtest - VectorBT + TA-Lib
Strategy: Buy when Fast EMA crosses above Slow EMA, sell on cross below.
Indicators: TA-Lib EMA (default; pandas-ta or vbt.MA are drop-in alternatives).
Fees: Indian delivery equity model (0.111% + Rs 20/order).
Benchmark: NIFTYBEES (Nifty 50 ETF) from the local candle store.
"""

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
FAST_EMA = 10
SLOW_EMA = 20
INIT_CASH = 1_000_000
FEES = 0.00111              # 0.111% per side (Indian delivery: STT + statutory)
FIXED_FEES = 20             # Rs 20 per order (entry and exit)
ALLOCATION = 0.75
BENCHMARK_SYMBOL = "NIFTYBEES"
BENCHMARK_EXCHANGE = "NSE"

# --- Fetch Data ---
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365 * 3)

print(f"Fetching {SYMBOL} ({EXCHANGE}) {INTERVAL} data from {start_date} to {end_date}")

df = load_candles(SYMBOL, EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))

close = df["close"]
print(f"Data loaded: {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")

# --- Strategy: EMA Crossover (TA-Lib) ---
ema_fast = talib.EMA(close, timeperiod=FAST_EMA)
ema_slow = talib.EMA(close, timeperiod=SLOW_EMA)

buy_raw = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
sell_raw = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))

print(f"Signals - Entries: {entries.sum()}, Exits: {exits.sum()}")

# --- Backtest ---
pf = vbt.Portfolio.from_signals(
    close, entries, exits,
    init_cash=INIT_CASH,
    size=ALLOCATION,
    size_type="percent",
    fees=FEES,
    fixed_fees=FIXED_FEES,
    direction="longonly",
    min_size=1,
    size_granularity=1,
    freq="1D",
)

# --- Benchmark: NIFTYBEES (Nifty 50 ETF) ---
print(f"\nFetching benchmark: {BENCHMARK_SYMBOL} ({BENCHMARK_EXCHANGE})")
df_bench = load_candles(BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))

bench_close = df_bench["close"].reindex(close.index).ffill().bfill()
pf_bench = vbt.Portfolio.from_holding(bench_close, init_cash=INIT_CASH, fees=FEES, freq="1D")

# --- Results ---
print("\n" + "=" * 60)
print(f"  EMA {FAST_EMA}/{SLOW_EMA} Crossover Backtest - {SYMBOL} ({EXCHANGE})")
print("=" * 60)
print(pf.stats())

# --- Strategy vs Benchmark Metrics ---
print("\n--- Strategy vs Benchmark ---")
comparison = pd.DataFrame({
    "Strategy": [
        f"{pf.total_return() * 100:.2f}%",
        f"{pf.sharpe_ratio():.2f}",
        f"{pf.sortino_ratio():.2f}",
        f"{pf.max_drawdown() * 100:.2f}%",
        f"{pf.trades.win_rate() * 100:.1f}%",
        f"{pf.trades.count()}",
        f"{pf.trades.profit_factor():.2f}",
    ],
    f"Benchmark ({BENCHMARK_SYMBOL})": [
        f"{pf_bench.total_return() * 100:.2f}%",
        f"{pf_bench.sharpe_ratio():.2f}",
        f"{pf_bench.sortino_ratio():.2f}",
        f"{pf_bench.max_drawdown() * 100:.2f}%",
        "-",
        "-",
        "-",
    ],
}, index=["Total Return", "Sharpe Ratio", "Sortino Ratio", "Max Drawdown",
          "Win Rate", "Total Trades", "Profit Factor"])
print(comparison.to_string())

# --- Explain Backtest Report ---
print("\n--- Backtest Report Explanation ---")
print(f"* Total Return: Strategy returned {pf.total_return() * 100:.2f}% vs "
      f"benchmark {pf_bench.total_return() * 100:.2f}%")
alpha = pf.total_return() - pf_bench.total_return()
print(f"  -> Alpha (excess return): {alpha * 100:.2f}%")
print(f"* Sharpe Ratio: {pf.sharpe_ratio():.2f} "
      f"({'Good' if pf.sharpe_ratio() > 1 else 'Below 1 - needs improvement'})")
print(f"  -> Measures risk-adjusted return. >1 acceptable, >2 excellent.")
print(f"* Sortino Ratio: {pf.sortino_ratio():.2f} "
      f"({'Good' if pf.sortino_ratio() > 1.5 else 'Moderate'})")
print(f"  -> Like Sharpe but only penalizes downside volatility.")
print(f"* Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
print(f"  -> Worst peak-to-trough decline. Can you stomach this loss?")
print(f"* Win Rate: {pf.trades.win_rate() * 100:.1f}%")
print(f"  -> Percentage of winning trades. EMA crossover typically 35-45%.")
print(f"* Profit Factor: {pf.trades.profit_factor():.2f} "
      f"({'Good' if pf.trades.profit_factor() > 1.5 else 'Marginal' if pf.trades.profit_factor() > 1 else 'Unprofitable'})")
print(f"  -> Gross profit / gross loss. >1.5 is good, >2 is excellent.")
print(f"* Total Trades: {pf.trades.count()}")
print(f"  -> {'Sufficient for statistical significance' if pf.trades.count() >= 30 else 'Too few trades - results unreliable'}")

# --- Plot ---
fig = pf.plot(
    subplots=["value", "underwater", "cum_returns"],
    template="plotly_dark",
    title=f"EMA {FAST_EMA}/{SLOW_EMA} Crossover - {SYMBOL} ({EXCHANGE} {INTERVAL})",
)
fig.show()

# --- Export Trades ---
trades_file = script_dir / f"{SYMBOL}_ema_crossover_trades.csv"
pf.positions.records_readable.to_csv(trades_file, index=False)
print(f"\nTrades exported to {trades_file}")
