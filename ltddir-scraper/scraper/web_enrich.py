"""OSINT / anomaly-signal collector for company investigation (best-effort).

This is NOT official data. It queries a web-search API and, instead of filtering
to one "official" website, it **surfaces and flags** everything useful for
spotting suspicious behaviour of newly registered companies:

  * websites found (even when the domain does NOT match the registered name —
    that mismatch is itself a red flag)
  * social profiles (LinkedIn / Facebook / Instagram / ...)
  * community mentions (Reddit / Quora / forums) for brand-mention tracing
  * scam / blacklist mentions (ScamAdviser / Trustpilot / RipoffReport / ...)
  * per-company risk flags (domain mismatch, multiple domains, shopping site,
    scam keywords in snippets)

Plus a no-API **batch analysis** over the whole list: shared registered address
(shell-factory signal), bulk incorporation dates, and random-looking names.

Providers (auto-detected): SerpAPI (SERPAPI_KEY) or Google Programmable Search
(GOOGLE_API_KEY + GOOGLE_CSE_ID). Without a key, only the batch analysis runs.
"""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests

from .utils import get_logger, normalize_name

# --------------------------------------------------------------------------- #
# Domain classification
# --------------------------------------------------------------------------- #
_SOCIAL_DOMAINS = (
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "tiktok.com", "youtube.com", "t.me", "wa.me", "whatsapp.com", "pinterest.com",
)
_COMMUNITY_DOMAINS = (
    "reddit.com", "quora.com", "medium.com", "stackexchange.com",
    "tripadvisor.com", "blogspot.com", "wordpress.com",
)
_SCAM_DOMAINS = (
    "scamadviser.com", "trustpilot.com", "ripoffreport.com", "scamdoc.com",
    "complaintsboard.com", "gripeo.com", "scam-detector.com", "mywot.com",
    "sitejabber.com", "scamwatch.gov.au", "fakespot.com",
)
_DIRECTORY_DOMAINS = (
    "opencorporates.com", "ltddir.com", "gov.hk", "companieshouse.gov.uk",
    "find-and-update.company-information.service.gov.uk", "bloomberg.com",
    "crunchbase.com", "dnb.com", "zaubacorp.com", "wikipedia.org", "google.com",
    "companieshouse.hk", "webb-site.com", "importyeti.com", "panjiva.com",
    "signalhire.com", "rocketreach.co", "apollo.io",
)

_SHOPPING_KEYWORDS = (
    "shop", "store", "buy now", "add to cart", "checkout", "sale", "outlet",
    "discount", "clearance", "free shipping", "% off", "order now", "best price",
    "official store", "online store", "shopping",
)
_SCAM_KEYWORDS = (
    "scam", "fraud", "fake", "counterfeit", "phishing", "ripoff", "rip-off",
    "do not buy", "avoid", "complaint", "fraudulent", "blacklist", "stolen",
    "chargeback", "not received", "never arrived",
)

_GENERIC_TOKENS = {"limited", "ltd", "plc", "llp", "company", "co", "the", "and", "of"}
_MATCH_RATIO = 0.80
_CONTAINMENT_RATIO = 0.70


# --------------------------------------------------------------------------- #
# Small pure helpers
# --------------------------------------------------------------------------- #
def registrable_domain(url: str) -> str:
    """Return the lowercased host of a URL without a leading 'www.'."""
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _host_in(url: str, domains: tuple[str, ...]) -> bool:
    host = registrable_domain(url)
    return any(host == d or host.endswith("." + d) for d in domains)


def classify(url: str) -> str:
    """Classify a result URL: social | community | scam | directory | website."""
    if _host_in(url, _SOCIAL_DOMAINS):
        return "social"
    if _host_in(url, _SCAM_DOMAINS):
        return "scam"
    if _host_in(url, _COMMUNITY_DOMAINS) or "forum" in registrable_domain(url):
        return "community"
    if _host_in(url, _DIRECTORY_DOMAINS):
        return "directory"
    return "website"


def company_core(name: str) -> str:
    """Reduce a company name to distinctive letters (no suffix/space/punct)."""
    tokens = [t for t in normalize_name(name).split() if t not in _GENERIC_TOKENS]
    return "".join(tokens)


def _domain_core(url: str) -> str:
    host = registrable_domain(url)
    label = host.split(".")[0] if host else ""
    return "".join(ch for ch in label if ch.isalnum())


