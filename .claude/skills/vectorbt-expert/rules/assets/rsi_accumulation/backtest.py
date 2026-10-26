"""
RSI Accumulation Backtest - VectorBT + TA-Lib
Strategy: Weekly RSI-based slab-wise accumulation of NIFTYBEES.
          Buy at the Friday close when the previous week's NIFTYBEES weekly RSI < 68.
          (The local store holds NIFTYBEES daily only, so trades use Friday daily bars.)
          Slab allocation: RSI 50-68 = 5%, RSI 30-50 = 10%, RSI <30 = 20%.
          Exit all when weekly RSI > 70.
Indicators: TA-Lib RSI.
Fees: Indian delivery equity model (0.111% + Rs 20/order).
Benchmark: NIFTYBEES (Nifty 50 ETF) from the local candle store.
"""

import sys
from datetime import datetime, timedelta, time
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt
import talib
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# market_lib.py lives in backtesting/ (copied by the setup skill)
for _p in Path(__file__).resolve().parents:
    if (_p / "market_lib.py").exists():
        sys.path.insert(0, str(_p))
        break
from market_lib import load_candles

# --- Config ---
script_dir = Path(__file__).resolve().parent

SYMBOL = "NIFTYBEES"
INDEX_SYMBOL = "NIFTYBEES"
EXCHANGE = "NSE"
INDEX_EXCHANGE = "NSE"
INTERVAL = "D"
INIT_CASH = 10_00_000
FEES = 0.00111              # Indian delivery equity
FIXED_FEES = 20             # Rs 20 per order
RSI_WINDOW = 14             # Weekly RSI period
RSI_BUY_THRESHOLD = 68      # Buy if weekly RSI < 68
RSI_EXIT_THRESHOLD = 70     # Exit all if weekly RSI > 70
FD_CAGR = 0.0645            # HDFC FD benchmark
BENCHMARK_SYMBOL = "NIFTYBEES"
BENCHMARK_EXCHANGE = "NSE"


def calc_cagr(start_val, end_val, years):
    if start_val <= 0 or end_val <= 0 or years <= 0:
        return 0.0
    return (end_val / start_val) ** (1 / years) - 1


# --- Fetch Data ---
end_date = datetime.now().date()
start_date_intraday = "2019-06-01"
start_date_daily = "2019-06-01"  # Extra warmup for 14-week RSI

print("Fetching data...")

# Daily NIFTYBEES data (for trading)
df_trade = load_candles(SYMBOL, EXCHANGE, INTERVAL, start=start_date_intraday, end=str(end_date))
print(f"  NIFTYBEES Daily: {len(df_trade)} bars from {df_trade.index[0]} to {df_trade.index[-1]}")

# Daily NIFTYBEES data again, for the weekly RSI (Nifty 50 index has no daily bars locally)
df_nifty = load_candles(INDEX_SYMBOL, INDEX_EXCHANGE, "D", start=start_date_daily, end=str(end_date))
print(f"  NIFTY Daily:   {len(df_nifty)} bars from {df_nifty.index[0]} to {df_nifty.index[-1]}")

# --- Compute Weekly RSI (TA-Lib) ---
nifty_weekly_close = df_nifty["close"].resample("W-FRI").last().dropna()
rsi_weekly = talib.RSI(nifty_weekly_close, timeperiod=RSI_WINDOW)

# Shift by 1 week: use PREVIOUS week's completed RSI (avoid lookahead)
rsi_weekly_prev = rsi_weekly.shift(1)

print(f"\n--- Weekly RSI (last 10 weeks) ---")
recent_rsi = rsi_weekly.dropna().tail(10)
for dt, val in recent_rsi.items():
    marker = ""
    if val < RSI_BUY_THRESHOLD:
        marker = " [BUY ZONE]"
    elif val > RSI_EXIT_THRESHOLD:
        marker = " [EXIT ZONE]"
    print(f"  {dt.date()}: RSI = {val:.2f}{marker}")

# --- Map Weekly RSI to Daily Bars ---
rsi_mapped = rsi_weekly_prev.reindex(df_trade.index, method="ffill")
close_trade = df_trade["close"]

# --- Identify Friday Bars ---
bar_dow = df_trade.index.dayofweek
is_friday = bar_dow == 4
friday_bars = pd.Series(is_friday, index=df_trade.index)

total_fridays = friday_bars.sum()
print(f"\nTotal Friday bars found: {total_fridays}")

