"""Rebuild site/data.json from the seed CSVs in data/seed/.

Run this only to start over from the original snapshot. Day to day, site/data.json is the
source of truth: the daily refresh appends to it (see docs/daily-refresh.md).
"""
import csv
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from classify import enrich  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = ROOT / "data" / "seed"


def rows(name):
    with open(SEED / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


COVERAGE_STATUS = {"full": "verified", "major": "partial", "some": "partial", "narrow": "partial", "none": "blank"}


def stack():
    """Granular stack map. Each row cites proof ids from dashboard_proofs.csv as evidence."""
    out = []
    for r in rows("stack_components.csv"):
        r["usage_log10"] = float(r["usage_log10"])
        r["evidence"] = [e for e in r["evidence"].split(";") if e]
        r["status_class"] = COVERAGE_STATUS[r["coverage"]]
        out.append(r)
    return out


def main():
    incidents = [enrich(r) for r in rows("dashboard_incidents.csv")]
    out = {
        "schema": 1,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "incidents": incidents,
        "proofs": rows("dashboard_proofs.csv"),
        "stack": stack(),
    }
    dest = ROOT / "site" / "data.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {dest}: {len(out['incidents'])} incidents, {len(out['proofs'])} proofs, {len(out['stack'])} stack rows")


if __name__ == "__main__":
    main()
