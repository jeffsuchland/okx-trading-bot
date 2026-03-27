# Project Progress Log

This file tracks all implementation cycles, decisions, and learnings during development.

---

## [Init] Deep Initialization - OKX Alpha-Seeker Bot

* **Status:** Success
* **Started:** 2026-03-10 15:32
* **Note:** Completed ralph-deep-init. Created prd.json with 29 tasks across 6 architectural groups:
  - **Exchange-Integration** (5 tasks): Project scaffolding, OKX API client, WebSocket stream, order management, balance sync
  - **Trading-Engine** (5 tasks): Base strategy/registry, RSI/MACD mean-reversion, grid trading, main loop, PnL tracker
  - **Risk-Management** (5 tasks): Position sizing, stop-loss automation, circuit breaker, daily loss limit, risk orchestrator
  - **Dashboard-UI** (5 tasks): FastAPI REST API, React layout shell, performance metrics page, settings page, panic/start/stop controls
  - **Testing** (4 tasks): Python test framework, frontend test framework, integration tests, API endpoint tests
  - **Infrastructure** (5 tasks): Config/secrets management, structured logging, app entry point, resilience patterns, data persistence

---

## [Cycle 1] Setup basic project structure and repository scaffolding

* **Status:** In Progress
* **Started:** 2026-03-10 16:28
* **Plan:**
  - Create backend/ directory with src/__init__.py package structure
  - Create backend/requirements.txt with all Python dependencies
  - Create frontend/ directory with Vite + React + Tailwind CSS scaffold
  - Create .env.example with placeholder OKX credentials
  - Create .gitignore covering Python, Node, and secrets
  - Create README.md with project overview and setup instructions
* **Files to create:** backend/src/__init__.py, backend/requirements.txt, frontend/ (Vite scaffold), .env.example, .gitignore, README.md
* **Verification:** Check files exist, verify `python -c "import src"` from backend/, verify `npm run build` from frontend/
* **Result:** Success

---

## [Cycle 2] OKX API client wrapper with authentication

* **Status:** In Progress
* **Started:** 2026-03-10 16:30
* **Plan:**
  - Create src/exchange/exceptions.py with custom OkxApiError
  - Create src/exchange/okx_client.py wrapping python-okx SDK
  - Load credentials from .env via python-dotenv
  - Implement get_account_balance(), get_ticker(), place_order(), cancel_order(), health_check()
  - Create tests/exchange/test_okx_client.py with mocked API responses
* **Files:** backend/src/exchange/exceptions.py, backend/src/exchange/okx_client.py, backend/tests/exchange/test_okx_client.py
* **Verification:** pytest tests/exchange/test_okx_client.py -v (exit code 0 — all 11 tests pass)
* **Result:** Success

---

## [Cycle 3] WebSocket market data stream

* **Status:** In Progress
* **Started:** 2026-03-10 16:35
* **Plan:**
  - Create src/exchange/ws_stream.py with WsStream class
  - Connect to OKX public WebSocket endpoint (wss://ws.okx.com:8443/ws/v5/public)
  - Implement subscribe(channel, instrument_id) and unsubscribe()
  - Parse incoming JSON messages and place on asyncio.Queue
  - Implement auto-reconnect with exponential backoff (max 30s)
  - Implement close() for clean shutdown
  - Create tests/exchange/test_ws_stream.py with mocked WebSocket
* **Files:** backend/src/exchange/ws_stream.py, backend/tests/exchange/test_ws_stream.py
* **Verification:** pytest tests/exchange/test_ws_stream.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 4] Order management service

* **Status:** In Progress
* **Started:** 2026-03-10 16:40
* **Plan:**
  - Create src/exchange/order_manager.py with OrderManager class
  - place_limit_order() delegates to OkxClient and tracks in-memory
  - cancel_order() cancels via OkxClient and removes from tracking
  - get_open_orders() returns tracked orders
  - cancel_all_orders() bulk cancels all tracked orders
  - panic_flatten() cancels all orders + market-sells non-USDT positions
  - Basic rate limiting (throttle to respect OKX 60 req/2s)
  - Create tests/exchange/test_order_manager.py
