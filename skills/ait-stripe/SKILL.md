---
name: ait-stripe
description: Use when users need Stripe payment workflows in ai-toolset CLI, including API key setup/status, balance retrieval, customers, charges, payment intents, subscriptions, and invoices.
---

# AIT Stripe

Use this skill for `ait-stripe` Stripe API integrations and command flows.

## Scope

- `packages/ait-stripe/src/ait_stripe/cli.py`
- `packages/ait-stripe/src/ait_stripe/client.py`
- `packages/ait-stripe/src/ait_stripe/models.py`
- `packages/ait-stripe/src/ait_stripe/commands/*.py`
- `tests/test_stripe/`

## Command Playbook

```bash
ait-stripe auth set-key
ait-stripe auth set-key --env          # reads AIT_STRIPE_API_KEY env var
ait-stripe auth status

ait-stripe balance

ait-stripe customers list
ait-stripe customers list --limit 50
ait-stripe customers list --starting-after cus_abc123
ait-stripe customers get cus_abc123

ait-stripe charges list
ait-stripe charges list --customer cus_abc123 --limit 10
ait-stripe charges get ch_abc123

ait-stripe payments list
ait-stripe payments list --customer cus_abc123
ait-stripe payments get pi_abc123

ait-stripe subscriptions list
ait-stripe subscriptions list --customer cus_abc123 --status active
ait-stripe subscriptions get sub_abc123

ait-stripe invoices list
ait-stripe invoices list --customer cus_abc123 --limit 20
ait-stripe invoices get in_abc123
```

## Guardrails

- API key is stored via `ait-core` `APIKeyStore` under the `"stripe"` service name.
- `StripeClient` resolves key from `settings.stripe.api_key` first, then keystore.
- All list endpoints support cursor-based pagination via `--starting-after`.
- `None` params are filtered before sending to Stripe to avoid empty query parameters.
