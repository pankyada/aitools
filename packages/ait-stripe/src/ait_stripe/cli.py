"""Typer CLI for `ait-stripe`."""

from __future__ import annotations

import asyncio
import getpass
import os

import typer
from ait_core.auth.api_key_store import APIKeyStore
from ait_core.config.settings import load_settings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.output.formatter import (
    CommandResponse,
    OutputMode,
    command_timer,
    format_output,
    make_error_response,
    make_success_response,
)

from ait_stripe.commands.balance import run_balance
from ait_stripe.commands.charges import run_get_charge, run_list_charges
from ait_stripe.commands.customers import run_get_customer, run_list_customers
from ait_stripe.commands.invoices import run_get_invoice, run_list_invoices
from ait_stripe.commands.payments import run_get_payment, run_list_payments
from ait_stripe.commands.subscriptions import run_get_subscription, run_list_subscriptions

app = typer.Typer(help="Stripe API command-line interface")
auth_app = typer.Typer(help="Auth and API-key operations")
customers_app = typer.Typer(help="Customer operations")
charges_app = typer.Typer(help="Charge operations")
payments_app = typer.Typer(help="Payment intent operations")
subscriptions_app = typer.Typer(help="Subscription operations")
invoices_app = typer.Typer(help="Invoice operations")

app.add_typer(auth_app, name="auth")
app.add_typer(customers_app, name="customers")
app.add_typer(charges_app, name="charges")
app.add_typer(payments_app, name="payments")
app.add_typer(subscriptions_app, name="subscriptions")
app.add_typer(invoices_app, name="invoices")


def _print(mode: OutputMode, response: CommandResponse) -> None:
    """Render and print response.

    Args:
        mode: Output mode.
        response: Response envelope.

    Returns:
        None.

    Raises:
        None.
    """

    rendered = format_output(response, mode)
    if rendered:
        print(rendered)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@auth_app.command("set-key")
