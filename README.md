# VectorBT Backtesting Skills for Agentic Coding Tools

A comprehensive collection of backtesting skills for trading strategies using VectorBT. Works with **40+ AI coding agents** via [skills.sh](https://github.com/vercel-labs/skills) — including Claude Code, Cursor, Codex, OpenCode, Cline, Windsurf, GitHub Copilot, Gemini CLI, Roo Code, and more.

Supports **Indian markets**, **US markets**, and **Crypto markets** with realistic transaction cost modeling, TA-Lib indicators (pandas-ta / vectorbt indicators when needed), market-specific benchmarking, OpenStatz tearsheets, and robustness testing. Broker-neutral by design — fee models use industry-standard references that can be customized for any broker.

## Quick Install

Install the skills into your project using [npx skills](https://github.com/vercel-labs/skills). The CLI auto-detects your AI coding agent and installs skills to the correct directory.

```bash
# GitHub shorthand
npx skills add mcsarathkumar/vectorbt-backtesting-skills

# Full GitHub URL
npx skills add https://github.com/mcsarathkumar/vectorbt-backtesting-skills
```

Install a specific skill only:

```bash
npx skills add mcsarathkumar/vectorbt-backtesting-skills -s backtest
npx skills add mcsarathkumar/vectorbt-backtesting-skills -s optimize
npx skills add mcsarathkumar/vectorbt-backtesting-skills -s vectorbt-expert
npx skills add mcsarathkumar/vectorbt-backtesting-skills -s setup
```

`setup` copies `market_lib.py` from the `vectorbt-expert` skill, so install both together (or install everything, as in the first command). Indian-market data is read from a local candle folder - set `CANDLES_DIR` in `.env` if yours is not at `/Users/mcsarathkumar/Workspace/indian-market-data/data/candles`.

List available skills before installing:

```bash
npx skills add mcsarathkumar/vectorbt-backtesting-skills -l
```

Install globally (available across all projects):

```bash
npx skills add mcsarathkumar/vectorbt-backtesting-skills -g
```

### Supported AI Coding Agents

Skills are installed via [skills.sh](https://github.com/vercel-labs/skills) which supports 40+ agents. Each agent reads skills from its own directory (project-level; `-g` installs to the same folder under your home directory):

| Agent | Skills Directory |
|-------|-----------------|
| Claude Code | `.claude/skills/` |
| Cursor | `.agents/skills/` |
| Codex | `.agents/skills/` |
| OpenCode | `.agents/skills/` |
| Cline | `.agents/skills/` |
| Windsurf | `.agents/skills/` |
| GitHub Copilot | `.agents/skills/` |
| Gemini CLI | `.agents/skills/` |
| Roo Code | `.agents/skills/` |
| + 30 more | Auto-detected by `npx skills` |

The `npx skills add` command detects which agents you have installed and places the skill files in the correct paths automatically.

## Supported Markets

| Market | Data Source | Fee Reference | Default Benchmark |
|--------|------------|---------------|-------------------|
| **India** | Local Parquet candles (NSE, BSE, F&O) | Delivery, Intraday, F&O (4-segment) | NIFTYBEES (Nifty 50 ETF) |
| **US** | yfinance (NYSE, NASDAQ) | Stocks, Options, Futures (per-share + per-contract) | S&P 500 |
| **Crypto** | yfinance / CCXT | Spot, Perpetual Futures (maker/taker) | Bitcoin |
| **Custom** | Any provider via extensible pattern | User-defined | User-defined |

> **Broker-neutral**: Fee models use realistic industry-standard defaults and can be adjusted for any broker by changing the `fees` and `fixed_fees` constants.

## Capabilities

### Skills (User-Invocable Commands)

| Command | What It Does |
|---------|-------------|
| `/setup` | Detects OS, creates venv, installs TA-Lib + all packages, creates `backtesting/` with `market_lib.py`, points `.env` at the candle store |
| `/backtest` | Generates a complete backtest script with signals, market-specific fees, benchmark comparison, plain-language report, OpenStatz tearsheet |
| `/optimize` | Parameter grid search with TA-Lib indicators, tqdm progress bars, Plotly heatmaps, best params vs benchmark |
| `/quick-stats` | Inline code block (no file) — fetch data, run EMA crossover, print compact stats + benchmark alpha |
| `/strategy-compare` | Side-by-side comparison of multiple strategies on same symbol, overlaid equity curves |

### Pre-Built Strategy Templates (12)

| Strategy | Type | Description |
|----------|------|-------------|
| EMA Crossover | Trend | EMA 10/20 crossover |
| RSI | Mean-reversion | RSI(14) oversold/overbought |
| Donchian Channel | Breakout | Channel breakout with shifted levels (no lookahead) |
| Supertrend | Trend | Supertrend with intraday session windows (9:30-15:00, exit 15:15) |
| MACD | Trend + Breakout | MACD zero-line regime + signal-candle breakout |
| SDA2 | Trend | WMA + STDDEV + ATR band system |
| Double Momentum | Momentum | MOM + MOM-of-MOM with next-bar fill |
| Dual Momentum | Rotation | Quarterly ETF rotation (NIFTYBEES vs GOLDBEES) |
| Buy & Hold | Passive | Static multi-asset allocation with FD benchmark |
| RSI Accumulation | Accumulation | Weekly RSI slab-wise buying (5%/10%/20% by RSI level) |
| Walk-Forward | Validation | Rolling train/test optimization with WFE scoring |
| Realistic Costs | Analysis | Same strategy across 5 fee tiers (zero to full delivery) |

### Knowledge Base (20 Rule Files)

| Category | What's Covered |
|----------|---------------|
| **Data** | Local Parquet candle store (India), yfinance (US/Global), CCXT (Crypto), custom providers, `.env` + `python-dotenv`, CSV loading, resampling |
| **Indicators** | TA-Lib by default (EMA, SMA, RSI, MACD, BBands, ATR, ADX, STDDEV, MOM ...); pandas-ta for the rest (Ichimoku, HMA, ALMA, VWMA ...); vectorbt indicators for parameter sweeps; `market_lib` signal helpers (exrem, crossover, flip, Donchian, Supertrend) |
| **Signals** | `ta.exrem()` signal cleaning, `ta.crossover()`, `ta.crossunder()`, `ta.flip()` regime detection |
| **Simulation** | `from_signals`, `from_orders`, `from_holding`, long/short/both directions |
| **Sizing** | Percent, Value, TargetPercent, whole shares (`min_size=1`), futures lot sizes, fractional crypto |
| **Costs** | **India**: 4-segment model (Delivery 0.111%, Intraday 0.0225%, Futures 0.018%, Options 0.098%). **US**: Per-share + per-contract model (Stocks ~0.01%, Options ~0.2%, Futures ~0.001%). **Crypto**: Maker/taker model (Spot 0.1%, Futures 0.02%/0.05%, funding rates). All customizable. |
| **Futures** | SEBI revised lot sizes (Dec 2025): NIFTY=65, BANKNIFTY=30, FINNIFTY=60. US: E-mini/Micro contract specs |
| **Risk** | Stop loss, take profit, trailing stop (`sl_trail`) |
| **Optimization** | Loop-based (TA-Lib) + broadcasting (`vbt.MA` / `vbt.talib` for parameter sweeps) |
| **Benchmarking** | India: NIFTYBEES (Nifty 50 ETF) from the local candle store. US: S&P 500 (`^GSPC`). Crypto: Bitcoin (`BTC-USD`). Strategy vs Benchmark table always produced |
| **Reporting** | Plain-language backtest explanation for normal traders. OpenStatz HTML tearsheets with 30+ metrics, Monte Carlo simulations |
| **Plotting** | Plotly dark theme, candlestick with `xaxis type="category"` (no weekend gaps), VectorBT 7-panel plot pack |
| **Validation** | Walk-forward analysis (WFE ratio), robustness testing (Monte Carlo trade shuffle, noise injection, parameter sensitivity, entry/exit delay, cross-symbol validation) |
| **Safety** | 10 common pitfalls with prevention, checklist before going live |

## Prerequisites

### 1. AI Coding Agent

Install any supported AI coding agent. For example:

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — `npm install -g @anthropic-ai/claude-code`
- [Cursor](https://cursor.com) — Desktop IDE with built-in AI
- [Codex](https://github.com/openai/codex) — `npm install -g @openai/codex`
- [OpenCode](https://github.com/opencode-ai/opencode) — `go install github.com/opencode-ai/opencode@latest`
- [Cline](https://github.com/cline/cline) — VS Code extension
- [Windsurf](https://windsurf.com) — Desktop IDE with AI
- Or any of the [40+ supported agents](https://github.com/vercel-labs/skills)

Then install the skills:

```bash
npx skills add mcsarathkumar/vectorbt-backtesting-skills
```

### 2. Data Source Setup

**Indian Markets** — reads the local [indian-market-data](../indian-market-data) Parquet store, no API or broker login needed:

```
/Users/mcsarathkumar/Workspace/indian-market-data/data/candles/<EXCHANGE>/<SYMBOL>/<interval>/...parquet
```

Override the location with `CANDLES_DIR` in `.env`. Coverage is uneven: most symbols have daily (`1day`) candles only; intraday (`1minute` ... `60minute`) exists for large caps. Check the symbol folder before backtesting. Scripts load data through `backtesting/market_lib.py` (`load_candles()`), which `/setup` copies from the vectorbt-expert skill.

**US Markets** — no setup needed. Uses yfinance (public Yahoo Finance data).

**Crypto Markets** — no setup needed for public data (yfinance or CCXT). Exchange API keys are optional (only for private endpoints).

### 3. Python Environment Setup

Use the `/setup` skill for automated setup, or manually:

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# TA-Lib needs its C library first
brew install ta-lib         # macOS
# sudo apt install libta-lib-dev  # Linux

# Install Python packages
pip install ta-lib pandas-ta vectorbt plotly anywidget nbformat pandas numpy pyarrow yfinance python-dotenv tqdm scipy numba ipywidgets openstatz ccxt
```

### 4. Configure API Keys

```bash
cp .env.sample .env
# Edit .env with your API keys
```

## Usage Examples

### `/setup` - Environment Setup

Detects OS, creates venv, installs dependencies, creates `backtesting/` with `market_lib.py`, and points `.env` at the candle store.

```
/setup
/setup python3.12
```

### `/backtest` - Quick Backtest

Create a complete backtest script with market-specific fees, benchmark comparison, plain-language report, and OpenStatz tearsheet.

```
# Indian Markets
/backtest ema-crossover SBIN NSE D
/backtest rsi RELIANCE NSE D
/backtest supertrend SBIN NSE 5m

# US Markets
/backtest ema-crossover AAPL
/backtest rsi MSFT

# Crypto Markets
/backtest ema-crossover BTC-USD
```

### `/optimize` - Parameter Optimization

Optimize strategy parameters, generate Plotly heatmaps, and compare best parameters vs benchmark.

```
/optimize ema-crossover SBIN NSE D
/optimize rsi AAPL
```

### `/quick-stats` - Inline Stats

Print key backtest stats with benchmark comparison without creating a file.

```
/quick-stats RELIANCE
/quick-stats AAPL
/quick-stats BTC-USD
```

### `/strategy-compare` - Compare Strategies

Compare multiple strategies side-by-side with benchmark.

```
/strategy-compare RELIANCE ema-crossover rsi donchian
/strategy-compare AAPL ema-crossover rsi macd
```

## Key Features

### Multi-Market Transaction Costs

Realistic fee models for each market, auto-selected based on the asset. All fee constants are configurable — adjust for your broker by changing the `fees` and `fixed_fees` values.

#### Indian Market Fees

| Segment | `fees` | `fixed_fees` |
|---------|--------|-------------|
| Delivery Equity | 0.00111 (0.111%) | Rs 20/order |
| Intraday Equity | 0.000225 (0.0225%) | Rs 20/order |
| F&O Futures | 0.00018 (0.018%) | Rs 20/order |
| F&O Options | 0.00098 (0.098%) | Rs 20/order |

#### US Market Fees

| Segment | `fees` | `fixed_fees` |
|---------|--------|-------------|
| Stocks (Pro/Fixed) | 0.0001 (0.01%) | $1.00/order |
| Stocks (Commission-Free) | 0.00001 (~0.001%) | $0 |
| Options | 0.002 (0.2%) | $0.65/contract |
| E-mini Futures (ES, NQ) | 0.000009 (~0.001%) | $2.25/contract |
| Micro Futures (MES, MNQ) | 0.00002 (~0.002%) | $0.55/contract |

#### Crypto Market Fees

| Segment | `fees` | `fixed_fees` |
|---------|--------|-------------|
| Spot (Base) | 0.001 (0.1%) | $0 |
| Spot (Discounted) | 0.00075 (0.075%) | $0 |
| USDT-M Futures (Taker) | 0.0005 (0.05%) | $0 |
| USDT-M Futures (Maker) | 0.0002 (0.02%) | $0 |
| COIN-M Futures (Taker) | 0.0005 (0.05%) | $0 |

> **Using a different broker?** Simply override the fee constants in your backtest script. The rule files include detailed breakdowns (STT, exchange fees, regulatory fees, clearing fees) so you can recalculate for any broker.

### Indicators (TA-Lib Default)

All strategies use TA-Lib for standard indicators. pandas-ta covers indicators TA-Lib lacks, and vectorbt indicators (`vbt.talib`, `vbt.MA`) are used for parameter sweeps or on request. `market_lib` provides the signal helpers.

```python
import talib
from market_lib import load_candles, exrem, supertrend

df = load_candles("SBIN", "NSE", "D")
ema_fast = talib.EMA(df["close"], timeperiod=10)
st_line, st_direction = supertrend(df["high"], df["low"], df["close"], period=10, multiplier=3.0)
entries = exrem(buy_raw.fillna(False), sell_raw.fillna(False))
```

### Market-Specific Benchmarks

| Market | Default Benchmark | Source |
|--------|-------------------|--------|
| India | NIFTYBEES (Nifty 50 ETF) | Local candle store |
| US | S&P 500 | yfinance (`^GSPC` or `SPY`) |
| Crypto | Bitcoin | yfinance (`BTC-USD`) |

Every backtest produces a Strategy vs Benchmark comparison table.

### OpenStatz Tearsheets

A modern interactive tearsheet with 30+ metrics, drawdown analysis, rolling statistics, monthly heatmaps, and Monte Carlo simulations. `ostz.dashboard(...)` renders the same interactive dashboard as `openstatz serve` into a single self-contained offline HTML file - no server, no `[app]` extra, no network. OpenStatz replaces QuantStats project-wide and keeps a numerical-parity contract on its metrics.

```python
import openstatz as ostz  # alias as ostz, not os - avoids shadowing the stdlib os module

# dashboard() needs the benchmark as a returns Series (not a ticker string)
benchmark = ostz.providers.download_returns("^NSEI").reindex(pf.returns().index).fillna(0)
ostz.dashboard(pf.returns(), benchmark=benchmark, output="tearsheet.html")
```

### Plain-Language Report Explanation

Every backtest explains results so normal traders can understand:

```
* Total Return: Your strategy made 45.23% while NIFTY 50 made 32.10%
  -> BEAT the market by 13.13%
* Max Drawdown: -12.34% - the biggest drop from peak
  -> On Rs 10,00,000 capital, worst temporary loss = Rs 1,23,400
* Sharpe Ratio: 1.45 (return per unit of risk, >1 decent, >2 excellent)
```

### Extensible Data Providers

Built-in support for the local candle store, yfinance, and CCXT. Add custom providers (Alpaca, Twelve Data, etc.) following the pattern in `data-fetching.md`. All API keys stored in `.env` via `python-dotenv`.

### SEBI Revised Lot Sizes (Effective 31 Dec 2025)

| Index | Lot Size | Exchange |
|-------|----------|----------|
| Nifty 50 | 65 | NFO |
| Nifty Bank | 30 | NFO |
| Nifty Financial Services | 60 | NFO |
| Nifty Midcap Select | 120 | NFO |
| Nifty Next 50 | 25 | NFO |
| BSE Sensex | 20 | BFO |
| BSE Bankex | 30 | BFO |
| BSE Sensex 50 | 70 | BFO |

### Backtesting Folder Structure

Strategy name = folder name. Symbol name = file prefix. Each strategy folder is self-contained.

```
backtesting/
├── ema_crossover/
│   ├── .env
│   ├── SBIN_ema_crossover_backtest.py
│   ├── SBIN_ema_crossover_trades.csv
│   ├── SBIN_tearsheet.html
│   ├── AAPL_ema_crossover_backtest.py
│   └── AAPL_ema_crossover_trades.csv
├── rsi/
│   ├── .env
│   ├── INFY_rsi_backtest.py
│   └── ...
├── supertrend/
│   └── ...
└── custom/
    └── ...
```

## Project Structure

```
.
├── .claude/
│   └── skills/
│       ├── setup/                    # /setup - Environment setup
│       │   └── SKILL.md
│       ├── backtest/                 # /backtest - Quick backtest
│       │   └── SKILL.md
│       ├── optimize/                 # /optimize - Parameter optimization
│       │   └── SKILL.md
│       ├── quick-stats/              # /quick-stats - Inline stats
│       │   └── SKILL.md
│       ├── strategy-compare/         # /strategy-compare - Compare strategies
│       │   └── SKILL.md
│       └── vectorbt-expert/          # Knowledge base (auto-loaded)
│           ├── SKILL.md              # Main skill (modular reference hub)
│           └── rules/                # 20 modular rule files
│               ├── data-fetching.md
│               ├── simulation-modes.md
│               ├── position-sizing.md
│               ├── indicators-signals.md
│               ├── ta-helpers.md
│               ├── stop-loss-take-profit.md
│               ├── parameter-optimization.md
│               ├── performance-analysis.md
│               ├── plotting.md
│               ├── indian-market-costs.md
│               ├── us-market-costs.md
│               ├── crypto-market-costs.md
│               ├── futures-backtesting.md
│               ├── long-short-trading.md
│               ├── csv-data-resampling.md
│               ├── walk-forward.md
│               ├── robustness-testing.md
│               ├── pitfalls.md
│               ├── strategy-catalog.md
│               ├── openstatz-tearsheet.md
│               └── assets/           # Production-ready templates
│                   ├── ema_crossover/backtest.py
│                   ├── rsi/backtest.py
│                   ├── donchian/backtest.py
│                   ├── supertrend/backtest.py
│                   ├── macd/backtest.py
│                   ├── sda2/backtest.py
│                   ├── momentum/backtest.py
│                   ├── dual_momentum/backtest.py
│                   ├── buy_hold/backtest.py
│                   ├── rsi_accumulation/backtest.py
│                   ├── walk_forward/template.py
│                   └── realistic_costs/template.py
├── .env.sample                      # Environment template (copy to .env)
├── backtesting/                      # Generated backtest scripts (per strategy)
│   ├── ema_crossover/
│   ├── rsi/
│   ├── donchian/
│   ├── supertrend/
│   ├── macd/
│   ├── sda2/
│   ├── momentum/
│   ├── dual_momentum/
│   ├── buy_hold/
│   ├── rsi_accumulation/
│   ├── walk_forward/
│   └── custom/
└── README.md
```

## Rule Files Reference

| Rule File | Description |
|-----------|-------------|
| `data-fetching.md` | Local candle store (India), yfinance (US), CCXT (Crypto), custom providers, `.env` setup |
| `simulation-modes.md` | from_signals, from_orders, from_holding, direction types |
| `position-sizing.md` | Amount/Value/Percent/TargetPercent sizing, whole shares |
| `indicators-signals.md` | TA-Lib strategy snippets (default), pandas-ta extras, signal generation |
| `ta-helpers.md` | TA-Lib / pandas-ta / vectorbt mapping; `market_lib` helpers: exrem, crossover, flip, Donchian, Supertrend |
| `stop-loss-take-profit.md` | Fixed SL, TP, trailing stop configurations |
| `parameter-optimization.md` | Broadcasting and loop-based optimization, heatmaps |
| `performance-analysis.md` | Stats, metrics, benchmark comparison, CAGR calculation |
| `plotting.md` | Candlestick (category x-axis), VectorBT plots, custom Plotly |
| `indian-market-costs.md` | Indian market fee model — delivery, intraday, F&O (4-segment) |
| `us-market-costs.md` | US market fee model — stocks, options, futures (per-share + per-contract) |
| `crypto-market-costs.md` | Crypto fee model — spot, perpetual futures, funding rates (maker/taker) |
| `futures-backtesting.md` | SEBI revised lot sizes (Dec 2025), US contract specs, value sizing |
| `long-short-trading.md` | Simultaneous long/short, direction comparison |
| `csv-data-resampling.md` | Loading CSV data, resampling with Indian market alignment |
| `walk-forward.md` | Walk-forward analysis, WFE ratio, rolling optimization |
| `robustness-testing.md` | Monte Carlo, noise test, parameter sensitivity, delay test |
| `pitfalls.md` | 10 common mistakes and checklist before going live |
| `strategy-catalog.md` | All strategy types with code snippets and asset references |
| `openstatz-tearsheet.md` | OpenStatz interactive offline dashboard, 30+ metrics, Monte Carlo (replaces QuantStats) |

## Data Sources

| Source | Use Case | Tickers/Codes | API Key Required |
|--------|----------|---------------|------------------|
| Local candles | Indian markets (primary) | `NSE/<SYMBOL>-EQ`, `BSE/<ticker>`, F&O in `fno_candles` | No (`CANDLES_DIR` optional) |
| yfinance | US markets, global, crypto | `AAPL`, `SPY`, `^GSPC`, `^NSEI`, `BTC-USD`, `ETH-USD` | No |
| CCXT | Crypto exchanges | `BTC/USDT`, `ETH/USDT` (higher resolution data) | Optional |
| Custom | Any provider | User-defined | User-defined |

## Configuration

Copy the `.env.sample` and fill in your API keys:

```bash
cp .env.sample .env
```

The `.env` file supports:

```
# Indian Markets - local Parquet candle store (default shown)
CANDLES_DIR=/Users/mcsarathkumar/Workspace/indian-market-data/data/candles

# Crypto Markets (CCXT) — Optional
CRYPTO_API_KEY=
CRYPTO_SECRET_KEY=

# Custom Data Providers - add your own keys
# ALPACA_API_KEY=
# TWELVEDATA_API_KEY=
```

US market data via yfinance does not require an API key.

## License

MIT
