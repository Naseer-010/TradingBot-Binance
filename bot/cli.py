"""
CLI Entry Point — Enhanced UX with Rich + Click
================================================

Two interaction modes:
  1. **Direct**  : `python -m bot.cli order --symbol BTCUSDT --side BUY ...`
  2. **Interactive** : `python -m bot.cli` → beautiful guided menu

Features:
  • Rich panels, tables, and spinners for premium terminal UX
  • Pre-order confirmation with order summary
  • Post-order result display with colour-coded status
  • Account balance preview
  • Full error display with actionable suggestions
"""

from __future__ import annotations

import sys
import os
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, Prompt
from rich.table import Table
from rich.text import Text
from rich import box

from bot import __version__
from bot.client import (
    BinanceFuturesClient,
    BotAPIError,
    BotConfigError,
    BotNetworkError,
)
from bot.logging_config import setup_logging
from bot.orders import OrderResult, place_order
from bot.validators import VALID_ORDER_TYPES, VALID_SIDES

console = Console()

# ── Branding ─────────────────────────────────────────────────────────

BANNER = r"""
[bold cyan]
  ██████╗ ██████╗ ██╗███╗   ███╗███████╗████████╗██████╗  █████╗ ██████╗ ███████╗
  ██╔══██╗██╔══██╗██║████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝
  ██████╔╝██████╔╝██║██╔████╔██║█████╗     ██║   ██████╔╝███████║██║  ██║█████╗  
  ██╔═══╝ ██╔══██╗██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  
  ██║     ██║  ██║██║██║ ╚═╝ ██║███████╗   ██║   ██║  ██║██║  ██║██████╔╝███████╗
  ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
[/bold cyan]
[dim]  Binance Futures Testnet Trading Bot  •  v{version}[/dim]
""".replace(
    "{version}", __version__
)


# ── Display Helpers ──────────────────────────────────────────────────


def show_banner():
    """Display the application banner."""
    console.print(BANNER)


def show_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
    current_price: Optional[float] = None,
):
    """Display a pre-execution order summary panel."""
    table = Table(
        box=box.ROUNDED,
        show_header=False,
        padding=(0, 2),
        title="📋 Order Summary",
        title_style="bold white",
    )
    table.add_column("Field", style="dim cyan", width=18)
    table.add_column("Value", style="bold white")

    table.add_row("Symbol", f"[bold yellow]{symbol}[/]")

    side_color = "green" if side == "BUY" else "red"
    table.add_row("Side", f"[bold {side_color}]{side}[/]")
    table.add_row("Order Type", f"[bold magenta]{order_type}[/]")
    table.add_row("Quantity", f"[bold]{quantity}[/]")

    if current_price:
        table.add_row("Current Price", f"[dim]${current_price:,.2f}[/]")

    if price and order_type != "MARKET":
        table.add_row("Limit Price", f"[bold]${price:,.2f}[/]")

    if stop_price and order_type == "STOP_LIMIT":
        table.add_row("Stop Price", f"[bold yellow]${stop_price:,.2f}[/]")

    if price and current_price and order_type != "MARKET":
        diff_pct = ((price - current_price) / current_price) * 100
        diff_color = "green" if diff_pct >= 0 else "red"
        table.add_row(
            "Price vs Market",
            f"[{diff_color}]{diff_pct:+.2f}%[/]",
        )

    console.print()
    console.print(table)
    console.print()


