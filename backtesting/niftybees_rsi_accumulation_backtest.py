import sys
from datetime import datetime, timedelta, time
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt
import talib
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# market_lib.py sits next to this script (copied by the setup skill)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_lib import load_candles

# --- Config ---
script_dir = Path(__file__).resolve().parent

SYMBOL = "NIFTYBEES"
INDEX_SYMBOL = "NIFTYBEES"
EXCHANGE = "NSE"
INDEX_EXCHANGE = "NSE"
INTERVAL = "D"
INIT_CASH = 10_00_000
FEES = 0.001              # 0.1%
RSI_WINDOW = 14           # Weekly RSI period
RSI_BUY_THRESHOLD = 68    # Buy if weekly RSI < 68
RSI_EXIT_THRESHOLD = 70   # Exit all if weekly RSI > 70

# Slab-wise allocation (% of INIT_CASH per buy)
# RSI 50-68: 5%, RSI 30-50: 10%, RSI <30: 20%
SLAB_ALLOC = {
    (50, 68): 0.05,   # 5% = 50K
    (30, 50): 0.10,   # 10% = 1L
    (0, 30):  0.20,   # 20% = 2L
}
FD_CAGR = 0.0645          # HDFC FD benchmark


def calc_cagr(start_val, end_val, years):
    if start_val <= 0 or end_val <= 0 or years <= 0:
        return 0.0
    return (end_val / start_val) ** (1 / years) - 1


# --- Fetch Data ---
end_date = datetime.now().date()
start_date_intraday = "2019-06-01"
start_date_daily = "2019-06-01"  # Extra warmup for 14-week RSI

print("Fetching data...")

# Daily NIFTYBEES data (for trading; the local store has no intraday NIFTYBEES)
df_trade = load_candles(SYMBOL, EXCHANGE, INTERVAL, start=start_date_intraday, end=str(end_date))
print(f"  NIFTYBEES Daily: {len(df_trade)} bars from {df_trade.index[0]} to {df_trade.index[-1]}")

# Daily NIFTYBEES data again, for the weekly RSI (Nifty 50 index has no daily bars locally)
df_nifty = load_candles(INDEX_SYMBOL, INDEX_EXCHANGE, "D", start=start_date_daily, end=str(end_date))
print(f"  NIFTYBEES Daily: {len(df_nifty)} bars from {df_nifty.index[0]} to {df_nifty.index[-1]}")

# --- Compute Weekly RSI ---
# Resample daily NIFTY to weekly (Friday close)
nifty_weekly_close = df_nifty["close"].resample("W-FRI").last().dropna()

# RSI on weekly closes
rsi_weekly = talib.RSI(nifty_weekly_close, timeperiod=RSI_WINDOW)

# Shift by 1 week: use PREVIOUS week's completed RSI (avoid lookahead)
# At the Friday close, the current week hasn't closed yet,
# so we use last week's RSI for the decision
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
# Forward-fill: each daily bar gets the most recent completed weekly RSI
rsi_mapped = rsi_weekly_prev.reindex(df_trade.index, method="ffill")

close_trade = df_trade["close"]

# --- Identify Friday Bars ---
bar_dow = df_trade.index.dayofweek

is_friday = bar_dow == 4
friday_bars = pd.Series(is_friday, index=df_trade.index)

total_fridays = friday_bars.sum()
print(f"\nTotal Friday close bars found: {total_fridays}")

# --- Build Entry/Exit Signals with Slab-wise Sizing ---
rsi_valid = friday_bars & rsi_mapped.notna()

# Buy condition: Friday close AND RSI < 68
buy_mask = rsi_valid & (rsi_mapped < RSI_BUY_THRESHOLD)

# Exit condition: Friday close AND RSI > 70
exit_mask = rsi_valid & (rsi_mapped > RSI_EXIT_THRESHOLD)

# Size array: default np.inf (for exits = sell all)
size_arr = pd.Series(np.inf, index=close_trade.index)

# Assign slab-wise buy amounts based on RSI level
slab_counts = {"RSI 50-68 (5%)": 0, "RSI 30-50 (10%)": 0, "RSI <30 (20%)": 0}
for dt in close_trade.index[buy_mask]:
    rsi_val = rsi_mapped.loc[dt]
    if rsi_val >= 50:
        size_arr.loc[dt] = INIT_CASH * 0.05   # 5% = 50K
        slab_counts["RSI 50-68 (5%)"] += 1
    elif rsi_val >= 30:
        size_arr.loc[dt] = INIT_CASH * 0.10   # 10% = 1L
        slab_counts["RSI 30-50 (10%)"] += 1
    else:
        size_arr.loc[dt] = INIT_CASH * 0.20   # 20% = 2L
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

