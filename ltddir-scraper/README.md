# Company Lookup — UK (Companies House) + Hong Kong (data.gov.hk) + ltddir scraper

Look up a list of company names and export matched company details (number,
status, incorporation date, registered address, directors, etc.) to an Excel
workbook. Multiple interchangeable data sources, **same input and output format**:

| Entry point | Source | Region | When to use |
| --- | --- | --- | --- |
| **`main_ch.py`** ✅ | Official **Companies House API** | 🇬🇧 UK | Reliable, free, legal, structured. Full fields incl. directors. |
| **`main_hk.py`** | Free **data.gov.hk** open API | 🇭🇰 Hong Kong | Free, no key. Number + type + incorporation date + address (no directors). |
| `main.py` | Scrapes **ltddir.com** via Playwright | 🇬🇧 UK | Only if you specifically need ltddir's data (Cloudflare-blocked). |

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
python main_ch.py                      # full run -> output/result_uk.xlsx
```

No browser, no Cloudflare, resumable, same columns as below.

> **Each tool writes its own files** so they never overwrite each other:
> `main_ch.py` → `output/result_uk.xlsx`, `main_hk.py` → `output/result_hk.xlsx`,
> `main.py` → `output/result_ltddir.xlsx` (each with its own resume log). Pass
> `--output` to choose a different path. Because progress is per-tool, switching
> regions does **not** need `--fresh`.

---

## Hong Kong path (`main_hk.py`) — free, no API key

Hong Kong's official registry (ICRIS) has **no free API** — directors and full
particulars are pay-per-document (≈HK$22/company). But the Companies Registry
publishes the "Registered Office Address of Live Local Companies" data **free**
on data.gov.hk, covering every *live* local company: company number (BRN),
English/Chinese name, and registered office address.

data.gov.hk now serves this as a searchable **open API** (no key), so there is
nothing large to download. Two modes:

### API mode (default, recommended)

```bash
# 1. Confirm the live API's JSON shape once (dumps raw response):
python main_hk.py --probe "HELENA LIMITED"

