"""
SDA2 Trend Following Backtest - VectorBT + TA-Lib
Strategy: WMA-based channel with STDDEV and ATR bands.
Indicators: TA-Lib WMA, STDDEV, ATR.
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
INIT_CASH = 1_000_000
FEES = 0.00111
FIXED_FEES = 20
ALLOCATION = 0.75
BENCHMARK_SYMBOL = "NIFTYBEES"
BENCHMARK_EXCHANGE = "NSE"

# --- Fetch Data ---
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365 * 3)

df = load_candles(SYMBOL, EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))

close = df["close"]
high = df["high"]
low = df["low"]
open_price = df["open"]

# --- Strategy: SDA2 Trend Following (TA-Lib) ---
base = ((high + low) / 2.0) + (open_price - close)
derived = talib.WMA(base, timeperiod=3)

sd7 = talib.STDDEV(derived, timeperiod=7)
atr2 = talib.ATR(high, low, close, timeperiod=2)

upper = derived + sd7 + (atr2 / 1.5)
lower = derived - sd7 - (atr2 / 1.0)

buy_raw = (close > upper) & (close.shift(1) <= upper.shift(1))
sell_raw = (lower > close) & (lower.shift(1) <= close.shift(1))

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), entries)

# --- Backtest ---
pf = vbt.Portfolio.from_signals(
    close, entries, exits,
    init_cash=INIT_CASH, size=ALLOCATION, size_type="percent",
    fees=FEES, fixed_fees=FIXED_FEES, direction="longonly",
    min_size=1, size_granularity=1, freq="1D",
)

# --- Benchmark ---
df_bench = load_candles(BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))
bench_close = df_bench["close"].reindex(close.index).ffill().bfill()
pf_bench = vbt.Portfolio.from_holding(bench_close, init_cash=INIT_CASH, fees=FEES, freq="1D")

# --- Results ---
print("\n" + "=" * 60)
print(f"  SDA2 Trend Following - {SYMBOL} ({EXCHANGE})")
print("=" * 60)
print(pf.stats())

print("\n--- Strategy vs Benchmark ---")
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

print("\n--- Backtest Report Explanation ---")
print(f"* Total Return: Your strategy made {pf.total_return() * 100:.2f}% "
      f"while NIFTY 50 made {pf_bench.total_return() * 100:.2f}%")
alpha = pf.total_return() - pf_bench.total_return()
if alpha > 0:
    print(f"  -> BEAT the market by {alpha * 100:.2f}%")
else:
    print(f"  -> UNDERPERFORMED the market by {abs(alpha) * 100:.2f}%")
print(f"* Sharpe Ratio: {pf.sharpe_ratio():.2f} (return per unit of risk, >1 decent, >2 excellent)")
print(f"* Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
print(f"  -> If you invested Rs {INIT_CASH:,}, the biggest temporary loss = Rs {abs(pf.max_drawdown()) * INIT_CASH:,.0f}")
print(f"* Win Rate: {pf.trades.win_rate() * 100:.1f}% - SDA2 is trend-following, expect 35-45%")
print(f"* Profit Factor: {pf.trades.profit_factor():.2f} - for every Rs 1 lost, you made Rs {pf.trades.profit_factor():.2f}")

fig = pf.plot(
    subplots=["value", "underwater", "cum_returns"],
    template="plotly_dark",
    title=f"SDA2 Trend Following - {SYMBOL} ({EXCHANGE} {INTERVAL})",
)
fig.show()

trades_file = script_dir / f"{SYMBOL}_sda2_trades.csv"
pf.positions.records_readable.to_csv(trades_file, index=False)
print(f"\nTrades exported to {trades_file}")
