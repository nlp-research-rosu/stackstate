"""Daily data refresh for site/data.json. Run by .github/workflows/daily-refresh.yml.

Steps:
  1. Read CISA's Known Exploited Vulnerabilities (KEV) catalog and recent security news feeds.
  2. Add each new KEV entry from the last two weeks that news coverage mentions (or that CISA
     marks as used by ransomware). These need no API key.
  3. If ANTHROPIC_API_KEY is set, ask Claude to pick real incidents out of the news items and
     new formal verification papers out of arXiv, and add those too.
  4. Move incidents older than 91 days to data/archive/incidents.json.
  5. Write site/data.json and data/last-refresh.json (what changed, for the run log).

Usage: python3 scripts/refresh.py [--no-llm] [--today YYYY-MM-DD] [--kev-file PATH] [--dry-run]
"""
import argparse
import csv
import datetime as dt
import email.utils
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import bug_class, component_for, enrich, flaw_group  # noqa: E402
import seed_data  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data.json"
ARCHIVE = ROOT / "data" / "archive" / "incidents.json"
REPORT = ROOT / "data" / "last-refresh.json"

WINDOW_DAYS = 91
KEV_LOOKBACK_DAYS = 14
NEWS_LOOKBACK_DAYS = 10
KEV_URLS = [
    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
    "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json",
]
NEWS_FEEDS = [
    "https://www.bleepingcomputer.com/feed/",
    "https://therecord.media/feed",
    "https://www.securityweek.com/feed/",
    "https://www.helpnetsecurity.com/feed/",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://krebsonsecurity.com/feed/",
    "https://techcrunch.com/category/security/feed/",
    "https://rekt.news/rss.xml",
]
ARXIV_FEEDS = ["https://rss.arxiv.org/rss/cs.LO", "https://rss.arxiv.org/rss/cs.PL", "https://rss.arxiv.org/rss/cs.CR"]
MODEL = "claude-opus-5-5"
UA = "StackStateRefresh/1.0 (+https://github.com/iamjustoutthere/stackstate)"

INCIDENT_KEYS = [
    "id", "date", "victim", "sector", "country", "attack_type", "initial_vector", "root_cause", "band", "layer",
    "product", "cve", "threat_actor", "impact", "records_or_loss", "amount_lost_usd", "funds_recovered_usd",
    "audited_by", "formally_verified", "claim_status", "source_url", "lang", "func",
]
PROOF_KEYS = [
    "id", "project", "band", "layer", "language", "what_verified", "by_whom", "method_class", "year", "status",
    "coverage_of_deployed_code", "deployed_in", "source_url", "lang", "func",
]
BANDS = [
    "Safety-critical systems",
    "Smart contracts & chains", "Applications & data", "Cloud & identity", "Network appliances",
    "Libraries & supply chain", "Crypto & protocols", "Compilers & runtimes", "Kernels & hypervisors",
    "Firmware", "Hardware & ISA",
]
LAYER_BY_BAND = {
    "Safety-critical systems": "safety_critical",
    "Smart contracts & chains": "smart_contract", "Applications & data": "application", "Cloud & identity": "identity",
    "Network appliances": "network_device", "Libraries & supply chain": "library", "Crypto & protocols": "crypto",
    "Compilers & runtimes": "runtime", "Kernels & hypervisors": "os_kernel", "Firmware": "firmware",
    "Hardware & ISA": "hardware",
}
FUNC_BY_BUG = {
    "Authentication & access checks": "Auth & access", "Injection & code execution": "Parsing & input",
    "Memory safety": "Memory & isolation", "Path & request handling": "Network & remote",
    "Contract & business logic": "Money & contracts",
}


# ---------- fetching ----------
def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load_kev(path=None):
    if path:
        return json.loads(Path(path).read_text())
    errors = []
    for u in KEV_URLS:
        try:
            return json.loads(fetch(u))
        except Exception as e:  # try the mirror next
            errors.append(f"{u}: {e}")
    raise RuntimeError("could not load KEV: " + "; ".join(errors))


def _text(el, tag):
    x = el.find(tag)
    return (x.text or "").strip() if x is not None and x.text else ""


