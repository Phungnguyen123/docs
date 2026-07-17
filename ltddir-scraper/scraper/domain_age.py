"""Domain registration age via RDAP (free, no key) — a fraud signal.

A brand-new domain paired with an e-commerce site is a classic scam tell. RDAP
(Registration Data Access Protocol) is the modern, JSON, keyless successor to
WHOIS; ``https://rdap.org`` bootstraps to the right registry automatically.

Network access is required (runs on the user's machine). All failures degrade to
"unknown age" so a lookup problem never breaks the run.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

import requests

from .utils import get_logger

RDAP_BOOTSTRAP = "https://rdap.org/domain/"


def registrable_from_host(host: str) -> str:
    """Reduce a host to a registrable-ish domain (best effort, no PSL).

    Handles common two-label public suffixes (co.uk, com.hk, com.cn, ...).
    """
    host = host.strip().lower().strip(".")
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    two_label_suffixes = {
        "co.uk", "org.uk", "com.hk", "com.cn", "com.au", "co.jp", "com.sg",
        "com.tw", "co.kr", "com.my", "co.nz",
    }
    last_two = ".".join(parts[-2:])
    if last_two in two_label_suffixes:
        return ".".join(parts[-3:])
    return last_two


def parse_registration_date(rdap: dict[str, Any]) -> str:
    """Return the ISO date (YYYY-MM-DD) of the 'registration' event, or ''."""
    for event in rdap.get("events", []) or []:
        if str(event.get("eventAction", "")).lower() in ("registration", "created"):
            raw = str(event.get("eventDate", ""))
            m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
            if m:
                return m.group(1)
    return ""


def age_days(registration_iso: str, *, today: date) -> int | None:
    """Days between a registration date and ``today`` (None if unparseable)."""
    try:
        reg = datetime.strptime(registration_iso, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (today - reg).days


def young_domain_flag(
    registration_iso: str, *, today: date, young_days: int = 180
) -> tuple[str, str] | None:
    """Return a (label, evidence) flag if the domain is newer than ``young_days``."""
    days = age_days(registration_iso, today=today)
    if days is None or days > young_days:
        return None
    return (
        f"newly registered domain ({days} days old)",
        f"registered {registration_iso} (verify at rdap.org)",
    )


class DomainAgeLookup:
    """Looks up domain registration dates via RDAP, with a small cache."""

    def __init__(self, *, timeout_s: float = 15.0) -> None:
        self._timeout = timeout_s
        self._log = get_logger()
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/rdap+json, application/json"})
        self._cache: dict[str, str] = {}

    def registration_date(self, domain: str) -> str:
        """Return the ISO registration date for ``domain`` ('' if unknown)."""
        domain = registrable_from_host(domain)
        if not domain:
            return ""
        if domain in self._cache:
            return self._cache[domain]
        iso = ""
        try:
            resp = self._session.get(f"{RDAP_BOOTSTRAP}{domain}", timeout=self._timeout)
            if resp.status_code == 200:
                iso = parse_registration_date(resp.json())
        except (requests.RequestException, ValueError) as exc:
            self._log.debug("RDAP lookup failed for %s: %s", domain, exc)
        self._cache[domain] = iso
        return iso


def _today_utc() -> date:
    """Current UTC date (isolated so it can be monkeypatched in tests)."""
    return datetime.now(timezone.utc).date()
