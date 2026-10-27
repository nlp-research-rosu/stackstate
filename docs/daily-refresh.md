# Daily refresh

A scheduled Claude task ("Proof Gap data refresh", runs daily at 05:37 UTC) starts a fresh session that:

1. reads the published `data.json` from the artifact,
2. searches reputable public sources for incidents disclosed since the newest entry, and for new formal verification results, confirming each by opening its source,
3. adds them using the fields in `data-schema.md` and the grouping rules below,
4. moves incidents older than 91 days to `archive/incidents.json`,
5. validates the file and republishes `data.json` to the artifact.

It updates the artifact, not this repository. To bring the repo up to date, copy the artifact's current `data.json` into `site/data.json` and commit it, or change the task so it also commits here.

## Code flaws

Every new incident gets `code_flaw`: true when the reported way in was a defect in software (a CVE or other exploited vulnerability, a zero-day, an injection, authentication bypass or memory-safety bug, or a logic bug in a smart contract or protocol). Phishing, stolen credentials, misconfiguration, malicious packages, abuse of legitimate access and incidents with no stated cause get false. Only `code_flaw: true` incidents appear on the Incidents tab, but all are kept in the data.

## Grouping rules (first match wins)

1. **crypto**: band Smart contracts & chains, or crypto/DeFi/blockchain/wallet victims
2. **ai**: band AI stack, func AI & agents, or LLM/agent/MCP products
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