def parse_feed(raw, feed):
    """RSS 2.0 or Atom -> list of {title, link, summary, date, feed}."""
    out = []
    root = ET.fromstring(raw)
    atom = "{http://www.w3.org/2005/Atom}"
    for it in root.iter("item"):
        d = _text(it, "pubDate") or _text(it, "{http://purl.org/dc/elements/1.1/}date")
        out.append({"title": _text(it, "title"), "link": _text(it, "link"), "summary": _text(it, "description"), "date": _date(d), "feed": feed})
    for it in root.iter(atom + "entry"):
        link = it.find(atom + "link")
        out.append({
            "title": _text(it, atom + "title"), "link": link.get("href", "") if link is not None else "",
            "summary": _text(it, atom + "summary") or _text(it, atom + "content"),
            "date": _date(_text(it, atom + "updated") or _text(it, atom + "published")), "feed": feed,
        })
    for o in out:
        o["summary"] = re.sub(r"<[^>]+>", " ", o["summary"])
        o["summary"] = re.sub(r"\s+", " ", o["summary"]).strip()[:600]
    return out


def _date(s):
    if not s:
        return ""
    try:
        return email.utils.parsedate_to_datetime(s).date().isoformat()
    except (TypeError, ValueError):
        m = re.match(r"\d{4}-\d{2}-\d{2}", s)
        return m.group(0) if m else ""


def load_feeds(urls, since, log):
    items = []
    for u in urls:
        try:
            got = [i for i in parse_feed(fetch(u), u) if i["link"] and (not i["date"] or i["date"] >= since)]
            items += got
            log["feeds"][u] = len(got)
        except Exception as e:
            log["feeds"][u] = f"error: {e}"
    return items


# ---------- KEV ----------
def kev_incidents(kev, news, known_cves, today, next_id, log):
    since = (today - dt.timedelta(days=KEV_LOOKBACK_DAYS)).isoformat()
    added = []
    for v in kev.get("vulnerabilities", []):
        cve = v["cveID"]
        if v["dateAdded"] < since or cve in known_cves:
            continue
        vendor, product = v["vendorProject"], v["product"].replace(" – ", ": ").replace("–", "-")
        name = product if product.lower().startswith(vendor.lower()) else f"{vendor} {product}"
        words = [w for w in re.findall(r"[a-z0-9]+", f"{vendor} {product}".lower()) if len(w) > 3]
        hits = [n for n in news if cve.lower() in (n["title"] + " " + n["summary"]).lower()]
        if not hits and words:
            # No CVE match: the headline itself must name the product and say it is being exploited.
            hits = [n for n in news if all(w in n["title"].lower() for w in words[:2]) and re.search(r"exploit|zero-day|attack|kev", n["title"].lower())]
        ransomware = v.get("knownRansomwareCampaignUse") == "Known"
        if not hits and not ransomware:
            log["kev_skipped"].append(cve)
            continue
        src = hits[0]["link"] if hits else f"https://nvd.nist.gov/vuln/detail/{cve}"
        news_text = hits[0]["title"] if hits else ""
        r = {k: "" for k in INCIDENT_KEYS}
        r.update(
            id=str(next_id + len(added)), date=v["dateAdded"], victim=f"{name} users", sector="multiple",
            country="global", attack_type="exploited vulnerability" + (" (zero-day)" if "zero-day" in news_text.lower() else ""),
            initial_vector=v["shortDescription"][:400], root_cause=v["vulnerabilityName"], product=name,
            cve=cve, threat_actor="unknown",
            impact=("Added to CISA KEV" + ("; used in ransomware campaigns" if ransomware else "") + (f". Reported: {news_text}" if news_text else ""))[:400],
            formally_verified="none found", claim_status="reported", source_url=src, lang="Not disclosed",
        )
        added.append(finish(r))
    return added


