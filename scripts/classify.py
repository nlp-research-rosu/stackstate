"""Shared rules that give each incident a `theme` (dashboard group) and a `people` count."""
import re

THEMES = ["ai", "supply", "cloud", "gov", "fin", "health", "edge", "other", "crypto"]


def theme(r):
    """First matching rule wins. Mirrors the rules in docs/daily-refresh.md."""
    s = r.get("sector", "").lower()
    v = r.get("victim", "").lower()
    p = (r.get("victim", "") + " " + r.get("product", "")).lower()
    if r.get("band") == "Smart contracts & chains" or re.search(r"crypto|defi|blockchain|wallet", s):
        return "crypto"
    if r.get("band") == "AI stack" or r.get("func") == "AI & agents" or re.search(r"litellm|claude|\bllm|\bai\b|\bmcp\b|copilot|kilo code|n8n", p):
        return "ai"
    if r.get("band") == "Libraries & supply chain" or r.get("func") == "Supply chain" or re.search(r"\bnpm\b|pypi|marketplace|\bphp\b|package", p):
        return "supply"
    if re.search(r"government|law enforcement|ministry|tribal|public sector|military|defense manpower", s + " " + v) or re.search(
        r"\bcounty\b|city of|department|ministry|police|municipal|state government|fbi|pentagon|public finan", v
    ):
        return "gov"
    if re.search(r"bank|financ|insur|payment|fintech|credit|private equity|hedge", s + " " + v):
        return "fin"
    if re.search(r"health|hospital|pharma|medical|surgeon", s + " " + v):
        return "health"
    if r.get("band") == "Cloud & identity" or r.get("func") == "Auth & access":
        return "cloud"
    if r.get("band") == "Network appliances":
        return "edge"
    return "other"


_NUM = r"([\d][\d.,]*)\s*(billion|million|bn|m(?![a-z])|k(?![a-z]))?\+?"
_NOUN = r"(records|accounts|people|individuals|users|customers|patients|members|residents|students|employees|persons|clients|living|professionals|citizens|taxpayers|subscribers|children|voters|applicants)"


def people(text):
    """Largest 'N <people-like noun>' figure in the text, or 0."""
    best = 0.0
    for m in re.finditer(_NUM + r"\s*(?:[a-z-]+\s){0,2}?" + _NOUN, text, re.I):
        n = float(m.group(1).replace(",", ""))
        u = (m.group(2) or "").lower()
        n *= 1e9 if u in ("billion", "bn") else 1e6 if u in ("million", "m") else 1e3 if u == "k" else 1
        best = max(best, n)
    return int(round(best))


# An incident counts as a code flaw when its reported way in was a defect in software:
# a CVE, an exploited or zero-day vulnerability, an injection/bypass/overflow bug, or a
# logic bug in a contract or protocol. Phishing, stolen credentials, misconfiguration,
# malicious packages and incidents with no stated cause do not count.
_CODE = re.compile(
    r"zero-day|0-day|exploited vulnerab|\bkev\b|sql injection|command injection|code injection|template-engine|deserializ|"
    r"buffer overflow|heap overflow|double-free|underflow|overflow|memory corruption|type confusion|out-of-b|\brce\b|"
    r"remote code|auth(entication)? bypass|authorization flaw|path traversal|directory traversal|ssrf|logic (bug|error)|"
    r"range-proof|precompile|reentrancy|oracle|price manipulation|unauthorized mint|exploited flaw|flaw in|crypto exploit"
)
_NOT_CODE = re.compile(r"phish|vishing|social engineer|helpdesk|stolen credential|password spray|insider|misconfig|malicious (package|extension)|legitimate (access|cpr)")
CODE_FLAW_INCLUDE = ("Coldcard", "Trezor", "SafePal", "The Hospital for Sick Children", "Gyazo", "Frontline Education",
                     "Liquid Network", "US Defense Manpower", "Bitget", "Targets of autonomous AI agent")
CODE_FLAW_EXCLUDE = ("VIVOTEK", "Healthcare, pharma", "Denmark national population", "Estore Corp", "Developers using VS Code")


def code_flaw(r):
    v = r.get("victim", "")
    if v.startswith(CODE_FLAW_EXCLUDE):
        return False
    if v.startswith(CODE_FLAW_INCLUDE):
        return True
    t = " ".join(r.get(k, "") for k in ("attack_type", "initial_vector", "root_cause", "impact")).lower()
    has_cve = bool(re.search(r"cve-\d", r.get("cve", "").lower()))
    if _NOT_CODE.search(t) and not (has_cve or "zero-day" in t):
        return False
    return has_cve or bool(_CODE.search(t)) or r.get("root_cause") in ("logic_bug", "access_control", "price_manipulation", "oracle_manipulation")


BUG_CLASSES = ["Memory safety", "Injection & code execution", "Authentication & access checks", "Contract & business logic", "Path & request handling", "Not disclosed"]


def bug_class(r):
    """Coarse class of the flaw, from the reported way in."""
    t = " ".join(r.get(k, "") for k in ("initial_vector", "attack_type", "impact", "root_cause", "product", "victim")).lower()
    if "metabase" in t:
        return "Injection & code execution"
    if re.search(r"overflow|underflow|double-free|use-after|out-of-b|type confusion|memory corruption|heap|race condition|link following", t):
        return "Memory safety"
    if re.search(r"injection|template-engine|command execution|code execution|\brce\b|deserializ", t):
        return "Injection & code execution"
    if re.search(r"auth|permission|bypass|jwt|access control|forge|unauthorized|signature|whitelist", t):
        return "Authentication & access checks"
    if re.search(r"oracle|price|governance|flash|mint|peg|logic|rounding|range-proof|precompile|interaction|created", t):
        return "Contract & business logic"
    if re.search(r"traversal|ssrf|host header", t):
        return "Path & request handling"
    return "Not disclosed"


def zero_day(r):
    t = " ".join(r.get(k, "") for k in ("attack_type", "initial_vector", "impact")).lower()
    return bool(re.search(r"zero-day|0-day", t))


def flaw_group(r):
    """Key shared by incidents that came from the same flaw: a named campaign or the first CVE."""
    t = " ".join(r.get(k, "") for k in ("initial_vector", "product", "victim")).lower()
    if "metabase" in t:
        return "Metabase SQL injection (CVE-2026-72898)"
    if re.search(r"cosmos|evmos", t):
        return "Cosmos EVM precompile flaw"
    c = r.get("cve", "").split(";")[0].strip()
    return c if c.lower().startswith("cve-") else ""


# Hand corrections where the largest number in the report is not the people count.
PEOPLE_OVERRIDES = {"Gyazo": 23_620_000}


def enrich(r):
    r["theme"] = theme(r)
    r["code_flaw"] = code_flaw(r)
    r["bug_class"] = bug_class(r) if r["code_flaw"] else ""
    r["zero_day"] = zero_day(r) if r["code_flaw"] else False
    r["flaw_group"] = flaw_group(r) if r["code_flaw"] else ""
    text = r.get("records_or_loss", "") if r["theme"] == "crypto" else r.get("records_or_loss", "") + " ; " + r.get("impact", "")
    r["people"] = people(text)
    for prefix, n in PEOPLE_OVERRIDES.items():
        if r.get("victim", "").startswith(prefix):
            r["people"] = n
    return r
