# OKX Automated Alpha-Seeker Bot

A production-ready, automated cryptocurrency trading bot for the OKX Exchange. Designed for maximal capital appreciation through high-probability, small-exposure trades with a safety-first architecture.

## Features

- **Exchange Integration**: Secure OKX V5 API (REST + WebSocket) for market data, order execution, and balance syncing
- **Modular Strategy Engine**: Pluggable strategies (RSI/MACD Mean Reversion, Grid Trading) with runtime switching
- **Risk Management**: Circuit breakers, stop-loss automation, position sizing, daily loss limits
- **Real-time Dashboard**: React/Tailwind UI for live metrics, strategy tuning, and emergency controls
- **Panic Button**: Instantly cancel all orders and flatten positions to USDT

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
├── .env.example
├── prd.json                 # Ralph backlog
└── progress.md              # Development log
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OKX API credentials ([create here](https://www.okx.com/account/my-api))

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env
# Edit .env with your OKX API credentials
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running

```bash
# Start backend (from backend/)
python main.py

# Start frontend dev server (from frontend/)
npm run dev
```

### Testing

```bash
# Backend tests
cd backend
pytest --cov=src tests/ -v

# Frontend tests
cd frontend
npm test
```

## Security

- API keys are loaded from `.env` via `python-dotenv` — **never hardcode credentials**
- `.env` is excluded from version control via `.gitignore`
- Use OKX simulated trading mode (`OKX_SIMULATED=true`) for testing

## License

MIT