# --- Build Entry/Exit Signals with Slab-wise Sizing ---
rsi_valid = friday_bars & rsi_mapped.notna()
buy_mask = rsi_valid & (rsi_mapped < RSI_BUY_THRESHOLD)
exit_mask = rsi_valid & (rsi_mapped > RSI_EXIT_THRESHOLD)

size_arr = pd.Series(np.inf, index=close_trade.index)

slab_counts = {"RSI 50-68 (5%)": 0, "RSI 30-50 (10%)": 0, "RSI <30 (20%)": 0}
for dt in close_trade.index[buy_mask]:
    rsi_val = rsi_mapped.loc[dt]
    if rsi_val >= 50:
        size_arr.loc[dt] = INIT_CASH * 0.05
        slab_counts["RSI 50-68 (5%)"] += 1
    elif rsi_val >= 30:
        size_arr.loc[dt] = INIT_CASH * 0.10
        slab_counts["RSI 30-50 (10%)"] += 1
    else:
        size_arr.loc[dt] = INIT_CASH * 0.20
        slab_counts["RSI <30 (20%)"] += 1

buy_count = buy_mask.sum()
exit_count = exit_mask.sum()
no_action = friday_bars.sum() - buy_count - exit_count
print(f"Buy signals (RSI < {RSI_BUY_THRESHOLD}):    {buy_count}")
print(f"Exit signals (RSI > {RSI_EXIT_THRESHOLD}):   {exit_count}")
print(f"No action (RSI {RSI_BUY_THRESHOLD}-{RSI_EXIT_THRESHOLD}): {no_action}")
print(f"\n--- Slab-wise Buy Breakdown ---")
for slab, count in slab_counts.items():
    print(f"  {slab}: {count} buys")

# --- Backtest ---
pf = vbt.Portfolio.from_signals(
    close=close_trade, entries=buy_mask, exits=exit_mask,
    size=size_arr, size_type="value", accumulate=True,
    direction="longonly", init_cash=INIT_CASH,
    fees=FEES, fixed_fees=FIXED_FEES,
    freq="1D", min_size=1, size_granularity=1,
)

# --- Results ---
print("\n" + "=" * 60)
print("  RSI Accumulation Strategy - NIFTYBEES (Slab-wise)")
print(f"  RSI 50-68: 5% | RSI 30-50: 10% | RSI <30: 20%")
print(f"  Exit all if RSI > {RSI_EXIT_THRESHOLD}")
print("=" * 60)
print(pf.stats())

equity = pf.value()
n_days = (close_trade.index[-1] - close_trade.index[0]).days
n_years = n_days / 365.25
cagr_strat = calc_cagr(INIT_CASH, equity.iloc[-1], n_years)
fd_final = INIT_CASH * (1 + FD_CAGR) ** n_years

# --- Benchmark ---
nifty_start = df_nifty["close"].loc[df_nifty.index >= close_trade.index[0].normalize()].iloc[0]
nifty_end = df_nifty["close"].iloc[-1]
cagr_nifty = calc_cagr(nifty_start, nifty_end, n_years)

niftybees_start = close_trade.iloc[0]
niftybees_end = close_trade.iloc[-1]
cagr_niftybees_bh = calc_cagr(niftybees_start, niftybees_end, n_years)
total_ret_bh = niftybees_end / niftybees_start - 1

# --- Strategy vs Benchmark ---
print("\n--- Strategy vs Benchmark ---")
comparison = pd.DataFrame({
    "RSI Accumulation": [
        f"{pf.total_return() * 100:.2f}%",
        f"{cagr_strat * 100:.2f}%",
        f"{pf.sharpe_ratio():.2f}",
        f"{pf.sortino_ratio():.2f}",
        f"{pf.max_drawdown() * 100:.2f}%",
        f"Rs {equity.iloc[-1]:,.0f}",
    ],
    f"Benchmark ({BENCHMARK_SYMBOL})": [
        f"{(nifty_end / nifty_start - 1) * 100:.2f}%",
        f"{cagr_nifty * 100:.2f}%",
        "-", "-", "-", "-",
    ],
    "NIFTYBEES B&H": [
        f"{total_ret_bh * 100:.2f}%",
        f"{cagr_niftybees_bh * 100:.2f}%",
        "-", "-", "-", "-",
    ],
    f"HDFC FD ({FD_CAGR*100:.2f}%)": [
        f"{(fd_final / INIT_CASH - 1) * 100:.2f}%",
        f"{FD_CAGR * 100:.2f}%",
        "-", "-", "0.00%",
        f"Rs {fd_final:,.0f}",
    ],
}, index=["Total Return", "CAGR", "Sharpe Ratio", "Sortino Ratio",
          "Max Drawdown", "Final Value"])
