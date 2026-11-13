"""The In focus pick rule; run with python3 -m unittest discover -s tests -v."""
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from refresh import pick_focus  # noqa: E402

TODAY = dt.date(2026, 11, 13)


def row(id, days_ago):
    return {"id": id, "date": (TODAY - dt.timedelta(days=days_ago)).isoformat()}


class PickFocusTests(unittest.TestCase):
    def test_pick_within_three_days_replaces_current(self):
        rows = [row("1", 2), row("2", 3)]
        self.assertEqual(pick_focus("1", rows[1], rows, TODAY), "2")

    def test_older_pick_is_ignored(self):
        rows = [row("1", 2), row("2", 4)]
        self.assertEqual(pick_focus("1", rows[1], rows, TODAY), "1")

    def test_no_pick_keeps_current(self):
        self.assertEqual(pick_focus("1", None, [row("1", 7)], TODAY), "1")

    def test_current_older_than_seven_days_is_dropped(self):
        self.assertIsNone(pick_focus("1", None, [row("1", 8)], TODAY))

    def test_archived_current_is_dropped(self):
        self.assertIsNone(pick_focus("1", None, [row("2", 1)], TODAY))

    def test_old_pick_does_not_save_an_expired_current(self):
        rows = [row("1", 9), row("2", 5)]
        self.assertIsNone(pick_focus("1", rows[1], rows, TODAY))

    def test_nothing_in_focus(self):
        self.assertIsNone(pick_focus(None, None, [row("1", 0)], TODAY))


if __name__ == "__main__":
    unittest.main()
