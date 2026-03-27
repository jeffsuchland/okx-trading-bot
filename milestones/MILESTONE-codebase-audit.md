# Milestone: Full Codebase Audit and Prioritized Improvement Plan

**Created:** 2026-03-27
**Status:** Complete
**Architect:** Claude Architect Agent

## Objective
Comprehensive analysis of the OKX Trading Bot codebase covering bugs, security, architecture, test gaps, production readiness, and frontend quality.

## Current State Summary

- **Backend tests:** 336 passed, 15 failed (out of 351)
- **Frontend tests:** 25 passed, 8 failed (out of 33)
- The project has working components but several material bugs, API contract mismatches, and significant gaps for production use.

---

## CRITICAL FIXES (Bugs and Security Issues)

### C1. OkxClient constructor parameter mismatch -- LIVE BUG

**Files:** `backend/main.py` line 71-76, `backend/src/exchange/okx_client.py` lines 19-25

`main.py` calls `OkxClient(sandbox=config.okx_sandbox)` but `OkxClient.__init__` accepts the parameter as `simulated`. Python will silently pass `sandbox=True` as `**kwargs` behavior -- actually it will **raise a TypeError** at runtime because `__init__` has no `sandbox` keyword parameter.

This means **the bot will crash immediately in non-demo mode** when trying to connect to the real OKX exchange. This is the highest-priority fix because it blocks all real trading.

**Fix:** Rename the `simulated` parameter in `OkxClient.__init__` to `sandbox`, or change `main.py` to pass `simulated=config.okx_sandbox`.

### C2. OkxClient `sandbox` vs `OKX_SIMULATED` env var confusion

**Files:** `backend/src/exchange/okx_client.py` line 29, `backend/src/config.py` line 42

The `Config` class uses `OKX_SANDBOX` env var, but `OkxClient` independently reads `OKX_SIMULATED` when no parameter is provided. The `.env.example` documents both. These are **two different env vars controlling the same thing**, creating a confusing mismatch where behavior depends on which code path initializes the client.

**Fix:** Standardize on one env var name. The `Config` class should be the single source of truth; remove the fallback `os.getenv` calls inside `OkxClient`.

### C3. Trailing stop-loss is broken -- 3 test failures

**File:** `backend/src/risk/stop_loss.py` lines 55-69

The trailing stop implementation has a logic bug. When `check_positions` is first called, it initializes `stop_price` based on `entry_price` (line 58), not `current_price`. On subsequent calls, the trailing logic only updates when `current_price > level["highest_price"]` (line 67), but the initial `highest_price` is set to the first `current_price` seen, not the entry price.

The core issue: the stop price is set from entry_price but the trailing uses highest_price from current_price. If entry=100 and first current=110, the stop becomes `100 * (1-0.02) = 98.0` instead of `110 * (1-0.02) = 107.8`. The stop should be calculated from `max(entry_price, current_price)` on initialization, or the trailing update should run on the initial call too.

**Fix:** On initialization, set `highest_price` to `max(entry_price, current_price)` and calculate `stop_price` from `highest_price` rather than `entry_price` when mode is "trailing".

### C4. Trading loop error handling is broken -- `_tick` exception escapes

**File:** `backend/src/engine/trading_loop.py` lines 49-74, 76-83

The `_tick()` method does NOT have a try/except around it. The try/except is in `_loop()` (line 80), which calls `_tick()`. However, the test `test_error_in_tick_is_caught` calls `_tick()` directly and expects it to catch errors internally.

More critically: the **real bug** is that `_tick()` calls `self._strategy.generate_signal()` on line 68, and if the strategy raises an exception, it propagates uncaught from `_tick()`. The `_loop()` method does catch this on line 81, BUT the test expects `_tick()` to be self-contained. This indicates a design mismatch -- either the test is wrong or `_tick()` should be defensive.

Looking at the actual `_loop` code: the try/except on line 79-82 DOES catch the error, so the loop keeps running. The test failure is a test design issue (calling `_tick()` directly). However, this means **any error in `_tick()` causes the entire tick to be lost** including any market data already consumed from the queue.

