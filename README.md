# OKX Automated Alpha-Seeker Bot

A production-ready, automated cryptocurrency trading bot for the OKX Exchange. Designed for maximal capital appreciation through high-probability, small-exposure trades with a safety-first architecture.

## Features

- **Exchange Integration**: Secure OKX V5 API (REST + WebSocket) for market data, order execution, and balance syncing
- **Modular Strategy Engine**: Pluggable strategies (RSI/MACD Mean Reversion, Grid Trading) with runtime switching
- **Risk Management**: Circuit breakers, stop-loss automation, position sizing, daily loss limits
- **Real-time Dashboard**: React/Tailwind UI for live metrics, strategy tuning, and emergency controls
- **Panic Button**: Instantly cancel all orders and flatten positions to USDT

---

## Installation Guide (Step by Step)

If you've never set up a project like this before, follow every step below in order. Commands are typed into a **terminal** (Command Prompt on Windows, Terminal on Mac/Linux).

### 1. Install Required Software

You need two programs installed on your computer before starting:

#### Python 3.11 or newer

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download the installer for your operating system
3. **Windows users:** During installation, check the box that says **"Add Python to PATH"** — this is important!
4. Verify it installed correctly by opening a terminal and typing:
   ```
   python --version
   ```
   You should see something like `Python 3.11.x` or higher.

#### Node.js 18 or newer