* **Files:** backend/src/exchange/order_manager.py, backend/tests/exchange/test_order_manager.py
* **Verification:** pytest tests/exchange/test_order_manager.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 5] Account balance synchronization

* **Status:** In Progress
* **Started:** 2026-03-10 16:45
* **Plan:**
  - Create src/exchange/balance_sync.py with BalanceSync class
  - Poll OkxClient.get_account_balance() on configurable interval (default 5s)
  - Maintain in-memory snapshot of balances
  - Expose get_usdt_balance(), get_total_equity(), get_positions()
  - Emit balance_updated callback when snapshot changes
  - Handle API errors gracefully without crashing sync loop
  - Create tests/exchange/test_balance_sync.py
* **Files:** backend/src/exchange/balance_sync.py, backend/tests/exchange/test_balance_sync.py
* **Verification:** pytest tests/exchange/test_balance_sync.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 6] Base strategy abstract class and strategy registry

* **Status:** In Progress
* **Started:** 2026-03-10 16:50
* **Plan:**
  - Create src/strategies/base_strategy.py with ABC BaseStrategy
  - Abstract methods: analyze(market_data), generate_signal(), execute()
  - Constructor accepts config dict for tunable parameters
  - Create src/strategies/registry.py with StrategyRegistry
  - register(name, cls), get(name), list_strategies()
  - Create tests/strategies/test_base_strategy.py and test_registry.py
* **Files:** backend/src/strategies/base_strategy.py, backend/src/strategies/registry.py, backend/tests/strategies/test_base_strategy.py, backend/tests/strategies/test_registry.py
* **Verification:** pytest tests/strategies/ -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 7] RSI/MACD mean-reversion strategy

* **Status:** In Progress
* **Started:** 2026-03-10 16:55
* **Plan:**
  - Create src/strategies/mean_reversion.py extending BaseStrategy
  - Implement calculate_rsi(prices, period) using Wilder's smoothing
  - Implement calculate_macd(prices, fast, slow, signal) returning line, signal, histogram
  - generate_signal(): BUY when RSI < oversold AND MACD histogram crosses up; SELL on inverse; HOLD otherwise
  - All thresholds configurable via config dict
  - Create tests/strategies/test_mean_reversion.py with known dataset verification
* **Files:** backend/src/strategies/mean_reversion.py, backend/tests/strategies/test_mean_reversion.py
* **Verification:** pytest tests/strategies/test_mean_reversion.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 8] Grid trading strategy

* **Status:** In Progress
* **Started:** 2026-03-10 16:48
* **Plan:**
  - Create src/strategies/grid_trading.py extending BaseStrategy
  - calculate_grid_levels(current_price, num_levels, spacing_pct) returns buy/sell level arrays
  - generate_signal() returns list of grid orders; tracks existing levels to avoid duplicates
  - Rebalance logic when price moves beyond outermost level
  - Configurable: num_levels (5), spacing_pct (0.5%), order_size_usdt
  - Create tests/strategies/test_grid_trading.py
* **Files:** backend/src/strategies/grid_trading.py, backend/tests/strategies/test_grid_trading.py
* **Verification:** pytest tests/strategies/test_grid_trading.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 9] Trading engine main loop

* **Status:** In Progress
* **Started:** 2026-03-10 16:50
* **Plan:**
  - Create src/engine/trading_loop.py with async TradingLoop class
  - Accept strategy, order_manager, market data queue
  - start() runs async loop consuming from queue
  - Each tick: strategy.analyze() → generate_signal() → execute orders
  - stop(), pause(), resume() controls
  - Configurable tick_interval_seconds (default 5)
  - Errors in a tick logged but don't crash loop
  - Create tests/engine/test_trading_loop.py
* **Files:** backend/src/engine/trading_loop.py, backend/tests/engine/test_trading_loop.py
* **Verification:** pytest tests/engine/test_trading_loop.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 10] Trade history and PnL tracker

