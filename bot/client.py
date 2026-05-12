"""
Binance Futures Testnet Client
==============================

Thin wrapper around python-binance that:
  • Loads credentials from environment / .env
  • Connects exclusively to the Futures Testnet
  • Provides typed, logged methods for order placement
  • Handles retries, timeouts, and API error classification

This layer is the *only* module that talks to Binance.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv

logger = logging.getLogger("trading_bot.client")

# ── Configuration ────────────────────────────────────────────────────

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


# ── Custom Exceptions ────────────────────────────────────────────────


class BotConfigError(Exception):
    """Raised when API credentials are missing or invalid."""


class BotAPIError(Exception):
    """Raised when a Binance API call fails after retries."""

    def __init__(self, message: str, code: int = -1, original: Exception = None):
        super().__init__(message)
        self.code = code
        self.original = original


class BotNetworkError(Exception):
    """Raised on connectivity / timeout failures."""


# ── Data Classes ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class OrderResponse:
    """Structured representation of a Binance order response."""

    order_id: int
    symbol: str
    side: str
    order_type: str
    status: str
    quantity: str
    executed_qty: str
    price: str
    avg_price: str
    time_in_force: str
    raw: Dict[str, Any] = field(repr=False, default_factory=dict)

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "OrderResponse":
        """Parse a raw API response dict into an OrderResponse."""
        return cls(
            order_id=data.get("orderId", 0),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            status=data.get("status", ""),
            quantity=str(data.get("origQty", "0")),
            executed_qty=str(data.get("executedQty", "0")),
            price=str(data.get("price", "0")),
            avg_price=str(data.get("avgPrice", data.get("price", "0"))),
            time_in_force=data.get("timeInForce", ""),
            raw=data,
        )


# ── Client ───────────────────────────────────────────────────────────


class BinanceFuturesClient:
    """
    Production-grade wrapper for Binance Futures Testnet interactions.

    Usage::

        client = BinanceFuturesClient()       # reads .env
        client = BinanceFuturesClient(api_key="...", api_secret="...")
        response = client.place_market_order("BTCUSDT", "BUY", 0.001)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        load_dotenv()

        self._api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self._api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")

        if not self._api_key:
            raise BotConfigError(
                "BINANCE_API_KEY is not set. "
                "Add it to your .env file or pass it directly."
            )
        if not self._api_secret:
            raise BotConfigError(
                "BINANCE_API_SECRET is not set. "
                "Add it to your .env file or pass it directly."
            )

        logger.info("Initialising Binance Futures Testnet client…")
        try:
            self._client = Client(
                self._api_key,
                self._api_secret,
                testnet=True,
            )

            # Phase 1: Verify network connectivity (unauthenticated)
            server_time = self._client.futures_time()
            logger.info(
                f"Testnet reachable (server time: {server_time.get('serverTime', 'N/A')})"
            )

            # Phase 2: Verify API credentials (authenticated endpoint)
            account = self._client.futures_account()
            can_trade = account.get("canTrade", False)
            if not can_trade:
                raise BotConfigError(
                    "API credentials are valid but trading is disabled on this account. "
                    "Check your testnet account permissions."
                )
            logger.info(
                f"Authenticated successfully — "
                f"canTrade={can_trade}, "
                f"balance={account.get('totalWalletBalance', '0')} USDT"
            )

        except BinanceAPIException as exc:
            if exc.code in (-2015, -2014, -1022):
                # Auth-specific errors
                logger.error(f"Authentication failed: {exc.message}")
                raise BotConfigError(
                    f"API credentials rejected by Binance: {exc.message}. "
                    f"Regenerate your API key/secret at https://testnet.binancefuture.com"
                ) from exc
            logger.error(f"Binance API error during init: {exc.message}")
            raise BotNetworkError(
                f"Could not connect to Binance Futures Testnet: {exc.message}"
            ) from exc

        except BotConfigError:
            raise  # Re-raise config errors as-is

        except Exception as exc:
            logger.error(f"Failed to connect to Binance Testnet: {exc}")
            raise BotNetworkError(
                f"Could not connect to Binance Futures Testnet: {exc}"
            ) from exc

    # ── Public API ───────────────────────────────────────────────────

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch futures account information."""
        return self._safe_call("futures_account", log_tag="AccountInfo")

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch exchange info for a specific symbol."""
        try:
            info = self._safe_call("futures_exchange_info", log_tag="ExchangeInfo")
            for s in info.get("symbols", []):
                if s["symbol"] == symbol.upper():
                    return s
        except Exception:
            logger.warning(f"Could not fetch exchange info for {symbol}")
        return None

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """Get the current market price for a symbol."""
        try:
            ticker = self._safe_call(
                "futures_symbol_ticker",
                log_tag="TickerPrice",
                symbol=symbol.upper(),
            )
            return float(ticker.get("price", 0))
        except Exception:
            logger.warning(f"Could not fetch ticker price for {symbol}")
            return None

    def place_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> OrderResponse:
        """Place a MARKET order on Binance Futures Testnet."""
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
        }
        logger.info(f"Placing MARKET order: {params}")
        raw = self._safe_call(
            "futures_create_order", log_tag="MarketOrder", **params
        )
        response = OrderResponse.from_api(raw)
        logger.info(
            f"MARKET order placed → ID={response.order_id} "
            f"status={response.status} executed={response.executed_qty}"
        )
        return response

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC",
    ) -> OrderResponse:
        """Place a LIMIT order on Binance Futures Testnet."""
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": quantity,
            "price": str(price),
            "timeInForce": time_in_force,
        }
        logger.info(f"Placing LIMIT order: {params}")
        raw = self._safe_call(
            "futures_create_order", log_tag="LimitOrder", **params
        )
        response = OrderResponse.from_api(raw)
        logger.info(
            f"LIMIT order placed → ID={response.order_id} "
            f"status={response.status} price={response.price}"
        )
        return response

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        time_in_force: str = "GTC",
    ) -> OrderResponse:
        """
        Place a STOP_LIMIT order on Binance Futures Testnet.

        The order becomes a LIMIT order when the market reaches `stop_price`.
        It will then execute at `price` or better.
        """
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "STOP",
            "quantity": quantity,
            "price": str(price),
            "stopPrice": str(stop_price),
            "timeInForce": time_in_force,
        }
        logger.info(f"Placing STOP_LIMIT order: {params}")
        raw = self._safe_call(
            "futures_create_order", log_tag="StopLimitOrder", **params
        )
        response = OrderResponse.from_api(raw)
        logger.info(
            f"STOP_LIMIT order placed → ID={response.order_id} "
            f"status={response.status} price={response.price} "
            f"stopPrice={stop_price}"
        )
        return response

    # ── Internal Helpers ─────────────────────────────────────────────

    def _safe_call(
        self, method_name: str, log_tag: str = "API", **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a Binance client method with retry logic and structured logging.

        Retries on network errors and transient API errors (rate limits, etc.).
        Fails immediately on client errors (invalid parameters, auth failures).
        """
        method = getattr(self._client, method_name, None)
        if method is None:
            raise BotAPIError(f"Unknown Binance client method: {method_name}")

        last_exception = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(
                    f"[{log_tag}] Attempt {attempt}/{MAX_RETRIES} → "
                    f"{method_name}({kwargs})"
                )
                result = method(**kwargs)
                logger.debug(f"[{log_tag}] Response: {result}")
                return result

            except BinanceAPIException as exc:
                last_exception = exc
                logger.error(
                    f"[{log_tag}] Binance API error (code={exc.code}): {exc.message}"
                )

                # Non-retryable errors (client mistakes, validation failures)
                if exc.code in (
                    -1013,  # Invalid quantity
                    -1021,  # Timestamp issue
                    -1100,  # Illegal characters
                    -1102,  # Missing mandatory parameter
                    -1121,  # Invalid symbol
                    -2010,  # Insufficient margin
                    -2015,  # Invalid API key
                    -4003,  # Quantity LOT_SIZE violation
                    -4016,  # Price filter violation (price too high/low)
                    -4164,  # Min notional violation (price × qty too small)
                ):
                    raise BotAPIError(
                        f"Binance API error: {exc.message}",
                        code=exc.code,
                        original=exc,
                    ) from exc

                # Retryable (rate limit, server issues)
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_SECONDS * attempt
                    logger.warning(f"[{log_tag}] Retrying in {delay}s…")
                    time.sleep(delay)

            except BinanceRequestException as exc:
                last_exception = exc
                logger.error(f"[{log_tag}] Network / request error: {exc}")
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_SECONDS * attempt
                    logger.warning(f"[{log_tag}] Retrying in {delay}s…")
                    time.sleep(delay)

            except Exception as exc:
                last_exception = exc
                logger.error(f"[{log_tag}] Unexpected error: {exc}")
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_SECONDS * attempt
                    logger.warning(f"[{log_tag}] Retrying in {delay}s…")
                    time.sleep(delay)

        raise BotAPIError(
            f"API call {method_name} failed after {MAX_RETRIES} attempts",
            original=last_exception,
        )
