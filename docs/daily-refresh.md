# Daily refresh

A scheduled GitHub Action keeps the dashboard current.

**GitHub Actions, 05:07 and 17:07 UTC** (`.github/workflows/daily-refresh.yml`) runs `scripts/refresh.py`, rebuilds the page and commits the result to `main`. The script:

1. reads CISA's Known Exploited Vulnerabilities catalog and the news feeds listed in `NEWS_FEEDS`;
2. adds each KEV entry from the last 14 days that news coverage mentions, or that CISA marks as used by ransomware, as a code-flaw incident sourced to the news article;
3. if the repository secret `OPENROUTER_API_KEY` is set, asks Claude through OpenRouter to pick incidents with a named victim out of the news items, and new machine-checked verification papers out of arXiv (cs.LO, cs.PL, cs.CR), and adds those too;
4. moves incidents older than 91 days to `data/archive/incidents.json`;
5. writes `site/data.json` and a run log, `data/last-refresh.json`, listing what was added, skipped and any errors.

Without the key the job still adds KEV entries and rolls the window, but adds no breaches or verification papers, and the run fails so the gap is visible.

Run it by hand from the Actions tab (Daily refresh, Run workflow), or locally with `python3 scripts/refresh.py --dry-run` to see what it would add.

A mirror of the page on claude.ai is republished from `main` after each run. That step only rebuilds the page and never edits data.

The repository is the source of truth. To correct an entry, edit `site/data.json` (see `data-schema.md`) and commit; the next publish picks it up.

## Code flaws

Every new incident gets `code_flaw`: true when the reported way in was a defect in software (a CVE or other exploited vulnerability, a zero-day, an injection, authentication bypass or memory-safety bug, or a logic bug in a smart contract or protocol). Phishing, stolen credentials, misconfiguration, malicious packages, abuse of legitimate access and incidents with no stated cause get false. Only `code_flaw: true` incidents appear on the Incidents tab, but all are kept in the data.

## Grouping rules (first match wins)

1. **crypto**: band Smart contracts & chains, or crypto/DeFi/blockchain/wallet victims
2. **ai**: band AI stack, func AI & agents, or LLM/agent/MCP products (the page shows these as Cloud & SaaS, or Government)
3. **supply**: band Libraries & supply chain, func Supply chain, or npm/PyPI/marketplace/PHP/package compromises
4. **gov**: government, public agencies, police, councils, national registers, military
5. **fin**: banks, financial services, payments, funds
6. **health**: hospitals, health systems, pharma, medical
7. **cloud**: band Cloud & identity, or func Auth & access
8. **edge**: band Network appliances
9. **other**

Keep these in step with `scripts/classify.py`.

## Source standards

Prefer primary or reputable sources: vendor and agency advisories, SEC 8-K filings, CISA KEV additions, regulator breach notices, BleepingComputer, The Record, SecurityWeek, Krebs on Security, TechCrunch, Reuters. Skip rumors with no named victim or source, and anything already recorded (same victim within three days, or the same CVE). Never add an entry without a source that was actually opened.