# --- Signal Log ---
print("\n--- Weekly Signal Log ---")
for dt in df_trade.index[friday_bars]:
    rsi_val = rsi_mapped.loc[dt]
    if pd.isna(rsi_val):
        continue
    if buy_mask.loc[dt]:
        alloc_pct = size_arr.loc[dt] / INIT_CASH * 100
        action = f"BUY {alloc_pct:.0f}%"
    elif exit_mask.loc[dt]:
        action = "EXIT"
    else:
        action = "HOLD"
    price = close_trade.loc[dt]
    print(f"  {dt.date()} {dt.time()} | RSI: {rsi_val:.2f} | Price: {price:.2f} | {action}")

# --- Backtest ---
# accumulate=True: entries add to position, exits with np.inf close full position
# direction="longonly": prevents short selling on exit when no position exists
pf = vbt.Portfolio.from_signals(
    close=close_trade,
    entries=buy_mask,
    exits=exit_mask,
    size=size_arr,
    size_type="value",
    accumulate=True,
    direction="longonly",
    init_cash=INIT_CASH,
    fees=FEES,
    freq="1D",
    min_size=1,
    size_granularity=1,
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

print(f"\n--- Key Metrics ---")
print(f"Total Return:    {pf.total_return() * 100:.2f}%")
print(f"CAGR:            {cagr_strat * 100:.2f}%")
print(f"Sharpe Ratio:    {pf.sharpe_ratio():.2f}")
print(f"Sortino Ratio:   {pf.sortino_ratio():.2f}")
print(f"Max Drawdown:    {pf.max_drawdown() * 100:.2f}%")
print(f"Final Value:     {equity.iloc[-1]:,.0f}")
print(f"Total Orders:    {pf.orders.count()}")

# --- Benchmarks ---
# NIFTY 50 index over same period
nifty_close_aligned = df_nifty["close"].reindex(
    pd.to_datetime(close_trade.index.date), method="ffill"
)
nifty_start = df_nifty["close"].loc[df_nifty.index >= close_trade.index[0].normalize()].iloc[0]
nifty_end = df_nifty["close"].iloc[-1]
cagr_nifty = calc_cagr(nifty_start, nifty_end, n_years)

# NIFTYBEES buy-and-hold
niftybees_start = close_trade.iloc[0]
niftybees_end = close_trade.iloc[-1]
cagr_niftybees_bh = calc_cagr(niftybees_start, niftybees_end, n_years)
total_ret_bh = (niftybees_end / niftybees_start - 1)

print(f"\n--- CAGR Benchmark Comparison ({n_years:.1f} years) ---")
bench_stats = pd.DataFrame({
    "RSI Accumulation": [
        f"{cagr_strat * 100:.2f}%",
        f"{pf.total_return() * 100:.2f}%",
        f"{pf.sharpe_ratio():.2f}",
        f"{pf.max_drawdown() * 100:.2f}%",
        f"{equity.iloc[-1]:,.0f}",
    ],
    "NIFTYBEES B&H": [
        f"{cagr_niftybees_bh * 100:.2f}%",
        f"{total_ret_bh * 100:.2f}%",
        "-",
        "-",
        "-",
    ],
    "NIFTY 50 Index": [
        f"{cagr_nifty * 100:.2f}%",
        f"{(nifty_end / nifty_start - 1) * 100:.2f}%",
        "-",
        "-",
        "-",
    ],
    f"HDFC FD ({FD_CAGR*100:.2f}%)": [
        f"{FD_CAGR * 100:.2f}%",
        f"{(fd_final / INIT_CASH - 1) * 100:.2f}%",
        "-",
        "0.00%",
        f"{fd_final:,.0f}",
    ],
}, index=["CAGR", "Total Return", "Sharpe Ratio", "Max Drawdown", "Final Value"])
print(bench_stats.to_string())

# --- Plot 1: Equity + Drawdown + RSI ---
# Resample equity to daily for cleaner plotting
equity_daily = equity.resample("D").last().dropna()
running_max = equity_daily.cummax()
drawdown_daily = equity_daily / running_max - 1

# FD equity curve
fd_daily_rate = (1 + FD_CAGR) ** (1 / 365.25) - 1
fd_equity = pd.Series(
    INIT_CASH * (1 + fd_daily_rate) ** np.arange(len(equity_daily)),
    index=equity_daily.index,
)

# NIFTYBEES B&H equity (normalized to same starting capital)
niftybees_daily = close_trade.resample("D").last().dropna()
niftybees_bh_equity = INIT_CASH * (niftybees_daily / niftybees_daily.iloc[0])

fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    row_heights=[0.45, 0.25, 0.30],
    vertical_spacing=0.06,
    subplot_titles=[
        "Portfolio Value: RSI Accumulation vs Benchmarks",
        "Drawdown",
        "NIFTY Weekly RSI (Decision Basis)",
    ],
)

