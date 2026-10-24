#!/usr/bin/env python3
"""ASX-port tests. Stdlib only.

Run: python3 -m unittest discover -s tests -v
"""
import datetime
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader, rel
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


scan = load("asx_scan", "trader-scanner/scan.py")
T = datetime.time

# ASX listed-companies file shape: title line, blank line, header, rows.
CSV = ("ASX listed companies as at Mon Jan 5 09:00:00 AEDT 2026\n"
       "\n"
       "Company name,ASX code,GICS industry group\n"
       '"BHP GROUP LIMITED","BHP","Materials"\n'
       '"COMMONWEALTH BANK OF AUSTRALIA","CBA","Financials"\n'
       '"CSL LIMITED","CSL","Health Care"\n')


class SydneyTime(unittest.TestCase):
    def test_dst_boundaries(self):
        o = scan.sydney_offset
        self.assertEqual(o(datetime.datetime(2026, 1, 15, 12)), 11)     # AEDT
        self.assertEqual(o(datetime.datetime(2026, 6, 15, 12)), 10)     # AEST
        self.assertEqual(o(datetime.datetime(2026, 10, 3, 15, 59)), 10)  # before DST
        self.assertEqual(o(datetime.datetime(2026, 10, 3, 16, 1)), 11)   # DST on
        self.assertEqual(o(datetime.datetime(2026, 4, 4, 15, 59)), 11)   # still DST
        self.assertEqual(o(datetime.datetime(2026, 4, 4, 16, 1)), 10)    # DST off

    def test_round_trip(self):
        utc = datetime.datetime(2026, 10, 24, 3, 0)
        self.assertEqual(scan.to_sydney(utc).hour, 14)
        self.assertEqual(scan.sydney_to_utc(datetime.datetime(2026, 10, 24, 14, 0)), utc)


class Session(unittest.TestCase):
    def test_normal_regular(self):
        self.assertEqual(scan.session(datetime.date(2026, 10, 21)), (T(10, 0), T(16, 0)))

    def test_early_close(self):
        self.assertEqual(scan.session(datetime.date(2026, 12, 24)), (T(10, 0), T(14, 10)))
        self.assertEqual(scan.session(datetime.date(2026, 12, 31)), (T(10, 0), T(14, 10)))

    def test_official_2026_closures(self):
        # The 7 official ASX closures of 2026.
        for d in (datetime.date(2026, 1, 1),   # New Year's Day
                  datetime.date(2026, 1, 26),  # Australia Day
                  datetime.date(2026, 4, 3),   # Good Friday
                  datetime.date(2026, 4, 6),   # Easter Monday
                  datetime.date(2026, 6, 8),   # King's Birthday
                  datetime.date(2026, 12, 25),  # Christmas
                  datetime.date(2026, 12, 28)):  # Boxing Day (observed)
            self.assertIsNone(scan.session(d), d)

    def test_anzac_2026_is_a_trading_day(self):
        # 25 Apr 2026 is a Saturday, so the ASX does not close the following Monday.
        self.assertIsNone(scan.session(datetime.date(2026, 4, 25)))   # weekend
        self.assertEqual(scan.session(datetime.date(2026, 4, 27)), (T(10, 0), T(16, 0)))


class Tickers(unittest.TestCase):
    def test_ax_suffix(self):
        self.assertEqual(scan.to_yahoo("BHP"), "BHP.AX")
        self.assertEqual(scan.to_yahoo("dhhf"), "DHHF.AX")

    def test_idempotent(self):
        self.assertEqual(scan.to_yahoo("BHP.AX"), "BHP.AX")
        self.assertEqual(scan.to_yahoo("bhp.ax"), "BHP.AX")


class Universe(unittest.TestCase):
    def test_parse_skips_title_and_blank(self):
        rows, _ = scan.parse_asx_csv(CSV)
        codes = [r["ASX code"] for r in rows]
        self.assertIn("BHP", codes)
        self.assertIn("CBA", codes)
        self.assertEqual(len(codes), 3)   # title + blank + header not counted

    def test_names(self):
        kept, _, _ = scan.build_universe(CSV)
        d = {r[0]: r[1] for r in kept}
        self.assertEqual(d["BHP"], "BHP GROUP LIMITED")
        self.assertEqual(len(kept), 3)

    def test_duplicate_code_folds_to_uppercase(self):
        kept, _, _ = scan.build_universe(CSV + '"DUP","bhp","Materials"\n')
        self.assertEqual(len(kept), 3)    # lowercase 'bhp' folds into 'BHP'


class ImportAll(unittest.TestCase):
    """Every tool must import cleanly."""

    TOOLS = [
        ("t_alerts", "trader-alerts/alerts.py"),
        ("t_broker", "trader-broker/ticket.py"),
        ("t_budget", "trader-budget/size.py"),
        ("t_entry", "trader-entry/entry.py"),
        ("t_exit", "trader-exit/exit.py"),
        ("t_news", "trader-news/news.py"),
        ("t_risk", "trader-risk/check.py"),
        ("t_timemachine", "trader-timemachine/timemachine.py"),
    ]

    def test_imports(self):
        for name, rel in self.TOOLS:
            with self.subTest(tool=rel):
                load(name, rel)


alerts = load("asx_alerts", "trader-alerts/alerts.py")
risk = load("asx_risk", "trader-risk/check.py")


class EarlyClose(unittest.TestCase):
    """The ASX early close is 14:10 (1h50m before the 16:00 close), not the US 3 hours."""

    def setUp(self):
        self.status = alerts.market_status(datetime.datetime(2026, 12, 24, 3, 0))  # 14:00 Sydney

    def test_early_close_day_is_open_until_1410(self):
        self.assertEqual(self.status["early_close"], "Christmas Eve")
        self.assertTrue(self.status["open"])

    def test_before_close_rule_shifts_110_minutes(self):
        self.assertEqual(alerts.ring_time({"at": "15:55", "before_close": True}, self.status), T(14, 5))

    def test_plain_rule_never_shifts(self):
        # trader-exit already resolved flat_by for the day; the plan alert must not shift twice
        self.assertEqual(alerts.ring_time({"at": "14:05"}, self.status), T(14, 5))

    def test_normal_day_does_not_shift(self):
        st = alerts.market_status(datetime.datetime(2026, 10, 23, 3, 0))
        self.assertIsNone(st["early_close"])
        self.assertEqual(alerts.ring_time({"at": "15:55", "before_close": True}, st), T(15, 55))

    def test_risk_window_uses_the_same_delta(self):
        self.assertEqual(risk._early_shift_minutes(), 110)
        self.assertEqual(risk._shift_min(datetime.time(15, 30), risk._early_shift_minutes()), T(13, 40))


if __name__ == "__main__":
    unittest.main(verbosity=2)