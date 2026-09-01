# multiply

agent multi tasking for a single project in 60days

## Valuation & bid auto-notifier

Tracks player market value and club enterprise ("face") value with
transparent, explainable formulas, and automatically notifies investors and
fans when a new bid comes in for a watched player or club.

- `src/multiply/valuation.py` — first-principles valuation multipliers
  (age curve, performance, contract length, league tier for players;
  revenue multiple, squad value, net debt for clubs).
- `src/multiply/models.py` — `Player`, `Club`, `Bid`, `Subscriber`.
- `src/multiply/store.py` — SQLite persistence.
- `src/multiply/notifier.py` — pluggable channels: console (default, no
  setup needed), email (SMTP via env vars), webhook (Slack/Discord-style
  JSON POST).
- `src/multiply/service.py` — `ValuationService.submit_bid(...)` records a
  bid and auto-dispatches investor vs. fan notifications when the bid is a
  new high, moves >=5% from the model valuation, or is marked verified.
- `src/multiply/cli.py` — command-line interface.

### Quick start

```bash
PYTHONPATH=src python examples/demo.py
```

### CLI usage

```bash
export PYTHONPATH=src

python -m multiply.cli add-club --id ofc --name "Oakview FC" \
    --revenue 90000000 --net-debt 20000000 --tier 2

python -m multiply.cli add-player --id p1 --name "A. Rossi" --age 24 \
    --position ST --performance 78 --contract-years 2.5 --tier 2 --club ofc

python -m multiply.cli add-subscriber --id inv1 --name "Riverbend Capital" \
    --audience investor --channel console --contact riverbend --watch ofc p1

python -m multiply.cli add-subscriber --id fan1 --name "Sam" \
    --audience fan --channel console --contact sam

python -m multiply.cli bid --target-type club --target-id ofc \
    --bidder "Northstar Partners" --amount 260000000 --verified

python -m multiply.cli value --target-type club --target-id ofc
```

To actually deliver email/webhook notifications (instead of console), set:

- Email: `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- Webhook: give the subscriber's `--contact` a Slack/Discord incoming-webhook URL

### Tests

```bash
pip install -e .[dev]
pytest
```
