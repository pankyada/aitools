# ait-stripe

Stripe API command-line tool for the ai-toolset.

## Commands

```
ait-stripe auth set-key        Set Stripe secret key
ait-stripe auth status         Show auth status

ait-stripe balance             Retrieve account balance

ait-stripe customers list      List customers
ait-stripe customers get <id>  Get customer by ID

ait-stripe charges list        List charges (optionally filter by customer)
ait-stripe charges get <id>    Get charge by ID

ait-stripe payments list       List payment intents
ait-stripe payments get <id>   Get payment intent by ID

ait-stripe subscriptions list  List subscriptions (optionally filter by customer/status)
ait-stripe subscriptions get <id>  Get subscription by ID

ait-stripe invoices list       List invoices (optionally filter by customer/status)
ait-stripe invoices get <id>   Get invoice by ID
```

## Setup

```bash
ait-stripe auth set-key
# or via environment variable
AIT_STRIPE_API_KEY=sk_... ait-stripe auth set-key --env
```
