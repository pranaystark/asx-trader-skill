---
name: trader-broker
description: >-
  Order Executor. Writes the order ticket for your ASX broker, manual by
  default, never without your yes. Shows each order as a plain ticket (a
  bracket shows its stop-loss, take-profit and the max loss at the stop) plus
  the exact order fields, records your yes word for word, and, if the order is
  placed through a tool, your agent's own Allow once / Deny card asks again.
  Builds the sell ticket that closes a day trade by your flat-by time, records
  fills, and logs each trade's max loss so trader-risk can hold the daily
  limit. Never asks for broker keys, logins or 2FA: on the ASX you place the
  ticket at your own broker (CommSec, Stake, IBKR, Pearler, SelfWealth,
  Superhero). Use when the user says "place the order", "buy it", "execute",
  "close my position", "flatten", "get me out", "connect your broker", "set up
  paper trading", or after /trader-risk passes.
argument-hint: "[order number]"
---

# trader-broker

The Order Executor is the only skill in this pack that can lead to a real
order, so it is the strictest. An order reaches the market only after three
separate gates, every time, for every order:

1. **trader-risk passed this exact order today** (matched by fingerprint).
2. **The user typed an explicit yes for this one order** in the chat.
3. **The user clicked Allow once** on your agent's own permission card, which
   appears because the order tool is set to "Needs approval".

Two yeses from the user, one PASS from the rules. No yes, no order.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show                     # every ticket, READY or not
python3 "${CLAUDE_SKILL_DIR}/ticket.py" approve --index 1 --reply "yes"
python3 "${CLAUDE_SKILL_DIR}/ticket.py" result --index 1 --status placed --broker-id ID --filled-qty 8 --filled-price 364.20
python3 "${CLAUDE_SKILL_DIR}/ticket.py" fill --symbol BHP --side sell --qty 8 --price 370.04
python3 "${CLAUDE_SKILL_DIR}/ticket.py" flatten --symbol BHP --qty 8
python3 "${CLAUDE_SKILL_DIR}/ticket.py" log
```

`ticket.py` never talks to a broker. It renders tickets, checks that a reply
is a real yes for that order, builds the flatten ticket, and keeps the log in
`trader/state/broker.json`. `--now "2026-10-19 10:15"` pins the clock (Sydney time).

## What it reads and writes

| file | what |
| --- | --- |
| `trader/orders.json` | the proposed orders (trader-budget writes it; `flatten` replaces it) |
| `trader/state/risk.json` | trader-risk's verdicts; only a PASS from today is READY |
| `trader/state/broker.json` | every yes, no, placed, failed and filled, with each entry's max loss |
| `trader/portfolio.json` | cash and shares, updated by `fill` and by `result --filled-qty` |
| `trader/plan.json` | the flat-by time for `flatten` |

## Placing the order (ASX)

This tool never talks to a broker itself. It writes the ticket - symbol, side,
quantity, entry, stop-loss, take-profit, time-in-force - and prints the exact
order fields. You place that order at your own ASX broker.

Alpaca's MCP server only reaches US markets, and IBKR's your agent connector is
not an ASX execution path to depend on, so on the ASX the last step is manual
by design. No broker login, API key or 2FA code is ever needed here - and
never ask for one, or read one back into the chat.

1. `ticket.py show` prints the ticket and the exact fields.
2. Place that order at your broker: CommSec, Stake, IBKR, Pearler, SelfWealth,
   Superhero - whichever you use. Type the numbers as printed.
3. If your broker supports a bracket (entry with an attached stop-loss and
   take-profit), use it; otherwise place the entry, then the stop-loss as a
   separate conditional order once the entry fills.
4. Record the fill so trader-risk keeps the daily limit straight:
   `ticket.py result --index N --status placed --broker-id <id>
   --filled-qty Q --filled-price P`.

**Bracket orders.** A bracket is the entry plus two linked orders (stop-loss
and take-profit) that cancel each other when one fills. Whole shares only,
`time_in_force` day or gtc. They end at the close, which is one more reason
to be flat by then. On the ASX a stop is usually a stop-loss conditional
order and a target a limit sell.

If your broker is wired into your agent as an MCP tool with its own approval
card, approve the one order there - but the rule below still holds: the
user's word-for-word yes comes first.

## Steps: the entry

1. `ticket.py show`. Only READY tickets go to the user. A ticket that is NOT
   READY or BLOCKED goes back to `/trader-risk`.
2. Show ONE ticket and ask: "Place this order? Reply yes or no." One order
   per question. Never offer "yes to all".
3. Run `ticket.py approve --index N --reply "<the user's reply, word for word>"`.
   If it prints "Not recorded", the reply was not an explicit yes for this
   order (for example "sure", "yes to all", or a yes that names a different
   stock or amount). Ask again. Never turn a reply into a yes yourself.
4. Only after "Recorded your yes", call the order with exactly the
   JSON the ticket printed. your agent's card appears: Allow once or Deny.
5. Record what happened: `ticket.py result --index N --status placed
   --broker-id <id> --filled-qty Q --filled-price P` (the fill from the
   response or `your broker's holdings view`), or `--status denied`, or `--status failed`
   with `--note`. A failed order is not retried without a new check and a new yes.
   The log keeps the entry's max loss for trader-risk's daily limit.

