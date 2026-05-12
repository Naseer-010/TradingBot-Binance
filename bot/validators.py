"""
Input Validators
================

Pure validation functions for all user-supplied trading parameters.
Each validator returns (is_valid: bool, error_message: str | None).

Design philosophy:
  • Fail fast with descriptive messages
  • No side effects — pure functions only
  • Centralised so both CLI and programmatic callers share the same rules
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# ── Constants ────────────────────────────────────────────────────────

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
SYMBOL_PATTERN = re.compile(r"^[A-Z]{2,10}USDT$")

MIN_QUANTITY = 0.00001
MAX_QUANTITY = 1_000_000
MIN_PRICE = 0.01
MAX_PRICE = 1_000_000_000


@dataclass(frozen=True)
class ValidationResult:
    """Immutable validation outcome."""

    valid: bool
    error: Optional[str] = None

    def __bool__(self) -> bool:
        return self.valid


# ── Individual Validators ────────────────────────────────────────────


def validate_symbol(symbol: str) -> ValidationResult:
    """
    Validate a trading pair symbol.

    Rules:
      • Must be uppercase
      • Must end with USDT (Futures USDT-M)
      • Only alphabetic characters, 2-10 chars before 'USDT'
    """
    if not symbol:
        return ValidationResult(False, "Symbol cannot be empty")

    symbol = symbol.upper().strip()

    if not SYMBOL_PATTERN.match(symbol):
        return ValidationResult(
            False,
            f"Invalid symbol '{symbol}'. "
            f"Expected format: <BASE>USDT (e.g., BTCUSDT, ETHUSDT). "
            f"Must be 2-10 uppercase letters followed by 'USDT'.",
        )

    return ValidationResult(True)


def validate_side(side: str) -> ValidationResult:
    """Validate order side (BUY / SELL)."""
    if not side:
        return ValidationResult(False, "Side cannot be empty")

    side = side.upper().strip()

    if side not in VALID_SIDES:
        return ValidationResult(
            False,
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}",
        )

    return ValidationResult(True)


def validate_order_type(order_type: str) -> ValidationResult:
    """Validate order type (MARKET / LIMIT / STOP_LIMIT)."""
    if not order_type:
        return ValidationResult(False, "Order type cannot be empty")

    order_type = order_type.upper().strip()

    if order_type not in VALID_ORDER_TYPES:
        return ValidationResult(
            False,
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}",
        )

    return ValidationResult(True)


def validate_quantity(quantity: float) -> ValidationResult:
    """Validate order quantity."""
    if quantity is None:
        return ValidationResult(False, "Quantity is required")

    try:
        qty = float(quantity)
    except (ValueError, TypeError):
        return ValidationResult(False, f"Quantity must be a number, got '{quantity}'")

    if qty <= 0:
        return ValidationResult(False, f"Quantity must be positive, got {qty}")

    if qty < MIN_QUANTITY:
        return ValidationResult(
            False,
            f"Quantity {qty} is below minimum ({MIN_QUANTITY})",
        )

    if qty > MAX_QUANTITY:
        return ValidationResult(
            False,
            f"Quantity {qty} exceeds maximum ({MAX_QUANTITY:,})",
        )

    return ValidationResult(True)


def validate_price(price: Optional[float], order_type: str) -> ValidationResult:
    """
    Validate price based on order type.

    • MARKET orders: price must be None or 0
    • LIMIT / STOP_LIMIT orders: price is required and must be positive
    """
    order_type = (order_type or "").upper().strip()

    if order_type == "MARKET":
        if price is not None and price > 0:
            return ValidationResult(
                False,
                "Price should not be specified for MARKET orders "
                "(the order executes at the current market price)",
            )
        return ValidationResult(True)

    # LIMIT and STOP_LIMIT require a price
    if price is None or price <= 0:
        return ValidationResult(
            False,
            f"Price is required for {order_type} orders and must be positive",
        )

    if price < MIN_PRICE:
        return ValidationResult(
            False,
            f"Price {price} is below minimum ({MIN_PRICE})",
        )

    if price > MAX_PRICE:
        return ValidationResult(
            False,
            f"Price {price} exceeds maximum ({MAX_PRICE:,.2f})",
        )

    return ValidationResult(True)


def validate_stop_price(
    stop_price: Optional[float], order_type: str
) -> ValidationResult:
    """
    Validate stop price — required only for STOP_LIMIT orders.
    """
    order_type = (order_type or "").upper().strip()

    if order_type != "STOP_LIMIT":
        return ValidationResult(True)

    if stop_price is None or stop_price <= 0:
        return ValidationResult(
            False,
            "Stop price is required for STOP_LIMIT orders and must be positive",
        )

    if stop_price < MIN_PRICE:
        return ValidationResult(
            False,
            f"Stop price {stop_price} is below minimum ({MIN_PRICE})",
        )

    if stop_price > MAX_PRICE:
        return ValidationResult(
            False,
            f"Stop price {stop_price} exceeds maximum ({MAX_PRICE:,.2f})",
        )

    return ValidationResult(True)


# ── Aggregate Validator ──────────────────────────────────────────────


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> ValidationResult:
    """
    Run all validations in sequence. Returns the first failure, or success.
    """
    checks = [
        validate_symbol(symbol),
        validate_side(side),
        validate_order_type(order_type),
        validate_quantity(quantity),
        validate_price(price, order_type),
        validate_stop_price(stop_price, order_type),
    ]

    for result in checks:
        if not result:
            return result

    return ValidationResult(True)
