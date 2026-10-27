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


# Which stack-map component (data/seed/stack_components.csv) the flawed code belongs to, for code-flaw
# incidents in the seed snapshot. New incidents get `component` set directly by the daily refresh.
_C = {
    "BI and data tools (Metabase and similar)": [17, 18, 22, 23, 24, 33, 71],
    "Load balancers and ADCs (F5, NetScaler, Kemp)": [20, 85, 105, 116],
    "SSL-VPN gateways (Ivanti, Fortinet, Citrix, Palo Alto)": [65, 136, 141],
    "Firewalls and firewall management": [84, 87, 109],
    "Router and switch operating systems (Cisco IOS, MikroTik, Zyxel)": [90, 104],
    "Email security gateways": [94, 145],
    "SD-WAN controllers": [119],
    "Windows drivers": [27],
    "Windows kernel and win32k": [79],
    "OS services and file handlers (Windows Shell, macOS daemons)": [39, 142],
    "Image, media and font parsers (libwebp, FreeType, ffmpeg)": [120],
    "VPN protocols (WireGuard, IPsec/IKE)": [40],
    "Linux networking (TCP/IP, netfilter, kTLS)": [101],
    "Cellular baseband firmware": [77],
    "IoT cameras and video recorders (Dahua, Hikvision and similar)": [172],
    "V8 JavaScript engine": [73, 86],
    "PHP interpreter": [160],
    "AI gateways and proxies (LiteLLM and similar)": [66],
    "Enterprise collaboration servers (SharePoint, Exchange, Confluence)": [38],
    "E-commerce and CMS platforms (Magento, WordPress)": [35, 78],
    "Remote management software (RMM, file transfer)": [80, 99],
    "Infrastructure management consoles (vCenter)": [37],
    "VoIP and PBX systems": [70],
    "Custom and third-party web applications": [44, 102, 121],
    "CI/CD pipelines and package registries": [67, 69],
    "Web frameworks (Starlette, Django, Express)": [68],
    "DeFi lending and exchange contracts (Aave, Compound, Uniswap)": [56, 61, 97, 128, 138, 169, 170],
    "Chain clients and VM modules (geth, Cosmos SDK/EVM)": [43, 46, 48, 49, 52, 74, 168],
    "Cross-chain bridges": [124, 155],
    "Wallets and signing (hardware wallets, multisig)": [4, 93],
}
COMPONENT_BY_ID = {str(i): c for c, ids in _C.items() for i in ids}

