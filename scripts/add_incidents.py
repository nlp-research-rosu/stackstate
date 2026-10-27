"""Add researched incidents to site/data.json.

Input: one or more JSON files, each a list of objects with these keys:
  date, victim, sector, country, attack_type, initial_vector, product, cve, threat_actor, impact,
  records_or_loss, people_exposed, code_flaw, zero_day, claim_status, source_url
Optional: amount_lost_usd, bug_class.

Each new incident gets the next id, its component and layer from the stack map, and the
classify rules, the same way the daily refresh fills them. Entries that match an existing
incident (same CVE and victim, or same victim within three days) are skipped.

Usage: python3 scripts/add_incidents.py FILE.json [FILE.json ...] [--dry-run]
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refresh  # noqa: E402

DATA = refresh.DATA


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def is_dupe(x, existing):
    v = norm(x["victim"])
    d = dt.date.fromisoformat(x["date"])
    cves = set(re.findall(r"CVE-\d{4}-\d+", x.get("cve", "")))
    for r in existing:
        rv = norm(r["victim"])
        close = abs((dt.date.fromisoformat(r["date"]) - d).days) <= 3
        same_name = v == rv or (len(v) > 6 and (v in rv or rv in v))
        if same_name and (close or cves & set(re.findall(r"CVE-\d{4}-\d+", r.get("cve", "")))):
            return r["id"]
    return None


def main():
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    data = json.loads(DATA.read_text())
    refresh.STACK_BAND.update({s["component"]: s["band"] for s in data["stack"]})
    next_id = max(int(r["id"]) for r in data["incidents"]) + 1
    added, skipped = [], []
    for f in files:
        for x in json.loads(Path(f).read_text()):
            if not str(x.get("source_url", "")).startswith("https://"):
                skipped.append(f'{x.get("victim")}: no https source')
                continue
            dup = is_dupe(x, data["incidents"] + added)
            if dup:
                skipped.append(f'{x["victim"]}: matches incident {dup}')
                continue
            r = {k: "" for k in refresh.INCIDENT_KEYS}
            r.update({k: str(x.get(k, "")) for k in ("date", "victim", "sector", "country", "attack_type", "initial_vector", "product", "cve", "threat_actor", "impact", "records_or_loss", "claim_status", "source_url")})
            r.update(id=str(next_id + len(added)), formally_verified="none found", lang="Not disclosed",
                     amount_lost_usd=str(int(x["amount_lost_usd"])) if x.get("amount_lost_usd") else "")
            fixed = {"code_flaw": bool(x["code_flaw"]), "zero_day": bool(x.get("zero_day")), "people": int(x.get("people_exposed") or 0)}
            if x.get("bug_class"):
                fixed["bug_class"] = x["bug_class"]
            added.append(refresh.finish(r, **fixed))
    for r in added:
        print(f'+ {r["id"]} {r["date"]} {r["victim"]} | people {r["people"]:,} | {"code flaw" if r["code_flaw"] else "other cause"} | {r["component"] or "-"}')
    for s in skipped:
        print("  skip", s)
    if not dry and added:
        data["incidents"] += added
        DATA.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {len(added)} new incidents to {DATA}")


if __name__ == "__main__":
    main()
