"""Read the CSVs in data/seed/, and rebuild site/data.json from them.

The Verification tab is edited in two CSVs, which are its source of truth:
  data/seed/stack_components.csv  one row per software component (the stack map)
  data/seed/dashboard_proofs.csv  one row per published verification effort
The Our contributions tab is edited in one CSV, exported from our findings tracker (only publicly reported bugs are listed):
  data/seed/findings.csv          count rows (stage totals per vertical) and bug rows (the public list)
The daily refresh (scripts/refresh.py) reloads both into site/data.json on every run.

Incidents are different: site/data.json is their source of truth, and the daily refresh
appends to it. Running this script directly rebuilds incidents from the original snapshot
(data/seed/dashboard_incidents.csv), which drops everything the refresh has added since.
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


def proofs():
    return rows("dashboard_proofs.csv")


def stack():
    """Granular stack map. Each row cites proof ids from dashboard_proofs.csv as evidence."""
    out = []
    for r in rows("stack_components.csv"):
        r["usage_log10"] = float(r["usage_log10"])
        r["evidence"] = [e for e in r["evidence"].split(";") if e]
        r["status_class"] = COVERAGE_STATUS[r["coverage"]]
        out.append(r)
    return out


def contrib():
    """Our contributions tab: stage counts per vertical and the public bug list, both from findings.csv."""
    r = rows("findings.csv")
    counts = [{"vertical": x["vertical"], "stage": x["stage"], "n": int(x["n"])} for x in r if x["kind"] == "count"]
    bugs = [{k: v for k, v in x.items() if k not in ("kind", "stage", "n")} for x in r if x["kind"] == "bug"]
    return {"counts": counts, "bugs": bugs}


def main():
    incidents = [enrich(r) for r in rows("dashboard_incidents.csv")]
    out = {
        "schema": 1,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "incidents": incidents,
        "proofs": proofs(),
        "stack": stack(),
        "contrib": contrib(),
    }
    dest = ROOT / "site" / "data.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {dest}: {len(out['incidents'])} incidents, {len(out['proofs'])} proofs, {len(out['stack'])} stack rows")


if __name__ == "__main__":
    main()
