# Stack State

**Ship as fast as the machine can check.**

Writing code is cheap now, and checking it is the slow part. When a machine checks every change, teams and their agents can move fast and still trust what ships. Stack State tracks how far the world's software is from that.

**Live dashboard: [stackstate.ai](https://stackstate.ai)** (updated daily)

## What's on the page

**Incidents** shows what unchecked code cost over the last 13 weeks. It counts publicly reported incidents where attackers got in through a flaw in code, such as an exploited CVE, an injection or a memory-safety bug. You can size the treemap by incidents, people exposed or money stolen. Phishing, stolen credentials, misconfiguration, malicious packages and blockchain losses under $10M are left out.

**How much of the world is verified** maps widely used software, from kernels and browsers to avionics and smart contracts. Each component shows the published, machine-checked verification it has, by anyone. Red marks components with no known verification that also had a public incident in the window.

Red records history. The page never claims a proof would have prevented an incident.

## Contribute

Both lists are incomplete by design, and every entry links to a public source. If something is missing or wrong, you can help fix it:

- [Open an issue](https://github.com/nlp-research-rosu/stackstate/issues/new/choose) to add an incident or a verification effort, correct an entry, or suggest a new component or category. A link is all we need.
- Or edit the data directly and open a pull request. [CONTRIBUTING.md](CONTRIBUTING.md) explains how.

Anyone's verification work counts, whatever the tool or method.

## How it works

A GitHub Action runs every day at 05:07 UTC. It pulls CISA's Known Exploited Vulnerabilities catalog and major security news feeds, adds new incidents with their sources, moves anything older than 13 weeks to the archive and rebuilds the page. Vercel deploys each new commit. The details are in [docs/daily-refresh.md](docs/daily-refresh.md).

The page is a single HTML file with [d3](https://d3js.org) bundled in. It needs no build tools beyond Python.

```
src/page.template.html        page source
site/index.html, data.json    the built page and its live data
data/seed/                    stack_components.csv and dashboard_proofs.csv (the Verification tab)
data/archive/                 incidents that have aged out of the window
scripts/refresh.py            the daily update
scripts/classify.py           rules that group incidents and match them to components
scripts/validate.py           data checks, run on every pull request
docs/data-schema.md           every field in data.json
```

## Run it locally

Requires Python 3.9 or later and no other dependencies.

```sh
python3 scripts/build_page.py          # rebuild the page from the template and data
python3 scripts/validate.py            # check the data
python3 -m http.server -d site 8000    # preview at http://localhost:8000
python3 scripts/refresh.py --dry-run   # see what today's refresh would add
```

## Data

All entries come from public reporting and published research. Groups, install bases and verified shares are rough editorial estimates, and corrections that cite a source are welcome.

## License

The code is under the [MIT License](LICENSE). The data (`data/` and `site/data.json`) is under [CC BY 4.0](LICENSE-DATA): reuse it freely, with credit to Stack State. Bundled third-party files keep their own licenses: d3 (ISC) and the Newsreader and IBM Plex Mono fonts (SIL Open Font License).

Maintained by Intent Computing. Contributions welcome.
