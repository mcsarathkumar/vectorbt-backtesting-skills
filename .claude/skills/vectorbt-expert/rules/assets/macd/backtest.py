"""
MACD Signal-Candle Breakout Backtest - VectorBT + TA-Lib
Strategy: MACD zero-line defines bull/bear regimes. Entry on breakout of signal candle.
Indicators: TA-Lib MACD + market_lib signal helpers (crossover, flip, exrem).
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
from market_lib import load_candles, exrem, crossover, crossunder, flip

# --- Config ---
script_dir = Path(__file__).resolve().parent

SYMBOL = "SBIN"
EXCHANGE = "NSE"
INTERVAL = "D"
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
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

# --- Strategy: MACD Signal-Candle Breakout (TA-Lib) ---
macd_series, macd_signal_line, macd_hist = talib.MACD(
    close, fastperiod=MACD_FAST, slowperiod=MACD_SLOW, signalperiod=MACD_SIGNAL
)
zero = pd.Series(0.0, index=close.index)

# MACD zero-line flips define regimes
bull_flip = crossover(macd_series, zero)
bear_flip = crossunder(macd_series, zero)

bull_regime = flip(bull_flip, bear_flip)
bear_regime = flip(bear_flip, bull_flip)

# Signal candle levels (capture and carry forward)
sig_high = high.where(bull_flip).ffill()
sig_low = low.where(bear_flip).ffill()

# Entries: price breaks signal candle level during matching regime
long_entry_raw = (crossover(high, sig_high) & bull_regime).fillna(False)

# Only first entry per regime; exit on bear regime flip
entries = exrem(long_entry_raw, bear_flip.fillna(False))
exits = exrem(bear_flip.fillna(False), long_entry_raw)

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

# --- Benchmark: NIFTYBEES ---
print(f"\nFetching benchmark: {BENCHMARK_SYMBOL} ({BENCHMARK_EXCHANGE})")
df_bench = load_candles(BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))

bench_close = df_bench["close"].reindex(close.index).ffill().bfill()
pf_bench = vbt.Portfolio.from_holding(bench_close, init_cash=INIT_CASH, fees=FEES, freq="1D")

# --- Results ---
print("\n" + "=" * 60)
print(f"  MACD Signal-Candle Breakout - {SYMBOL} ({EXCHANGE})")
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
print(f"* Total Return: Your strategy made {pf.total_return() * 100:.2f}% "
      f"while NIFTY 50 made {pf_bench.total_return() * 100:.2f}%")
alpha = pf.total_return() - pf_bench.total_return()
if alpha > 0:
    print(f"  -> Your strategy BEAT the market by {alpha * 100:.2f}% (positive alpha)")
else:
    print(f"  -> Your strategy UNDERPERFORMED the market by {abs(alpha) * 100:.2f}%")
print(f"* Sharpe Ratio: {pf.sharpe_ratio():.2f}")
print(f"  -> This measures return per unit of risk. Think of it as 'bang for your buck'.")
print(f"     Below 1 = not enough return for the risk taken")
print(f"     1-2 = decent, 2+ = very good")
print(f"* Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
print(f"  -> The biggest drop from peak. If you invested 10L, you would have temporarily")
print(f"     lost up to Rs {abs(pf.max_drawdown()) * INIT_CASH:,.0f} before recovering.")
print(f"* Win Rate: {pf.trades.win_rate() * 100:.1f}% of trades were profitable")
print(f"* Profit Factor: {pf.trades.profit_factor():.2f}")
print(f"  -> For every Rs 1 lost, you made Rs {pf.trades.profit_factor():.2f} in profits.")

# --- Plot ---
fig = pf.plot(
    subplots=["value", "underwater", "cum_returns"],
    template="plotly_dark",
    title=f"MACD Signal-Candle Breakout - {SYMBOL} ({EXCHANGE} {INTERVAL})",
)
fig.show()

# --- Export ---
trades_file = script_dir / f"{SYMBOL}_macd_trades.csv"
pf.positions.records_readable.to_csv(trades_file, index=False)
print(f"\nTrades exported to {trades_file}")