print(comparison.to_string())

# --- Explain ---
print("\n--- Backtest Report Explanation ---")
print(f"* Total Return: Your strategy made {pf.total_return() * 100:.2f}%")
print(f"  while NIFTY 50 made {(nifty_end / nifty_start - 1) * 100:.2f}%")
alpha = pf.total_return() - (nifty_end / nifty_start - 1)
if alpha > 0:
    print(f"  -> BEAT the market by {alpha * 100:.2f}%")
else:
    print(f"  -> UNDERPERFORMED by {abs(alpha) * 100:.2f}%")
print(f"* CAGR: {cagr_strat * 100:.2f}% annualized vs FD at {FD_CAGR * 100:.2f}%")
print(f"* Max Drawdown: {pf.max_drawdown() * 100:.2f}% - the biggest drop from peak")
print(f"  -> On Rs {INIT_CASH:,} capital, the worst temporary loss = Rs {abs(pf.max_drawdown()) * INIT_CASH:,.0f}")
print(f"* This is a SYSTEMATIC ACCUMULATION strategy")
print(f"  -> Buys more when market is fearful (low RSI) and less when greedy (high RSI)")
print(f"  -> Exits everything when RSI signals extreme overbought conditions")
print(f"* Total buy signals: {buy_count}, Exit signals: {exit_count}")

# --- Plot ---
equity_daily = equity.resample("D").last().dropna()
running_max = equity_daily.cummax()
drawdown_daily = equity_daily / running_max - 1

fd_daily_rate = (1 + FD_CAGR) ** (1 / 365.25) - 1
fd_equity = pd.Series(
    INIT_CASH * (1 + fd_daily_rate) ** np.arange(len(equity_daily)),
    index=equity_daily.index,
)

niftybees_daily = close_trade.resample("D").last().dropna()
niftybees_bh_equity = INIT_CASH * (niftybees_daily / niftybees_daily.iloc[0])

rsi_plot = rsi_weekly.dropna()
rsi_plot = rsi_plot[rsi_plot.index >= close_trade.index[0]]

fig = make_subplots(
    rows=3, cols=1, shared_xaxes=True,
    row_heights=[0.45, 0.25, 0.30], vertical_spacing=0.06,
    subplot_titles=[
        "Portfolio Value: RSI Accumulation vs Benchmarks",
        "Drawdown",
        "NIFTY Weekly RSI (Decision Basis)",
    ],
)

fig.add_trace(go.Scatter(x=equity_daily.index, y=equity_daily.values,
    name="RSI Accumulation", line=dict(color="#00d4aa", width=2.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=niftybees_bh_equity.index, y=niftybees_bh_equity.values,
    name="NIFTYBEES B&H", line=dict(color="#4488ff", width=1.5, dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=fd_equity.index, y=fd_equity.values,
    name=f"HDFC FD {FD_CAGR*100:.2f}%", line=dict(color="#888888", width=1.5, dash="dashdot")), row=1, col=1)

fig.add_trace(go.Scatter(x=drawdown_daily.index, y=drawdown_daily.values,
    name="Drawdown", fill="tozeroy", line=dict(color="#ff4444", width=1)), row=2, col=1)

fig.add_trace(go.Scatter(x=rsi_plot.index, y=rsi_plot.values,
    name="Weekly RSI", line=dict(color="#aa88ff", width=1.5)), row=3, col=1)
fig.add_hline(y=RSI_BUY_THRESHOLD, line_dash="dash", line_color="#00d4aa",
              annotation_text=f"Buy < {RSI_BUY_THRESHOLD}", row=3, col=1)
fig.add_hline(y=RSI_EXIT_THRESHOLD, line_dash="dash", line_color="#ff4444",
              annotation_text=f"Exit > {RSI_EXIT_THRESHOLD}", row=3, col=1)

fig.update_yaxes(tickformat=",", side="right", row=1, col=1)
fig.update_yaxes(tickformat=".1%", side="right", row=2, col=1)
fig.update_yaxes(title_text="RSI", side="right", row=3, col=1)
fig.update_layout(template="plotly_dark",
    title=f"RSI Accumulation: Buy NIFTYBEES Fri 3:15 PM (RSI<{RSI_BUY_THRESHOLD}), Exit (RSI>{RSI_EXIT_THRESHOLD})",
    height=850)
fig.show()

# --- Export ---
orders_file = script_dir / "niftybees_rsi_accumulation_orders.csv"
pf.orders.records_readable.to_csv(orders_file, index=False)
print(f"\nOrders exported to {orders_file}")
