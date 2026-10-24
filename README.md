# The Day Trader skill — ASX edition

Nine skills for day trading **Australian shares on the ASX**: scan the market
for setups, track the news, time every entry and exit, and replay the outcome
before you risk a dollar.

Fork of [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)
(MIT), retargeted from US markets to the ASX. **See [ASX-NOTES.md](ASX-NOTES.md)
for exactly what changed.**

Free, MIT, no signup, no API key. The tools are plain Python (3.8+, standard
library only) reading free public data: Yahoo Finance `.AX` charts and the ASX
listed-companies file.

And no trade goes through until you say yes. Nothing in this pack can place an
order on its own; on the ASX the last step is manual by design.

## Install

Copy the nine skill folders into your agent's skills directory:

```bash
for d in trader-*; do cp -r "$d" ~/.hermes/skills/; done   # Hermes
# for d in trader-*; do cp -r "$d" ~/.claude/skills/; done  # Claude Code
```

Paste any `SKILL.md` at the top of a chat to run it as a mode; you lose the
Python tools but the method still works. Nothing to `pip install`.

## The nine

| command | job | what it does |
| --- | --- | --- |
| `/trader-scanner` | Chart Scanner | Scans the ASX for setups: opening-range breakouts, flags, oversold bounces. |
| `/trader-news` | News Monitor | Tracks breaking news on every stock you watch and flags what moves it. |
| `/trader-entry` | Entry Timer | Watches a setup bar by bar and tells you the moment to get in. |
| `/trader-exit` | Exit Planner | Sets your stop and your target before you enter, so you know when to get out. |
| `/trader-timemachine` | Time Machine | Replays every possible outcome of a trade before you risk a dollar: 10,000 simulated sessions plus every past time the setup fired. |
| `/trader-risk` | Risk Manager | Checks every trade against your limits and blocks anything over them. |
| `/trader-budget` | Budget Manager | Sizes every position to your budget and your max loss per trade. |
| `/trader-broker` | Order Executor | Writes the ticket and the exact order fields; you place it at your ASX broker, never without your yes. |
| `/trader-alerts` | Price Alerts | Rings when a price, a stop or the flat-by time hits. |

Dropped from the US original (no ASX analogue): `trader-analyst` (SEC/earnings),
`trader-pelosi` (US Congress disclosures).

## How to use it

Everything lands in a `trader/` folder in your project, and each skill reads
what the last one wrote:

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker   (one trade)
alerts: stop, target, flat by the close                                        (while it is open)
```

Illustrative run (BHP on the ASX; numbers rounded to show the shape):

1. **`/trader-scanner`** at 10:15 AM Sydney: of the charts it scanned, several
   closed above their 15-minute opening range. BHP is one.
2. **`/trader-news`**: the morning's BHP headlines and today's move, in Sydney time.
3. **`/trader-entry`** watched BHP bar by bar: "waiting" while the 10:10 candle
   formed, then "triggered" on the first 5-minute close above the range.
4. **`/trader-exit`** set the plan before the entry: stop under the range, target
   a multiple of that risk, flat by 15:50 either way.
5. **`/trader-timemachine`** replayed the rest of the session 10,000 times from
   BHP's own recent bars, and re-ran the rule on every past session it fired. Its
   verdict is the honest odds, not a promise.
6. **`/trader-budget`** with a $5,000 account and a $50 max loss per trade sizes
   the whole shares that fit and writes one bracket order (entry, stop-loss,
   take-profit).
7. **`/trader-risk`** checks it against your limits: max loss, daily loss limit,
   trades per day, reward-to-risk, entry window, position size, cash. PASS or BLOCK.
8. **`/trader-broker`** shows the ticket in plain words and the exact order
   fields. You type yes for that one order, then place it at your broker
   (CommSec, Stake, IBKR, Pearler, SelfWealth, Superhero). Alpaca cannot trade
   the ASX, so this step is manual by design.
9. **`/trader-alerts`** rings on the stop, the target and at the flat-by time to
   close whatever is still open.

## The tools

All standard-library Python. Free public endpoints, read politely.

```bash
python3 trader-scanner/scan.py universe                      # ~2,049 ASX codes -> trader/universe.txt
python3 trader-scanner/scan.py daily --symbols BHP,CBA,CSL   # pre-market setups
python3 trader-scanner/scan.py orb --at 10:15                # opening-range breakouts so far
python3 trader-news/news.py --tickers BHP --hours 12         # headlines + today's move
python3 trader-entry/entry.py check BHP --setup orb          # waiting / triggered / expired
python3 trader-exit/exit.py plan --symbol BHP --stop pct:1.5 --target 2R --write
python3 trader-timemachine/timemachine.py run --symbol BHP --write
python3 trader-budget/size.py --budget 5000 --write
python3 trader-risk/check.py                                 # PASS / BLOCK per order
python3 trader-broker/ticket.py show                         # the tickets, READY or not
python3 trader-alerts/alerts.py add --from-plan              # stop, target, flat by the close
python3 trader-alerts/alerts.py clock --now "2026-10-23 11:00"   # market open / holiday
```

`--now` is **Sydney** time. On a weekend or an ASX holiday the intraday scans
find nothing; live commands need a trading day.

```bash
python3 -m unittest discover -s tests -v
```

The tests run offline: Sydney DST boundaries, the ASX session and the 2026
holidays, the `.AX` ticker rule, and the listed-companies parser.

## Fine print

**Not financial advice.** This is software that reads public data and does
arithmetic. It cannot see the future. Most people who day trade lose money. You
can lose money. Talk to a licensed professional if you need advice.

**No trade goes through until you say yes.** Only `/trader-broker` leads to an
order, and only after `/trader-risk` passes that exact order and you type yes for
it. One yes covers one trade, never a batch.

**Manual by default.** Alpaca's MCP server only reaches US markets; for the ASX
this pack writes the ticket and you place it at your own broker. Never paste a
broker login, API key or 2FA code into a chat, and never read them back.

**The Time Machine is a simulation, not a prediction.** It is built from the
stock's own last 60 days of 5-minute bars. An earnings report, a halt or a
headline can do things those 60 days never did.

**A stop is a plan, not a guarantee.** In a fast market or across a gap, a stop
order can fill well past its price.

**The data is free and unofficial.** Yahoo's chart endpoint is not an official
API: it can lag, change or rate-limit you. Check anything that matters against
your broker before you act on it.

**ASX specifics.** Regular session 10:00–16:00 Sydney (AEST/AEDT); early close
14:10 on 24 and 31 December; ~2,049 listed codes; whole shares only; T+2
settlement, CGT and franking are not modelled; all amounts are AUD.

## Files

```
trader-scanner/     SKILL.md, scan.py
trader-news/        SKILL.md, news.py
trader-entry/       SKILL.md, entry.py
trader-exit/        SKILL.md, exit.py
trader-timemachine/ SKILL.md, timemachine.py
trader-risk/        SKILL.md, check.py
trader-budget/      SKILL.md, size.py, config.example.json, targets.example.json
trader-broker/      SKILL.md, ticket.py
trader-alerts/      SKILL.md, alerts.py, alerts.example.json
tests/              unittest suite (ASX calendar, session, ticker, parser)
ASX-NOTES.md        what changed from the US original
```

MIT. Fork of [Jake Schincariol](https://opusjake.ai)'s day-trader-skill.