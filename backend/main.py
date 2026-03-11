"""Application entry point — wires all components and manages lifecycle."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import Any

import uvicorn

from src.api.app import create_app
from src.config import Config
from src.engine.pnl_tracker import PnlTracker
from src.engine.trading_loop import TradingLoop
from src.exchange.balance_sync import BalanceSync
from src.exchange.okx_client import OkxClient
from src.exchange.order_manager import OrderManager
from src.exchange.ws_stream import WsStream
from src.logging_config import get_logger, setup_logging
from src.risk.risk_manager import RiskManager
from src.strategies.registry import StrategyRegistry

logger = get_logger("main")


def log_config_summary(config: Config) -> None:
    """Log a config summary without exposing secrets."""
    logger.info("=== OKX Trading Bot Starting ===")
    logger.info("Trading pair: %s", config.trading_pair)
    logger.info("Strategy: %s", config.strategy_name)
    logger.info("Spend per trade: %.2f USDT", config.spend_per_trade)
    logger.info("Max exposure: %.2f USDT", config.max_exposure)
    logger.info("Stop-loss: %.1f%% (%s)", config.stop_loss_pct, config.stop_loss_mode)
    logger.info("Max drawdown: %.1f%%", config.max_drawdown_pct)
    logger.info("Daily loss limit: %.2f USDT", config.daily_loss_limit)
    logger.info("Server: %s:%d", config.server_host, config.server_port)
    logger.info("Sandbox mode: %s", config.okx_sandbox)


def build_components(config: Config) -> dict[str, Any]:
    """Initialize all components in correct dependency order.

    Returns:
        Dict of named components for injection into the API.
    """
    # 1. Exchange client
    creds = config.get_okx_credentials()
    okx_client = OkxClient(
        api_key=creds["api_key"],
        secret_key=creds["secret_key"],
        passphrase=creds["passphrase"],
        sandbox=config.okx_sandbox,
    )

    # 2. WebSocket stream
    ws_stream = WsStream(sandbox=config.okx_sandbox)

    # 3. Order manager (depends on client)
    order_manager = OrderManager(okx_client)

    # 4. Balance sync (depends on client)
    balance_sync = BalanceSync(okx_client)

    # 5. Strategy (from registry)
    trading_config = config.get_trading_config()
    strategy_cls = StrategyRegistry.get(config.strategy_name)
    strategy = strategy_cls(config=trading_config)

    # 6. Risk manager (depends on config)
    risk_manager = RiskManager(trading_config)
    risk_manager.set_order_manager(order_manager)

    # 7. PnL tracker
    pnl_tracker = PnlTracker()

    # 8. Market data queue + Trading loop (depends on strategy, order_manager)
    market_data_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    trading_loop = TradingLoop(
        strategy=strategy,
        order_manager=order_manager,
        market_data_queue=market_data_queue,
        tick_interval_seconds=config.tick_interval,
    )

    return {
        "okx_client": okx_client,
        "ws_stream": ws_stream,
        "order_manager": order_manager,
        "balance_sync": balance_sync,
        "strategy": strategy,
        "risk_manager": risk_manager,
        "pnl_tracker": pnl_tracker,
        "trading_loop": trading_loop,
        "market_data_queue": market_data_queue,
    }


async def shutdown(components: dict[str, Any]) -> None:
    """Graceful shutdown: stop trading loop, close WebSocket, log shutdown."""
    logger.info("Shutting down gracefully...")

    trading_loop = components.get("trading_loop")
    if trading_loop and trading_loop.is_running:
        await trading_loop.stop()
        logger.info("Trading loop stopped")

    ws_stream = components.get("ws_stream")
    if ws_stream:
        try:
            await ws_stream.close()
            logger.info("WebSocket closed")
        except Exception:
            logger.warning("WebSocket close failed (may already be closed)")

    logger.info("=== OKX Trading Bot Stopped ===")


def main() -> None:
    """Entry point: load config, build components, start server."""
    setup_logging()

    try:
        config = Config()
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    log_config_summary(config)

    components = build_components(config)
    app = create_app(dependencies=components)

    server_config = config.get_server_config()

    # Register shutdown handler
    loop = asyncio.new_event_loop()

    def _signal_handler(sig: int, frame: Any) -> None:
        logger.info("Received signal %s, initiating shutdown...", sig)
        loop.run_until_complete(shutdown(components))
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    uvicorn.run(
        app,
        host=server_config["host"],
        port=server_config["port"],
        log_level="info",
    )


if __name__ == "__main__":
    main()
