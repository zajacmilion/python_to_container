# AI job-market scraper (PL)

Scrapes Polish IT job boards for AI/ML platform roles, normalises the
technology names, and ranks demand — input for a concrete learning path.

## Run

Dependencies (`requests`) are declared in `pyproject.toml`/`uv.lock` and
managed with [uv](https://docs.astral.sh/uv/) — no manual `pip install`:

```bash
uv run python run.py            # full scrape -> data/offers_*.json
uv run python run.py --quick    # 1 page per query
uv run python analyze.py        # bucket + rank -> data/analysis.json
uv run python report.py         # render -> data/report.html
```

`analyze.py` reads the saved offers, so you can re-tune the taxonomy and
re-rank without hitting the portals again. `report.py` reads `analysis.json`
and `data/offers_*.json` and renders a static, dependency-free HTML page:
per-bucket tech tables with salary + share-of-offers bars, the AI-vs-QA gap
and overlap lists, and a searchable/filterable table of every individual
offer (by title/company/skills text, profile, and source — filtering is
plain client-side JS, no build step).

If you're not using `uv run`, activate the venv first
(`source .venv/bin/activate`) so `python` resolves to it.

## Sources

| Portal | Access route | Notes |
|---|---|---|
| justjoin.it | Next.js App Router streaming payload (`self.__next_f`) | 100 offers/page, clean `requiredSkills` |
| nofluffjobs.com | `POST /api/search/posting` | needs `salaryCurrency`; `rawSearch` is unreliable — see below |
| pracuj.pl | react-query cache inside `__NEXT_DATA__` | TLS-fingerprints python-requests, so `common.get()` falls back to curl |
| czyjesteldorado.pl | streaming payload | cross-portal aggregator; carries a `source` field |
| theprotocol.it | **not working** | `apus-api.theprotocol.it/offers/search` rejects unauthenticated calls (400). Partially covered via the aggregator. |

## Why title-based filtering

Portal keyword search cannot be trusted — nofluffjobs' `rawSearch` returns
most of its database when it can't parse the phrase (2 400+ hits for
"AI Engineer"). `scraper/relevance.py` (in `src/python_to_container/`)
therefore buckets offers on the job
**title**, which is the honest signal, and drops non-engineering roles that
merely name-drop AI (sales, recruiting, training).

## Layout

```
src/python_to_container/
  scraper/
    common.py      HTTP (+curl fallback), Next.js payload parsing, Offer model
    sources/       one adapter per portal
    taxonomy.py    ~96 canonical technologies with alias patterns
    relevance.py   title -> {ai_core, data_platform, qa}
    aggregate.py   counts, co-occurrence, median salary, dedupe
run.py             scrape
analyze.py         rank + gap analysis
report.py          HTML summary + offers browser
```

`run.py`/`analyze.py`/`report.py` import the package as
`python_to_container.scraper.*` — the project is installed editable into
`.venv` (via `uv sync`/`uv add`), so nothing extra is needed to resolve it.

Dedupe is by normalised `company|title`, keeping the primary portal's copy
over the aggregator's mirror.

## Being polite

0.7 s between requests, page caps on every source, no auth bypass, no
parallel hammering. Public listing data only.
