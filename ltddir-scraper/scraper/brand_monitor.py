"""Brand-abuse / impersonation monitor for a group of protected brands.

Given a watchlist of a company group's protected assets (brand names, official
domains, office addresses, legal entity names), this hunts for OTHER websites
that reuse those assets — typosquats, clone sites, and impersonation/recovery-
scam pages like the ``globalchaincp.com`` that reused BBCIncorp's address.

Data sources, in order of preference (privacy + cost):
  1. **crt.sh** — Certificate Transparency logs (free, no key). Finds every TLS
     certificate whose domain contains a brand string → typosquats/clones.
  2. **urlscan.io** — search of already-scanned pages (free; key raises limits).
  3. **Web search** — optional, via the official Google Programmable Search API
     (recommended) or SerpAPI, reusing :class:`web_enrich.WebEnricher`. Used to
     find pages that reuse an *address* or *entity name* (not just the domain).

Official domains are allow-listed, so the group's own sites are never flagged.
Every suspect carries the reason + an evidence URL for manual verification.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import requests

from .domain_age import DomainAgeLookup, _today_utc, age_days
from .utils import get_logger, redact
from .web_enrich import WebEnricher, classify, registrable_domain

# Extra known directory/review/data-broker platforms that merely *mention*
# companies (not impersonators) — filtered down so real abuse stands out.
_EXTRA_MENTION_DOMAINS = (
    "zoominfo.com", "offshorecorptalk.com", "offshorereviews.com", "500px.com",
    "glassdoor.com", "indeed.com", "kompass.com", "yelp.com", "medium.com",
    "mycareersfuture.gov.sg", "sgpbusiness.com", "opengovsg.com", "about.me",
)


def categorize(domain: str, brands: list[str]) -> str:
    """Classify a suspect: impersonation vs mention vs unknown site to verify."""
    bare = "".join(ch for ch in domain.lower() if ch.isalnum())
    if any("".join(b.lower().split()) in bare for b in brands if b):
        return "impersonation (brand in domain)"
    host = registrable_domain(domain) if "://" in domain else domain.lower()
    if host.endswith(_EXTRA_MENTION_DOMAINS) or any(host == d or host.endswith("." + d) for d in _EXTRA_MENTION_DOMAINS):
        return "known platform / mention"
    if classify("https://" + host) in ("directory", "social", "community", "scam", "marketplace"):
        return "known platform / mention"
    return "unknown site — verify"

CRTSH_URL = "https://crt.sh/"
URLSCAN_SEARCH = "https://urlscan.io/api/v1/search/"


# --------------------------------------------------------------------------- #
# Watchlist
# --------------------------------------------------------------------------- #
@dataclass
class Watchlist:
    """Protected assets of a brand group."""

    brands: list[str] = field(default_factory=list)          # e.g. "BBCIncorp"
    official_domains: list[str] = field(default_factory=list)  # allow-list
    addresses: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)         # legal names

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Watchlist":
        return cls(
            brands=[str(x) for x in data.get("brands", [])],
            official_domains=[str(x).lower() for x in data.get("official_domains", [])],
            addresses=[str(x) for x in data.get("addresses", [])],
            entities=[str(x) for x in data.get("entities", [])],
        )


def is_official(domain: str, official_domains: list[str]) -> bool:
    """True if ``domain`` is (a subdomain of) a watch-listed official domain."""
    d = registrable_domain(domain) if "://" in domain else domain.lower().lstrip(".")
    d = d[4:] if d.startswith("www.") else d
    return any(d == o or d.endswith("." + o) for o in official_domains)


# --------------------------------------------------------------------------- #
# Pure parsers
# --------------------------------------------------------------------------- #
def extract_crtsh_domains(records: list[dict[str, Any]]) -> set[str]:
    """Pull unique domains from a crt.sh JSON response."""
    domains: set[str] = set()
    for rec in records or []:
        for field_name in ("name_value", "common_name"):
            val = rec.get(field_name, "")
            for raw in str(val).splitlines():
                dom = raw.strip().lower().lstrip("*.")
                if dom and "." in dom and " " not in dom:
                    domains.add(dom)
    return domains


def extract_urlscan(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (domain, result_url) pairs from a urlscan search response."""
    out: list[tuple[str, str]] = []
    for r in data.get("results", []) or []:
        page = r.get("page", {}) or {}
        dom = str(page.get("domain", "")).lower()
        url = str(page.get("url", "") or r.get("result", ""))
        if dom:
            out.append((dom, url))
    return out


# --------------------------------------------------------------------------- #
# Candidate model
# --------------------------------------------------------------------------- #
@dataclass
class Suspect:
    """A domain suspected of abusing a watch-listed asset."""

    domain: str
    sources: set[str] = field(default_factory=set)
    reasons: list[tuple[str, str]] = field(default_factory=list)  # (label, evidence)
    registered: str = ""
    category: str = ""

    def add(self, source: str, label: str, evidence: str = "") -> None:
        self.sources.add(source)
        if (label, evidence) not in self.reasons:
            self.reasons.append((label, evidence))

    def score(self) -> int:
        """Higher = more suspicious. Impersonation ranks up; mere mentions down."""
        s = len(self.sources)
        if any("address" in lbl.lower() for lbl, _ in self.reasons):
            s += 2
        days = age_days(self.registered, today=_today_utc()) if self.registered else None
        if days is not None and 0 <= days <= 180:
            s += 1
        if self.category.startswith("impersonation"):
            s += 3
        elif self.category.startswith("known platform"):
            s = max(0, s - 2)  # directory/review mentions are not abuse
        return s

    def to_row(self) -> dict[str, str]:
        return {
            "Suspect Domain": self.domain,
            "Category": self.category,
            "Risk Score": self.score(),
            "Sources": ", ".join(sorted(self.sources)),
            "Domain Registered": self.registered,
            "Why Flagged": "; ".join(lbl for lbl, _ in self.reasons),
            "Evidence": " | ".join(f"{lbl}: {ev}" for lbl, ev in self.reasons if ev),
        }


