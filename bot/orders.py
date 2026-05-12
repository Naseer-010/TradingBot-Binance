"""
Order Placement Logic
=====================

Orchestration layer that sits between the CLI and the Binance client.
Responsibilities:
  • Validate inputs (via validators module)
  • Delegate to the appropriate client method
  • Return structured results
  • Handle and log all errors gracefully

This module is agnostic to the UI — it can be called from CLI, API, or tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from bot.client import (
    BinanceFuturesClient,
    BotAPIError,
    BotConfigError,
    BotNetworkError,
    OrderResponse,
)
from bot.validators import validate_order_params

logger = logging.getLogger("trading_bot.orders")


# ── Result Wrapper ───────────────────────────────────────────────────


@dataclass
class OrderResult:
    """Encapsulates the outcome of an order attempt."""

    success: bool
    response: Optional[OrderResponse] = None
    error: Optional[str] = None
    error_code: Optional[int] = None


# ── Order Dispatcher ─────────────────────────────────────────────────


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> OrderResult:
    """
    Validate inputs and place an order on Binance Futures Testnet.

    Args:
        client:     Initialised BinanceFuturesClient instance.
        symbol:     Trading pair (e.g., BTCUSDT).
        side:       BUY or SELL.
        order_type: MARKET, LIMIT, or STOP_LIMIT.
        quantity:   Order quantity.
        price:      Limit price (required for LIMIT / STOP_LIMIT).
        stop_price: Trigger price (required for STOP_LIMIT).

    Returns:
        OrderResult with success/failure details.
    """
    # Normalise inputs
    symbol = (symbol or "").upper().strip()
    side = (side or "").upper().strip()
    order_type = (order_type or "").upper().strip().replace("-", "_").replace(" ", "_")

    # ── Validation ───────────────────────────────────────────────
    validation = validate_order_params(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )

    if not validation:
        logger.error(f"Validation failed: {validation.error}")
        return OrderResult(success=False, error=validation.error)

    # ── Dispatch ─────────────────────────────────────────────────
    try:
        if order_type == "MARKET":
            response = client.place_market_order(symbol, side, quantity)

        elif order_type == "LIMIT":
            response = client.place_limit_order(symbol, side, quantity, price)

        elif order_type == "STOP_LIMIT":
            response = client.place_stop_limit_order(
                symbol, side, quantity, price, stop_price
            )

        else:
            # Should never reach here due to validation, but just in case
            return OrderResult(
                success=False,
                error=f"Unsupported order type: {order_type}",
            )

        return OrderResult(success=True, response=response)

    except BotAPIError as exc:
        logger.error(f"API error placing {order_type} order: {exc}")
        return OrderResult(
            success=False,
            error=str(exc),
            error_code=exc.code,
        )

    except BotNetworkError as exc:
        logger.error(f"Network error placing {order_type} order: {exc}")
        return OrderResult(
            success=False,
            error=f"Network error: {exc}",
        )

    except BotConfigError as exc:
        logger.error(f"Configuration error: {exc}")
        return OrderResult(
            success=False,
            error=f"Configuration error: {exc}",
        )

    except Exception as exc:
        logger.exception(f"Unexpected error placing {order_type} order")
        return OrderResult(
            success=False,
            error=f"Unexpected error: {exc}",
        )