def show_order_result(result: OrderResult):
    """Display the order execution result."""
    if result.success and result.response:
        resp = result.response

        table = Table(
            box=box.DOUBLE_EDGE,
            show_header=False,
            padding=(0, 2),
            title="✅ Order Executed Successfully",
            title_style="bold green",
            border_style="green",
        )
        table.add_column("Field", style="dim cyan", width=18)
        table.add_column("Value", style="bold white")

        table.add_row("Order ID", f"[bold yellow]{resp.order_id}[/]")
        table.add_row("Symbol", resp.symbol)

        side_color = "green" if resp.side == "BUY" else "red"
        table.add_row("Side", f"[bold {side_color}]{resp.side}[/]")
        table.add_row("Type", resp.order_type)

        status_color = {
            "NEW": "yellow",
            "FILLED": "green",
            "PARTIALLY_FILLED": "cyan",
            "CANCELED": "red",
            "EXPIRED": "red",
        }.get(resp.status, "white")
        table.add_row("Status", f"[bold {status_color}]{resp.status}[/]")

        table.add_row("Quantity", resp.quantity)
        table.add_row("Executed Qty", resp.executed_qty)
        table.add_row("Price", f"${float(resp.price):,.2f}" if float(resp.price) > 0 else "Market")
        table.add_row("Avg Price", f"${float(resp.avg_price):,.2f}" if float(resp.avg_price) > 0 else "N/A")

        if resp.time_in_force:
            table.add_row("Time in Force", resp.time_in_force)

        console.print()
        console.print(table)
        console.print()

    else:
        error_panel = Panel(
            Text(f"\n{result.error}\n", style="bold red"),
            title="❌ Order Failed",
            title_align="left",
            border_style="red",
            padding=(1, 2),
        )
        console.print()
        console.print(error_panel)

        # Actionable suggestions
        if result.error_code:
            suggestions = {
                -1013: "Check that quantity meets the symbol's minimum notional / step size.",
                -1021: "Timestamp issue. Check your system clock synchronisation.",
                -1100: "Illegal characters in a parameter. Verify all inputs.",
                -1102: "A mandatory parameter was missing. Verify all inputs.",
                -1121: "Invalid symbol. Use `BTCUSDT`, `ETHUSDT`, etc.",
                -2010: "Insufficient margin. Check your testnet account balance.",
                -2015: "Invalid API key or permissions. Regenerate your testnet keys.",
                -4003: "Quantity must comply with LOT_SIZE filter.",
                -4016: "Price exceeds allowed range. BUY LIMIT price must be below ~105% of market price. "
                       "Try a price closer to or below the current market price.",
                -4164: "Order value (price × quantity) is too small — minimum is $50. "
                       "Increase the quantity or the price.",
            }
            suggestion = suggestions.get(result.error_code)
            if suggestion:
                console.print(
                    f"  [dim yellow]💡 Suggestion: {suggestion}[/]"
                )
        console.print()


