"""OSINT trace: hunt open-web discussions of the companies / their infrastructure.

For a suspected shell-company factory, the highest-value moves are not per-company
searches but **pivots** on the shared infrastructure:

  * the shared registered address (one address behind many companies)
  * each distinctive storefront domain that was discovered

For each pivot this runs a few platform-targeted queries (Reddit, Telegram,
Quora, forums, scam-report sites) and collects the discussion links, so an
organised operation — the same address or store discussed across scam forums —
becomes visible. Bounded and logged to keep API usage predictable.

Requires a search provider (see web_enrich.WebEnricher). Pure parsing helpers are
unit-tested; the network sweep is thin.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from .utils import get_logger, normalize_name
from .web_enrich import classify, registrable_domain

if TYPE_CHECKING:  # pragma: no cover
    from .web_enrich import WebEnricher

# Extra scam keywords for keeping a general-web result as relevant.
_TRACE_KEYWORDS = (
    "scam", "fraud", "fake", "complaint", "shell company", "shell companies",
    "money laundering", "chargeback", "ripoff", "did not receive", "never arrived",
    "blacklist", "warning",
)


def platform_of(url: str) -> str:
    """Human-readable platform label for a result URL."""
    host = registrable_domain(url)
    if "t.me" in host or "telegram" in host:
        return "Telegram"
    if "reddit.com" in host:
        return "Reddit"
    if "quora.com" in host:
        return "Quora"
    if "discord" in host:
        return "Discord"
    kind = classify(url)
    if kind == "scam":
        return "Scam-report"
    if kind == "community":
        return "Forum/Community"
    return "Web"


def is_trace_relevant(result: dict[str, str]) -> bool:
    """Keep community/telegram/scam results, or any result mentioning red-flag terms."""
    url = result.get("link", "")
    if platform_of(url) != "Web":
        return True
    text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
    return any(k in text for k in _TRACE_KEYWORDS)


@dataclass
class Mention:
    """One open-web discussion linked to a pivot (address/domain/company)."""

    platform: str
    url: str
    title: str
    related_to: str
    pivot_type: str  # "address" | "domain" | "company"

    def to_row(self) -> dict[str, str]:
        return {
            "Platform": self.platform,
            "Pivot Type": self.pivot_type,
            "Related To": self.related_to,
            "Title": self.title[:160],
            "URL": self.url,
        }


def collect_pivots(
    rows: list[dict[str, str]], *, shared_min: int = 3, max_domains: int = 25
) -> tuple[list[str], list[str]]:
    """Return (address pivots, domain pivots) worth searching.

    Address pivots: registered addresses shared by >= ``shared_min`` companies.
    Domain pivots: distinctive storefront/website domains (marketplaces and
    directories excluded — searching "etsy.com scam" is noise).
    """
    addr_display: dict[str, str] = {}
    addr_counts: Counter[str] = Counter()
    for r in rows:
        raw = r.get("Registered Address", "").strip()
        if raw:
            key = normalize_name(raw)
            addr_counts[key] += 1
            addr_display.setdefault(key, raw)
    addresses = [addr_display[k] for k, n in addr_counts.most_common() if n >= shared_min]

    domains: list[str] = []
    for r in rows:
        for col in ("Website", "Other Domains", "Marketplace Listings"):
            for part in _split(r.get(col, "")):
                dom = registrable_domain(part) or part
                if not dom or "." not in dom:
                    continue
                if classify("https://" + dom) in ("marketplace", "directory", "social"):
                    continue
                if dom not in domains:
                    domains.append(dom)
    return addresses, domains[:max_domains]


def _split(cell: str) -> list[str]:
    return [p.strip() for p in str(cell or "").split("|") if p.strip()]


class OsintTracer:
    """Runs the pivot sweep and returns de-duplicated mentions."""

    def __init__(self, enricher: "WebEnricher", *, pause_s: float = 0.4) -> None:
        self._enricher = enricher
        self._pause = pause_s
        self._log = get_logger()

    def trace(
        self, rows: list[dict[str, str]], *, shared_min: int = 3, max_domains: int = 25
    ) -> list[Mention]:
        """Sweep address + domain pivots across community/scam platforms."""
        addresses, domains = collect_pivots(rows, shared_min=shared_min, max_domains=max_domains)
        self._log.info(
            "OSINT trace: %d address pivot(s), %d domain pivot(s)", len(addresses), len(domains)
        )
        mentions: list[Mention] = []
        seen: set[tuple[str, str]] = set()

        for addr in addresses:
            q = f'"{addr}" (scam OR fraud OR "shell company" OR reddit OR telegram OR complaint)'
            mentions += self._run(q, related_to=addr, pivot_type="address", seen=seen)
        for dom in domains:
            q = f'"{dom}" (scam OR review OR complaint OR reddit OR telegram OR fraud)'
            mentions += self._run(q, related_to=dom, pivot_type="domain", seen=seen)
        self._log.info("OSINT trace: %d mention(s) collected", len(mentions))
        return mentions

    def _run(self, query, *, related_to, pivot_type, seen):  # noqa: ANN001
        out: list[Mention] = []
        try:
            results = self._enricher.raw_results(query)
        except Exception as exc:  # noqa: BLE001 - a bad query must not abort the sweep
            self._log.warning("OSINT query failed (%s): %s", related_to, exc)
            return out
        for r in results:
            url = r.get("link", "")
            if not url or not is_trace_relevant(r):
                continue
            key = (related_to, url)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                Mention(
                    platform=platform_of(url),
                    url=url,
                    title=r.get("title", ""),
                    related_to=related_to,
                    pivot_type=pivot_type,
                )
            )
        time.sleep(self._pause)
        return out


def build_osint_sheets(mentions: list[Mention]) -> dict[str, "pd.DataFrame"]:
    """Build 'OSINT Trace' (all mentions) and 'OSINT Summary' (counts) sheets."""
    if not mentions:
        return {}
    trace_df = pd.DataFrame([m.to_row() for m in mentions])
    platform_counts = Counter(m.platform for m in mentions)
    pivot_counts = Counter(m.related_to for m in mentions)
    summary_rows = [{"Metric": f"platform: {p}", "Count": n} for p, n in platform_counts.most_common()]
    summary_rows += [{"Metric": f"pivot: {p}", "Count": n} for p, n in pivot_counts.most_common(15)]
    return {
        "OSINT Trace": trace_df,
        "OSINT Summary": pd.DataFrame(summary_rows),
    }
