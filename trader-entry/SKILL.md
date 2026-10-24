---
name: trader-entry
description: >-
  Entry Timer. Watches a setup bar by bar and tells you the moment to get in.
  Reads free Yahoo 1-minute or 5-minute bars, builds the opening range (the
  first 15 minutes by default) and calls the entry on the first completed bar
  that CLOSES above the range high, or above a level you give it (like a
  20-day high from the scanner), with an optional volume check. Says waiting
  and how far, triggered with the time and the price, expired, or not open
  yet, and writes trader/entry.json for /trader-exit. Long side only. It never
  places an order. Use when the user says "tell me when to get in", "watch
  BHP", "has it broken out", "did it break the opening range", "entry
  signal", "time my entry", "check my watchlist", or after /trader-scanner
  and /trader-news, before /trader-exit.
argument-hint: "[TICKER] [--setup orb|level] [--interval 5m|1m]"
---

# trader-entry

The Entry Timer turns a setup into one moment: the bar that confirms it. It
reads bars, 1-minute or 5-minute, and waits for each one to finish. A price
that pokes above the high in the middle of a bar is not an entry. A bar that
CLOSES above it is. Then it says the time and the price, writes them down for
the Exit Planner, and stops. It never buys anything. Day trading loses most
people money, and a clean signal does not change that.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/entry.py" check BHP                  # 15-minute opening range, 5-minute bars
python3 "${CLAUDE_SKILL_DIR}/entry.py" check BHP --write          # also save trader/entry.json
python3 "${CLAUDE_SKILL_DIR}/entry.py" check BHP --setup level --level 371.20
python3 "${CLAUDE_SKILL_DIR}/entry.py" check BHP --interval 1m --min-volume-x 1.5
python3 "${CLAUDE_SKILL_DIR}/entry.py" watch BHP --until 15:30    # one line per closed bar, stops on the trigger
python3 "${CLAUDE_SKILL_DIR}/entry.py" watchlist                   # every hit in trader/watchlist.json
```

Other flags: `--or-minutes N` (default 15), `--json`, `--offline FILE` (a
saved Yahoo chart JSON, `.json` or `.json.gz`, or a folder of
`<TICKER>.json`), `--now "2026-10-19 10:15"` (Sydney time) to replay a day.
`watch` with `--now` or `--offline` runs on a simulated clock and replays the
day bar by bar without waiting.

## What it reads and writes

| file | what |
| --- | --- |
| `trader/watchlist.json` | the scanner's hits (`hits[].symbol`), for `watchlist` |
| `trader/config.json` | `no_entries_before` (10:15) and `no_entries_after` (15:30), Sydney time. Optional |
| Yahoo chart API | today's bars, `range=1d&interval=5m` (or `1m`): free, unofficial, can lag |
| `trader/entry.json` | with `check --write`, or when `watch` triggers: symbol, setup, status, time, bar, price, level, opening range |

## The rule

- **Opening range (orb).** The high and low of the first 15 minutes: the
  10:00, 9:35 and 9:40 five-minute bars, or fifteen 1-minute bars. The level
  to beat is the range high.
- **Level.** A price you give, like a 20-day high from `/trader-scanner`.
- **The trigger** is the first completed bar after the range that CLOSES
  above the level. A wick above is not a trigger. A close exactly at the
  level is not above it.
- **The time** is that bar's close time (the 10:10 bar closes at 10:15 AM).
  The price is its close, to the cent.
- **Only closed bars count.** A bar is closed when the clock passes its start
  plus 5 (or 1) minutes and Yahoo has caught up to that moment (it waits a
  minute at most). Yahoo's live tick, like 10:49:45, is never a bar.
- **Volume, if you want it.** `--min-volume-x 1.5` also needs the trigger
  bar's volume at 1.5 times the range bars' average. The 10:00 bar holds the
  opening auction, so 1.0 is already strict.
- **Time limits.** No entries before 10:15 or after 15:30 (config). On a 2:10
  p.m. early close the cutoff moves up with the close, to 13:40.
- **What it says.** Waiting (and how far the last close is from the level),
  triggered, expired, or no data. Before 10:00: not open yet. Before 10:15: the
  range is still forming. Weekends and ASX holidays: the market is closed.

## Steps

1. Get the symbol from the user, or run `entry.py watchlist` after
   `/trader-scanner`. Check `/trader-news` for it first.
2. Run `entry.py check SYMBOL`. Tell the user the status in one line:
   waiting and how far, triggered at what time and price, or expired.
3. To wait for it, your agent can run `entry.py watch SYMBOL --until 15:30` in
   the background, or `entry.py check SYMBOL --write` on a `/loop` every 5
   minutes. `watch` wakes just after each bar closes, prints one line per
   bar, and exits 0 on the trigger (it writes `trader/entry.json`) or 1 when
   the setup expires. Keep the computer awake while it watches: a sleeping
   laptop pauses it, and it catches up, late, when it wakes.
4. When it triggers, say the time and the price, and that nothing was placed.
   If the trigger is more than a bar old, say that too: a late entry is a
   different trade.
5. Hand off to `/trader-exit` to set the stop and the target BEFORE anything
   is bought.

## Example: the reel

BHP.AX, Monday 2026-10-19, 5-minute bars. The session opens at 10:00 Sydney, so
the 15-minute opening range is 10:00-10:15. At 10:12 the 10:10 bar is still
open, so it waits:

```
BHP.AX  Mon 2026-10-19 10:12 AEST  opening-range breakout (15-minute range) on 5-minute bars (Yahoo, free, can lag)
Opening range 10:00-10:15: high $55.50, low $55.00 (2 of 3 bars, still forming).
RANGE FORMING  2 of 3 range bars closed; the range is set at 10:15.
The 10:10 bar is still forming ($55.72 so far, closes 10:15 AM); it does not count until it closes.
```

The range is set at 10:15, and the 10:15 bar closes above it at 10:20:

```
BHP.AX  Mon 2026-10-19 10:20 AEST  opening-range breakout (15-minute range) on 5-minute bars (Yahoo, free, can lag)
Opening range 10:00-10:15: high $55.80, low $55.00 (3 of 3 bars).
TRIGGERED 10:20 AM at $55.84: the 10:15 bar (bar 3) closed above the range high $55.80 (+0.07%).
This is the moment to get in, if you take the trade. Nothing was placed.
Next: set the stop and target BEFORE you buy: /trader-exit (exit.py plan --from trader/entry.json).
```

With `--min-volume-x 1` that breakout bar is too thin (0.56x the range's
volume), so it keeps waiting:

```
BHP.AX  Mon 2026-10-19 10:20 AEST  opening-range breakout (15-minute range) on 5-minute bars (Yahoo, free, can lag)
Opening range 10:00-10:15: high $55.80, low $55.00 (3 of 3 bars).
WAITING  the 10:15 bar closed above at $55.84 but on 0.56x the range's volume, under your 1.00x.
The 10:20 bar is still forming ($55.95 so far, closes 10:25 AM); it does not count until it closes.
```

## Rules

- Bar by bar, on free Yahoo 1-minute or 5-minute bars. They are unofficial
  and can lag. Say so when a minute matters.
- A signal is information, not an order, and not a promise. Nothing here
  promises winning trades or money.
- Long side only. v2 plans longs only. If the user wants a short, say that.
- One trigger per setup per day: the first close above. Later closes do not
  reset it.
- Never call an entry early because a bar looks like it will close above.

## What it never does

It never places an order, never sizes a position, never sets the stop (that
is `/trader-exit`), never moves the level after the fact, and never counts a
bar that has not closed. It never runs `/trader-broker` from a background
watch: nobody is there to say yes.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on your agent's own card because the order tool is set to "Needs approval"
  (Customize > Connectors > tool permissions). Never set an order tool to "Always allow".
- No options, margin, short selling or leverage unless the config allows it and the user confirms.
- Broker keys live in environment variables or the your agent app config, never in the chat.
