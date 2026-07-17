"""Score a candidate website for online-shopping-scam indicators (best-effort).

Fetches a page and applies transparent heuristics common to scam storefronts:
missing trust pages (contact/about/returns/privacy), urgency/discount pressure,
and no company identity on the page. Output is a *lead score*, never a verdict —
every hit is shown with the text that triggered it so you can verify.

Network access required (runs on the user's machine); failures degrade to a
blank scan so the run never breaks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import requests

from .utils import get_logger

# Trust pages a legitimate shop almost always links; absence is suspicious.
_TRUST_TERMS = ("contact", "about", "return", "refund", "privacy", "terms", "shipping")
# Urgency / pressure language common on scam stores.
_URGENCY_TERMS = (
    "limited time", "hurry", "only today", "flash sale", "ends soon",
    "almost gone", "selling fast", "while stocks last", "countdown",
)
# Steep-discount language.
_DISCOUNT_TERMS = ("% off", "clearance", "liquidation", "up to 90", "up to 80", "up to 70", "biggest sale")
# Signs a real business identity is present (reduces suspicion).
_IDENTITY_TERMS = ("company number", "registered in", "vat", "brn", "business registration", "©", "copyright")


@dataclass
class ShopScan:
    """Result of scanning one page for scam-shop indicators."""

    url: str = ""
    score: int = 0
    hits: list[str] = field(default_factory=list)
    fetched: bool = False

    def summary(self) -> str:
        """One-cell summary: 'score N/6: hit; hit; ...' or a status note."""
        if not self.fetched:
            return "not scanned"
        if not self.hits:
            return "score 0: no obvious scam-shop signals"
        return f"score {self.score}: " + "; ".join(self.hits)


def score_html(html: str, url: str = "") -> ShopScan:
    """Score raw HTML for scam-shop indicators (pure, unit-tested)."""
    text = re.sub(r"<[^>]+>", " ", html or "").lower()
    text = re.sub(r"\s+", " ", text)
    scan = ShopScan(url=url, fetched=True)

    missing_trust = [t for t in ("contact", "return", "privacy") if t not in text]
    if missing_trust:
        scan.score += 1
        scan.hits.append("missing trust pages: " + ", ".join(missing_trust))

    urgency = [t for t in _URGENCY_TERMS if t in text]
    if urgency:
        scan.score += 1
        scan.hits.append("urgency language: " + ", ".join(urgency[:3]))

    discount = [t for t in _DISCOUNT_TERMS if t in text]
    if discount:
        scan.score += 1
        scan.hits.append("steep-discount language: " + ", ".join(discount[:3]))

    if not any(t in text for t in _IDENTITY_TERMS):
        scan.score += 1
        scan.hits.append("no business identity on page (no company no./VAT/BRN)")

    if not any(t in text for t in ("contact", "@", "tel", "phone", "address")):
        scan.score += 1
        scan.hits.append("no contact details found")

    # A shop that is almost entirely "buy/sale/cart" words with little else.
    shop_words = sum(text.count(w) for w in ("add to cart", "buy now", "checkout", "sale"))
    if shop_words >= 5 and len(text) < 4000:
        scan.score += 1
        scan.hits.append("thin page dominated by purchase prompts")

    return scan


class ShopScanner:
    """Fetches pages and scores them (network; failures degrade gracefully)."""

    def __init__(self, *, timeout_s: float = 15.0, user_agent: str = "") -> None:
        self._timeout = timeout_s
        self._log = get_logger()
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": user_agent or "Mozilla/5.0 (compatible; company-osint/1.0)"}
        )

    def scan(self, url: str) -> ShopScan:
        """Fetch and score ``url``; returns an unfetched ShopScan on failure."""
        if not url:
            return ShopScan()
        try:
            resp = self._session.get(url, timeout=self._timeout)
            if resp.status_code != 200 or "text/html" not in resp.headers.get("Content-Type", ""):
                return ShopScan(url=url)
            return score_html(resp.text, url)
        except requests.RequestException as exc:
            self._log.debug("Shop scan failed for %s: %s", url, exc)
            return ShopScan(url=url)
