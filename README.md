# Stack State

**State of the Stack**: a public view of reported security incidents across the industry, next to the published formal verification work on the software everyone depends on.

Live dashboard: https://claude.ai/artifact/KsHnYSQutEAXduLsAfJept (private; shared from the artifact's Share menu)

The dashboard has two tabs:

- **Incidents** (dark): publicly reported incidents from the last 13 weeks. One square per incident, a method-to-area flow, incidents by week, incidents by software layer, and the largest reported data exposures and losses.
- **Verification** (light): published, machine-checked verification across 40 widely deployed components, the least-verified components by reach, verification efforts over time, and incidents against verification work per layer.

Every chart is interactive, and filters on one chart apply to the rest of the tab.

## Repository layout

```
site/
  index.html          built page (published as the artifact)
  data.json           live data the page rereads every five minutes
src/
  page.template.html  page source; __FONTS__ and __DATA__ are filled in by the build
  fonts.css           embedded font faces (SIL OFL: Newsreader, IBM Plex Mono)
scripts/
  build_page.py       template + fonts + site/data.json -> site/index.html
  seed_data.py        data/seed/*.csv -> site/data.json (start over from the snapshot)
  classify.py         rules that assign each incident a group (`theme`) and a people count
data/seed/            original CSV snapshot, Jul 28 - Oct 26, 2026
docs/
  data-schema.md      every field in data.json
  daily-refresh.md    how the daily update job works, including its full instructions
legacy/
  proof-gap-original.html  the first version of the dashboard, kept for reference
```

## Working on it

Requires Python 3.9+ and nothing else.

```sh
python3 scripts/build_page.py          # rebuild site/index.html after editing the template or data
python3 -m http.server -d site 8000    # preview at http://localhost:8000 (data.json loads over http)
```

- **Edit the page**: change `src/page.template.html`, then run `build_page.py`.
- **Fix or add a data entry**: edit `site/data.json` directly (see `docs/data-schema.md`), then run `build_page.py` so the embedded fallback copy matches.
- **Change grouping rules**: edit `scripts/classify.py` and keep `docs/daily-refresh.md` in sync, since the daily job follows the written rules.

Opening `site/index.html` straight from disk works, but the browser blocks the `data.json` fetch, so the page falls back to its embedded copy and the live indicator turns amber.

## Data

All entries come from public reporting and published research, and every incident and verification effort carries a `source_url`. Groups, layers and the "approximate share verified" figures are editorial estimates; corrections are welcome as pull requests that cite a source.

## Publishing

The live page is a claude.ai artifact. To publish changes, ask Claude (in a session with this repo) to publish `site/index.html` with `site/data.json` to the artifact URL above.