def _strong_match(core: str, candidate: str) -> bool:
    """True if ``candidate`` confidently matches the company ``core``."""
    if not core or not candidate:
        return False
    if SequenceMatcher(None, core, candidate).ratio() >= _MATCH_RATIO:
        return True
    if core in candidate and len(core) / len(candidate) >= _CONTAINMENT_RATIO:
        return True
    if candidate in core and len(candidate) / len(core) >= _CONTAINMENT_RATIO:
        return True
    return False


def _text_of(result: dict[str, str]) -> str:
    return f"{result.get('title', '')} {result.get('snippet', '')}".lower()


_RARE_LETTERS = set("qxzjk")


def looks_random_name(name: str) -> bool:
    """Heuristic: does the name look machine-generated (bulk-registration tell)?

    Flags several tells common to auto-generated brand names: 'q' not followed by
    'u', two or more rare letters (q/x/z/j/k), an unusually low vowel ratio, or a
    long consonant cluster.
    """
    for token in (t for t in normalize_name(name).split() if t not in _GENERIC_TOKENS):
        if len(token) < 5:
            continue
        if re.search(r"q(?!u)", token):
            return True
        if sum(c in _RARE_LETTERS for c in token) >= 2:
            return True
        vowels = sum(c in "aeiou" for c in token)
        if vowels / len(token) < 0.30:
            return True
        if re.search(r"[bcdfghjklmnpqrstvwxz]{4,}", token):
            return True
    return False


# --------------------------------------------------------------------------- #
# Per-company web signals
# --------------------------------------------------------------------------- #
@dataclass
class WebSignals:
    """Everything the web search surfaced for one company, for manual review."""

    website: str = ""
    website_matches_name: bool | None = None  # None = no website found
    other_domains: list[str] = field(default_factory=list)
    socials: list[str] = field(default_factory=list)
    community: list[str] = field(default_factory=list)
    scam_mentions: list[str] = field(default_factory=list)
    domain_registered: str = ""  # ISO date of the website domain's registration
    shop_scan: str = ""  # summary of scam-shop indicators (see shop_scan.py)
    # Each flag is (label, evidence) — evidence is a URL/detail to verify by hand.
    flags: list[tuple[str, str]] = field(default_factory=list)

    def add_flag(self, label: str, evidence: str = "") -> None:
        """Record a risk flag with an optional evidence URL/detail."""
        self.flags.append((label, evidence))

    def match_label(self) -> str:
        if self.website_matches_name is None:
            return ""
        return "Yes" if self.website_matches_name else "No"

    @staticmethod
    def _join(items: list[str]) -> str:
        return " | ".join(dict.fromkeys(i for i in items if i))

    def other_domains_cell(self) -> str:
        return self._join(self.other_domains)

    def socials_cell(self) -> str:
        return self._join(self.socials)

    def community_cell(self) -> str:
        return self._join(self.community)

    def scam_cell(self) -> str:
        return self._join(self.scam_mentions)

    def risk_cell(self) -> str:
        return "; ".join(dict.fromkeys(label for label, _ in self.flags))

    def evidence_cell(self) -> str:
        """Render 'label: url' for each flag that has evidence, for verification."""
        seen: dict[str, str] = {}
        for label, ev in self.flags:
            if ev and label not in seen:
                seen[label] = ev
        return " | ".join(f"{label}: {ev}" for label, ev in seen.items())


