# UK Company Lookup — ltddir.com scraper + Companies House API

Look up a list of company names and export matched company details (number,
status, incorporation date, registered address, directors, etc.) to an Excel
workbook. Two interchangeable data sources, **same input and output format**:

| Entry point | Source | When to use |
| --- | --- | --- |
| **`main_ch.py`** ✅ recommended | Official **Companies House API** | Reliable, free, legal, structured. **Use this.** |
| `main.py` | Scrapes **ltddir.com** via Playwright | Only if you specifically need ltddir's data. |

> **Why two?** `ltddir.com` is a Cloudflare-protected *aggregator* — it re-packages
> UK registry data and actively blocks automation (verified: `HTTP 403` +
> `__cf_chl_rt_tk` challenge that does not clear even in a real headed browser).
> The UK registry it aggregates, **Companies House**, offers the same data through
> a free official API with no anti-bot barrier — so for UK "LIMITED" companies the
> API path is faster, more reliable, and ToS-compliant. The scraper is kept for
> completeness and in case ltddir stops challenging automation.

---

## Quick start (recommended path — Companies House API)

```bash
cd ltddir-scraper
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Get a FREE API key (2 min): https://developer.company-information.service.gov.uk/
#    Sign in -> "Your applications" -> create an application (Live) -> create an API key.
# 2. Set it in your shell:
export CH_API_KEY=your_key_here        # Windows PowerShell: $env:CH_API_KEY="your_key_here"

# 3. Put your names in input/companies.xlsx (column "Company Name"), then:
python main_ch.py --limit 5            # smoke test the first 5
python main_ch.py                      # full run -> output/result.xlsx
```

No browser, no Cloudflare, resumable, same `result.xlsx` columns as below.

---

## About the two sources

`ltddir.com` is **not** an official government registry — it is a public directory
that *aggregates* company information. The **Companies House API** IS the official
UK registry (companies incorporated in England & Wales, Scotland, and Northern
Ireland). For authoritative data, prefer the API.

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
│   ├── utils.py              # logging, normalisation, similarity, retries, anti-bot
│   ├── parser.py             # label-driven field extraction (shared CompanyRecord)
│   ├── search.py             # ltddir search: perform search, collect candidates
│   ├── crawler.py            # ltddir: browser lifecycle + per-company pipeline
│   ├── companies_house.py    # Companies House API client + JSON mappers
│   └── exporter.py           # Excel I/O + resumable progress store (shared)
├── tests/                    # offline unit tests (no network needed)
├── config.py                 # all settings & selector strategies
├── main_ch.py                # ✅ entry point — Companies House API (recommended)
├── main.py                   # entry point — ltddir.com scraper
├── inspect_site.py           # ltddir live-site inspection helper
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

## Anti-bot handling — important

**ltddir.com is protected by Cloudflare.** A plain automated request receives
`HTTP 403` and a redirect to a Cloudflare challenge URL (`…?__cf_chl_rt_tk=…`),
so the real page (and its search box) never loads in a bare headless browser.

This project mitigates that, but cannot guarantee a bypass:

- **Light stealth** — launches with `--disable-blink-features=AutomationControlled`
  and injects an init script hiding `navigator.webdriver`, reducing trivial
  fingerprinting.
- **Challenge auto-solve wait** — on detecting a challenge (via the URL marker,
  a 403/429/503 status, or interstitial text) the crawler waits up to
  `challenge_wait_s` (default 40s) for a real browser to clear it, instead of
  failing instantly. Run **headed** (`--show`) for the best chance — Cloudflare's
  *managed* challenge often auto-solves in a visible browser.
- If it still doesn't clear, the company is recorded as `not_found` with a
  `blocked:` note in `Remarks` and the run continues.

Escalation if Cloudflare keeps blocking:

1. Always run `--show` (headed) and increase `delay_min_s`/`delay_max_s`.
2. Add `pip install playwright-stealth` and apply it for stronger evasion.
3. **Recommended alternative — use the official [Companies House API]**
   (https://developer.company-information.service.gov.uk/). ltddir.com merely
   aggregates UK registry data; the Companies House API is free, authoritative,
   ToS-compliant, and returns every requested field as structured JSON with no
   scraping or Cloudflare in the way. For a list of UK "LIMITED" companies this
   is the more reliable path.

---

## Notes & limitations

- Selector strategy lists in `config.py` ship with sensible candidates but should
  be **confirmed against the live site with `inspect_site.py`** before a large
  run — the tool is built so this is a config change, not a code change.
- Respect the target site's Terms of Service and `robots.txt`, and keep request
  rates polite. This project is intended for lawful, low-volume lookups of public
  data.