# Row 1: Equity curves
fig.add_trace(go.Scatter(
    x=equity_daily.index, y=equity_daily.values,
    name="RSI Accumulation", line=dict(color="#00d4aa", width=2.5),
), row=1, col=1)
fig.add_trace(go.Scatter(
    x=niftybees_bh_equity.index, y=niftybees_bh_equity.values,
    name="NIFTYBEES B&H", line=dict(color="#4488ff", width=1.5, dash="dot"),
), row=1, col=1)
fig.add_trace(go.Scatter(
    x=fd_equity.index, y=fd_equity.values,
    name=f"HDFC FD {FD_CAGR*100:.2f}%", line=dict(color="#888888", width=1.5, dash="dashdot"),
), row=1, col=1)

# Row 2: Drawdown
fig.add_trace(go.Scatter(
    x=drawdown_daily.index, y=drawdown_daily.values,
    name="Drawdown", fill="tozeroy",
    line=dict(color="#ff4444", width=1),
), row=2, col=1)

# Row 3: Weekly RSI with thresholds
rsi_plot = rsi_weekly.dropna()
rsi_plot = rsi_plot[rsi_plot.index >= close_trade.index[0]]
fig.add_trace(go.Scatter(
    x=rsi_plot.index, y=rsi_plot.values,
    name="Weekly RSI", line=dict(color="#aa88ff", width=1.5),
), row=3, col=1)
fig.add_hline(y=RSI_BUY_THRESHOLD, line_dash="dash", line_color="#00d4aa",
              annotation_text=f"Buy < {RSI_BUY_THRESHOLD}", row=3, col=1)
fig.add_hline(y=RSI_EXIT_THRESHOLD, line_dash="dash", line_color="#ff4444",
              annotation_text=f"Exit > {RSI_EXIT_THRESHOLD}", row=3, col=1)

fig.update_yaxes(tickformat=",", side="right", row=1, col=1)
fig.update_yaxes(tickformat=".1%", side="right", row=2, col=1)
fig.update_yaxes(title_text="RSI", side="right", row=3, col=1)
fig.update_layout(
    template="plotly_dark",
    title=f"RSI Accumulation: Buy NIFTYBEES Fri close (RSI<{RSI_BUY_THRESHOLD}), Exit (RSI>{RSI_EXIT_THRESHOLD})",
    height=850,
    showlegend=True,
    legend=dict(x=0.01, y=0.99),
)
fig.show()

# --- Plot 2: Cash Deployed vs Portfolio Value ---
cash = pf.cash().resample("D").last().dropna()
invested = equity_daily - cash.reindex(equity_daily.index).ffill()

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=equity_daily.index, y=equity_daily.values,
    name="Portfolio Value", line=dict(color="#00d4aa", width=2),
    fill="tonexty", fillcolor="rgba(0,212,170,0.1)",
))
fig2.add_trace(go.Scatter(
    x=invested.index, y=invested.values,
    name="Invested Value", line=dict(color="#4488ff", width=1.5),
))
fig2.add_trace(go.Scatter(
    x=cash.index, y=cash.reindex(equity_daily.index).ffill().values,
    name="Cash", line=dict(color="#ffaa00", width=1.5, dash="dot"),
))
fig2.update_layout(
    template="plotly_dark",
    title="RSI Accumulation: Portfolio Value vs Cash vs Invested",
    xaxis_title="Date",
    yaxis_title="Value (INR)",
    yaxis=dict(tickformat=","),
    height=600,
    showlegend=True,
    legend=dict(x=0.01, y=0.99),
)
fig2.update_yaxes(side="right")
fig2.show()

# --- Export ---
orders_file = script_dir / "niftybees_rsi_accumulation_orders.csv"
pf.orders.records_readable.to_csv(orders_file, index=False)
print(f"\nOrders exported to {orders_file}")
