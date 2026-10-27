# data.json schema (version 1)

```json
{ "schema": 1, "generated_at": "2026-10-27T06:51:00Z", "incidents": [], "proofs": [], "stack": [] }
```

All values are strings unless noted. Use `""` for unknown, and `"unknown"` for `cve` and `threat_actor`.

## incidents

| field | meaning |
|---|---|
| id | unique integer, as a string |
| date | disclosure date, `YYYY-MM-DD` |
| victim, sector, country | who was affected |
| attack_type, initial_vector, root_cause | what happened, as reported |
| band | layer of the stack (see list below) |
| layer | finer layer tag: ai_stack, application, crypto, firmware, hardware, human/social, identity, library, network_device, os_kernel, runtime, saas_cloud, smart_contract, unknown |
| product, cve, threat_actor | affected product, CVE IDs, named actor |
| impact | one or two factual sentences |
| records_or_loss | as reported, e.g. `~1.2 million records` |
| amount_lost_usd, funds_recovered_usd | numbers as strings, `""` if none |
| audited_by | audit firm if reported |
| formally_verified | `none found` unless the affected code has published verification |
| claim_status | `reported` (confirmed by victim or authority) or `claimed/unconfirmed` |
| source_url | the source used |
| lang | C/C++, Rust, Go, Java/.NET, Python, JS/TS, PHP, Solidity & chain, Assembly & hardware, Specs & policy, Not disclosed |
| func | Parsing & input, Auth & access, Crypto & keys, Memory & isolation, Network & remote, Data & storage, Compile & execute, Money & contracts, AI & agents, Supply chain, People, Unknown |
| theme | dashboard group: ai, supply, cloud, gov, fin, health, edge, other, crypto (rules in `scripts/classify.py`) |
| people | integer; people, accounts or records exposed if reported, else 0 |

**band values:** People, AI stack, Smart contracts & chains, Applications & data, Cloud & identity, Network appliances, Libraries & supply chain, Crypto & protocols, Compilers & runtimes, Kernels & hypervisors, Firmware, Hardware & ISA.

The page derives the incident method (ransomware, data theft, exploited vulnerability, supply chain, AI-enabled, crypto theft, other) from `attack_type`.

## proofs

id, project, band, layer, language, what_verified, by_whom, method_class (`proof_assistant`, `proof_assistant+refinement`, `smt_deductive`, `symbolic_protocol`, `bounded_model_checking`, `model_checking`, `testing_only`), year, status (`VERIFIED`, `PARTIAL`, `SPEC_ONLY`, `TESTING_ONLY`, `IN_PROGRESS`), coverage_of_deployed_code, deployed_in, source_url, lang, func.

## stack

component, band, layer, usage_estimate, usage_log10 (log10 of estimated install base), status_class (`verified`, `partial`, `blank`), verification_status, blank_rank, blank_score, incidents_3mo, what_is_unverified, closest_existing_work.

The page's "approximate share verified" is `1 - blank_score / usage_log10` (1.0 for `verified`). It is a rough editorial estimate, not a measurement.

## archive

Incidents older than 13 weeks move to `archive/incidents.json` (same fields) when the daily job runs.
