"""
RSI Backtest - VectorBT + TA-Lib
Strategy: Buy when RSI crosses below oversold, sell when RSI crosses above overbought.
Indicators: TA-Lib RSI.
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
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
INIT_CASH = 1_000_000
FEES = 0.00111              # Indian delivery equity
FIXED_FEES = 20             # Rs 20 per order
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

# --- Strategy: RSI (TA-Lib) ---
rsi = talib.RSI(close, timeperiod=RSI_PERIOD)

buy_raw = (rsi < RSI_OVERSOLD) & (rsi.shift(1) >= RSI_OVERSOLD)
sell_raw = (rsi > RSI_OVERBOUGHT) & (rsi.shift(1) <= RSI_OVERBOUGHT)

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
print(f"  RSI({RSI_PERIOD}) Backtest - {SYMBOL} ({EXCHANGE})")
print(f"  Oversold: {RSI_OVERSOLD} | Overbought: {RSI_OVERBOUGHT}")
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
print(f"* Total Return: Strategy returned {pf.total_return() * 100:.2f}% vs "
      f"benchmark {pf_bench.total_return() * 100:.2f}%")
alpha = pf.total_return() - pf_bench.total_return()
print(f"  -> Alpha (excess return): {alpha * 100:.2f}%")
print(f"* Sharpe Ratio: {pf.sharpe_ratio():.2f} "
      f"({'Good' if pf.sharpe_ratio() > 1 else 'Below 1 - needs improvement'})")
print(f"  -> Measures risk-adjusted return. >1 acceptable, >2 excellent.")
print(f"* Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
print(f"  -> Worst peak-to-trough decline. RSI strategies tend to have lower drawdowns.")
print(f"* Win Rate: {pf.trades.win_rate() * 100:.1f}%")
print(f"  -> RSI strategies typically have higher win rates (50-65%) but smaller gains.")
print(f"* Profit Factor: {pf.trades.profit_factor():.2f} "
      f"({'Good' if pf.trades.profit_factor() > 1.5 else 'Marginal' if pf.trades.profit_factor() > 1 else 'Unprofitable'})")
print(f"* Total Trades: {pf.trades.count()}")
print(f"  -> {'Sufficient' if pf.trades.count() >= 30 else 'Too few trades - results unreliable'}")

# --- Plot ---
fig = pf.plot(
    subplots=["value", "underwater", "cum_returns"],
    template="plotly_dark",
    title=f"RSI({RSI_PERIOD}) Strategy - {SYMBOL} ({EXCHANGE} {INTERVAL})",
)
fig.show()

# --- Export ---
trades_file = script_dir / f"{SYMBOL}_rsi_trades.csv"
pf.positions.records_readable.to_csv(trades_file, index=False)
print(f"\nTrades exported to {trades_file}")
