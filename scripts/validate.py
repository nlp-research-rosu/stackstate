"""Check the data before it is merged. Run: python3 scripts/validate.py (exits 1 on errors)."""
import csv
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = ROOT / "data" / "seed"
BANDS = {
    "AI stack", "Safety-critical systems", "Smart contracts & chains", "Applications & data", "Cloud & identity",
    "Network appliances", "Libraries & supply chain", "Crypto & protocols", "Compilers & runtimes",
    "Kernels & hypervisors", "Firmware", "Hardware & ISA",
}
METHODS = {"proof_assistant", "proof_assistant+refinement", "smt_deductive", "abstract_interpretation", "symbolic_protocol", "bounded_model_checking", "model_checking", "testing_only"}
STATUSES = {"VERIFIED", "PARTIAL", "SPEC_ONLY", "TESTING_ONLY", "IN_PROGRESS"}
COVERAGE = {"full", "major", "some", "narrow", "none"}
errors = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def rows(name):
    with open(SEED / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


proofs = rows("dashboard_proofs.csv")
ids = set()
year_now = dt.date.today().year
for i, p in enumerate(proofs, start=2):
    w = f"dashboard_proofs.csv line {i}"
    for k in ("id", "project", "band", "what_verified", "by_whom", "method_class", "year", "status", "source_url"):
        if not p.get(k, "").strip():
            err(w, f"{k} is empty")
    if p["id"] in ids:
        err(w, f"duplicate id {p['id']}")
    ids.add(p["id"])
    if p["band"] not in BANDS:
        err(w, f"unknown band {p['band']!r}")
    if p["method_class"] not in METHODS:
        err(w, f"unknown method_class {p['method_class']!r}")
    if p["status"] not in STATUSES:
        err(w, f"unknown status {p['status']!r}")
    if not (re.fullmatch(r"\d{4}", p["year"]) and 1960 <= int(p["year"]) <= year_now):
        err(w, f"year {p['year']!r} is not between 1960 and {year_now}")
    if not p["source_url"].startswith("https://"):
        err(w, "source_url must start with https://")

names = set()
stack = rows("stack_components.csv")
for i, s in enumerate(stack, start=2):
    w = f"stack_components.csv line {i}"
    if not s["component"].strip():
        err(w, "component is empty")
    if s["component"] in names:
        err(w, f"duplicate component {s['component']!r}")
    names.add(s["component"])
    if s["band"] not in BANDS:
        err(w, f"unknown band {s['band']!r}")
    if s["coverage"] not in COVERAGE:
        err(w, f"coverage must be one of {sorted(COVERAGE)}")
    try:
        float(s["usage_log10"])
    except ValueError:
        err(w, "usage_log10 must be a number")
    for e in filter(None, s["evidence"].split(";")):
        if e not in ids:
            err(w, f"evidence id {e} is not in dashboard_proofs.csv")

data = json.loads((ROOT / "site" / "data.json").read_text(encoding="utf-8"))
seen = set()
for r in data["incidents"]:
    w = f"site/data.json incident {r.get('id')}"
    if len(r) != 30:
        err(w, f"has {len(r)} fields, expected 30")
    if r.get("id") in seen:
        err(w, "duplicate id")
    seen.add(r.get("id"))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("date", "")):
        err(w, "date must be YYYY-MM-DD")
    if not isinstance(r.get("code_flaw"), bool) or not isinstance(r.get("zero_day"), bool):
        err(w, "code_flaw and zero_day must be true or false")
    if r.get("component") and r["component"] not in names:
        err(w, f"component {r['component']!r} is not on the stack map")
    if not str(r.get("source_url", "")).startswith("https://"):
        err(w, "source_url must start with https://")

if errors:
    print(f"{len(errors)} problem(s):")
    print("\n".join("  " + e for e in errors))
    sys.exit(1)
print(f"OK: {len(proofs)} verification efforts, {len(stack)} components, {len(data['incidents'])} incidents")