# --------------------------------------------------------------------------- #
# Monitor
# --------------------------------------------------------------------------- #
class BrandMonitor:
    """Runs the multi-source impersonation sweep for a watchlist."""

    def __init__(
        self,
        *,
        enricher: WebEnricher | None = None,
        age: DomainAgeLookup | None = None,
        timeout_s: float = 25.0,
        pause_s: float = 0.5,
    ) -> None:
        self._log = get_logger()
        self._enricher = enricher
        self._age = age or DomainAgeLookup()
        self._timeout = timeout_s
        self._pause = pause_s
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "brand-monitor/1.0"})
        import os

        self._urlscan_key = os.environ.get("URLSCAN_API_KEY", "")

    def scan(self, wl: Watchlist, *, max_domains: int = 200) -> list[Suspect]:
        """Return de-duplicated suspects across all sources."""
        suspects: dict[str, Suspect] = {}

        def candidate(domain: str) -> Suspect | None:
            if not domain or is_official(domain, wl.official_domains):
                return None
            key = registrable_domain(domain) if "://" in domain else domain.lower().lstrip(".")
            key = key[4:] if key.startswith("www.") else key
            return suspects.setdefault(key, Suspect(domain=key))

        # 1) crt.sh — cert transparency per brand token.
        for brand in wl.brands:
            for dom in self._crtsh(brand):
                c = candidate(dom)
                if c:
                    c.add("crt.sh", f"TLS cert contains brand '{brand}'", f"{CRTSH_URL}?q=%25{brand}%25")

        # 2) urlscan — scanned pages mentioning a brand.
        for brand in wl.brands:
            for dom, url in self._urlscan(brand):
                c = candidate(dom)
                if c:
                    c.add("urlscan", f"urlscan page mentions '{brand}'", url)

        # 3) web search — pages reusing an ADDRESS or ENTITY (strongest signal).
        if self._enricher is not None and self._enricher.enabled():
            for addr in wl.addresses:
                for dom, url in self._web(f'"{addr}"'):
                    c = candidate(dom)
                    if c:
                        c.add("search", "web page reuses protected ADDRESS", url)
            for ent in wl.entities:
                for dom, url in self._web(f'"{ent}"'):
                    c = candidate(dom)
                    if c:
                        c.add("search", f"web page reuses entity name '{ent}'", url)

        # Categorise, then enrich with domain age (bounded).
        for s in suspects.values():
            s.category = categorize(s.domain, wl.brands)
        ranked = sorted(suspects.values(), key=lambda s: len(s.sources), reverse=True)[:max_domains]
        for s in ranked:
            s.registered = self._age.registration_date(s.domain)
        self._log.info("Brand monitor: %d suspect domain(s)", len(ranked))
        # Impersonation first, then unknown-site, then mere mentions.
        _cat_rank = {"impersonation": 0, "unknown": 1, "known": 2}
        return sorted(
            ranked,
            key=lambda s: (_cat_rank.get(s.category.split()[0], 1), -s.score()),
        )

    # ---- network helpers (each degrades to empty on failure) ------------- #
    def _crtsh(self, term: str) -> set[str]:
        # crt.sh is free but often slow; give it a longer timeout and one retry.
        for attempt in range(2):
            try:
                resp = self._session.get(
                    CRTSH_URL, params={"q": f"%{term}%", "output": "json"}, timeout=60
                )
                if resp.status_code == 200:
                    return extract_crtsh_domains(resp.json())
                break
            except (requests.RequestException, ValueError) as exc:
                if attempt == 0:
                    time.sleep(2)
                    continue
                self._log.warning("crt.sh failed for %s: %s", term, redact(str(exc)))
        time.sleep(self._pause)
        return set()

    def _urlscan(self, term: str) -> list[tuple[str, str]]:
        headers = {"API-Key": self._urlscan_key} if self._urlscan_key else {}
        try:
            resp = self._session.get(
                URLSCAN_SEARCH, params={"q": term}, headers=headers, timeout=self._timeout
            )
            if resp.status_code == 200:
                return extract_urlscan(resp.json())
        except (requests.RequestException, ValueError) as exc:
            self._log.warning("urlscan failed for %s: %s", term, redact(str(exc)))
        time.sleep(self._pause)
        return []

    def _web(self, query: str) -> list[tuple[str, str]]:
        assert self._enricher is not None
        try:
            results = self._enricher.raw_results(query)
        except requests.RequestException as exc:
            self._log.warning("web search failed for %s: %s", query, redact(str(exc)))
            return []
        out = [(registrable_domain(r.get("link", "")), r.get("link", "")) for r in results]
        time.sleep(self._pause)
        return [(d, u) for d, u in out if d]


def build_brand_sheet(suspects: list[Suspect]) -> pd.DataFrame:
    """Build the 'Brand Abuse' DataFrame (empty frame if no suspects)."""
    cols = ["Suspect Domain", "Category", "Risk Score", "Sources", "Domain Registered", "Why Flagged", "Evidence"]
    if not suspects:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([s.to_row() for s in suspects], columns=cols)
