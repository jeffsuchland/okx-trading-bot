"""OKX API client wrapper with authentication."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from okx import Account, MarketData, Trade

from src.exchange.exceptions import OkxApiError

load_dotenv()


class OkxClient:
    """Authenticated wrapper around the python-okx SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        passphrase: str | None = None,
        simulated: bool | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OKX_API_KEY", "")
        self.secret_key = secret_key or os.getenv("OKX_SECRET_KEY", "")
        self.passphrase = passphrase or os.getenv("OKX_PASSPHRASE", "")
        flag = "1" if (simulated if simulated is not None else os.getenv("OKX_SIMULATED", "true").lower() == "true") else "0"

        self._account_api = Account.AccountAPI(
            self.api_key, self.secret_key, self.passphrase, False, flag
        )
        self._market_api = MarketData.MarketAPI(
            self.api_key, self.secret_key, self.passphrase, False, flag
        )
        self._trade_api = Trade.TradeAPI(
            self.api_key, self.secret_key, self.passphrase, False, flag
        )

    @staticmethod
    def _check_response(response: dict[str, Any]) -> dict[str, Any]:
        """Validate OKX API response and raise on error."""
        code = response.get("code", "1")
        if code != "0":
            msg = response.get("msg", "Unknown error")
            raise OkxApiError(code=code, message=msg)
        return response

    def get_account_balance(self, currency: str = "USDT") -> dict[str, Any]:
        """Return parsed balance for the given currency."""
        response = self._account_api.get_account_balance(ccy=currency)
        self._check_response(response)
        details = response["data"][0]["details"]
        for detail in details:
            if detail["ccy"] == currency:
                return {
                    "currency": currency,
                    "available": float(detail.get("availBal", 0)),
                    "equity": float(detail.get("eq", 0)),
                    "frozen": float(detail.get("frozenBal", 0)),
                }
        return {"currency": currency, "available": 0.0, "equity": 0.0, "frozen": 0.0}

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        """Return bid/ask/last price for a given instrument."""
        response = self._market_api.get_ticker(instId=symbol)
        self._check_response(response)
        ticker = response["data"][0]
        return {
            "symbol": symbol,
            "bid": float(ticker.get("bidPx", 0)),
            "ask": float(ticker.get("askPx", 0)),
            "last": float(ticker.get("last", 0)),
            "volume_24h": float(ticker.get("vol24h", 0)),
            "timestamp": ticker.get("ts", ""),
        }

    def place_order(
        self,
        symbol: str,
        side: str,
        size: str,
        price: str | None = None,
        order_type: str = "limit",
        trade_mode: str = "cash",
    ) -> dict[str, Any]:
        """Submit an order and return the order ID."""
        params: dict[str, Any] = {
            "instId": symbol,
            "tdMode": trade_mode,
            "side": side,
            "ordType": order_type,
            "sz": size,
        }
        if price is not None and order_type == "limit":
            params["px"] = price

        response = self._trade_api.place_order(**params)
        self._check_response(response)
        order_data = response["data"][0]
        return {
            "order_id": order_data.get("ordId", ""),
            "client_order_id": order_data.get("clOrdId", ""),
            "status_code": order_data.get("sCode", ""),
            "status_msg": order_data.get("sMsg", ""),
        }

    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Cancel a specific order."""
        response = self._trade_api.cancel_order(instId=symbol, ordId=order_id)
        self._check_response(response)
        return response["data"][0]

    def health_check(self) -> bool:
        """Return True if the OKX API is reachable."""
        try:
            response = self._market_api.get_system_time()
            self._check_response(response)
            return True
        except Exception:
            return False