# 2. Put your HK company names in input/companies.xlsx, then:
python main_hk.py --limit 5
python main_hk.py
```

The client queries `data.cr.gov.hk` per name (exact-prefix, then again without
the legal suffix to catch LTD/LIMITED variants) and picks the best match. Fields
are extracted **tolerantly** by keyword, so slight JSON naming differences don't
break it — run `--probe` first and, if a field looks unmapped, tell me the raw
keys and I'll tune `scraper/hk_api.py`.

### CSV mode (if you prefer a downloaded file)

If you do download a CSV/XLSX from the
[dataset page](https://data.gov.hk/en-data/dataset/hk-cr-crdata-list-addr) into
`input/hk/`:

```bash
python main_hk.py --dataset input/hk --show-columns   # verify detected columns
python main_hk.py --dataset input/hk                  # match locally
```

**What you get (API mode):** Company Number (BRN), English name, **Company Type**,
**Incorporation Date**, Registered Address, Company Status (Live), match
confidence — output to the same `result.xlsx`. (Confirmed against the live API,
whose fields are `Brn`, `English_Company_Name`, `Company_Type`,
`Date_of_Incorporation`, `Address_of_Registered_Office`.)
**What you do NOT get** (needs paid ICRIS): directors and company secretary.

### Anomaly / OSINT signals — for investigating suspicious companies

Built for spotting suspicious behaviour of newly registered companies (scam
storefronts, shell-company factories, impersonation). It **surfaces and flags**
signals rather than hiding them — e.g. a company registered under one name but
operating a store on an unrelated domain is a red flag the tool keeps and marks.

**Batch signals (always on, no API key, from registry data)** land in the
**Risk Signals** column:

- `shared registered address (N companies)` — many of your companies at one
  address = shell-factory tell
- `bulk incorporation date (N on <date>)` — mass same-day registration
- `random-looking name` — machine-generated brand names (VRAXIONYX, QYLARIS…)

**Web signals (opt-in `--enrich-web`, needs a search API key)** add columns
**Website, Website Matches Name, Other Domains, Social Media, Community Mentions,
Scam/Blacklist Mentions**, and more Risk Signals:

- `website domain does not match company name` (kept + flagged, not dropped)
- `multiple distinct domains (N)`
- `shopping / e-commerce keywords in results`
- `scam / blacklist / complaint mention` (ScamAdviser / Trustpilot / RipoffReport)
- Community mentions from Reddit / Quora / forums for brand-mention tracing

**Deep signals (opt-in, combine with `--enrich-web`):**

- `--whois` — free RDAP lookup of the website's **domain registration date**;
  flags `newly registered domain (N days old)` (new domain + shop = classic scam).
  Adds a **Domain Registered** column.
- `--scan-shop` — fetches the website and **scores scam-shop indicators** (missing
  contact/returns/privacy, urgency & steep-discount language, no business identity).
  Adds a **Shop Scam Scan** column; flags `scam-shop score N/6`.
- `--deep` — an extra scam/complaint-focused search query per company.

**Verify everything — the Evidence column.** Every web-derived flag carries the
source URL in an **Evidence** column (e.g. `website domain does not match company
name: https://…`), and batch flags list the peer companies (`shared address with:
A, B, C`). Nothing is a verdict — each flag is a lead to check by hand.

**Cluster sheets.** The output workbook has extra tabs — **Shared Addresses** and
**Incorporation Clusters** — grouping linked companies so a shell-company network
is visible at a glance.

**Suspected Networks tab (link analysis).** A **Suspected Networks** sheet runs a
connected-components (union-find) analysis that links companies sharing a
distinctive attribute — same registered address, same website/other domain, the
same community/scam URL, or the same bulk incorporation date — and reports each
resulting *ring*. Links are transitive: if A—B share a domain and B—C share an
address, A/B/C surface as one network. Each row lists the members, a **Linked By**
column explaining every connection (with the shared value), and the group's total
risk-flag count, so an entire operation shows up as one line even when the
individual companies use different addresses.

```bash
# Configure ONE provider:
export SERPAPI_KEY=...                        # SerpAPI, or
export GOOGLE_API_KEY=...  GOOGLE_CSE_ID=...   # Google Programmable Search (CSE)

python main_hk.py --probe-web "HELENA LIMITED"                 # inspect one company's signals
python main_hk.py --input input/hongkong.xlsx --enrich-web     # web signals (1 search/company)
python main_hk.py --input input/hongkong.xlsx --enrich-web --whois --scan-shop --deep  # everything
```

All web-derived output is **best-effort OSINT, not proof**. `--deep`/`--scan-shop`/
`--whois` add network calls (and `--deep` doubles search-API usage) — smoke-test
with `--limit 5` first.

> **Cannot be obtained at all:** *UBO / beneficial-owner nationality* — Hong
> Kong's Significant Controllers Register is private by law (inspectable only by
> authorities), so it is unavailable even for a fee. *Applicant/presentor contact*
> and *nature of business* are not in CR open data (paid document / filed with the
> tax office respectively).

---

## About the sources

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
│   ├── companies_house.py    # Companies House API client + JSON mappers (UK)
│   ├── hk_api.py             # data.cr.gov.hk live API client (Hong Kong, default)
│   ├── hk_registry.py        # data.gov.hk CSV/XLSX loader + matcher (Hong Kong)
│   ├── web_enrich.py         # OSINT signal collector + batch clusters
│   ├── domain_age.py         # RDAP domain-registration-age lookup
│   ├── shop_scan.py          # scam-shop page scorer
│   ├── networks.py           # union-find link analysis (Suspected Networks)
│   └── exporter.py           # Excel I/O + resumable progress store (shared)
├── input/hk/                 # put the Hong Kong data.gov.hk dataset file(s) here
├── tests/                    # offline unit tests (no network needed)
├── config.py                 # all settings & selector strategies
├── main_ch.py                # ✅ entry point — Companies House API (UK)
├── main_hk.py                # entry point — Hong Kong data.gov.hk matcher
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