## Steps: while it is open, and out by the close

- trader-alerts watches the stop, the target and the flat-by time
  (`alerts.py add --from-plan`). The bracket's own orders do the stopping.
- When the stop-loss or the take-profit fills, record it:
  `ticket.py fill --symbol BHP --side sell --qty 8 --price 358.32`.
- By `flat_by` (15:55 Sydney), anything still open gets closed:
  1. Ask your broker how many shares are held: `your broker's holdings view` (read only).
  2. `ticket.py flatten --symbol BHP --qty 8` writes a market sell for those
     shares to `trader/orders.json`.
  3. `/trader-risk`. A sell that only closes what the user holds is never
     blocked by the daily limits or the entry window.
  4. `ticket.py show`, then the user's yes for that one order, as above.
  5. The bracket's stop-loss and take-profit still hold those shares, so
     your broker rejects a new sell until they are canceled: `get_orders` (status
     open, nested true) shows them; your broker's cancel each one (Needs
     approval). Then the order with the ticket, then `result`.

## Example: the reel

```
ORDER 1 of 1, PAPER account, your broker
  BUY 8 BHP, market, good for today
  stop-loss 358.32
  take-profit 370.04
  max loss about $46.88 if the stop fills at 358.32 (it can fill worse in a fast market)
  why: opening-range breakout on BHP: 8 shares, bound by your $50 max loss per trade (8 x 5.86 = $46.88 at the stop)
  READY: trader-risk PASS, waiting for your yes
  Your agent will call place_stock_order with exactly:
    {"symbol": "BHP", "side": "buy", "qty": "8", "type": "market", "time_in_force": "day",
     "order_class": "bracket", "take_profit_limit_price": "370.04", "stop_loss_stop_price": "358.32"}
```

The user replies "yes". your agent records it, calls the order, and the
card reads "your agent wants to use Place stock order" with that JSON and two
buttons: Allow once, Deny. Allow once sends it to the paper account. The
`why` and the plan stay in the file; they are never sent.

## What it never does

- Never places an order without all three gates, and never two orders on one yes.
- Never places orders from a scheduled or background task: nobody is there to say yes.
- Never asks for, reads, stores or repeats API keys or passwords.
- Never switches `ALPACA_PAPER_TRADE` or `"paper"` to live. The user does that themselves.
- Never calls `close_all_positions`, `cancel_all_orders`, option or crypto order tools on its own.
- Never promises a fill price: a market order and a stop fill at whatever the market gives.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on your agent's own card because the order tool is set to "Needs approval"
  (Customize > Connectors > tool permissions). Never set an order tool to "Always allow".
- No options, margin, short selling or leverage unless the config allows it and the user confirms.
- Broker keys live in environment variables or the your agent app config, never in the chat.
