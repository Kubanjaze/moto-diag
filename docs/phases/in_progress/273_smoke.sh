#!/usr/bin/env bash
# Phase 273 — the smoke calls and the webhook run, in Stripe's test mode.
#
#   bash docs/phases/in_progress/273_smoke.sh prepare   # scratch copy of live
#   bash docs/phases/in_progress/273_smoke.sh check
#   bash docs/phases/in_progress/273_smoke.sh connect   # prints the onboarding link
#   bash docs/phases/in_progress/273_smoke.sh status
#   bash docs/phases/in_progress/273_smoke.sh setup     # the simulated reader
#   bash docs/phases/in_progress/273_smoke.sh webhook   # server + stripe listen, end to end
#   bash docs/phases/in_progress/273_smoke.sh summary
#
# The keys are loaded from ~/.config/motodiag/stripe-test.env into this
# process's environment and never printed. The webhook secret goes from
# `stripe listen --print-secret` straight into the server's environment;
# `stripe listen`'s own output, which names it, is redacted before it is
# written. Never `set -x` in this file.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
PY="$ROOT/.venv/bin/python"
RUN="$HERE/273_smoke"
KEYS="$HOME/.config/motodiag/stripe-test.env"
DB="$HOME/.cache/motodiag/phase273/smoke.db"
PORT=8273
STAGE="${1:?stage}"
mkdir -p "$RUN"

export MOTODIAG_DB_PATH="$DB"

if [[ "$STAGE" == "prepare" ]]; then
  exec "$PY" "$HERE/273_smoke.py" prepare
fi

[[ -f "$KEYS" ]] || { echo "missing $KEYS"; exit 1; }
perm="$(stat -f '%Lp' "$KEYS")"
[[ "$perm" == "600" ]] || { echo "$KEYS must be mode 600 (it is $perm)"; exit 1; }
set -a
# shellcheck disable=SC1090
. "$KEYS"
set +a
case "${MOTODIAG_STRIPE_API_KEY:-}" in
  sk_test_*|rk_test_*) ;;
  *) echo "the key in $KEYS is not a test-mode key; nothing was called"; exit 1 ;;
esac
export MOTODIAG_BILLING_PROVIDER=stripe
export MOTODIAG_ENV=dev
export MOTODIAG_STRIPE_CALL_LOG="$RUN/calls.jsonl"

if [[ "$STAGE" != "webhook" && "$STAGE" != "resend" ]]; then
  exec "$PY" "$HERE/273_smoke.py" "$STAGE"
fi
# `resend EVT_ID`: the server and stripe listen again, then Stripe
# redelivers that event (`stripe events resend`), then the portal call.

# ---- the webhook run: stripe listen -> a server on the scratch copy -------
command -v stripe >/dev/null || { echo "the Stripe CLI is not installed"; exit 1; }
MOTODIAG_STRIPE_WEBHOOK_SECRET="$(stripe listen --print-secret)"
export MOTODIAG_STRIPE_WEBHOOK_SECRET
[[ "$MOTODIAG_STRIPE_WEBHOOK_SECRET" == whsec_* ]] || { echo "stripe listen gave no secret (is the CLI logged in?)"; exit 1; }

EVENTS="payment_intent.succeeded,payment_intent.payment_failed,charge.refunded,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.paid,invoice.payment_failed"
URL="http://127.0.0.1:$PORT/v1/billing/webhooks/stripe"

LOGTAG=""
[[ "$STAGE" == "resend" ]] && LOGTAG="_resend"
"$ROOT/.venv/bin/motodiag" serve --host 127.0.0.1 --port "$PORT" > "$RUN/server$LOGTAG.log" 2>&1 &
SERVER=$!
stripe listen --latest --events "$EVENTS" --forward-to "$URL" --forward-connect-to "$URL" 2>&1 \
  | sed -u -E 's/whsec_[A-Za-z0-9]+/whsec_[redacted]/g' > "$RUN/listen$LOGTAG.log" &
LISTEN=$!
cleanup() { kill "$SERVER" 2>/dev/null || true; pkill -f "stripe listen --latest --events" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup EXIT

for _ in $(seq 1 60); do
  curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1 && grep -q "Ready" "$RUN/listen$LOGTAG.log" && break
  sleep 1
done
curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null || { echo "the server did not start; see $RUN/server$LOGTAG.log"; exit 1; }
grep -q "Ready" "$RUN/listen$LOGTAG.log" || { echo "stripe listen did not get ready; see $RUN/listen$LOGTAG.log"; exit 1; }
echo "server on 127.0.0.1:$PORT (scratch copy), stripe listen ready"

wait_for() {  # wait_for <seconds> <sql> <expected>
  local t="$1" q="$2" want="$3" got=""
  for _ in $(seq 1 "$t"); do
    got="$(sqlite3 "$DB" "$q" 2>/dev/null || true)"
    [[ "$got" == "$want" ]] && { echo "  -> $got"; return 0; }
    sleep 1
  done
  echo "  -> timed out; last value: '$got' (wanted '$want')"; return 1
}
IDS="$RUN/ids.json"
TERMINAL_INV="$("$PY" -c "import json;print(json.load(open('$IDS'))['terminal_invoice'])")"
CHECKOUT_INV="$("$PY" -c "import json;print(json.load(open('$IDS'))['checkout_invoice'])")"
USER_ID="$("$PY" -c "import json;print(json.load(open('$IDS'))['user'])")"

if [[ "$STAGE" == "resend" ]]; then
  EVT="${2:?event id}"
  echo "Stripe redelivers $EVT"
  stripe events resend "$EVT" > "$RUN/resend.json"
  wait_for 120 "SELECT event_id FROM stripe_webhook_events WHERE event_id = '$EVT' AND processed_at IS NOT NULL" "$EVT"
  echo "4. The customer portal for that subscription"
  "$PY" "$HERE/273_smoke.py" portal
  "$PY" "$HERE/273_smoke.py" summary
  exit 0
fi

echo "1. Terminal: the simulated reader pays invoice $TERMINAL_INV"
"$PY" "$HERE/273_smoke.py" terminal
wait_for 90 "SELECT status FROM invoices WHERE id = $TERMINAL_INV" "paid"

echo "2. Checkout: pay the invoice link below in a browser with card 4242 4242 4242 4242"
"$PY" "$HERE/273_smoke.py" paylink
wait_for 600 "SELECT status FROM invoices WHERE id = $CHECKOUT_INV" "paid"

echo "3. Subscription: pay the checkout link below with card 4242 4242 4242 4242"
"$PY" "$HERE/273_smoke.py" checkout
wait_for 600 "SELECT tier || ' ' || status FROM subscriptions WHERE user_id = $USER_ID AND stripe_subscription_id IS NOT NULL" "shop active"
wait_for 120 "SELECT status FROM subscription_payments WHERE user_id = $USER_ID" "paid"

echo "4. The customer portal for that subscription"
"$PY" "$HERE/273_smoke.py" portal

"$PY" "$HERE/273_smoke.py" summary