* **Status:** In Progress
* **Started:** 2026-03-10 16:52
* **Plan:**
  - Create src/engine/pnl_tracker.py with PnlTracker class
  - record_trade(trade_info) stores trade with timestamp, symbol, side, qty, price, fee
  - get_daily_pnl(), get_cumulative_pnl(), get_win_loss_ratio(), get_recent_trades(n)
  - Persist trade log to JSON file; load on startup
  - Create tests/engine/test_pnl_tracker.py
* **Files:** backend/src/engine/pnl_tracker.py, backend/tests/engine/test_pnl_tracker.py
* **Verification:** pytest tests/engine/test_pnl_tracker.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 11] Position sizing engine

* **Status:** In Progress
* **Started:** 2026-03-10 16:55
* **Plan:**
  - Create src/risk/position_sizer.py with PositionSizer class
  - calculate_qty(price, current_exposure) returns qty based on spend_per_trade
  - Returns 0 when would exceed max_total_exposure
  - update_exposure(trade_info), get_current_exposure()
  - Hot-reloadable via update_config()
  - Create tests/risk/test_position_sizer.py
* **Files:** backend/src/risk/position_sizer.py, backend/tests/risk/test_position_sizer.py
* **Verification:** pytest tests/risk/test_position_sizer.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 12] Stop-loss automation

* **Status:** In Progress
* **Started:** 2026-03-10 16:58
* **Plan:**
  - Create src/risk/stop_loss.py with StopLossManager class
  - Fixed mode: triggers when unrealized loss exceeds stop_loss_pct
  - Trailing mode: updates stop price upward as profits increase
  - check_positions(positions) evaluates each position
  - get_stop_levels() returns current stop prices
  - Skips positions already being closed
  - Create tests/risk/test_stop_loss.py
* **Files:** backend/src/risk/stop_loss.py, backend/tests/risk/test_stop_loss.py
* **Verification:** pytest tests/risk/test_stop_loss.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 13] Max drawdown circuit breaker

* **Status:** In Progress
* **Started:** 2026-03-10 17:00
* **Plan:**
  - Create src/risk/circuit_breaker.py with CircuitBreaker class
  - update(current_equity) tracks peak equity and calculates drawdown
  - is_triggered() returns True when drawdown exceeds threshold
  - reset() clears triggered state
  - get_status() returns drawdown pct and triggered state
  - Create tests/risk/test_circuit_breaker.py
* **Files:** backend/src/risk/circuit_breaker.py, backend/tests/risk/test_circuit_breaker.py
* **Verification:** pytest tests/risk/test_circuit_breaker.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 14] Daily loss limit guard

* **Status:** In Progress
* **Started:** 2026-03-10 17:02
* **Plan:**
  - Create src/risk/daily_limit.py with DailyLimitGuard class
  - check(daily_pnl) returns True (safe) or False (halt)
  - Tracks halted state; auto-resets at UTC midnight
  - get_status() returns daily_loss, limit, is_halted
  - Create tests/risk/test_daily_limit.py with mocked datetime
* **Files:** backend/src/risk/daily_limit.py, backend/tests/risk/test_daily_limit.py
* **Verification:** pytest tests/risk/test_daily_limit.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 15] Risk manager orchestrator

* **Status:** In Progress
* **Started:** 2026-03-10 17:47
* **Plan:**
  - Create src/risk/risk_manager.py orchestrating PositionSizer, StopLossManager, CircuitBreaker, DailyLimitGuard
  - pre_trade_check(signal) runs sizing, daily limit, circuit breaker checks → (approved, reason)
  - post_trade_update(trade_result) updates exposure, PnL, stop-loss
  - get_risk_status() returns unified status dict
  - update_config() hot-reloads all sub-components
  - panic() delegates to OrderManager.panic_flatten() and halts
  - Create tests/risk/test_risk_manager.py
* **Files:** backend/src/risk/risk_manager.py, backend/tests/risk/test_risk_manager.py
* **Verification:** pytest tests/risk/test_risk_manager.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 16] FastAPI backend REST API for dashboard

