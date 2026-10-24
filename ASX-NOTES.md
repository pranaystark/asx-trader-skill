# ASX Trader — Australia port of day-trader-skill

Fork of `github.com/Jakeschincariol/day-trader-skill` (MIT) retargeted from
US markets to the **Australian Securities Exchange (ASX)**. Same architecture:
nine `trader-*` skill folders, each a `SKILL.md` plus one stdlib-only Python tool.

## What changed (US → ASX)

| Area | US original | ASX port |
| --- | --- | --- |
| Session | 9:30–16:00 ET | 10:00–16:00 Sydney (AEST/AEDT) |
| TZ helper | `eastern_offset` | `sydney_offset` (+11 AEDT, +10 AEST), `to_sydney`, `sydney_to_utc` |
| Early close | 13:00 ET | 14:10 Sydney (24 & 31 Dec) |
| Holidays | NYSE tables | official ASX calendar: 7 closures 2026, 8 in 2027 (`ASX_HOLIDAYS`, `ASX_EARLY_CLOSE`) |
| Universe | Nasdaq Trader symbol dirs | ASX listed-companies file → `parse_asx_csv` / `build_universe` → ~2,049 codes |
| Tickers | bare symbol | `to_yahoo()` appends `.AX` (BHP → BHP.AX), idempotent |
| Broker | Alpaca MCP | manual ticket for your ASX broker (Alpaca cannot trade ASX) |
| Wording | "Claude" | "your agent" |

**Dropped** (no ASX analogue): `trader-analyst` (SEC/analyst data),
`trader-pelosi` (US House-Clerk disclosures), `tests/` (US ET/9:30 fixtures).

**Unchanged:** the flow plan → size → risk(PASS) → ticket → word-for-word yes;
simulation, alerts, sizing logic; the nine tools:
scanner, news, entry, exit, timemachine, budget, risk, broker, alerts.

## ASX specifics & caveats

- **No Alpaca on the ASX.** `trader-broker` writes the ticket + the exact order
  fields; you place it yourself at CommSec, Stake, IBKR, Pearler, SelfWealth or
  Superhero. Never paste broker keys or 2FA into chat.
- **Liquidity filter is US-tuned.** Defaults ($5+ price, 1,000,000+ shares/bar)
  are generous for the ASX; low-volume small caps will drop out — loosen the
  volume threshold if you want them.
- **Whole shares only.** Bracket orders take no fractions; ASX suits this.
- **Data is free/unofficial.** Yahoo `.AX` quotes and daily bars can lag or
  rate-limit. Delayed quotes are not a trading signal.
- **Not modelled:** CGT/franking, T+2 settlement, corporate actions, AUD vs the
  US-tools' origin. All amounts are AUD; the tool prints `$` without a label.
- **News:** headlines/moves come from Yahoo AU; company news comes from each
  company's ASX announcements feed
  (`asx.api.markitdigital.com/asx-research/1.0/companies/<CODE>/announcements`),
  free and key-less, with the filing PDF at `.../1.0/file/<documentKey>`.
- **Early close is 1h50m, not 3h.** The ASX stops normal trading at 14:10 on
  24 & 31 Dec, so the flat-by and the risk window move up by 110 minutes
  (15:55 -> 14:05), not by the US 3 hours.
- Market clock for any date: `python3 trader-alerts/alerts.py clock --now "YYYY-MM-DD HH:MM"`.

## First run

```bash
cp trader-budget/config.example.json trader/config.json   # your budget/rules
python3 trader-scanner/scan.py universe                   # ~2,049 ASX codes -> trader/universe.txt
python3 trader-scanner/scan.py daily --symbols BHP,CBA,CSL --now "2026-10-23 11:00"
python3 trader-news/news.py --tickers BHP
python3 trader-exit/exit.py plan --symbol BHP --entry 55.85 --stop pct:1.5 --target 2R --date 2026-10-23 --write
python3 trader-budget/size.py --budget 5000 --now "2026-10-23 11:00" --write
python3 trader-risk/check.py --now "2026-10-23 11:00" --today 2026-10-23
python3 trader-broker/ticket.py show
```

`--now` is **Sydney** time. Live commands need an ASX trading day; on a weekend
or ASX holiday `daily` uses the last close and `orb`/intraday scans find nothing.

## Verify

```bash
python3 -m unittest discover -s tests -v
```

Education and tooling, not financial advice.