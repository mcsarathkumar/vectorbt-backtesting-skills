"""
Realistic Transaction Cost Analysis Template - VectorBT + TA-Lib
Compares strategy performance across different cost models:
  1. Zero fees (unrealistic upper bound)
  2. Simplified flat fee
  3. Indian delivery equity (realistic)
  4. Indian intraday equity
  5. Indian F&O futures
Shows the real impact of transaction costs on strategy profitability.
Indicators: TA-Lib EMA.
Benchmark: NIFTYBEES (Nifty 50 ETF) from the local candle store.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt
import talib
import plotly.graph_objects as go

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
ALLOCATION = 0.75
BENCHMARK_SYMBOL = "NIFTYBEES"
BENCHMARK_EXCHANGE = "NSE"

# --- Indian Market Fee Models ---
FEE_MODELS = {
    "Zero Fees (Unrealistic)": {
        "fees": 0, "fixed_fees": 0, "slippage": 0,
    },
    "Simplified 0.1%": {
        "fees": 0.001, "fixed_fees": 0, "slippage": 0,
    },
    "Delivery Equity": {
        "fees": 0.00111,       # 0.111% (STT 0.1% both + statutory)
        "fixed_fees": 20,      # Rs 20 per order
        "slippage": 0.0005,    # 0.05% slippage
    },
    "Intraday Equity": {
        "fees": 0.000225,      # 0.0225% (STT 0.025% sell + statutory)
        "fixed_fees": 20,      # Rs 20 per order
        "slippage": 0.0005,
    },
    "F&O Futures": {
        "fees": 0.00018,       # 0.018% (STT 0.02% sell + statutory)
        "fixed_fees": 20,
        "slippage": 0.0002,    # Lower slippage for liquid futures
    },
}

# --- Fetch Data ---
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365 * 3)

df = load_candles(SYMBOL, EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))

close = df["close"]

# --- Generate Signals (TA-Lib EMA) ---
ema_fast = talib.EMA(close, timeperiod=FAST_EMA)
ema_slow = talib.EMA(close, timeperiod=SLOW_EMA)

buy_raw = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
sell_raw = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
exits = exrem(sell_raw.fillna(False), buy_raw.fillna(False))

# --- Benchmark ---
df_bench = load_candles(BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE, INTERVAL, start=str(start_date), end=str(end_date))
bench_close = df_bench["close"].reindex(close.index).ffill().bfill()

# --- Run Backtest for Each Fee Model ---
results = {}
portfolios = {}

for model_name, params in FEE_MODELS.items():
    pf = vbt.Portfolio.from_signals(
        close, entries, exits,
        init_cash=INIT_CASH,
        size=ALLOCATION,
        size_type="percent",
        fees=params["fees"],
        fixed_fees=params["fixed_fees"],
        slippage=params.get("slippage", 0),
        direction="longonly",
        min_size=1,
        size_granularity=1,
        freq="1D",
    )
    portfolios[model_name] = pf
    results[model_name] = {
        "Total Return": f"{pf.total_return() * 100:.2f}%",
        "Sharpe Ratio": f"{pf.sharpe_ratio():.2f}",
        "Max Drawdown": f"{pf.max_drawdown() * 100:.2f}%",
        "Win Rate": f"{pf.trades.win_rate() * 100:.1f}%",
        "Total Trades": str(pf.trades.count()),
        "Profit Factor": f"{pf.trades.profit_factor():.2f}",
        "Total Fees Paid": f"Rs {pf.orders.records['fees'].sum():,.0f}",
    }

# Add benchmark
pf_bench = vbt.Portfolio.from_holding(bench_close, init_cash=INIT_CASH, freq="1D")
results[f"Benchmark ({BENCHMARK_SYMBOL})"] = {
    "Total Return": f"{pf_bench.total_return() * 100:.2f}%",
    "Sharpe Ratio": f"{pf_bench.sharpe_ratio():.2f}",
    "Max Drawdown": f"{pf_bench.max_drawdown() * 100:.2f}%",
    "Win Rate": "-",
    "Total Trades": "-",
    "Profit Factor": "-",
    "Total Fees Paid": "-",
}

# --- Print Results ---
print("\n" + "=" * 80)
print(f"  Transaction Cost Impact Analysis - EMA {FAST_EMA}/{SLOW_EMA} on {SYMBOL}")
print("=" * 80)
results_df = pd.DataFrame(results)
print(results_df.to_string())

# --- Explain for Traders ---
zero_return = portfolios["Zero Fees (Unrealistic)"].total_return()
delivery_return = portfolios["Delivery Equity"].total_return()
cost_drag = zero_return - delivery_return

print("\n--- What This Means for You ---")
print(f"* With zero fees, this strategy returns {zero_return * 100:.2f}%")
print(f"* With realistic delivery fees, it returns {delivery_return * 100:.2f}%")
print(f"* Transaction costs eat {cost_drag * 100:.2f}% of your returns")
print(f"  -> That is Rs {cost_drag * INIT_CASH:,.0f} lost to fees on Rs {INIT_CASH:,} capital")

if delivery_return > 0:
    print(f"\n* Strategy is STILL PROFITABLE after realistic costs")
else:
    print(f"\n* Strategy becomes UNPROFITABLE with realistic costs!")
    print(f"  -> The edge is not large enough to overcome transaction costs")
    print(f"  -> Consider: fewer trades, higher timeframe, or a different strategy")

# --- Plot: Equity Curves for All Fee Models ---
fig = go.Figure()
for model_name, pf in portfolios.items():
    equity = pf.value()
    cum_ret = equity / equity.iloc[0] - 1
    fig.add_trace(go.Scatter(
        x=cum_ret.index, y=cum_ret * 100,
        name=model_name, mode='lines',
    ))

# Add benchmark
bench_cum = bench_close / bench_close.iloc[0] - 1
fig.add_trace(go.Scatter(
    x=bench_cum.index, y=bench_cum * 100,
    name=f"Benchmark ({BENCHMARK_SYMBOL})", mode='lines',
    line=dict(dash='dash', color='gray'),
))

fig.update_layout(
    template="plotly_dark",
    title=f"Impact of Transaction Costs - EMA {FAST_EMA}/{SLOW_EMA} on {SYMBOL}",
    xaxis_title="Date",
    yaxis_title="Cumulative Return (%)",
    yaxis=dict(ticksuffix="%"),
    height=600,
    legend=dict(x=0.01, y=0.99),
)
fig.update_yaxes(side="right")
fig.show()

# --- Export ---
export_file = script_dir / f"{SYMBOL}_cost_analysis.csv"
results_df.to_csv(export_file)
print(f"\nResults exported to {export_file}")
