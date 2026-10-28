# Stack State

**State of the Stack** is a small community project with two incomplete lists. One tracks publicly reported security incidents that started with a flaw in code. The other tracks published formal verification of widely used software, from 1990s safety-critical systems to recent work. Formal verification goes back to the 1960s, and much of it isn't on the list yet: see [CONTRIBUTING.md](CONTRIBUTING.md) to add or fix something.

Live dashboard: https://stackstate.ai (also published at https://claude.ai/artifact/KsHnYSQutEAXduLsAfJept)

The page has two tabs.

**Incidents** (dark) covers publicly reported incidents from the last 13 weeks where the attackers got in through a flaw in code: exploited vulnerabilities, injection and bypass bugs, contract logic errors. Phishing, stolen credentials, misconfiguration and malicious packages are left out, and so are smart-contract and blockchain incidents with losses under $10M. The tab opens with a treemap of where the flawed code was, by component, that can be sized by number of incidents, people exposed or money stolen. Below that are a grid of bug type against layer with zero-days marked, a flow from what the flawed code was doing to who got hit, and a weekly bar chart.

**Verification** (light) shows how many of the 108 widely deployed components on our list (including avionics, rail, air traffic control, medical devices and spacecraft) have full published formal verification, a stack map of how much of each one is verified (with the evidence behind it), and a running total of published verification work.

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
  seed_data.py        data/seed/*.csv -> site/data.json (start over from the snapshot; drops refresh additions)
  validate.py         checks the CSVs and data.json (runs on every pull request)
  refresh.py          daily update: CISA KEV + news feeds (+ Claude, if ANTHROPIC_API_KEY is set) -> site/data.json
  classify.py         rules that assign each incident a group (`theme`) and a people count
data/seed/            original CSV snapshot, Jul 28 to Oct 26, 2026, plus stack_components.csv (the stack map, editable)
docs/
  data-schema.md      every field in data.json
  daily-refresh.md    how the daily update works (GitHub Actions, then the artifact publish)
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

There are two copies of the page:

- **Public site (Vercel):** https://stackstate.ai, the link to share. Vercel deploys the `site/` folder of `main` on every commit (settings in `vercel.json`, no build step), so it updates after each daily refresh. Visitor counts come from Vercel Web Analytics (no cookies). Link previews use `site/og.png`, which the daily job re-renders. If the site lives at another address, set `STACKSTATE_URL` (in the workflow and when running `build_page.py`) so the preview tags point at it.
- **claude.ai artifact:** https://claude.ai/artifact/KsHnYSQutEAXduLsAfJept, republished daily by a scheduled Claude task (see `docs/daily-refresh.md`).

### Setting up Vercel (once)

1. At https://vercel.com/new, import `iamjustoutthere/stackstate` (allow the Vercel GitHub app on that repository).
2. Name the project `stackstate`. Leave the framework preset as Other; `vercel.json` already sets the output directory to `site` with no build. Deploy.
3. In the project, open Analytics and enable Web Analytics.
4. In the project, open Settings, then Domains, and add `stackstate.ai` (and `www.stackstate.ai`), then set the DNS records Vercel shows at your domain registrar.
