# 🚀 Primetrade Trading Bot — Binance Futures Testnet

A production-grade Python trading bot for placing orders on **Binance Futures Testnet (USDT-M)**, built with clean architecture, comprehensive logging, and a premium CLI experience.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Binance](https://img.shields.io/badge/Binance-Futures%20Testnet-F0B90B?style=for-the-badge&logo=binance&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

## ✨ Features

| Feature | Description |
|---|---|
| **Market Orders** | Execute immediately at current market price |
| **Limit Orders** | Set your price — order fills when market reaches it |
| **Stop-Limit Orders** ⭐ | Bonus: trigger-based limit orders for advanced strategies |
| **Interactive Mode** | Beautiful guided menu with prompts, validation & confirmation |
| **Direct CLI** | One-liner commands with `--symbol`, `--side`, `--type`, etc. |
| **Rich Terminal UI** | Colour-coded tables, spinners, panels powered by Rich |
| **Structured Logging** | Dual-output: styled console + rotating log files |
| **Input Validation** | Comprehensive validation with actionable error messages |
| **Retry Logic** | Automatic retries on transient API / network failures |
| **Account Balance** | View your testnet portfolio at a glance |
| **Price Checker** | Quick-check any symbol's current market price |

---

## 📁 Project Structure

```
primetrade_task/
├── bot/
│   ├── __init__.py          # Package metadata
│   ├── __main__.py          # python -m bot entry point
│   ├── cli.py               # CLI + Interactive UI (Click + Rich)
│   ├── client.py            # Binance API client wrapper
│   ├── orders.py            # Order orchestration logic
│   ├── validators.py        # Input validation (pure functions)
│   └── logging_config.py    # Dual-output logging configuration
├── logs/                    # Auto-generated log files
│   ├── trading_bot.log          # Latest session log
│   └── trading_bot_YYYYMMDD_HHMMSS.log  # Timestamped logs
├── .env                     # API credentials (not committed)
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 🛠️ Setup

### Prerequisites

- **Python 3.9+**
- A **Binance Futures Testnet** account → [Register here](https://testnet.binancefuture.com/)

### 1. Clone & Enter

```bash
git clone <repo-url>
cd primetrade_task
```

### 2. Create Virtual Environment (recommended)

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Credentials

Create a `.env` file in the project root:

```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> **How to get credentials:**
> 1. Go to [Binance Futures Testnet](https://testnet.binancefuture.com/)
> 2. Log in with GitHub
> 3. Click "API Key" in the top menu
> 4. Generate a new key pair
> 5. Copy both the **API Key** and **Secret Key** into `.env`

---

## 🚀 How to Run

### Interactive Mode (Recommended)

```bash
python -m bot
```

This launches a beautiful guided interface with menus, prompts, and colour-coded feedback.

### Direct CLI Commands

#### Place a Market Order

```bash
python -m bot order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

#### Place a Limit Order

```bash
python -m bot order --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500.00
```

#### Place a Stop-Limit Order (Bonus)

```bash
python -m bot order --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.001 --price 95000 --stop-price 96000
```

#### Skip Confirmation

```bash
python -m bot order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --yes
```

#### Check Account Balance

```bash
python -m bot balance
```

#### Check Current Price

```bash
python -m bot price --symbol BTCUSDT
```

#### View Help

```bash
python -m bot --help
python -m bot order --help
```

---

## 📋 Example Outputs

### Market Order (BUY)

```
📋 Order Summary
┌──────────────────┬─────────────┐
│ Symbol           │ BTCUSDT     │
│ Side             │ BUY         │
│ Order Type       │ MARKET      │
│ Quantity         │ 0.001       │
│ Current Price    │ $103,456.78 │
└──────────────────┴─────────────┘

✅ Order Executed Successfully
╔══════════════════╦═══════════════╗
║ Order ID         ║ 123456789     ║
║ Symbol           ║ BTCUSDT       ║
║ Side             ║ BUY           ║
║ Type             ║ MARKET        ║
║ Status           ║ FILLED        ║
║ Quantity         ║ 0.001         ║
║ Executed Qty     ║ 0.001         ║
║ Avg Price        ║ $103,456.78   ║
╚══════════════════╩═══════════════╝
```

### Limit Order (SELL)

```
📋 Order Summary
┌──────────────────┬──────────────┐
│ Symbol           │ ETHUSDT      │
│ Side             │ SELL         │
│ Order Type       │ LIMIT        │
│ Quantity         │ 0.01         │
│ Current Price    │ $3,245.67    │
│ Limit Price      │ $3,500.00    │
│ Price vs Market  │ +7.84%       │
└──────────────────┴──────────────┘

✅ Order Executed Successfully
╔══════════════════╦═══════════════╗
║ Order ID         ║ 987654321     ║
║ Status           ║ NEW           ║
║ Price            ║ $3,500.00     ║
║ Time in Force    ║ GTC           ║
╚══════════════════╩═══════════════╝
```

---

## 📝 Logging

All API interactions are logged to two destinations:

| Destination | Level | Format |
|---|---|---|
| `logs/trading_bot.log` | DEBUG+ | Plain text with timestamps |
| Console (Rich) | INFO+ | Coloured, styled output |

Each session also creates a timestamped log file (e.g., `trading_bot_20260510_003000.log`) for historical reference.

**Sample log entry:**
```
2026-05-10 00:30:15 │ INFO     │ trading_bot.client   │ Placing MARKET order: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': 0.001}
2026-05-10 00:30:16 │ INFO     │ trading_bot.client   │ MARKET order placed → ID=123456789 status=FILLED executed=0.001
```

---

## 🏗️ Architecture & Design Decisions

### Separation of Concerns

```
CLI Layer (cli.py)          → User interaction, display, prompts
  ↓
Orchestration (orders.py)   → Validation, routing, error wrapping
  ↓
API Client (client.py)      → Binance API communication, retries
  ↓
Validators (validators.py)  → Pure input validation functions
```

### Key Design Choices

- **Pure Validators**: All validation functions are side-effect-free, returning typed `ValidationResult` objects. This makes them testable and reusable across CLI and programmatic callers.

- **Retry with Backoff**: The client retries transient errors (rate limits, server issues) up to 3 times with linear backoff, but fails immediately on client errors (invalid params, auth failures).

- **Custom Exception Hierarchy**: `BotConfigError`, `BotAPIError`, `BotNetworkError` enable precise error handling at each layer.

- **Typed Responses**: `OrderResponse` dataclass provides structured access to API responses while preserving the raw dict for debugging.

---

## ⚠️ Assumptions

1. **Testnet Only** — This bot is hardcoded to use `https://testnet.binancefuture.com`. It will **never** execute on mainnet.
2. **USDT-M Futures** — All symbols are assumed to be USDT-margined futures pairs (e.g., `BTCUSDT`, `ETHUSDT`).
3. **Default Leverage** — The bot uses the account's current leverage setting. Adjust leverage manually on the testnet dashboard if needed.
4. **Time in Force** — Limit and Stop-Limit orders default to `GTC` (Good Till Cancelled).
5. **No Streaming** — This is a CLI tool for discrete order placement, not a live trading dashboard.

---

## 🎯 Bonus Features Implemented

- ✅ **Stop-Limit Orders** — Third order type beyond MARKET and LIMIT
- ✅ **Enhanced CLI UX** — Interactive menus, prompts, validation messages, colour-coded output
- ✅ **Account Balance Viewer** — Portfolio overview with PnL display
- ✅ **Price Checker** — Quick symbol price lookup
- ✅ **Pre-order Confirmation** — Summary panel with market price comparison before execution

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Built for Primetrade.ai</b><br>
  <sub>Python Developer Intern — Application Task</sub>
</p>
