"""Link analysis: group companies into suspected networks (connected clusters).

Investigators care less about single risky companies than about *rings* — sets
of companies tied together by shared infrastructure. This module links companies
that share a distinctive attribute and reports the connected components (groups)
using union-find. Each group lists WHY its members are linked, so the grouping is
transparent and verifiable, plus a group-level risk tally.

Linking attributes (all derived from data already in the output rows):
  * same registered address
  * same website / other domain (registrable domain)
  * same community or scam URL (e.g. both named in one Reddit thread / ScamAdviser)
  * same bulk incorporation date (only when many companies share that exact date)

Pure and network-free, so it is fully unit-tested.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

from .utils import normalize_name
from .web_enrich import registrable_domain


class _UnionFind:
    """Minimal union-find (disjoint-set) over hashable items."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        self._parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self.add(x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:  # path compression
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        self._parent[self.find(a)] = self.find(b)

    def groups(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = defaultdict(list)
        for item in self._parent:
            out[self.find(item)].append(item)
        return out


@dataclass
class _LinkKey:
    """A shared attribute value and the reason label it represents."""

    kind: str
    value: str
    members: list[str] = field(default_factory=list)


def _split_cell(cell: str) -> list[str]:
    """Split a ' | '-joined multi-value output cell into parts."""
    return [p.strip() for p in str(cell or "").split("|") if p.strip()]


def _domains_of(row: dict[str, str]) -> set[str]:
    """All registrable domains referenced by a row (website + other domains)."""
    domains: set[str] = set()
    if row.get("Website"):
        d = registrable_domain(row["Website"])
        if d:
            domains.add(d)
    for part in _split_cell(row.get("Other Domains", "")):
        d = registrable_domain(part) or part.lower()
        if d:
            domains.add(d)
    return domains


def _shared_urls_of(row: dict[str, str]) -> set[str]:
    """Community/scam URLs referenced by a row (shared mentions link firms)."""
    urls: set[str] = set()
    for col in ("Community Mentions", "Scam/Blacklist Mentions"):
        for part in _split_cell(row.get(col, "")):
            if part.startswith("http"):
                urls.add(part)
    return urls


def build_link_keys(
    rows: list[dict[str, str]], *, bulk_date_min: int = 3
) -> dict[tuple[str, str], list[str]]:
    """Map each shared attribute -> the companies that share it (>=2 companies)."""
    keys: dict[tuple[str, str], list[str]] = defaultdict(list)
    name_of = "Input Company Name"

    date_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.get("Incorporation Date"):
            date_counts[r["Incorporation Date"]] += 1

    for r in rows:
        name = r.get(name_of, "")
        if not name:
            continue
        addr = normalize_name(r.get("Registered Address", ""))
        if addr:
            keys[("address", addr)].append(name)
        for dom in _domains_of(r):
            keys[("domain", dom)].append(name)
        for url in _shared_urls_of(r):
            keys[("shared-link", url)].append(name)
        date = r.get("Incorporation Date", "")
        if date and date_counts[date] >= bulk_date_min:
            keys[("bulk-date", date)].append(name)

    return {k: v for k, v in keys.items() if len(set(v)) >= 2}


@dataclass
class Network:
    """A suspected network (connected group) of companies."""

    members: list[str]
    reasons: list[str]
    risk_flag_count: int

    def to_row(self, index: int) -> dict[str, str]:
        return {
            "Network #": index,
            "Company Count": len(self.members),
            "Companies": ", ".join(sorted(self.members)),
            "Linked By": "; ".join(self.reasons),
            "Total Risk Flags in Group": self.risk_flag_count,
        }


def build_networks(rows: list[dict[str, str]], *, bulk_date_min: int = 3) -> list[Network]:
    """Return suspected networks: connected components over shared attributes."""
    link_keys = build_link_keys(rows, bulk_date_min=bulk_date_min)
    uf = _UnionFind()
    for members in link_keys.values():
        uniq = sorted(set(members))
        for m in uniq:
            uf.add(m)
        for other in uniq[1:]:
            uf.union(uniq[0], other)

    # Reasons per company-set root.
    reasons_by_root: dict[str, list[str]] = defaultdict(list)
    for (kind, value), members in link_keys.items():
        root = uf.find(sorted(set(members))[0])
        label = {
            "address": "shared address",
            "domain": "shared domain",
            "shared-link": "co-mentioned link",
            "bulk-date": "same incorporation date",
        }[kind]
        short = value if len(value) <= 60 else value[:57] + "..."
        reasons_by_root[root].append(f"{label} ({short}) x{len(set(members))}")

    risk_flags_by_name = {
        r.get("Input Company Name", ""): len(_split_cell_semicolon(r.get("Risk Signals", "")))
        for r in rows
    }

    networks: list[Network] = []
    for root, members in uf.groups().items():
        uniq = sorted(set(members))
        if len(uniq) < 2:
            continue
        flag_total = sum(risk_flags_by_name.get(m, 0) for m in uniq)
        networks.append(
            Network(members=uniq, reasons=sorted(set(reasons_by_root[root])), risk_flag_count=flag_total)
        )
    # Biggest / most-flagged groups first.
    networks.sort(key=lambda n: (len(n.members), n.risk_flag_count), reverse=True)
    return networks


def _split_cell_semicolon(cell: str) -> list[str]:
    return [p.strip() for p in str(cell or "").split(";") if p.strip()]


def build_networks_sheet(rows: list[dict[str, str]], *, bulk_date_min: int = 3) -> "pd.DataFrame | None":
    """Build the 'Suspected Networks' DataFrame, or None if no groups exist."""
    networks = build_networks(rows, bulk_date_min=bulk_date_min)
    if not networks:
        return None
    return pd.DataFrame([n.to_row(i) for i, n in enumerate(networks, 1)])
