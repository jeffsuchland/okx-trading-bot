# Progress Log

- 2026-03-27: [Engineer] Implemented API key authentication (C6) and risk config input validation (C7). Created `backend/src/api/auth.py` with `require_api_key` FastAPI dependency that checks X-API-Key header or api_key query param against API_SECRET_KEY env var (skipped when unset for dev/demo mode). Applied auth to all mutation endpoints (PUT /api/config, POST /api/panic, /api/start, /api/stop). Added `RiskConfigUpdate` Pydantic model to `backend/src/api/routes.py` that validates non-negative values for spend_per_trade/max_exposure/daily_loss_limit and 0-100 range for stop_loss_pct/max_drawdown_pct. Updated `backend/tests/api/test_routes.py` with TestAuthentication (8 tests) and TestRiskConfigValidation (10 tests) classes. Files: backend/src/api/auth.py, backend/src/api/routes.py, backend/tests/api/test_routes.py

- 2026-03-27: [Engineer] Fixed 12 backend test failures across 4 test files. Files: backend/src/exchange/okx_client.py, backend/src/utils/storage.py, backend/tests/test_main.py, backend/tests/test_config.py, backend/tests/integration/test_trading_flow.py.

  Changes made:
  - Installed uvicorn package (was missing from environment)
  - backend/src/exchange/okx_client.py: Removed module-level load_dotenv() call that was contaminating os.environ with DEMO_MODE=true from backend/.env, causing Config validation to be silently bypassed in tests
  - backend/src/utils/storage.py: Removed default=str from json.dump() so non-serializable objects raise TypeError instead of being silently stringified
  - backend/tests/test_main.py: Fixed test_build_creates_all_components to set config.demo_mode=False and use mock_registry.return_value.get (instance method) instead of mock_registry.get (class method)
  - backend/tests/test_config.py: Added monkeypatch.delenv calls to test_defaults_when_not_set to clear optional env vars leaked by prior tests loading _VALID_ENV
  - backend/tests/integration/test_trading_flow.py: Rewrote _feed_oversold_data price series to reliably produce BUY signal (decline 200->72 over 65 steps then jump to 79.2 gives RSI=21.8 < 30 with MACD histogram crossing from negative to positive); fixed _make_mock_client to return unique order IDs via side_effect so two placed limit orders don't collide in _open_orders dict; updated order_id assertions to use startswith