**Fix:** Move the try/except into `_tick()` itself, or at minimum add more granular error handling so queue drainage isn't lost when signal generation fails.

### C5. `time.sleep()` in async context -- blocking the event loop

**Files:** `backend/src/exchange/order_manager.py` line 42, `backend/src/utils/resilience.py` line 51, line 113

`OrderManager._throttle()` calls `time.sleep()` which **blocks the entire async event loop**. This means when the rate limiter kicks in, ALL async tasks (WebSocket listener, balance sync, API endpoints) freeze. In a trading bot, this could cause missed market data and stale WebSocket connections.

Similarly, `retry_with_backoff` and `RateLimiter.acquire()` use `time.sleep()` which will block the event loop if called from async code.

**Fix:** Convert `_throttle()` to `async def _throttle()` using `await asyncio.sleep()`. Same for the resilience utilities, or provide async variants.

### C6. PUT /api/config has no input validation -- arbitrary code injection risk

**File:** `backend/src/api/routes.py` lines 89-97

The `PUT /api/config` endpoint accepts arbitrary dicts for `strategy` and `risk` parameters and passes them directly to `strategy.update_config(body.strategy)` and `risk_manager.update_config(body.risk)`. Since `BaseStrategy.update_config` does `self.config.update(new_config)`, an attacker can inject **any keys** into the strategy config dict, including keys that might be used in unsafe ways later.

More concretely for risk: sending `{"max_daily_loss": 0.01}` would effectively disable the daily loss guard. While this isn't RCE, it allows an attacker who can reach the API to **manipulate all risk parameters** to their most dangerous values.

**Fix:** Add Pydantic validation models for each parameter type with explicit fields and value constraints (min/max ranges for numeric values). Reject unknown keys.

### C7. CORS allows credentials but no authentication exists

**File:** `backend/src/api/app.py` lines 21-27

CORS is configured with `allow_credentials=True` but there is zero authentication on any endpoint. Anyone who can reach the API can start/stop the bot, trigger panic mode, and reconfigure all risk parameters. In production, this is a severe security issue.

**Fix:** Add API key or session-based authentication. At minimum, add a `BOT_API_SECRET` environment variable that must be passed as a header on all requests.

---

## HIGH PRIORITY IMPROVEMENTS (Reliability and Correctness)

### H1. Duplicate polling -- Dashboard and App.tsx both poll `/api/balance` every 5s

**Files:** `frontend/src/App.tsx` lines 14-15, `frontend/src/pages/DashboardPage.tsx` lines 39-40

Both `App.tsx` and `DashboardPage` independently poll `/api/balance` every 5 seconds. When the user is on the dashboard, this means **2 balance requests every 5 seconds** -- double the necessary load. With all pages, App.tsx is always polling status+balance regardless of which page is active.

**Fix:** Centralize data fetching into a React context or use a data fetching library (SWR, React Query) with deduplication.

### H2. WebSocket stream is initialized but never started

**File:** `backend/main.py` lines 78, 107-113

`WsStream` is created in `build_components()` but `ws_stream.start()` is never called anywhere. The `market_data_queue` is created and passed to `TradingLoop`, but nothing ever puts data into it. The trading loop ticks but the queue is always empty, so `data_items` is always `[]`, and the strategy never gets any market data.

This means **the strategy never receives any price data**, so `generate_signal()` always returns `HOLD` (insufficient data). The bot appears to run but does absolutely nothing.

**Fix:** In `main.py` or in a startup lifecycle hook, call `ws_stream.start()` and `ws_stream.subscribe("tickers", config.trading_pair)`, and wire `ws_stream.queue` to the `market_data_queue` (or pass the same queue to both).

### H3. BalanceSync is initialized but never started

**File:** `backend/main.py` lines 83-84

`BalanceSync` is created but `balance_sync.start()` is never called. The balance data displayed in the dashboard is always `0.0` (or the demo seed value in demo mode). In live mode, balance never updates.