* **Status:** In Progress
* **Started:** 2026-03-10 17:48
* **Plan:**
  - Create src/api/routes.py with FastAPI router
  - Endpoints: GET /api/status, /api/balance, /api/pnl, /api/config, PUT /api/config, POST /api/panic, /api/start, /api/stop
  - CORS middleware for localhost:5173
  - Create src/api/app.py as FastAPI app factory
  - Create tests/api/test_routes.py with httpx TestClient
* **Files:** backend/src/api/app.py, backend/src/api/routes.py, backend/tests/api/__init__.py, backend/tests/api/test_routes.py
* **Verification:** pytest tests/api/test_routes.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 17] React dashboard layout and navigation shell

* **Status:** In Progress
* **Started:** 2026-03-10 17:50
* **Plan:**
  - Create layout components: Sidebar, StatusBar, Layout
  - Create page stubs: DashboardPage, SettingsPage, TradeLogPage
  - Wire React Router in App.tsx with BrowserRouter
  - Dark theme via Tailwind dark classes
  - Status bar: bot status dot (green/yellow/red), USDT balance
  - Create tests: App.test.tsx verifying nav, status bar, routing
* **Files:** frontend/src/components/*, frontend/src/pages/*, frontend/src/App.tsx, frontend/src/main.tsx, frontend/src/App.test.tsx
* **Verification:** npm test (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 18] Dashboard home page with performance metrics

* **Status:** In Progress
* **Started:** 2026-03-10 17:55
* **Plan:**
  - Replace DashboardPage stub with full metrics cards and trades table
  - Cards: Daily PnL (+/- color), Cumulative PnL, Win Rate, Current Exposure, Account Equity
  - Recent trades table: timestamp, symbol, side, qty, price, pnl
  - useEffect polling every 5s from /api/pnl and /api/balance
  - Loading skeleton, error state
  - Create DashboardPage.test.tsx
* **Files:** frontend/src/pages/DashboardPage.tsx, frontend/src/pages/DashboardPage.test.tsx
* **Verification:** npm test (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 19] Settings page with strategy and risk controls

* **Status:** In Progress
* **Started:** 2026-03-10 18:00
* **Plan:**
  - Replace SettingsPage stub with form controls
  - Strategy section: dropdown, RSI/MACD/grid parameter inputs
  - Risk section: spend_per_trade, max_exposure, stop_loss_pct, max_drawdown_pct, daily_loss_limit
  - Input validation (no negatives, numeric only)
  - Save button calls PUT /api/config, shows success/error toast
  - Pre-populate from GET /api/config on load
  - Create SettingsPage.test.tsx
* **Files:** frontend/src/pages/SettingsPage.tsx, frontend/src/pages/SettingsPage.test.tsx
* **Verification:** npm test (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 20] Panic button and bot start/stop controls

* **Status:** In Progress
* **Started:** 2026-03-10 18:05
* **Plan:**
  - Create BotControls component with Panic button, Start/Stop toggle
  - Panic button: large red, confirmation modal, POST /api/panic
  - Start/Stop: toggle based on status, POST /api/start / /api/stop
  - Disabled with spinner during API call
  - Add to StatusBar
  - Create BotControls.test.tsx
* **Files:** frontend/src/components/BotControls.tsx, frontend/src/components/BotControls.test.tsx, frontend/src/components/StatusBar.tsx
* **Verification:** npm test (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 21] Setup Python testing framework and fixtures

* **Status:** In Progress
* **Started:** 2026-03-10 18:10
* **Plan:**
  - Create tests/conftest.py with shared fixtures: MockOkxClient, sample market data (100 candles)
  - Create pyproject.toml with pytest config and coverage thresholds (80%)
  - Ensure tests/ directory mirrors src/ structure
  - Verify with pytest --collect-only and pytest --cov
* **Files:** backend/tests/conftest.py, backend/pyproject.toml, backend/tests/test_conftest_fixtures.py
* **Verification:** pytest --collect-only && pytest tests/test_conftest_fixtures.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 22] Setup frontend testing framework

* **Status:** In Progress
* **Started:** 2026-03-10 18:12
* **Plan:**
  - Create custom render utility (src/test/render.tsx) wrapping components with MemoryRouter
  - Create MSW handlers for all /api/* endpoints (src/test/handlers.ts)
  - Create MSW server instance (src/test/server.ts)
  - Update setup.ts to start/stop MSW server
  - Verify with npm test
* **Files:** frontend/src/test/render.tsx, frontend/src/test/handlers.ts, frontend/src/test/server.ts, frontend/src/test/setup.ts
* **Verification:** npm test (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 23] Integration tests for trading flow

* **Status:** In Progress
* **Started:** 2026-03-10 18:15
* **Plan:**
  - Create tests/integration/__init__.py and test_trading_flow.py
  - Test full cycle: market data -> strategy signal -> risk check -> order -> fill -> PnL update
  - Test risk-blocks path: risk check rejects trade
  - Test stop-loss trigger: position drops -> market sell
  - Test circuit breaker: drawdown exceeds limit -> trading halted
  - Test panic flatten: cancel all orders, close all positions
  - All tests use MockOkxClient from conftest, no real API calls
* **Files:** backend/tests/integration/__init__.py, backend/tests/integration/test_trading_flow.py
* **Verification:** pytest tests/integration/test_trading_flow.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 24] API endpoint tests

* **Status:** In Progress
* **Started:** 2026-03-10 18:18
* **Plan:**
  - Existing test_routes.py covers most criteria from Cycle 16
  - Add missing test_invalid_config (422 validation errors)
  - Add schema assertion helpers to verify frontend-expected shapes
  - Verify with pytest tests/api/test_routes.py -v
* **Files:** backend/tests/api/test_routes.py
* **Verification:** pytest tests/api/test_routes.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 25] Environment configuration and secrets management

* **Status:** In Progress
* **Started:** 2026-03-10 18:20
* **Plan:**
  - Create src/config.py with Config class loading from .env via python-dotenv
  - Validate required vars (OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE), raise ConfigError if missing
  - Default values for optional vars (SPEND_PER_TRADE=10, MAX_EXPOSURE=100, etc.)
  - get_trading_config() returns dict for strategy/risk init
  - Immutable after load
  - Create .env.example documenting all vars
  - Create tests/test_config.py
* **Files:** backend/src/config.py, backend/.env.example, backend/tests/test_config.py
* **Verification:** pytest tests/test_config.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 26] Structured logging system

* **Status:** In Progress
* **Started:** 2026-03-10 18:22
* **Plan:**
  - Create src/logging_config.py with JSON formatter, console handler, rotating file handler
  - get_logger(component) returns prefixed logger
  - Console: colored human-readable; File: JSON to logs/bot.log, 10MB rotation, 5 backups
  - Create tests/test_logging_config.py
* **Files:** backend/src/logging_config.py, backend/tests/test_logging_config.py
* **Verification:** pytest tests/test_logging_config.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 27] Application entry point and lifecycle management

* **Status:** In Progress
* **Started:** 2026-03-10 18:25
* **Plan:**
  - Create backend/main.py wiring Config, OkxClient, WsStream, OrderManager, BalanceSync, strategy, RiskManager, TradingLoop, PnlTracker, FastAPI server
  - Add /api/health endpoint returning 200
  - Graceful shutdown on SIGINT/SIGTERM
  - Startup logs show config summary without secrets
  - Create tests/test_main.py verifying init order, shutdown, health, startup logs
* **Files:** backend/main.py, backend/tests/test_main.py, backend/src/api/routes.py (health endpoint)
* **Verification:** pytest tests/test_main.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 28] Error handling and resilience patterns

* **Status:** In Progress
* **Started:** 2026-03-10 18:28
* **Plan:**
  - Create src/utils/resilience.py with retry_with_backoff decorator, RateLimiter class, RateLimitExceeded exception
  - retry_with_backoff: configurable max_retries, base_delay, exception types, exponential backoff
  - RateLimiter: token bucket algorithm, max_calls/period, wait or raise modes
  - All events logged with attempt count and delay
  - Create tests/utils/test_resilience.py
* **Files:** backend/src/utils/resilience.py, backend/tests/utils/__init__.py, backend/tests/utils/test_resilience.py
* **Verification:** pytest tests/utils/test_resilience.py -v (exit code 0 — all tests pass)
* **Result:** Success

---

## [Cycle 30] Wire full data pipeline — H2/H3/H4/H5 fixes

* **Status:** Complete
* **Started:** 2026-03-27
* **What was fixed:**
  - H2: WsStream now started + subscribed in `/api/start` (connect, subscribe tickers for trading pair)
  - H3: BalanceSync.start() now called in `/api/start`; stop() called in `/api/stop`
  - H4: TradingLoop._tick() now calls `_execute_signal()` which places real orders via OrderManager (BUY/SELL market orders, GRID limit orders)
  - H5: PnlTracker.record_trade() is now called after each order is placed
  - WsStream.queue is now directly connected to TradingLoop's market_data_queue in `build_components()`
  - OrderManager methods converted to `async` (place_limit_order, place_market_order, cancel_order, cancel_all_orders, panic_flatten)
  - RiskManager.panic() converted to `async`
  - All callers updated to `await` the async methods
  - Error handling added inside `_tick()` so individual signal errors don't crash the loop
* **Files changed:**
  - `backend/main.py` — queue wiring, pnl_tracker/trading_pair/spend_per_trade passed to TradingLoop, balance_sync stop in shutdown, WsStream URL for sandbox
  - `backend/src/exchange/order_manager.py` — all mutation methods made async
  - `backend/src/risk/risk_manager.py` — panic() made async
  - `backend/src/engine/trading_loop.py` — added _execute_signal(), pnl_tracker param, error handling in _tick()
  - `backend/src/api/routes.py` — /api/start wires WsStream+BalanceSync; /api/panic awaits; /api/stop stops balance_sync
  - `backend/tests/exchange/test_order_manager.py` — all tests converted to async
  - `backend/tests/risk/test_risk_manager.py` — panic tests converted to async
  - `backend/tests/integration/test_trading_flow.py` — order calls converted to async
  - `backend/tests/api/test_routes.py` — risk_manager.panic made AsyncMock; balance_sync mocks fixed
  - `backend/tests/test_main.py` — added config.demo_mode=False, trading_pair, spend_per_trade

---

## [2026-03-27] Bug Fix H6: Shutdown lifecycle — signal handler using wrong event loop

- **Status:** Done
- **Engineer:** Fixed signal handler using `asyncio.new_event_loop()` (a dead loop, not uvicorn's running loop).
- **Solution:** Replaced the broken `signal.signal()` + `loop.run_until_complete()` pattern with a FastAPI lifespan context manager (`@asynccontextmanager`). The lifespan runs in the actual uvicorn event loop, so `await shutdown(components)` properly cleans up all async resources.
- **Shutdown now covers:** trading loop stop, balance sync stop, open order cancellation, WebSocket close, background task cancellation.
- **`create_app` updated** to accept an optional `lifespan` parameter, passed through to `FastAPI(lifespan=...)`.
- **Files:** `backend/main.py`, `backend/src/api/app.py`

---

## [Cycle 29] Data persistence layer

* **Status:** In Progress
* **Started:** 2026-03-10 18:40
* **Plan:**
  - Create src/utils/storage.py with JsonStorage class
  - save(filepath, data): atomic write via temp file + rename
  - load(filepath): read/parse JSON, return None if missing
  - backup(filepath): timestamped copy in data/backups/
  - Thread-safe via threading.Lock
  - Auto-create data directory if missing
  - Create tests/utils/test_storage.py
* **Files:** backend/src/utils/storage.py, backend/tests/utils/test_storage.py
* **Verification:** pytest tests/utils/test_storage.py -v (exit code 0 — all tests pass)
* **Result:** Success
