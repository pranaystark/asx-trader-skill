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


if __name__ == "__main__":
    unittest.main(verbosity=2)