**Fix:** Start the balance sync polling loop during application startup, and stop it during shutdown.

### H4. Strategy `execute()` does nothing -- trading signals never reach the order manager

**Files:** `backend/src/strategies/mean_reversion.py` lines 96-102, `backend/src/strategies/grid_trading.py` lines 146-151, `backend/src/engine/trading_loop.py` lines 67-74

Both strategies' `execute()` methods just log and return the signal dict. They don't actually place orders. The `TradingLoop._tick()` calls `self._strategy.execute(signal)` (line 72) but doesn't do anything with the result -- it just logs "Signal executed".

Nobody ever calls `order_manager.place_limit_order()` or `place_market_order()` with real data. The entire order placement pipeline is disconnected.

**Fix:** The `TradingLoop._tick()` should take the signal result and use `self._order_manager` to actually place orders. Or the strategies should be given an order_manager reference.

### H5. PnL tracker `record_trade()` is never called

**File:** `backend/src/engine/pnl_tracker.py`

`PnlTracker` is instantiated in `build_components()` but nothing ever calls `record_trade()`. Since orders are never placed (H4), no trades are recorded. But even if orders were placed, there is no code that feeds fill data back to the PnL tracker.

**Fix:** After order placement, wire fill results to `pnl_tracker.record_trade()`.

### H6. Signal handler calls `loop.run_until_complete` during uvicorn's event loop

**File:** `backend/main.py` lines 166-176

The signal handler creates a new event loop (`asyncio.new_event_loop()`) on line 166, then calls `loop.run_until_complete(shutdown(components))` on line 170. But uvicorn manages its own event loop, and `loop` here is a different, unused loop. This means the shutdown coroutine runs on a loop that has never run, which may fail silently or raise errors because the async tasks (trading loop, ws_stream) were created on uvicorn's loop.

**Fix:** Use FastAPI's lifespan events (`@app.on_event("startup")` / `@app.on_event("shutdown")`) or the newer `lifespan` context manager to manage component lifecycle.

### H7. PnlTracker file I/O is not thread-safe

**File:** `backend/src/engine/pnl_tracker.py` lines 29-43

`_save()` and `_load()` use raw `open()` without any locking. If `record_trade()` is called concurrently (from multiple async tasks), the file could be corrupted. The `JsonStorage` utility in `src/utils/storage.py` already provides thread-safe atomic writes, but PnlTracker doesn't use it.

**Fix:** Replace the raw file I/O in PnlTracker with `JsonStorage.save()` / `JsonStorage.load()`.

### H8. `_build_demo_client()` returns incomplete mock

**File:** `backend/main.py` lines 48-55

The demo mock client only stubs `place_order`, `cancel_order`, `get_positions`, and `get_balance`. But `BalanceSync._poll()` calls `client.get_account_balance()` and `BalanceSync._sync_positions()` calls `client._account_api.get_positions()`. The MagicMock will return MagicMock objects for these, which will crash when the code tries to parse the response (e.g., `response["data"][0]["details"]`). This only works because `BalanceSync.start()` is never called (H3), but if H3 is fixed, demo mode will crash.

**Fix:** Add proper stubs for `get_account_balance` and `_account_api.get_positions()` in the demo mock.

---

## MEDIUM PRIORITY (Code Quality and Testing Gaps)

### M1. 15 backend test failures need fixing

Multiple test files have failures that indicate code-test divergence:
- `tests/test_config.py::TestDefaults::test_defaults_when_not_set` -- Env var leakage from `.env` file (SPEND_PER_TRADE=25 overrides the default of 10). Test needs proper env isolation.
- `tests/api/test_routes.py` -- 2 failures: balance mock returns list instead of expected float. The test fixture's BalanceSync mock doesn't match the actual interface.
- `tests/integration/test_trading_flow.py` -- 3 failures: Mean reversion strategy needs very specific price sequences to produce BUY signals; the test data doesn't trigger the conditions. Also `panic_flattens` test expects 2 orders tracked but the mock only tracks 1.
- `tests/risk/test_stop_loss.py` -- 3 trailing stop failures (see C3 above).
- `tests/test_main.py` -- `build_components` test expects OkxClient to be called but demo mode uses MagicMock instead.
- `tests/engine/test_trading_loop.py` -- Error handling test (see C4 above).
- `tests/utils/test_storage.py` -- `test_no_partial_write_on_failure` expects TypeError from json.dump but the `default=str` parameter in JsonStorage.save makes everything serializable.

