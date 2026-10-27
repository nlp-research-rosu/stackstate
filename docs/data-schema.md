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
| bug_class | for code flaws: Memory safety, Injection & code execution, Authentication & access checks, Contract & business logic, Path & request handling, Not disclosed |
| zero_day | boolean; exploited before a fix existed |
| flaw_group | key shared by incidents from the same flaw (a named campaign or the first CVE) |
| code_flaw | boolean; true when the reported way in was a defect in software (rules in `scripts/classify.py`). Only these appear on the Incidents tab. |

**band values:** People, AI stack, Smart contracts & chains, Applications & data, Cloud & identity, Network appliances, Libraries & supply chain, Crypto & protocols, Compilers & runtimes, Kernels & hypervisors, Firmware, Hardware & ISA.

The page derives the incident method (ransomware, data theft, exploited vulnerability, supply chain, AI-enabled, crypto theft, other) from `attack_type`.

## proofs

id, project, band, layer, language, what_verified, by_whom, method_class (`proof_assistant`, `proof_assistant+refinement`, `smt_deductive`, `symbolic_protocol`, `bounded_model_checking`, `model_checking`, `testing_only`), year, status (`VERIFIED`, `PARTIAL`, `SPEC_ONLY`, `TESTING_ONLY`, `IN_PROGRESS`), coverage_of_deployed_code, deployed_in, source_url, lang, func.

## stack

Built from `data/seed/stack_components.csv` (edit that file, then run `scripts/seed_data.py`).

component, band, usage_estimate (text), usage_log10 (number, log10 of estimated install base; sets block width), coverage (`full`, `major`, `some`, `narrow`, `none`), evidence (list of proof ids from `proofs` that support the coverage level), what_is_unverified, closest_existing_work, status_class (derived: `verified` for full, `partial` for major/some/narrow, `blank` for none).

Coverage levels are editorial estimates of how much of the deployed component is covered by published, machine-checked verification. Every level above `none` must cite at least one proof id.

## archive

Incidents older than 13 weeks move to `archive/incidents.json` (same fields) when the daily job runs.