# ---------- Claude ----------
INCIDENT_SCHEMA = {
    "type": "object",
    "properties": {
        "incidents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "integer", "description": "index of the news item this came from"},
                    "date": {"type": "string", "description": "YYYY-MM-DD the incident was disclosed"},
                    "victim": {"type": "string"},
                    "sector": {"type": "string"},
                    "country": {"type": "string"},
                    "attack_type": {"type": "string"},
                    "initial_vector": {"type": "string", "description": "how the attackers got in, one sentence"},
                    "product": {"type": "string", "description": "the software or service that was flawed or abused"},
                    "cve": {"type": "string", "description": "CVE ids separated by '; ', or 'unknown'"},
                    "threat_actor": {"type": "string"},
                    "impact": {"type": "string"},
                    "records_or_loss": {"type": "string"},
                    "people": {"type": "integer", "description": "people or records exposed, 0 if not reported"},
                    "amount_lost_usd": {"type": "number", "description": "money stolen in USD, 0 if not reported"},
                    "code_flaw": {"type": "boolean"},
                    "zero_day": {"type": "boolean"},
                    "bug_class": {"type": "string", "enum": ["Memory safety", "Injection & code execution", "Authentication & access checks", "Contract & business logic", "Path & request handling", "Not disclosed"]},
                    "claim_status": {"type": "string", "enum": ["reported", "claimed/unconfirmed"]},
                },
                "required": ["item", "date", "victim", "sector", "country", "attack_type", "initial_vector", "product", "cve", "threat_actor", "impact", "records_or_loss", "people", "amount_lost_usd", "code_flaw", "zero_day", "bug_class", "claim_status"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["incidents"],
    "additionalProperties": False,
}

PROOF_SCHEMA = {
    "type": "object",
    "properties": {
        "proofs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "integer"},
                    "project": {"type": "string"},
                    "band": {"type": "string", "enum": BANDS},
                    "language": {"type": "string"},
                    "what_verified": {"type": "string"},
                    "by_whom": {"type": "string"},
                    "method_class": {"type": "string", "enum": ["proof_assistant", "proof_assistant+refinement", "smt_deductive", "abstract_interpretation", "symbolic_protocol", "bounded_model_checking", "model_checking", "testing_only"]},
                    "status": {"type": "string", "enum": ["VERIFIED", "PARTIAL", "SPEC_ONLY", "IN_PROGRESS"]},
                    "coverage_of_deployed_code": {"type": "string"},
                    "deployed_in": {"type": "string"},
                },
                "required": ["item", "project", "band", "language", "what_verified", "by_whom", "method_class", "status", "coverage_of_deployed_code", "deployed_in"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["proofs"],
    "additionalProperties": False,
}

INCIDENT_PROMPT = """You maintain a public dashboard of security incidents. Below are recent news items as JSON, each with an index.

Return the items that report a real security incident against a named victim (a company, agency, project or a clearly named group of users of one product), disclosed on or after {since}. Skip opinion pieces, vendor marketing, patch round-ups with no confirmed exploitation, arrests and lawsuits about old incidents, and anything in the "already recorded" list (same victim within three days, or the same CVE).

For each incident, fill every field from the item text only. Do not guess numbers: use 0 when the item gives none.
- code_flaw is true when the reported way in was a defect in software: an exploited CVE or other vulnerability, a zero-day, an injection, an authentication bypass, a memory-safety bug, or a logic bug in a contract or protocol. It is false for phishing, stolen or reused credentials, misconfiguration, malicious packages, insider abuse, or no stated cause.
- zero_day is true only when the item says the flaw was exploited before a fix existed.
- claim_status is "claimed/unconfirmed" when only the attackers claim it.

Already recorded (victim | date | CVE):
{known}

News items:
{items}"""

PROOF_PROMPT = """You maintain a public list of published formal verification of widely used software. Below are new arXiv papers as JSON, each with an index.

Return only papers that report machine-checked verification (proof assistant, SMT-based deductive verification, model checking or symbolic protocol analysis) of real software or protocols that are widely deployed or shipped in production (kernels, compilers, cryptographic libraries, network stacks, parsers, smart contracts, cloud policy engines and similar). Skip pure theory, new logics, tools evaluated only on benchmarks, and papers about verifying toy programs.

Fill every field from the abstract. status is VERIFIED only when the paper claims full functional correctness of the deployed component; otherwise PARTIAL, SPEC_ONLY or IN_PROGRESS.

Papers:
{items}"""


def ask_claude(prompt, schema, log):
    import anthropic  # only needed when an API key is set

    client = anthropic.Anthropic()
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as e:
        log["errors"].append(f"Claude API {e.status_code}: {e.message}")
        return None
    except anthropic.APIConnectionError as e:
        log["errors"].append(f"Claude API connection: {e}")
        return None
    if resp.stop_reason in ("refusal", "max_tokens"):
        log["errors"].append(f"Claude stopped: {resp.stop_reason}")
        return None
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


def llm_incidents(news, data, since, next_id, log):
    known_links = {r["source_url"] for r in data["incidents"]}
    fresh = [n for n in news if n["link"] not in known_links][:150]
    if not fresh:
        return []
    recent = sorted(data["incidents"], key=lambda r: r["date"])[-120:]
    known = "\n".join(f'{r["victim"]} | {r["date"]} | {r["cve"]}' for r in recent)
    items = json.dumps([{"i": i, "title": n["title"], "date": n["date"], "summary": n["summary"]} for i, n in enumerate(fresh)], ensure_ascii=False)
    out = ask_claude(INCIDENT_PROMPT.format(since=since, known=known, items=items), INCIDENT_SCHEMA, log)
    added = []
    for x in (out or {}).get("incidents", []):
        if not 0 <= x["item"] < len(fresh) or x["date"] < since:
            continue
        r = {k: "" for k in INCIDENT_KEYS}
        r.update({k: str(x[k]) for k in ("date", "victim", "sector", "country", "attack_type", "initial_vector", "product", "cve", "threat_actor", "impact", "records_or_loss", "claim_status")})
        r.update(id=str(next_id + len(added)), formally_verified="none found", source_url=fresh[x["item"]]["link"], lang="Not disclosed",
                 amount_lost_usd=str(int(x["amount_lost_usd"])) if x["amount_lost_usd"] else "")
        added.append(finish(r, code_flaw=x["code_flaw"], zero_day=x["zero_day"], bug_class=x["bug_class"], people=x["people"]))
    return added


def llm_proofs(papers, data, today, log):
    known = {p["source_url"] for p in data["proofs"]} | {p["project"].lower() for p in data["proofs"]}
    pat = re.compile(r"verif|proof|proven|certified|formal", re.I)
    fresh = [p for p in papers if p["link"] not in known and pat.search(p["title"] + " " + p["summary"])][:80]
    if not fresh:
        return []
    items = json.dumps([{"i": i, "title": p["title"], "abstract": p["summary"]} for i, p in enumerate(fresh)], ensure_ascii=False)
    out = ask_claude(PROOF_PROMPT.format(items=items), PROOF_SCHEMA, log)
    next_id = max(int(p["id"]) for p in data["proofs"]) + 1
    added = []
    for x in (out or {}).get("proofs", []):
        if not 0 <= x["item"] < len(fresh) or x["project"].lower() in known:
            continue
        p = {k: "" for k in PROOF_KEYS}
        p.update({k: x[k] for k in ("project", "band", "language", "what_verified", "by_whom", "method_class", "status", "coverage_of_deployed_code", "deployed_in")})
        p.update(id=str(next_id + len(added)), layer=LAYER_BY_BAND.get(x["band"], ""), year=str(today.year), source_url=fresh[x["item"]]["link"],
                 lang=_lang(x["language"]), func="Compile & execute")
        added.append(p)
    return added


def _lang(s):
    s = s.lower()
    for pat, lang in [(r"rust", "Rust"), (r"\bc\b|c\+\+|c/c", "C/C++"), (r"solidity|evm|move", "Solidity & chain"), (r"asm|assembly|hardware|verilog", "Assembly & hardware"),
                      (r"java|c#|\.net", "Java/.NET"), (r"python", "Python"), (r"script|ts\b", "JS/TS")]:
        if re.search(pat, s):
            return lang
    return "Specs & policy"


# ---------- shared ----------
def finish(r, **fixed):
    """Fill derived fields: component and band from the stack map, then the classify rules."""
    comp = component_for(r)
    r["component"] = comp
    band = STACK_BAND.get(comp, "")
    r["band"] = band or "Applications & data"
    r["layer"] = LAYER_BY_BAND.get(r["band"], "unknown")
    enrich(r)
    for k, v in fixed.items():
        r[k] = v
    if "code_flaw" in fixed and not fixed["code_flaw"]:
        r.update(bug_class="", zero_day=False, flaw_group="", component="")
    elif fixed.get("code_flaw"):
        # The text rules may have judged this not a code flaw; fill what they skipped.
        r["component"] = r.get("component") or comp
        r["bug_class"] = r.get("bug_class") or bug_class(r)
        r["flaw_group"] = r.get("flaw_group") or flaw_group(r)
    r["func"] = FUNC_BY_BUG.get(r.get("bug_class", ""), "Unknown")
    if "people" in fixed:
        r["people"] = int(fixed["people"] or 0)
    return r


STACK_BAND = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--today")
    ap.add_argument("--kev-file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    today = dt.date.fromisoformat(a.today) if a.today else dt.datetime.now(dt.timezone.utc).date()
    data = json.loads(DATA.read_text())
    # The Verification tab comes from the CSVs, so edits merged there show up on the next run.
    data["proofs"], data["stack"] = seed_data.proofs(), seed_data.stack()
    STACK_BAND.update({s["component"]: s["band"] for s in data["stack"]})
    log = {"run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "today": today.isoformat(), "feeds": {}, "kev_skipped": [], "errors": [],
           "added_incidents": [], "added_proofs": [], "archived": 0}

    news = load_feeds(NEWS_FEEDS, (today - dt.timedelta(days=NEWS_LOOKBACK_DAYS)).isoformat(), log)
    log["news_items"] = len(news)
    next_id = max(int(r["id"]) for r in data["incidents"]) + 1
    known_cves = set(re.findall(r"CVE-\d{4}-\d+", " ".join(r["cve"] for r in data["incidents"])))
    try:
        new = kev_incidents(load_kev(a.kev_file), news, known_cves, today, next_id, log)
    except RuntimeError as e:
        log["errors"].append(str(e))
        new = []

    use_llm = not a.no_llm and os.environ.get("ANTHROPIC_API_KEY")
    log["llm"] = bool(use_llm)
    new_proofs = []
    if use_llm:
        data_plus = {**data, "incidents": data["incidents"] + new}
        new += llm_incidents(news, data_plus, (today - dt.timedelta(days=NEWS_LOOKBACK_DAYS)).isoformat(), next_id + len(new), log)
        papers = load_feeds(ARXIV_FEEDS, (today - dt.timedelta(days=3)).isoformat(), log)
        new_proofs = llm_proofs(papers, data, today, log)

    data["incidents"] += new
    data["proofs"] += new_proofs
    if new_proofs and not a.dry_run:
        f = seed_data.SEED / "dashboard_proofs.csv"
        with open(f, "a", encoding="utf-8", newline="") as out:
            csv.DictWriter(out, PROOF_KEYS).writerows(new_proofs)
    cutoff = (today - dt.timedelta(days=WINDOW_DAYS - 1)).isoformat()
    old = [r for r in data["incidents"] if r["date"] < cutoff]
    data["incidents"] = [r for r in data["incidents"] if r["date"] >= cutoff]
    data["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    log["archived"] = len(old)
    log["added_incidents"] = [f'{r["id"]} {r["date"]} {r["victim"]} ({"code flaw" if r["code_flaw"] else "other cause"})' for r in new]
    log["added_proofs"] = [f'{p["id"]} {p["project"]}' for p in new_proofs]

    print(json.dumps(log, indent=1))
    if a.dry_run:
        return
    if old:
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        arch = json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else []
        seen = {r["id"] for r in arch}
        ARCHIVE.write_text(json.dumps(arch + [r for r in old if r["id"] not in seen], indent=1, ensure_ascii=False) + "\n")
    DATA.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    REPORT.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