### M2. 8 frontend test failures

The SettingsPage tests fail because they look for `strategy-params` testid which is inside a collapsed "Advanced" section. The tests don't click to expand it first. Dashboard tests have similar timing/mock issues.

### M3. No test coverage for these scenarios:
- WebSocket reconnection logic (`ws_stream.py`)
- BalanceSync polling loop
- Concurrent access to PnlTracker
- Config hot-reload while trading is active
- What happens when `panic()` is called during an active trade execution
- Frontend: TradeLogPage is completely empty (no tests, no implementation)
- No end-to-end test that the frontend can actually talk to the backend

### M4. `load_dotenv()` called in two places

**Files:** `backend/src/config.py` line 30, `backend/src/exchange/okx_client.py` line 13

`load_dotenv()` is called at module-level in `okx_client.py` AND in `Config.__init__()`. This means importing `okx_client` loads env vars before `Config` has a chance to set them up, potentially with stale or wrong values.

**Fix:** Remove the module-level `load_dotenv()` from `okx_client.py`. Let `Config` be the single entry point for environment loading.

### M5. `MagicMock` imported unconditionally in main.py

**File:** `backend/main.py` line 13

`from unittest.mock import MagicMock` is imported unconditionally in the production entry point. This works but is a code smell -- test utilities should not be imported in production code.

**Fix:** Conditionally import only when `demo_mode` is True, or create a proper `DemoClient` class.

### M6. Grid strategy uses floating-point equality for `_active_levels`

**File:** `backend/src/strategies/grid_trading.py` lines 113, 123

Grid prices are compared using `price not in self._active_levels` where `_active_levels` is a `set[float]`. Floating-point equality comparison is unreliable -- e.g., `50000 * (1 - 0.005)` might not exactly equal the same computation done differently. This could cause duplicate orders at the "same" price level.

**Fix:** Round prices to a fixed number of decimal places before comparison, or use a tolerance-based approach.

### M7. `WsStream` uses deprecated `websockets.client.WebSocketClientProtocol`

**File:** `backend/src/exchange/ws_stream.py` line 11

As shown in the test warnings, this import is deprecated in websockets v14. It should be updated to the modern API.

---

## NICE TO HAVE (UX, Performance, Polish)

### N1. TradeLogPage is a stub

**File:** `frontend/src/pages/TradeLogPage.tsx`

The page just shows "Trade history will appear here" with no actual implementation. It should fetch `/api/pnl` or a dedicated trade log endpoint and display a searchable, sortable table.

### N2. No loading states after initial load on Dashboard

**File:** `frontend/src/pages/DashboardPage.tsx` lines 58-70

The loading skeleton only shows on initial mount. After that, if the API goes down, the data just freezes at stale values with no visual indication. Should show a "connection lost" banner or dim the data.

### N3. Settings page doesn't load risk params from API

**File:** `frontend/src/pages/SettingsPage.tsx` lines 99-115

`loadConfig` fetches `/api/config` and populates `strategyParams` but never populates `riskParams`. The risk fields always show as empty (placeholder only). The save function sends both, so saving empty risk params means sending `{}` which has no effect.

**Fix:** In `loadConfig`, also extract risk parameters from the API response and populate `riskParams`.

### N4. Sidebar collapse toggle button is missing

**File:** `frontend/src/components/Layout.tsx` line 13

`collapsed` state is created but there's no button to toggle it. The sidebar is always expanded.

### N5. No favicon or document title

The browser tab just shows "Vite + React + TS" default. Should show "OKX Trading Bot" or similar.

### N6. InfoTooltip positioning could overflow viewport

