# Contributing to Stack State

Stack State is a small community project, and both of its lists are incomplete. Formal verification goes back to the 1960s, and a lot of good work (aerospace, rail, medical devices, hardware, older research systems) isn't on the list yet. Additions and corrections are very welcome, from anyone.

## The quick way: open an issue

Pick a form on the [new issue page](https://github.com/nlp-research-rosu/stackstate/issues/new/choose):

- **Add a verification project.** A link to the paper, report or repository is all we need.
- **Add an incident.** It should be publicly reported, and the way in should be a flaw in code.
- **Correction.** Anything wrong, out of date or overstated.
- **New row, column or category.** A component missing from the stack map, a whole category of software, a new field, or an edge case to decide on. For example, should proofs of algorithms or distributed protocols count when they aren't tied to one shipped product?

Every entry on the page also has a "Suggest a correction" link that opens a pre-filled issue.

## The direct way: a pull request

The Verification tab comes from two CSV files. You can edit them on GitHub in the browser.

- **`data/seed/dashboard_proofs.csv`** has one row per verification effort. Give a new row the next unused `id`, and fill in at least `project`, `band`, `what_verified`, `by_whom`, `method_class`, `year`, `status` and `source_url`.
  - `status`:
    - `VERIFIED` means full functional correctness of the deployed component.
    - `PARTIAL` means some properties or part of the code.
    - `SPEC_ONLY` means a model or specification only.
    - `TESTING_ONLY` and `IN_PROGRESS` are also allowed.
  - `method_class`: one of `proof_assistant`, `proof_assistant+refinement`, `smt_deductive`, `abstract_interpretation`, `symbolic_protocol`, `bounded_model_checking`, `model_checking` or `testing_only`.
- **`data/seed/stack_components.csv`** has one row per component on the stack map.
  - `coverage` is `full`, `major`, `some`, `narrow` or `none`.
  - `evidence` lists the ids of rows in the proofs file that support it, separated by semicolons.
  - `usage_log10` is a rough size of the install base. For example, 9.0 means about a billion devices or users.

Incidents live in `site/data.json`. A daily job adds them, and you can fix one by editing its entry there. The field list is in `docs/data-schema.md`.

Before you open the pull request, run:

```sh
python3 scripts/validate.py
```

The same check runs automatically on every pull request. Once a change is merged, it shows up on the site after the next daily refresh.

## What we ask

- **Link a source for everything.** It should be something a reader can open.
- **Prefer understating to overstating.** If a proof covers a model rather than the shipped code, or only some properties, say so. Use `PARTIAL` or `SPEC_ONLY` rather than `VERIFIED`.
- **Keep the two tabs separate.** The page never claims a proof would have prevented an incident.