def extract_signals(results: list[dict[str, str]], company_name: str) -> WebSignals:
    """Classify search results into investigation signals (pure, testable)."""
    core = company_core(company_name)
    sig = WebSignals()

    website_urls: list[str] = []
    for r in results:
        link = r.get("link", "")
        if not link:
            continue
        kind = classify(link)
        if kind == "website":
            website_urls.append(link)
        elif kind == "social":
            sig.socials.append(link)
        elif kind == "community":
            sig.community.append(link)
        elif kind == "scam":
            sig.scam_mentions.append(link)
        # 'directory' results are ignored as noise.

    # Website + name-match flag (mismatch is a red flag, not a reason to drop).
    if website_urls:
        sig.website = website_urls[0]
        sig.website_matches_name = _strong_match(core, _domain_core(website_urls[0]))
        seen_domains = {registrable_domain(website_urls[0])}
        for u in website_urls[1:]:
            dom = registrable_domain(u)
            if dom and dom not in seen_domains:
                seen_domains.add(dom)
                sig.other_domains.append(dom)

    # Scam keywords anywhere in the result text (record the URL as evidence).
    scam_keyword_url = ""
    for r in results:
        text = _text_of(r)
        if any(k in text for k in _SCAM_KEYWORDS):
            link = r.get("link", "")
            host = registrable_domain(link) or "search result"
            sig.scam_mentions.append(f"{host} (keyword)")
            scam_keyword_url = scam_keyword_url or link

    # Compile risk flags, each with an evidence URL/detail where possible.
    if not website_urls:
        sig.add_flag("no website found in search")
    if sig.website and sig.website_matches_name is False:
        sig.add_flag("website domain does not match company name", sig.website)
    distinct = len({registrable_domain(u) for u in website_urls})
    if distinct >= 2:
        sig.add_flag(
            f"multiple distinct domains ({distinct})",
            ", ".join(dict.fromkeys(registrable_domain(u) for u in website_urls)),
        )
    shop_url = next(
        (r.get("link", "") for r in results if any(k in _text_of(r) for k in _SHOPPING_KEYWORDS)),
        "",
    )
    if shop_url:
        sig.add_flag("shopping / e-commerce keywords in results", shop_url)
    if sig.scam_mentions:
        scam_url = next((m for m in sig.scam_mentions if m.startswith("http")), "") or scam_keyword_url
        sig.add_flag("scam / blacklist / complaint mention", scam_url)
    return sig


# --------------------------------------------------------------------------- #
# Batch (no-API) analysis over the whole list
# --------------------------------------------------------------------------- #
def _peers(rows: list[dict[str, str]], key_fn, value, self_name: str, cap: int = 6) -> list[str]:  # noqa: ANN001
    """Return other companies' names sharing a key value (for evidence)."""
    names = [
        r.get("Input Company Name", "")
        for r in rows
        if key_fn(r) == value and r.get("Input Company Name", "") != self_name
    ]
    return names[:cap]


def annotate_batch_signals(
    rows: list[dict[str, str]], *, min_shared: int = 2, min_bulk: int = 3
) -> list[dict[str, str]]:
    """Add cross-company red flags to each row's 'Risk Signals' + 'Evidence'.

    Uses only registry data already collected (no network): shared registered
    address, bulk incorporation dates, and random-looking names. Evidence lists
    the peer companies so the flag can be verified.
    """
    def _addr_key(r: dict[str, str]) -> str:
        return normalize_name(r.get("Registered Address", ""))

    def _inc_key(r: dict[str, str]) -> str:
        return r.get("Incorporation Date", "")

    addr_counts = Counter(_addr_key(r) for r in rows if r.get("Registered Address", "").strip())
    inc_counts = Counter(_inc_key(r) for r in rows if r.get("Incorporation Date", "").strip())

    for r in rows:
        labels: list[str] = []
        evidence: list[str] = []
        name = r.get("Input Company Name", "")

        addr = _addr_key(r)
        if addr and addr_counts[addr] >= min_shared:
            labels.append(f"shared registered address ({addr_counts[addr]} companies)")
            peers = _peers(rows, _addr_key, addr, name)
            evidence.append(
                "shared address with: " + ", ".join(peers) + (" ..." if addr_counts[addr] - 1 > len(peers) else "")
            )

        inc = _inc_key(r)
        if inc and inc_counts[inc] >= min_bulk:
            labels.append(f"bulk incorporation date ({inc_counts[inc]} on {inc})")
            peers = _peers(rows, _inc_key, inc, name)
            evidence.append(f"same incorporation date ({inc}) as: " + ", ".join(peers) + (" ..." if inc_counts[inc] - 1 > len(peers) else ""))

        if looks_random_name(name):
            labels.append("random-looking name")

        if labels:
            r["Risk Signals"] = "; ".join(x for x in [r.get("Risk Signals", "")] + labels if x)
        if evidence:
            r["Evidence"] = " | ".join(x for x in [r.get("Evidence", "")] + evidence if x)
    return rows