**File:** `frontend/src/components/InfoTooltip.tsx` line 24

The tooltip always positions `left-6 top-0` which could overflow on the right edge of the screen on mobile.

### N7. Accessibility: missing ARIA labels on several interactive elements

- Strategy selection buttons in SettingsPage have no `aria-pressed` state
- Status dot in StatusBar has no `aria-label`
- Toast notifications don't use `role="alert"`

### N8. Dashboard cards recalculate on every render

**File:** `frontend/src/pages/DashboardPage.tsx` lines 89-150

The `cards` array is recreated on every render. Should be memoized with `useMemo`.

---

## Summary Table

| ID | Severity | Area | One-line Description |
|----|----------|------|---------------------|
| C1 | CRITICAL | Backend | OkxClient `sandbox` param mismatch -- crashes in live mode |
| C2 | CRITICAL | Backend | Two conflicting env vars for simulated mode |
| C3 | CRITICAL | Backend | Trailing stop-loss calculation is wrong |
| C4 | CRITICAL | Backend | Trading loop tick error handling gap |
| C5 | CRITICAL | Backend | `time.sleep()` blocks async event loop |
| C6 | CRITICAL | Security | No input validation on config update endpoint |
| C7 | CRITICAL | Security | No authentication on any API endpoint |
| H1 | HIGH | Frontend | Duplicate polling of `/api/balance` |
| H2 | HIGH | Backend | WebSocket stream never started -- no market data flows |
| H3 | HIGH | Backend | BalanceSync never started -- balances never update |
| H4 | HIGH | Backend | Strategy execute() never places actual orders |
| H5 | HIGH | Backend | PnL tracker never receives trade data |
| H6 | HIGH | Backend | Signal handler uses wrong event loop |
| H7 | HIGH | Backend | PnlTracker file I/O not thread-safe |
| H8 | HIGH | Backend | Demo mock client incomplete -- will crash if sync starts |
| M1 | MEDIUM | Testing | 15 backend test failures |
| M2 | MEDIUM | Testing | 8 frontend test failures |
| M3 | MEDIUM | Testing | Missing test coverage for critical paths |
| M4 | MEDIUM | Backend | load_dotenv called in multiple places |
| M5 | MEDIUM | Backend | unittest.mock imported in production |
| M6 | MEDIUM | Backend | Float equality for grid price levels |
| M7 | MEDIUM | Backend | Deprecated websockets API usage |
| N1 | LOW | Frontend | TradeLogPage is unimplemented |
| N2 | LOW | Frontend | No stale data indicator after API failure |
| N3 | LOW | Frontend | Settings page doesn't load risk params |
| N4 | LOW | Frontend | Sidebar collapse button missing |
| N5 | LOW | Frontend | No favicon or document title |
| N6 | LOW | Frontend | Tooltip overflow on small screens |
| N7 | LOW | Frontend | Missing ARIA attributes |
| N8 | LOW | Frontend | Cards array not memoized |

## Recommended Fix Order

1. **C1+C2** -- Fix OkxClient parameter naming (blocks all live trading)
2. **H2+H3+H4+H5** -- Wire up the data flow pipeline (WS -> Queue -> Strategy -> OrderManager -> PnlTracker). Without this, the bot literally does nothing.
3. **C3** -- Fix trailing stop-loss (money-losing bug)
4. **C5** -- Convert blocking sleep to async sleep
5. **C6+C7** -- Add input validation and authentication
6. **H6** -- Fix shutdown lifecycle
7. **C4+H7** -- Error handling and thread safety
8. **M1+M2** -- Fix all test failures
9. **N3** -- Load risk params in settings UI
10. Everything else

## Decisions
- 2026-03-27: Analysis-only milestone. No code changes made.

## Progress Log
- 2026-03-27: Read all 20 backend source files and 14 frontend source files. Ran backend tests (336 pass, 15 fail). Ran frontend tests (25 pass, 8 fail). Identified 7 critical issues, 8 high-priority issues, 7 medium issues, and 8 nice-to-have items.
