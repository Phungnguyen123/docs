# LTDDir Company Directory Scraper

A production-ready, resumable [Playwright](https://playwright.dev/python/) scraper
that looks up a list of company names on the public business directory
[ltddir.com](https://www.ltddir.com/companies/) and exports the matched company
details to an Excel workbook.

> **What this site is.** `ltddir.com` is **not** an official government registry.
> It is a public directory that *aggregates* company information. Treat the data
> as best-effort and verify anything important against an authoritative source.

---

## Highlights

- **Label-driven extraction.** Instead of brittle CSS paths, the parser collects
  every `label → value` pair on a detail page (tables, definition lists, and
  "Label: value" text) and maps them onto canonical fields. Minor redesigns of
  the site don't break it.
- **Adaptive selectors.** Search-box, submit, result-item and result-link
  selectors are ordered *strategy lists* in `config.py`. Adapting to a markup
  change means adding a selector, not editing logic.
- **Confident matching.** Exact match after case/space/punctuation/accent
  normalisation; otherwise the highest-similarity candidate with a recorded
  confidence score.
- **Fault tolerant.** Automatic retries (timeout / network / navigation) with
  exponential backoff, per-company error isolation (one failure never aborts the
  run), and polite 1–3 s random delays.
- **Resumable.** Progress is saved after every company; restart skips completed
  rows automatically.
- **Configurable browser.** `headless=True/False` via `config.py` or `--show`.

---

## Project structure

```
ltddir-scraper/
├── input/
│   └── companies.xlsx        # your input list (column "Company Name")
├── output/
│   ├── result.xlsx           # generated
│   └── _progress.jsonl       # generated resume log
├── logs/
│   └── scraper.log           # generated
├── scraper/
│   ├── __init__.py
│   ├── utils.py              # logging, normalisation, similarity, retries
│   ├── parser.py             # label-driven field extraction
│   ├── search.py             # perform search, collect candidates
│   ├── crawler.py            # browser lifecycle + per-company pipeline
│   └── exporter.py           # Excel I/O + resumable progress store
├── tests/                    # offline unit tests (no network needed)
├── config.py                 # all settings & selector strategies
├── main.py                   # entry point
├── inspect_site.py           # Phase-1 live site inspection helper
├── requirements.txt
└── README.md
```

---

## Installation

Requires **Python 3.12+** (works on 3.11 too).

```bash
cd ltddir-scraper

# 1. (recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. install the Playwright browser (Chromium)
playwright install chromium
```

> **Pinned/pre-installed browser?** If Chromium is already on the machine and you
> don't want Playwright to download its own, point the scraper at it:
> ```bash
> export PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chrome
> ```
> (or set `chromium_executable_path` in `config.py`).

---

## Usage

### 1. Prepare the input

Put your list in `input/companies.xlsx` with a header column named
**`Company Name`** (any casing). If no such column exists, the first column is
used.

| Company Name    |
| --------------- |
| HELENA LIMITED  |
| FITAZZY LIMITED |
| VELOURA LIMITED |

A ready-to-edit sample is included.

### 2. (Phase 1 — recommended once) Inspect the live site

Confirm the site's real structure and selectors before a big run. This prints
the search mechanism, any hidden API calls, working selectors, and a sample
detail page's extracted fields — so you can curate `config.py` from evidence
rather than assumptions:

```bash
python inspect_site.py --query "HELENA LIMITED"
```

### 3. Run the scraper

```bash
python main.py                    # headless, uses input/ and output/ defaults
python main.py --show             # visible browser (debugging)
python main.py --limit 5          # smoke-test the first 5 names
python main.py --fresh            # ignore prior progress and restart
python main.py --input path/to/list.xlsx --output path/to/out.xlsx
```

The run is resumable: if interrupted, just run the same command again — completed
companies are skipped.

### 4. Read the output

`output/result.xlsx` with columns:

`Input Company Name`, `Matched Company Name`, `Match Status`, `Confidence Score`,
`Company Number`, `Company Type`, `Company Status`, `Incorporation Date`,
`Registered Address`, `Directors`, `Company Secretary`, `Business Nature`,
`Previous Names`, `Remarks`, `Source URL`, `Crawl Timestamp`.

**Match Status** is one of: `exact`, `fuzzy`, `low_confidence`, `not_found`.
Rows that failed after all retries are recorded as `not_found` with the reason in
`Remarks` — the run never crashes on a single bad company.

---

## Configuration (`config.py`)

| Setting | Purpose |
| --- | --- |
| `headless` | Show/hide the browser. |
| `max_retries`, `retry_backoff_base_s` | Retry policy (default 3 retries; 2s/4s/8s). |
| `delay_min_s`, `delay_max_s` | Random delay between companies (default 1–3s). |
| `min_confidence`, `strong_confidence` | Fuzzy-match thresholds. |
| `*_selectors` | Ordered selector strategies for search / results / links. |
| `field_label_map` | Label keywords → canonical detail fields. |
| `chromium_executable_path` | Explicit Chromium binary (optional). |

---

## Testing

Offline unit tests cover normalisation, matching, label→field mapping, the
resumable progress store, and Excel I/O — no network required:

```bash
pip install pytest
python -m pytest tests/ -q
```

---

## Logging

`logs/scraper.log` (and stderr) record, per company: start, each retry, success
or failure, and duration. Use `--verbose` for debug-level detail.

---

## Anti-bot handling

The crawler fingerprints common block pages (Cloudflare "Just a moment…",
CAPTCHA, "access denied", rate-limit notices) and raises a clear `AntiBotError`,
recorded in `Remarks`, instead of silently scraping a challenge page. If the site
begins actively challenging automation you have three escalation options:

1. Increase `delay_min_s`/`delay_max_s` and reduce concurrency (already 1 page at
   a time) to stay under rate limits.
2. Run with `--show` (non-headless) — challenge pages sometimes clear with a real
   browser profile.
3. If a **hidden JSON API** is found by `inspect_site.py`, prefer calling it
   directly (faster and more stable than DOM scraping); point `search.py` at that
   endpoint.

---

## Notes & limitations

- Selector strategy lists in `config.py` ship with sensible candidates but should
  be **confirmed against the live site with `inspect_site.py`** before a large
  run — the tool is built so this is a config change, not a code change.
- Respect the target site's Terms of Service and `robots.txt`, and keep request
  rates polite. This project is intended for lawful, low-volume lookups of public
  data.
