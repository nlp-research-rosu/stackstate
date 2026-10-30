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
VERTICALS = {"rl-training", "rl-envs", "evals", "inference", "agents", "infra"}
COUNT_STAGES = {"scanned", "findings", "verified", "fix_proposed", "reported", "fixed"}
BUG_TYPES = {"wrong-score", "right-answer-marked-wrong", "crash-or-hang", "reward-pays-wrong-answer", "silent-training-bug", "other"}
BUG_STATUSES = {"reported", "acknowledged", "pr-open", "fixed"}
FINDINGS_COLS = ["kind", "id", "repo", "vertical", "bug_type", "title", "status", "issue_url", "fix_url", "fix_by", "stage", "n"]
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

findings = rows("findings.csv")
with open(SEED / "findings.csv", encoding="utf-8", newline="") as f:
    if next(csv.reader(f)) != FINDINGS_COLS:
        err("findings.csv", f"columns must be exactly {FINDINGS_COLS}")
        findings = []  # the row checks below assume the right columns
GH_ISSUE = r"https://github\.com/[\w.-]+/[\w.-]+/issues/\d+"
GH_PR = r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+"
counted, bug_ids = set(), set()
for i, b in enumerate(findings, start=2):
    w = f"findings.csv line {i}"
    if b["vertical"] not in VERTICALS:
        err(w, f"unknown vertical {b['vertical']!r}")
    if b["kind"] == "count":
        stage = b["stage"][5:] if b["stage"].startswith("type_") else b["stage"]
        if (b["stage"] not in COUNT_STAGES) and stage not in BUG_TYPES:
            err(w, f"unknown stage {b['stage']!r}")
        if not b.get("n", "").isdigit():
            err(w, "n must be a whole number")
        if (b["vertical"], b["stage"]) in counted:
            err(w, "duplicate count row")
        counted.add((b["vertical"], b["stage"]))
    elif b["kind"] == "bug":
        for k in ("id", "repo", "title"):
            if not b[k].strip():
                err(w, f"{k} is empty")
        if b["id"] in bug_ids:
            err(w, f"duplicate id {b['id']}")
        bug_ids.add(b["id"])
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", b["repo"]):
            err(w, "repo must be owner/name")
        if b["bug_type"] not in BUG_TYPES:
            err(w, f"unknown bug_type {b['bug_type']!r}")
        if b["status"] not in BUG_STATUSES:
            err(w, f"unknown status {b['status']!r}")
        if not re.fullmatch(GH_ISSUE, b["issue_url"]):
            err(w, "issue_url must be a github.com issue link")
        if b["fix_url"] and not re.fullmatch(GH_PR, b["fix_url"]):
            err(w, "fix_url must be a github.com pull request link")
        if b["status"] in ("pr-open", "fixed") and not b["fix_url"]:
            err(w, f"status {b['status']} needs a fix_url")
        if b["fix_by"] not in ("us", "maintainers", ""):
            err(w, "fix_by must be us, maintainers or blank")
        if re.search(r"[\u2013\u2014]|security audit|vulnerab|exploit", b["title"], re.I):
            err(w, "title has a dash or a word the page does not use")
    else:
        err(w, f"kind must be count or bug, not {b['kind']!r}")
for v in VERTICALS:
    for st in COUNT_STAGES:
        if (v, st) not in counted:
            err("findings.csv", f"missing count row {v}/{st}")

if findings:
    cnt = {(b["vertical"], b["stage"]): int(b["n"]) for b in findings if b["kind"] == "count" and b["n"].isdigit()}
    for v in VERTICALS:
        c = lambda st: cnt.get((v, st), 0)
        if not (c("fixed") <= c("reported") <= c("verified") <= c("findings")):
            err("findings.csv", f"{v}: need fixed <= reported <= verified <= findings")
        if sum(c("type_" + t) for t in BUG_TYPES) != c("findings"):
            err("findings.csv", f"{v}: the type_* counts must add up to findings")
    if sum(cnt.get((v, "reported"), 0) for v in VERTICALS) != len(bug_ids):
        err("findings.csv", f"total reported must equal the number of bug rows ({len(bug_ids)})")

data = json.loads((ROOT / "site" / "data.json").read_text(encoding="utf-8"))
seen = set()
for r in data["incidents"]:
    w = f"site/data.json incident {r.get('id')}"
    expected_fields = 30 + ("under_investigation" in r)
    if len(r) != expected_fields:
        err(w, f"has {len(r)} fields, expected {expected_fields}")
    if "under_investigation" in r and not isinstance(r["under_investigation"], bool):
        err(w, "under_investigation must be true or false")
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
print(f"OK: {len(proofs)} verification efforts, {len(stack)} components, {len(data['incidents'])} incidents, {len(bug_ids)} reported bugs")