1. Go to [nodejs.org](https://nodejs.org/)
2. Download the **LTS** (Long Term Support) version
3. Run the installer with default settings
4. Verify it installed correctly:
   ```
   node --version
   npm --version
   ```
   You should see version numbers for both.

### 2. Download This Project

If you have Git installed:
```
git clone https://github.com/jeffsuchland/okx-trading-bot.git
cd okx-trading-bot
```

If you don't have Git, you can download the ZIP from GitHub and extract it to a folder on your computer, then open a terminal in that folder.

### 3. Get Your OKX API Keys

You need API credentials from OKX to connect the bot to your account.

1. Log into your OKX account at [okx.com](https://www.okx.com)
2. Go to **Profile → API** (or visit [okx.com/account/my-api](https://www.okx.com/account/my-api))
3. Click **Create API Key**
4. Give it a name (e.g., "Trading Bot")
5. Set permissions to **Trade** (read + trade, but NOT withdrawal)
6. Save the three values you receive:
   - **API Key**
   - **Secret Key**
   - **Passphrase**

> ⚠️ **Keep these secret!** Never share them or commit them to Git.

### 4. Configure Your Environment File

The `.env` file stores your private settings. It is never uploaded to GitHub.

**On Windows:**
```
copy backend\.env.example .env
```

**On Mac/Linux:**
```
cp backend/.env.example .env
```

Now open the `.env` file in any text editor (Notepad, VS Code, etc.) and replace the placeholder values:

```
OKX_API_KEY=paste_your_api_key_here
OKX_SECRET_KEY=paste_your_secret_key_here
OKX_PASSPHRASE=paste_your_passphrase_here
```

**Leave `OKX_SANDBOX=true` until you're ready to trade with real money.** This uses OKX's simulated environment so you can test safely.

### 5. Set Up the Backend (Python)

Open a terminal in the project folder and run these commands one at a time:

```
cd backend
```

Create an isolated Python environment (keeps this project's packages separate from your system):

**On Windows:**
```
python -m venv venv
venv\Scripts\activate
```

**On Mac/Linux:**
```
python3 -m venv venv
source venv/bin/activate
```

> You should see `(venv)` appear at the beginning of your terminal prompt. This means the virtual environment is active.

Install the required Python packages:
```
pip install -r requirements.txt
```

This may take a minute. Wait for it to finish.

### 6. Set Up the Frontend (Dashboard)

Open a **new terminal** (keep the backend one open) and navigate to the frontend folder:

```
cd frontend
npm install
```

This downloads all the JavaScript packages needed for the dashboard. It may take a few minutes the first time.

### 7. Start the Bot

You need **two terminals running at the same time** — one for the backend, one for the frontend.

**Terminal 1 — Backend** (make sure `(venv)` is showing):
```
cd backend
python main.py
```

You should see log messages indicating the server started on `http://127.0.0.1:8000`.

**Terminal 2 — Frontend:**
```
cd frontend
npm run dev
```

This will show a URL like `http://localhost:5173`. Open that URL in your web browser to see the dashboard.

### 8. Verify Everything Works

1. Open your browser to `http://localhost:5173`
2. You should see the trading dashboard with status cards and controls
3. The bot status should show as "stopped" until you click **Start**
4. Use the **Settings** page to adjust strategy and risk parameters
5. Start with **sandbox mode** (`OKX_SANDBOX=true`) to test without real money

---

## Stopping the Bot

- Press `Ctrl + C` in each terminal window to stop the backend and frontend
- The bot will gracefully shut down, closing WebSocket connections and stopping the trading loop

---

## Switching to Live Trading

When you're comfortable with the bot's behavior in sandbox mode:

1. Open your `.env` file
2. Change `OKX_SANDBOX=true` to `OKX_SANDBOX=false`
3. Restart the backend

> ⚠️ **Warning:** Live trading uses real money. Start with small values for `SPEND_PER_TRADE` and `MAX_EXPOSURE` in your `.env` file.

---

## Configuration Reference

All settings are in your `.env` file. Here are the key ones:

| Setting | Default | Description |
|---------|---------|-------------|
| `OKX_SANDBOX` | `true` | Use simulated trading (set `false` for real money) |
| `TRADING_PAIR` | `BTC-USDT` | Which crypto pair to trade |
| `STRATEGY_NAME` | `MeanReversionStrategy` | Active trading strategy |
| `SPEND_PER_TRADE` | `10` | USDT amount per trade |
| `MAX_EXPOSURE` | `100` | Maximum total USDT in open positions |
| `STOP_LOSS_PCT` | `2.0` | Auto-sell if a position drops this % |
| `MAX_DRAWDOWN_PCT` | `5.0` | Halt trading if account drops this % |
| `DAILY_LOSS_LIMIT` | `50.0` | Stop trading after this much daily loss (USDT) |

---

## Running Tests (Optional)

If you want to verify the code is working correctly:

```
# Backend tests (from backend/ with venv active)
pytest --cov=src tests/ -v

# Frontend tests (from frontend/)
npm test
```

---

## Project Structure

```
okx-trading-bot/
├── backend/                 # Python backend
│   ├── src/
│   │   ├── exchange/        # OKX API client, WebSocket, order management
│   │   ├── strategies/      # Trading strategies (mean reversion, grid)
│   │   ├── engine/          # Trading loop, PnL tracker
│   │   ├── risk/            # Risk management components
│   │   ├── api/             # FastAPI REST endpoints
│   │   └── utils/           # Logging, storage, resilience utilities
│   ├── tests/               # Python tests
│   ├── requirements.txt
│   └── main.py
├── frontend/                # React + Tailwind dashboard
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
└── .env.example             # Template for your private settings
```

## Troubleshooting

**"python is not recognized"** — Python isn't in your PATH. Reinstall Python and check "Add to PATH".

**"npm is not recognized"** — Node.js isn't installed or not in your PATH. Reinstall Node.js.

**"Missing required environment variables"** — Your `.env` file is missing or doesn't have the OKX keys filled in. See Step 4.

**Dashboard shows "Error" or can't connect** — Make sure the backend is running in Terminal 1 before opening the dashboard.

**"Port already in use"** — Another program is using port 8000 or 5173. Close it, or change `SERVER_PORT` in `.env`.

## Security

- API keys are loaded from `.env` via `python-dotenv` — **never hardcode credentials**
- `.env` is excluded from version control via `.gitignore`
- Start with sandbox mode (`OKX_SANDBOX=true`) before using real funds

## License

MIT
