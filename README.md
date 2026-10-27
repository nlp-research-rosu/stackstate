# Stack State

**State of the Stack** is a public page with two halves. One tracks reported security incidents that started with a flaw in code. The other tracks published formal verification of the software most of us rely on.

Live dashboard: https://claude.ai/artifact/KsHnYSQutEAXduLsAfJept (anyone with the link can view it)

The page has two tabs.

**Incidents** (dark) covers publicly reported incidents from the last 13 weeks where the attackers got in through a flaw in code: exploited vulnerabilities, injection and bypass bugs, contract logic errors. Phishing, stolen credentials, misconfiguration and malicious packages are left out, and so are smart-contract and blockchain incidents with losses under $10M. The tab opens with a map of every component, grouped by layer, where each component that had an incident gets a tile with its count and a 13-week strip. Below that are a treemap of incidents by component, a grid of bug type against layer with zero-days marked, a flow from what the flawed code was doing to who got hit, and a weekly bar chart.

**Verification** (light) shows how many of 102 widely deployed components have full published formal verification, a stack map of how much of each one is verified (with the evidence behind it), and a running total of published verification work.

The tabs are kept apart on purpose. The page never claims that a proof would have stopped a given incident. Every chart is interactive, and a filter set on one chart applies to the rest of its tab.

## Repository layout

```
site/
  index.html          built page, a complete HTML document
  data.json           live data the page rereads every five minutes
dist/                 (git-ignored) artifact.html, the same page for publishing as a claude.ai artifact
src/
  page.template.html  page source; __FONTS__ and __DATA__ are filled in by the build
  fonts.css           embedded font faces (SIL OFL: Newsreader, IBM Plex Mono)
  vendor/d3.v7.9.0.min.js  bundled so charts render offline and in link previews (ISC license)
scripts/
  build_page.py       template + fonts + site/data.json -> site/index.html
  seed_data.py        data/seed/*.csv -> site/data.json (start over from the snapshot)
  classify.py         rules that assign each incident a group (`theme`) and a people count
data/seed/            original CSV snapshot, Jul 28 to Oct 26, 2026, plus stack_components.csv (the stack map, editable)
docs/
  data-schema.md      every field in data.json
  daily-refresh.md    how the daily update job works, including its full instructions
legacy/
  proof-gap-original.html  the first version of the dashboard, kept for reference
```

## Working on it

Requires Python 3.9+ and nothing else.

```sh
python3 scripts/build_page.py          # rebuild site/index.html and dist/artifact.html
python3 -m http.server -d site 8000    # preview at http://localhost:8000 (data.json loads over http)
```

- **Edit the page**: change `src/page.template.html`, then run `build_page.py`.
- **Fix or add a data entry**: edit `site/data.json` directly (see `docs/data-schema.md`), then run `build_page.py` so the embedded fallback copy matches.
- **Change grouping rules**: edit `scripts/classify.py` and keep `docs/daily-refresh.md` in sync, since the daily job follows the written rules.

Opening `site/index.html` straight from disk works; the browser blocks the `data.json` fetch there, so the page uses its embedded copy and the live indicator turns amber.

## Data

All entries come from public reporting and published research, and every incident and verification effort carries a `source_url`. Groups, layers and the "approximate share verified" figures are editorial estimates; corrections are welcome as pull requests that cite a source.

## Publishing

The live page is a claude.ai artifact. To publish changes, ask Claude (in a session with this repo) to publish `dist/artifact.html` with `site/data.json` (as `data.json`) to the artifact URL above. The link preview image is an automatic capture of the top of the Incidents tab, so keep the headline and the first chart rows within the first screen.
