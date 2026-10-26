"""
Donchian Channel Breakout Backtest - VectorBT + TA-Lib
Strategy: Buy when price breaks above N-period high, sell when breaks below N-period low.
Indicators: rolling Donchian channel from market_lib (shifted by 1 to avoid lookahead).
Fees: Indian delivery equity model (0.111% + Rs 20/order).
Benchmark: NIFTYBEES (Nifty 50 ETF) from the local candle store.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

# market_lib.py lives in backtesting/ (copied by the setup skill)
for _p in Path(__file__).resolve().parents:
    if (_p / "market_lib.py").exists():
        sys.path.insert(0, str(_p))
        break
from market_lib import load_candles, exrem, crossover, crossunder, donchian

# --- Config ---
script_dir = Path(__file__).resolve().parent

SYMBOL = "SBIN"
EXCHANGE = "NSE"
INTERVAL = "D"
DONCHIAN_PERIOD = 20
INIT_CASH = 1_000_000
FEES = 0.00111
FIXED_FEES = 20
ALLOCATION = 0.75
BENCHMARK_SYMBOL = "NIFTYBEES"
BENCHMARK_EXCHANGE = "NSE"

# --- Fetch Data ---
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365 * 3)

print(f"Fetching {SYMBOL} ({EXCHANGE}) {INTERVAL} data from {start_date} to {end_date}")

df = load_candles(SYMBOL, EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))

close = df["close"]
high = df["high"]
low = df["low"]
print(f"Data loaded: {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")

# --- Strategy: Donchian Channel Breakout ---
upper, middle, lower = donchian(high, low, period=DONCHIAN_PERIOD)

# Shift by 1 to avoid lookahead bias
upper_shifted = upper.shift(1)
lower_shifted = lower.shift(1)

buy_raw = crossover(close, upper_shifted).fillna(False)
sell_raw = crossunder(close, lower_shifted).fillna(False)

entries = exrem(buy_raw, sell_raw)
exits = exrem(sell_raw, buy_raw)

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
print(f"  Donchian({DONCHIAN_PERIOD}) Channel Breakout - {SYMBOL} ({EXCHANGE})")
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
        "-", "-", "-",
    ],
}, index=["Total Return", "Sharpe Ratio", "Sortino Ratio", "Max Drawdown",
          "Win Rate", "Total Trades", "Profit Factor"])
print(comparison.to_string())

# --- Explain Backtest Report ---
print("\n--- Backtest Report Explanation ---")
print(f"* Total Return: {pf.total_return() * 100:.2f}% vs benchmark {pf_bench.total_return() * 100:.2f}%")
alpha = pf.total_return() - pf_bench.total_return()
print(f"  -> Alpha: {alpha * 100:.2f}%")
print(f"* Sharpe Ratio: {pf.sharpe_ratio():.2f} - risk-adjusted return (>1 good, >2 excellent)")
print(f"* Max Drawdown: {pf.max_drawdown() * 100:.2f}% - worst peak-to-trough decline")
print(f"* Win Rate: {pf.trades.win_rate() * 100:.1f}% - Donchian breakout typically 30-40% (trend-following)")
print(f"* Profit Factor: {pf.trades.profit_factor():.2f} - gross profit / gross loss (>1.5 good)")
print(f"* Total Trades: {pf.trades.count()} - "
      f"{'sufficient' if pf.trades.count() >= 30 else 'too few for statistical significance'}")

# --- Plot ---
fig = pf.plot(
    subplots=["value", "underwater", "cum_returns"],
    template="plotly_dark",
    title=f"Donchian({DONCHIAN_PERIOD}) Breakout - {SYMBOL} ({EXCHANGE} {INTERVAL})",
)
fig.show()

# --- Export ---
trades_file = script_dir / f"{SYMBOL}_donchian_trades.csv"
pf.positions.records_readable.to_csv(trades_file, index=False)
print(f"\nTrades exported to {trades_file}")
