"""Offline regression checks; run with python3 -m unittest discover -s tests -v."""
import datetime as dt
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://techcrunch.com/2026/10/29/binance-pauses-withdrawals-as-hackers-suspected-of-stealing-billions-in-crypto/"


class BinanceRecordTests(unittest.TestCase):
    def test_one_sourced_binance_incident_preserves_unknowns(self):
        data = json.loads((ROOT / "site/data.json").read_text())
        archive = json.loads((ROOT / "data/archive/incidents.json").read_text())
        all_rows = data["incidents"] + archive
        matches = [r for r in all_rows if r["victim"] == "Binance" and r["date"] == "2026-10-29"]
        self.assertEqual(len(matches), 1)
        row = matches[0]

        self.assertRegex(row["id"], r"^\d+$")
        self.assertEqual(sum(r["id"] == row["id"] for r in all_rows), 1)
        self.assertEqual(row["claim_status"], "reported")
        self.assertIs(row["code_flaw"], False)
        self.assertIs(row["zero_day"], False)
        self.assertIs(row["under_investigation"], True)
        for field in ("amount_lost_usd", "funds_recovered_usd", "records_or_loss", "initial_vector", "root_cause", "component", "flaw_group"):
            self.assertEqual(row[field], "", field)
        self.assertEqual(row["people"], 0)
        self.assertEqual(row["cve"], "unknown")
        self.assertEqual(row["threat_actor"], "unknown")
        self.assertEqual(row["source_url"], SOURCE)
        self.assertIn("withdrawals on multiple networks", row["impact"])
        self.assertIn("remain unconfirmed", row["impact"])
        self.assertNotRegex(row["impact"], r"\$|billion|million|private.key|signing")
        generated = dt.datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
        self.assertGreater(generated, dt.datetime(2026, 10, 29, 11, 25, 47, tzinfo=dt.timezone.utc))


class InvestigationSchemaTests(unittest.TestCase):
    def validate(self, change):
        # Exercise the real CLI against disposable data; never import/run refresh.py.
        import os
        import shutil
        import subprocess
        import sys
        import tempfile

        data = json.loads((ROOT / "site/data.json").read_text())
        for row in data["incidents"]:
            row.pop("under_investigation", None)
        change(data["incidents"][0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "site").mkdir()
            shutil.copyfile(ROOT / "scripts/validate.py", root / "scripts/validate.py")
            shutil.copytree(ROOT / "data/seed", root / "data/seed")
            (root / "site/data.json").write_text(json.dumps(data))
            return subprocess.run(
                [sys.executable, str(root / "scripts/validate.py")],
                env={"PATH": os.defpath, "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True, check=False,
            )

    def test_optional_boolean_investigation_marker_is_accepted(self):
        for value in (True, False):
            with self.subTest(value=value):
                result = self.validate(lambda row: row.update(under_investigation=value))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_boolean_investigation_marker_is_rejected(self):
        for value in ("true", "false", 1, None):
            with self.subTest(value=value):
                result = self.validate(lambda row: row.update(under_investigation=value))
                self.assertEqual(result.returncode, 1)
                self.assertIn("under_investigation must be true or false", result.stdout)

    def test_marker_does_not_replace_a_required_field(self):
        def change(row):
            row.pop("victim")
            row["under_investigation"] = True
        result = self.validate(change)
        self.assertEqual(result.returncode, 1)
        self.assertIn("fields", result.stdout)


class RefreshScheduleTests(unittest.TestCase):
    def test_existing_workflow_runs_at_0507_and_1707_utc(self):
        import re
        workflow = (ROOT / ".github/workflows/daily-refresh.yml").read_text()
        self.assertEqual(re.findall(r'cron:\s*"([^"]+)"', workflow), ["7 5,17 * * *"])

    def test_public_frequency_copy_matches_the_schedule(self):
        expectations = {
            "src/page.template.html": ("Updated twice daily",),
            "scripts/build_page.py": ("Updated twice daily",),
            "README.md": ("updated twice daily", "05:07 and 17:07 UTC"),
            "docs/daily-refresh.md": ("# Twice-daily refresh", "05:07 and 17:07 UTC", "best effort"),
            "CONTRIBUTING.md": ("twice-daily",),
            "docs/data-schema.md": ("twice-daily", "under_investigation"),
        }
        for file, phrases in expectations.items():
            with self.subTest(file=file):
                text = (ROOT / file).read_text()
                for phrase in phrases:
                    self.assertTrue(phrase in text, f"{file} must state {phrase!r}")
                self.assertNotRegex(text.lower(), r"updated daily|every day at|the daily update|a daily job|next daily refresh|when the daily job")

    def test_prebuilt_page_contains_current_data_and_frequency_metadata(self):
        import re
        page = (ROOT / "site/index.html").read_text()
        embedded = re.search(r'<script id="pg-data" type="application/json">(.*?)</script>', page, re.S)
        assert embedded is not None, "prebuilt page needs embedded data"
        data = json.loads((ROOT / "site/data.json").read_text())
        self.assertTrue(json.loads(embedded[1]) == data, "prebuilt embedded data must match site/data.json")
        descriptions = re.findall(r'<meta (?:name|property)="(?:description|og:description|twitter:description)" content="([^"]+)"', page)
        self.assertEqual(len(descriptions), 3)
        for description in descriptions:
            self.assertIn("Updated twice daily", description)
        self.assertIn('id="a-investigation"', page)
        self.assertNotIn("__DATA__", page)


if __name__ == "__main__":
    unittest.main()
