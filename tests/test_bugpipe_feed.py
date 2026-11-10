"""The Our contributions refresh from bugpipe; run with python3 -m unittest discover -s tests -v."""
import csv
import os
import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import refresh  # noqa: E402

CSV = ROOT / "data" / "seed" / "findings.csv"


def feed_from_csv():
    """The committed findings.csv in /v1/dashboard's shape."""
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    counts = [{"vertical": r["vertical"], "stage": r["stage"], "n": int(r["n"])} for r in rows if r["kind"] == "count"]
    bugs = [{k: r[k] for k in refresh.FINDINGS_COLS[1:10]} for r in rows if r["kind"] == "bug"]
    return {"counts": counts, "bugs": bugs}


class BugpipeFeedTests(unittest.TestCase):
    def setUp(self):
        self.before = CSV.read_bytes()
        self.addCleanup(CSV.write_bytes, self.before)

    def run_with(self, get, token="t"):
        log = {"errors": []}
        with mock.patch.dict(os.environ, {"BUGPIPE_TOKEN": token} if token else {}, clear=False):
            if not token:
                os.environ.pop("BUGPIPE_TOKEN", None)
            refresh.refresh_findings(log, get=get)
        return log

    def test_the_feed_round_trips_to_the_same_csv(self):
        log = self.run_with(lambda url: feed_from_csv())
        self.assertEqual(log["errors"], [])
        self.assertEqual(CSV.read_bytes(), self.before)

    def test_bad_data_keeps_the_old_file(self):
        feed = feed_from_csv()
        feed["bugs"] = feed["bugs"][1:]                     # reported no longer equals the number of bug rows
        log = self.run_with(lambda url: feed)
        self.assertIn("failed validate.py", log["errors"][0])
        self.assertEqual(CSV.read_bytes(), self.before)

    def test_a_failed_fetch_or_no_token_keeps_the_old_file(self):
        def down(url):
            raise OSError("connection refused")
        self.assertIn("connection refused", self.run_with(down)["errors"][0])
        self.assertEqual(self.run_with(lambda url: {"counts": [], "bugs": []}, token="")["bugpipe"], False)
        self.assertEqual(CSV.read_bytes(), self.before)

    def test_skipped_findings_are_reported(self):
        log = self.run_with(lambda url: {**feed_from_csv(), "skipped": ["BP-9"]})
        self.assertIn("BP-9", log["errors"][0])


if __name__ == "__main__":
    unittest.main()