def build_cluster_sheets(
    rows: list[dict[str, str]], *, min_shared: int = 2, min_bulk: int = 3
) -> dict[str, "pd.DataFrame"]:
    """Build summary DataFrames grouping companies by shared address / date.

    Returns a dict of {sheet_name: DataFrame}, only for clusters that actually
    exist, so an investigator can see linked groups at a glance.
    """
    sheets: dict[str, pd.DataFrame] = {}

    addr_groups: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        key = normalize_name(r.get("Registered Address", ""))
        if key:
            addr_groups.setdefault(key, []).append(r)
    addr_rows = [
        {
            "Registered Address": grp[0].get("Registered Address", ""),
            "Company Count": len(grp),
            "Companies": ", ".join(g.get("Input Company Name", "") for g in grp),
            "Company Numbers": ", ".join(g.get("Company Number", "") for g in grp),
        }
        for grp in addr_groups.values()
        if len(grp) >= min_shared
    ]
    if addr_rows:
        sheets["Shared Addresses"] = pd.DataFrame(
            sorted(addr_rows, key=lambda x: -x["Company Count"])
        )

    inc_groups: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        key = r.get("Incorporation Date", "")
        if key:
            inc_groups.setdefault(key, []).append(r)
    inc_rows = [
        {
            "Incorporation Date": date,
            "Company Count": len(grp),
            "Companies": ", ".join(g.get("Input Company Name", "") for g in grp),
        }
        for date, grp in inc_groups.items()
        if len(grp) >= min_bulk
    ]
    if inc_rows:
        sheets["Incorporation Clusters"] = pd.DataFrame(
            sorted(inc_rows, key=lambda x: -x["Company Count"])
        )

    return sheets


# --------------------------------------------------------------------------- #
# Search client
# --------------------------------------------------------------------------- #
class WebEnricher:
    """Queries a web-search API and returns investigation signals."""

    def __init__(self, *, timeout_s: float = 20.0, max_retries: int = 2, backoff_base_s: float = 2.0) -> None:
        self._log = get_logger()
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._backoff = backoff_base_s
        self._serpapi_key = os.environ.get("SERPAPI_KEY", "")
        self._google_key = os.environ.get("GOOGLE_API_KEY", "")
        self._google_cx = os.environ.get("GOOGLE_CSE_ID", "")
        self._session = requests.Session()

    def enabled(self) -> bool:
        return bool(self._serpapi_key or (self._google_key and self._google_cx))

    def provider(self) -> str:
        if self._serpapi_key:
            return "serpapi"
        if self._google_key and self._google_cx:
            return "google_cse"
        return "none"

    def raw_results(self, query: str) -> list[dict[str, str]]:
        """Return normalised [{title, link, snippet}] results for ``query``."""
        if self._serpapi_key:
            data = self._get(
                "https://serpapi.com/search.json",
                {"q": query, "api_key": self._serpapi_key, "num": 10, "engine": "google"},
            )
            return _normalize_serpapi(data)
        if self._google_key and self._google_cx:
            data = self._get(
                "https://www.googleapis.com/customsearch/v1",
                {"q": query, "key": self._google_key, "cx": self._google_cx, "num": 10},
            )
            return _normalize_google(data)
        return []

    def gather(self, company_name: str, *, region_hint: str = "", deep: bool = False) -> WebSignals:
        """Search for a company and return investigation signals.

        ``deep`` runs a second scam/complaint-focused query (more API calls).
        """
        queries = [f'"{company_name}"' + (f" {region_hint}" if region_hint else "")]
        if deep:
            queries.append(f'"{company_name}" (scam OR review OR complaint OR fraud)')
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for q in queries:
            try:
                for r in self.raw_results(q):
                    link = r.get("link", "")
                    if link and link not in seen:
                        seen.add(link)
                        results.append(r)
            except requests.RequestException as exc:
                self._log.warning("Web search failed for %s: %s", company_name, exc)
        return extract_signals(results, company_name)

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(self._backoff * (2**attempt))
        raise requests.RequestException(str(last_exc))


def _normalize_serpapi(data: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in data.get("organic_results", []) or []:
        out.append({"title": str(r.get("title", "")), "link": str(r.get("link", "")), "snippet": str(r.get("snippet", ""))})
    return out


def _normalize_google(data: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in data.get("items", []) or []:
        out.append({"title": str(r.get("title", "")), "link": str(r.get("link", "")), "snippet": str(r.get("snippet", ""))})
    return out
