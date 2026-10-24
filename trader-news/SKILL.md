---
name: trader-news
description: >-
  News Monitor. Tracks breaking news on every stock you watch and flags what
  moves it: Yahoo Finance headlines per ticker, each company's ASX
  announcements (results, guidance, capital raisings, director changes, halts,
  price-sensitive ones flagged) and how
  far each stock is from yesterday's close. Shows only what is new since the
  last check, newest first, in Sydney time, tags each item (earnings,
  analyst, deal, halt, regulatory, macro...) and never repeats one. Use when
  the user says "any news on BHP", "why is this moving", "what's the news on
  my watchlist", "morning briefing", "pre-market news", "monitor the news",
  "did anything break", "check the announcements", or after /trader-scanner finds setups.
argument-hint: "[tickers]"
---

# trader-news

A chart can look perfect and still be about to gap on an earnings date, a
halt or a lawsuit. Before a setup becomes a trade, this skill reads the two
feeds that carry those first, for every stock on the watchlist, and tells you
only what is new. It also prints how far each stock has moved today, so a
headline and a move sit side by side.

Tool in this folder (standard library Python, no keys):

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py"                         # watchlist + plan + portfolio
python3 "${CLAUDE_SKILL_DIR}/news.py" --tickers BHP CBA --hours 12
python3 "${CLAUDE_SKILL_DIR}/news.py" --no-sec --json
```

## What it reads and writes

| file / feed | what |
| --- | --- |
| `--tickers`, else `trader/watchlist.json` | the scanner's hits (trader-scanner) |
| `trader/plan.json` | the trade you are planning (trader-exit) |
| `trader/portfolio.json` | what you hold (trader-broker records fills there) |
| Yahoo Finance headline RSS | `https://feeds.finance.yahoo.com/rss/2.0/headline?s=BHP.AX&region=AU&lang=en-AU` |
| Yahoo Finance chart endpoint | the last price against yesterday's close (unofficial, can lag) |
| ASX company announcements | `asx.api.markitdigital.com/asx-research/1.0/companies/<CODE>/announcements?pageSize=N`, free, no key; a price-sensitive one is marked `!` |
| `trader/state/news.json` | what has been shown, kept 30 days |

## The rules

- **Headlines are leads, not facts.** Before telling the user something
  happened, open the story or the filing and read it. Quote the source and
  link it. Never summarise a paywalled story you could not read: say so.
- **Announcements beat headlines.** If an announcement and a headline
  disagree, the announcement is what the company told the ASX.
- **Say what it touches.** Every item lists the tickers it touches and its
  tags: earnings, analyst, legal, deal, capital, people, risk, halt,
  regulatory, macro. Announcements marked `!` are the ones the company itself
  flagged as price sensitive: results, guidance, a capital raising, a director
  change or a trading halt - the items that most often move the price.
- **MOVING** marks a stock 3 % or more from yesterday's close (`--move-pct`).
  A move with no headline is worth saying out loud too.
- **No predictions.** Report what was published and how far the price is from
  yesterday's close. Never say what the stock will do next.

## Steps

1. Run the check: `python3 "${CLAUDE_SKILL_DIR}/news.py"`. Exit code 1 means
   nothing new. `--all` shows items already seen, `--json` gives everything
   machine readable, `--dry-run` leaves the state alone.
2. Read the items that matter: every `!` filing, anything tagged earnings,
   halt, legal, regulatory or risk, and every MOVING ticker first.
3. Write a short brief, per ticker: what happened, the source and link, the
   move, and one line on why it matters to the setup (for example "earnings
   are this week: an overnight gap can jump past any stop").
4. If a story changes the picture, say so before `/trader-entry` and
   `/trader-exit`: an earnings date inside the trade, a halt, an offering.
   Never act on a headline alone.

During the session: `/loop 15m /trader-news`, or a scheduled task each
morning before the open.

## Example: the reel

Friday 2026-10-23, BHP broke its opening range at 10:15 AM AEST. The check at
10:15 (Yahoo Finance's BHP.AX feed) leads with the morning's real stories:
"BHP quarterly production softer on weather" (8:00, earnings),
"Rio, BHP flagged as iron ore price slips" (8:04, analyst, macro). The ASX
announcements list adds the company's own filing: "Quarterly Activities
Report" (market sensitive, earnings). The brief: "Results inside the trade
window, so this can gap; in and out before the close. One new
date-sensitive announcement." At 10:52 the price line reads `BHP 55.05 +3.31%
vs yesterday's close 53.28 at 10:52 AEST  MOVING`. When a ticker has no news,
say so rather than padding the brief.

## What it never does

- Never invents or embellishes a story, a quote or a number.
- Never trades on news, and never tells the user to buy or sell because of a
  headline.
- Never hammers a server: one request per feed per ticker, a pause between
  calls, and ASX's 10 requests a second limit stays far away.

## Safety

Education and tooling, not financial advice. This skill only reads and
reports. Nothing places an order except `/trader-broker`, after
`/trader-risk` passes and the user types an explicit yes for that order.
