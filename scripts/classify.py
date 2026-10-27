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


# Hand corrections where the largest number in the report is not the people count.
PEOPLE_OVERRIDES = {"Gyazo": 23_620_000}


def enrich(r):
    r["theme"] = theme(r)
    text = r.get("records_or_loss", "") if r["theme"] == "crypto" else r.get("records_or_loss", "") + " ; " + r.get("impact", "")
    r["people"] = people(text)
    for prefix, n in PEOPLE_OVERRIDES.items():
        if r.get("victim", "").startswith(prefix):
            r["people"] = n
    return r