def show_account_balance(client: BinanceFuturesClient):
    """Display account balance summary."""
    try:
        account = client.get_account_info()
        assets = account.get("assets", [])

        # Filter to non-zero balances
        active_assets = [
            a
            for a in assets
            if float(a.get("walletBalance", 0)) > 0
        ]

        if not active_assets:
            console.print("[dim]No assets with balance found.[/]")
            return

        table = Table(
            title="💰 Account Balance",
            title_style="bold white",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        table.add_column("Asset", style="bold cyan")
        table.add_column("Wallet Balance", style="bold green", justify="right")
        table.add_column("Unrealised PnL", style="bold yellow", justify="right")
        table.add_column("Available", style="bold white", justify="right")

        for asset in active_assets[:10]:  # Top 10
            pnl = float(asset.get("unrealizedProfit", 0))
            pnl_style = "green" if pnl >= 0 else "red"
            table.add_row(
                asset.get("asset", "?"),
                f"{float(asset.get('walletBalance', 0)):,.4f}",
                f"[{pnl_style}]{pnl:+,.4f}[/]",
                f"{float(asset.get('availableBalance', 0)):,.4f}",
            )

        console.print()
        console.print(table)
        console.print()

    except Exception as exc:
        console.print(f"[dim red]Could not fetch account info: {exc}[/]")


# ── CLI Commands ─────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    🚀 Primetrade Trading Bot — Binance Futures Testnet

    Run without arguments for interactive mode, or use subcommands:

    \b
      trading-bot order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
      trading-bot balance
    """
    if ctx.invoked_subcommand is None:
        interactive_mode()


@cli.command()
@click.option("--symbol", "-s", required=True, help="Trading pair (e.g., BTCUSDT)")
@click.option(
    "--side",
    "-d",
    required=True,
    type=click.Choice(["BUY", "SELL"], case_sensitive=False),
    help="Order side",
)
@click.option(
    "--type",
    "-t",
    "order_type",
    required=True,
    type=click.Choice(["MARKET", "LIMIT", "STOP_LIMIT"], case_sensitive=False),
    help="Order type",
)
@click.option("--quantity", "-q", required=True, type=float, help="Order quantity")
@click.option(
    "--price",
    "-p",
    type=float,
    default=None,
    help="Limit price (required for LIMIT/STOP_LIMIT)",
)
@click.option(
    "--stop-price",
    "-sp",
    type=float,
    default=None,
    help="Stop/trigger price (required for STOP_LIMIT)",
)
@click.option(
    "--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt"
)
def order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
    yes: bool,
):
    """Place an order on Binance Futures Testnet."""
    logger = setup_logging()
    show_banner()

    try:
        client = BinanceFuturesClient()
    except (BotConfigError, BotNetworkError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)

    # Get current price for context
    current_price = client.get_ticker_price(symbol)

    show_order_summary(symbol, side, order_type, quantity, price, stop_price, current_price)

    if not yes:
        if not Confirm.ask("[bold]Confirm order placement?[/]", default=False):
            console.print("[dim]Order cancelled.[/]")
            sys.exit(0)

    with console.status("[bold cyan]Placing order…[/]", spinner="dots"):
        result = place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )

    show_order_result(result)
    sys.exit(0 if result.success else 1)


@cli.command()
def balance():
    """Show account balance on Binance Futures Testnet."""
    logger = setup_logging()
    show_banner()

    try:
        client = BinanceFuturesClient()
    except (BotConfigError, BotNetworkError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)

    show_account_balance(client)


@cli.command()
@click.option("--symbol", "-s", default="BTCUSDT", help="Trading pair")
def price(symbol: str):
    """Get the current price of a trading pair."""
    logger = setup_logging()

    try:
        client = BinanceFuturesClient()
    except (BotConfigError, BotNetworkError) as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)

    current = client.get_ticker_price(symbol)
    if current:
        console.print(
            Panel(
                f"[bold yellow]{symbol}[/]  →  [bold green]${current:,.2f}[/]",
                title="📈 Current Price",
                border_style="cyan",
                padding=(1, 3),
            )
        )
    else:
        console.print(f"[red]Could not fetch price for {symbol}[/]")


# ── Interactive Mode ─────────────────────────────────────────────────


def interactive_mode():
    """Beautiful interactive menu-driven trading interface."""
    logger = setup_logging()
    show_banner()

    console.print(
        Panel(
            "[bold]Welcome to the Primetrade Trading Bot![/]\n\n"
            "[dim]This bot connects to the Binance Futures Testnet (USDT-M)\n"
            "for safe, risk-free order placement and testing.[/]",
            border_style="cyan",
            padding=(1, 3),
        )
    )

    # Connect
    try:
        with console.status("[bold cyan]Connecting to Binance Futures Testnet…[/]", spinner="dots"):
            client = BinanceFuturesClient()
        console.print("[bold green]✓[/] Connected successfully!\n")
    except BotConfigError as exc:
        console.print(f"\n[bold red]Configuration Error:[/] {exc}")
        console.print(
            "\n[dim]Make sure your .env file contains "
            "BINANCE_API_KEY and BINANCE_API_SECRET[/]"
        )
        sys.exit(1)
    except BotNetworkError as exc:
        console.print(f"\n[bold red]Connection Error:[/] {exc}")
        sys.exit(1)

    # Show balance
    show_account_balance(client)

    while True:
        console.print(
            Panel(
                "[bold]What would you like to do?[/]\n\n"
                "  [cyan]1[/] → Place an order\n"
                "  [cyan]2[/] → Check account balance\n"
                "  [cyan]3[/] → Check current price\n"
                "  [cyan]4[/] → Exit",
                title="📌 Menu",
                title_align="left",
                border_style="blue",
                padding=(1, 3),
            )
        )

        choice = Prompt.ask(
            "[bold]Select option[/]",
            choices=["1", "2", "3", "4"],
            default="1",
        )

        if choice == "1":
            _interactive_place_order(client)
        elif choice == "2":
            show_account_balance(client)
        elif choice == "3":
            _interactive_check_price(client)
        elif choice == "4":
            console.print("\n[bold cyan]Goodbye! Happy trading! 👋[/]\n")
            break


def _interactive_place_order(client: BinanceFuturesClient):
    """Guide the user through placing an order interactively."""
    console.print("\n[bold]━━━ Place New Order ━━━[/]\n")

    # Symbol
    symbol = Prompt.ask(
        "[cyan]Symbol[/]",
        default="BTCUSDT",
    ).upper().strip()

    # Current price
    current_price = client.get_ticker_price(symbol)
    if current_price:
        console.print(f"  [dim]Current {symbol} price: ${current_price:,.2f}[/]")

    # Side
    side = Prompt.ask(
        "[cyan]Side[/]",
        choices=["BUY", "SELL", "buy", "sell"],
        default="BUY",
    ).upper()

    # Order Type
    order_type = Prompt.ask(
        "[cyan]Order Type[/]",
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        default="MARKET",
    ).upper()

    # Quantity
    quantity = FloatPrompt.ask("[cyan]Quantity[/]", default=0.001)

    # Price (for LIMIT / STOP_LIMIT)
    price = None
    stop_price_val = None

    if order_type in ("LIMIT", "STOP_LIMIT"):
        if current_price:
            # BUY LIMIT: set below market (you want to buy at a discount)
            # SELL LIMIT: set above market (you want to sell at a premium)
            if side == "BUY":
                default_price = round(current_price * 0.98, 2)  # 2% below market
            else:
                default_price = round(current_price * 1.02, 2)  # 2% above market
        else:
            default_price = 50000.0

        # Ensure quantity meets minimum notional ($50)
        min_qty_for_notional = 50.0 / default_price if default_price > 0 else 0.001
        if quantity < min_qty_for_notional:
            console.print(
                f"  [dim yellow]⚠ Adjusting quantity from {quantity} to "
                f"{round(min_qty_for_notional, 6)} to meet $50 minimum notional[/]"
            )
            quantity = round(min_qty_for_notional, 6)

        price = FloatPrompt.ask(
            "[cyan]Limit Price ($)[/]",
            default=default_price,
        )

    if order_type == "STOP_LIMIT":
        if current_price:
            # SELL stop: trigger below market; BUY stop: trigger above market
            if side == "SELL":
                default_stop = round(current_price * 0.99, 2)
            else:
                default_stop = round(current_price * 1.01, 2)
        else:
            default_stop = 49000.0
        stop_price_val = FloatPrompt.ask(
            "[cyan]Stop/Trigger Price ($)[/]",
            default=default_stop,
        )

    # Summary & confirmation
    show_order_summary(symbol, side, order_type, quantity, price, stop_price_val, current_price)

    if not Confirm.ask("[bold]Confirm order placement?[/]", default=True):
        console.print("[dim]Order cancelled.[/]\n")
        return

    # Execute
    with console.status("[bold cyan]Placing order…[/]", spinner="dots"):
        result = place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price_val,
        )

    show_order_result(result)


def _interactive_check_price(client: BinanceFuturesClient):
    """Interactively check a symbol's price."""
    symbol = Prompt.ask(
        "[cyan]Symbol[/]",
        default="BTCUSDT",
    ).upper().strip()

    current = client.get_ticker_price(symbol)
    if current:
        console.print(
            Panel(
                f"[bold yellow]{symbol}[/]  →  [bold green]${current:,.2f}[/]",
                title="📈 Current Price",
                border_style="cyan",
                padding=(1, 3),
            )
        )
    else:
        console.print(f"[red]Could not fetch price for {symbol}[/]")
    console.print()


# ── Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