def auth_set_key(
    env: bool = typer.Option(False, "--env", help="Read key from AIT_STRIPE_API_KEY"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Set Stripe API key in encrypted store.

    Examples:
        ait-stripe auth set-key
        ait-stripe auth set-key --env
    """

    start = command_timer()
    try:
        key_store = APIKeyStore()
        key = (
            os.getenv("AIT_STRIPE_API_KEY", "").strip()
            if env
            else getpass.getpass("Stripe API key: ").strip()
        )
        if not key:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Stripe API key cannot be empty",
                exit_code=ExitCode.INVALID_INPUT,
            )

        key_store.set_key("stripe", key)
        response = make_success_response("ait-stripe", "auth set-key", {"configured": True}, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "auth set-key", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("status")
def auth_status(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Show Stripe auth status.

    Examples:
        ait-stripe auth status
    """

    start = command_timer()
    try:
        key_store = APIKeyStore()
        key = key_store.get_key("stripe")
        response = make_success_response(
            "ait-stripe",
            "auth status",
            {
                "configured": key is not None,
                "preview": APIKeyStore.mask_value(key) if key else None,
            },
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "auth status", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------


@app.command("balance")
def balance(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Retrieve account balance.

    Examples:
        ait-stripe balance
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_balance(load_settings()))
        response = make_success_response("ait-stripe", "balance", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "balance", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


@customers_app.command("list")
def list_customers(
    limit: int = typer.Option(20, "--limit", help="Max records"),
    starting_after: str | None = typer.Option(None, "--starting-after", help="Pagination cursor"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List Stripe customers.

    Examples:
        ait-stripe customers list --limit 10
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_list_customers(load_settings(), limit=limit, starting_after=starting_after)
        )
        response = make_success_response("ait-stripe", "customers list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "customers list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@customers_app.command("get")
def get_customer(
    customer_id: str = typer.Argument(..., help="Stripe customer ID"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get a Stripe customer by ID.

    Examples:
        ait-stripe customers get cus_abc123
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_get_customer(load_settings(), customer_id=customer_id))
        response = make_success_response("ait-stripe", "customers get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "customers get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


# ---------------------------------------------------------------------------
# Charges
# ---------------------------------------------------------------------------


@charges_app.command("list")
def list_charges(
    limit: int = typer.Option(20, "--limit", help="Max records"),
    customer: str | None = typer.Option(None, "--customer", help="Filter by customer ID"),
    starting_after: str | None = typer.Option(None, "--starting-after", help="Pagination cursor"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List Stripe charges.

    Examples:
        ait-stripe charges list --limit 10 --customer cus_abc123
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_list_charges(
                load_settings(), limit=limit, customer=customer, starting_after=starting_after
            )
        )
        response = make_success_response("ait-stripe", "charges list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "charges list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@charges_app.command("get")
def get_charge(
    charge_id: str = typer.Argument(..., help="Stripe charge ID"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get a Stripe charge by ID.

    Examples:
        ait-stripe charges get ch_abc123
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_get_charge(load_settings(), charge_id=charge_id))
        response = make_success_response("ait-stripe", "charges get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "charges get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


@payments_app.command("list")
def list_payments(
    limit: int = typer.Option(20, "--limit", help="Max records"),
    customer: str | None = typer.Option(None, "--customer", help="Filter by customer ID"),
    starting_after: str | None = typer.Option(None, "--starting-after", help="Pagination cursor"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List Stripe payment intents.

    Examples:
        ait-stripe payments list --limit 10
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_list_payments(
                load_settings(), limit=limit, customer=customer, starting_after=starting_after
            )
        )
        response = make_success_response("ait-stripe", "payments list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "payments list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@payments_app.command("get")
def get_payment(
    payment_id: str = typer.Argument(..., help="Stripe payment intent ID"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get a Stripe payment intent by ID.

    Examples:
        ait-stripe payments get pi_abc123
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_get_payment(load_settings(), payment_id=payment_id))
        response = make_success_response("ait-stripe", "payments get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "payments get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


@subscriptions_app.command("list")
def list_subscriptions(
    limit: int = typer.Option(20, "--limit", help="Max records"),
    customer: str | None = typer.Option(None, "--customer", help="Filter by customer ID"),
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    starting_after: str | None = typer.Option(None, "--starting-after", help="Pagination cursor"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List Stripe subscriptions.

    Examples:
        ait-stripe subscriptions list --status active
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_list_subscriptions(
                load_settings(),
                limit=limit,
                customer=customer,
                status=status,
                starting_after=starting_after,
            )
        )
        response = make_success_response("ait-stripe", "subscriptions list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "subscriptions list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@subscriptions_app.command("get")
def get_subscription(
    subscription_id: str = typer.Argument(..., help="Stripe subscription ID"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get a Stripe subscription by ID.

    Examples:
        ait-stripe subscriptions get sub_abc123
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_get_subscription(load_settings(), subscription_id=subscription_id)
        )
        response = make_success_response("ait-stripe", "subscriptions get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "subscriptions get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


@invoices_app.command("list")
def list_invoices(
    limit: int = typer.Option(20, "--limit", help="Max records"),
    customer: str | None = typer.Option(None, "--customer", help="Filter by customer ID"),
    starting_after: str | None = typer.Option(None, "--starting-after", help="Pagination cursor"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List Stripe invoices.

    Examples:
        ait-stripe invoices list --limit 10
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_list_invoices(
                load_settings(), limit=limit, customer=customer, starting_after=starting_after
            )
        )
        response = make_success_response("ait-stripe", "invoices list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "invoices list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@invoices_app.command("get")
def get_invoice(
    invoice_id: str = typer.Argument(..., help="Stripe invoice ID"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get a Stripe invoice by ID.

    Examples:
        ait-stripe invoices get in_abc123
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_get_invoice(load_settings(), invoice_id=invoice_id))
        response = make_success_response("ait-stripe", "invoices get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-stripe", "invoices get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


if __name__ == "__main__":
    app()