# Keyword rules for incidents added by the daily refresh (first match wins).
# Each pattern is tested against vendor, product, victim and the way in.
COMPONENT_RULES = [
    (r"litellm|ai gateway|llm proxy", "AI gateways and proxies (LiteLLM and similar)"),
    (r"metabase|superset|tableau|power bi|looker|grafana", "BI and data tools (Metabase and similar)"),
    (r"sharepoint|exchange server|confluence|jira|collabora|onlyoffice|zimbra", "Enterprise collaboration servers (SharePoint, Exchange, Confluence)"),
    (r"magento|adobe commerce|wordpress|drupal|joomla|woocommerce|craft cms|sitecore", "E-commerce and CMS platforms (Magento, WordPress)"),
    (r"n-able|n-central|connectwise|screenconnect|kaseya|simplehelp|moveit|goanywhere|cleo|crushftp|rmm|file transfer", "Remote management software (RMM, file transfer)"),
    (r"vcenter|vsphere|vmware aria|hpe oneview|ilo amplifier", "Infrastructure management consoles (vCenter)"),
    (r"voip|pbx|3cx|mitel|avaya|freepbx", "VoIP and PBX systems"),
    (r"esxi", "VMware ESXi"),
    (r"ivanti connect|pulse secure|globalprotect|fortigate ssl|ssl-?vpn|anyconnect|sma ?1000|sma ?100|secure access", "SSL-VPN gateways (Ivanti, Fortinet, Citrix, Palo Alto)"),
    (r"netscaler|citrix adc|big-?ip|\bf5\b|loadmaster|kemp|a10 networks", "Load balancers and ADCs (F5, NetScaler, Kemp)"),
    (r"firewall|fortios|fortigate|pan-os|sonicos|fmc|firepower|asa\b|watchguard|sophos", "Firewalls and firewall management"),
    (r"email (security )?gateway|asyncos|secure email|barracuda esg|proofpoint", "Email security gateways"),
    (r"sd-?wan|vmanage|catalyst sd|velocloud", "SD-WAN controllers"),
    (r"routeros|mikrotik|\bios xe\b|ios xr|nx-os|zyxel|tp-link|d-link|router|switch", "Router and switch operating systems (Cisco IOS, MikroTik, Zyxel)"),
    (r"camera|nvr|dvr|video recorder|hikvision|dahua|axis comm", "IoT cameras and video recorders (Dahua, Hikvision and similar)"),
    (r"baseband|modem|exynos|qualcomm.*(modem|baseband)", "Cellular baseband firmware"),
    (r"bmc|ipmi|idrac|ilo\b|megarac", "Baseboard management controllers (BMC)"),
    (r"uefi|bios|secure boot", "UEFI and BIOS firmware"),
    (r"plc|scada|ics\b|industrial|rockwell|siemens simatic|schneider", "Industrial control and PLC firmware"),
    (r"\bv8\b|chrome|chromium", "V8 JavaScript engine"),
    (r"webkit|safari|firefox|gecko|blink", "Browser engines (Blink, WebKit, Gecko)"),
    (r"\bphp\b", "PHP interpreter"),
    (r"node\.?js", "Node.js runtime"),
    (r"win32k|windows kernel|ntoskrnl|clfs|common log file", "Windows kernel and win32k"),
    (r"windows .*driver|afd\.sys|\.sys\b", "Windows drivers"),
    (r"windows|smartscreen|mark of the web|explorer|shell|macos|apple .*daemon", "OS services and file handlers (Windows Shell, macOS daemons)"),
    (r"android .*(framework|media)|pixel", "Android framework and media services"),
    (r"binder", "Android Binder IPC"),
    (r"ios kernel|xnu|iphone|ipados", "Apple XNU kernel"),
    (r"linux kernel.*(net|tcp|netfilter|ktls)|netfilter|nf_tables", "Linux networking (TCP/IP, netfilter, kTLS)"),
    (r"linux kernel", "Linux core (memory, scheduler, filesystems)"),
    (r"runc|containerd|docker engine", "Container runtimes (runc, containerd)"),
    (r"kubernetes|ingress-nginx", "Kubernetes controllers and operators"),
    (r"libwebp|freetype|ffmpeg|imagemagick|libtiff|libpng|coregraphics|imageio", "Image, media and font parsers (libwebp, FreeType, ffmpeg)"),
    (r"brotli|zlib|\bxz\b|zstd|libarchive|7-zip|winrar", "Compression (zlib, xz, zstd)"),
    (r"openssl", "OpenSSL"),
    (r"openssh|sshd", "OpenSSH"),
    (r"wireguard|ipsec|ike\b", "VPN protocols (WireGuard, IPsec/IKE)"),
    (r"active directory|kerberos|netlogon|ldap", "Active Directory and Kerberos"),
    (r"entra|azure ad|okta|google workspace|identity provider", "Cloud identity providers (Entra ID, Okta, Google)"),
    (r"saml|xml signature", "SAML and XML-signature libraries"),
    (r"jwt|oauth|oidc", "OAuth, OIDC and JWT token validation"),
    (r"nginx|apache http|httpd|envoy|haproxy|iis\b|tomcat", "Web servers and reverse proxies (nginx, Apache, Envoy, HAProxy)"),
    (r"django|express|starlette|spring|struts|rails|laravel|next\.js", "Web frameworks (Starlette, Django, Express)"),
    (r"github actions|gitlab|jenkins|teamcity|ci/cd|package registr", "CI/CD pipelines and package registries"),
    (r"postgres|mysql|sql server|oracle database|mariadb", "Relational databases (PostgreSQL, MySQL, SQL Server)"),
    (r"redis|mongodb|elasticsearch", "Key-value and document stores (Redis, MongoDB)"),
    (r"bridge", "Cross-chain bridges"),
    (r"wallet|multisig|safe\{?wallet|hardware wallet", "Wallets and signing (hardware wallets, multisig)"),
    (r"defi|lending|dex\b|amm|vault|exchange contract|perpetual", "DeFi lending and exchange contracts (Aave, Compound, Uniswap)"),
    (r"chain|cosmos|evm|geth|validator|consensus client", "Chain clients and VM modules (geth, Cosmos SDK/EVM)"),
]


def component_for(r):
    t = " ".join(r.get(k, "") for k in ("product", "victim", "initial_vector", "root_cause")).lower()
    for pat, comp in COMPONENT_RULES:
        if re.search(pat, t):
            return comp
    return ""


# Hand corrections where the largest number in the report is not the people count.
PEOPLE_OVERRIDES = {"Gyazo": 23_620_000}
# Corrections from source checks, where the text rules get it wrong.
ZERO_DAY_OVERRIDES = {"78": True, "79": True, "90": True, "105": True, "160": True}
BUG_CLASS_OVERRIDES = {"27": "Memory safety", "90": "Authentication & access checks", "145": "Path & request handling"}


def enrich(r):
    r["theme"] = theme(r)
    r["code_flaw"] = code_flaw(r)
    r["bug_class"] = bug_class(r) if r["code_flaw"] else ""
    r["zero_day"] = zero_day(r) if r["code_flaw"] else False
    r["flaw_group"] = flaw_group(r) if r["code_flaw"] else ""
    r["component"] = (COMPONENT_BY_ID.get(str(r.get("id"))) or r.get("component", "")) if r["code_flaw"] else ""
    if r["code_flaw"]:
        r["zero_day"] = ZERO_DAY_OVERRIDES.get(str(r.get("id")), r["zero_day"])
        r["bug_class"] = BUG_CLASS_OVERRIDES.get(str(r.get("id")), r["bug_class"])
    text = r.get("records_or_loss", "") if r["theme"] == "crypto" else r.get("records_or_loss", "") + " ; " + r.get("impact", "")
    r["people"] = people(text)
    for prefix, n in PEOPLE_OVERRIDES.items():
        if r.get("victim", "").startswith(prefix):
            r["people"] = n
    return r
