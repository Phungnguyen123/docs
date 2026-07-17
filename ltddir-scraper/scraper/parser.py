"""Extraction of company detail fields from a rendered detail page.

The strategy is *label-driven*: instead of depending on exact CSS paths (which
break whenever the site is redesigned), we collect every ``label -> value`` pair
we can find on the page (tables, definition lists, and "Label: value" text
blocks) and then map those labels onto our canonical field names using the
configurable ``field_label_map``. The mapping step is a pure function and is
covered by unit tests.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.async_api import Page


@dataclass
class CompanyRecord:
    """A single company's extracted fields. Missing values stay empty strings."""

    company_name: str = ""
    company_number: str = ""
    company_status: str = ""
    company_type: str = ""
    incorporation_date: str = ""
    registered_address: str = ""
    directors: str = ""
    company_secretary: str = ""
    business_nature: str = ""
    previous_names: str = ""
    remarks: str = ""
    source_url: str = ""
    # Optional extras populated by some sources (e.g. Hong Kong).
    company_name_other: str = ""  # non-English name (e.g. Chinese)
    redomiciliation_date: str = ""

    def as_dict(self) -> dict[str, str]:
        """Return the record as a plain dict."""
        return asdict(self)


def _clean(text: str) -> str:
    """Collapse whitespace and trim a value string."""
    return re.sub(r"\s+", " ", text or "").strip(" \t\n\r:•-")


def map_labels_to_fields(
    pairs: dict[str, str],
    field_label_map: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    """Map raw ``label -> value`` pairs onto canonical field names.

    Pure and deterministic so it can be unit-tested without a browser. For each
    canonical field the first label (by longest, most specific keyword match)
    that appears in ``pairs`` wins.
    """
    normalized_pairs = {_clean(k).lower(): _clean(v) for k, v in pairs.items() if _clean(v)}
    result: dict[str, str] = {}

    for canonical, keywords in field_label_map.items():
        # Try most specific keywords first (longer strings are more specific).
        for keyword in sorted(keywords, key=len, reverse=True):
            match = _best_label_for_keyword(normalized_pairs, keyword)
            if match is not None:
                result[canonical] = normalized_pairs[match]
                break
    return result


def _best_label_for_keyword(pairs: dict[str, str], keyword: str) -> str | None:
    """Return the pair-label best matching ``keyword`` (exact before substring)."""
    kw = keyword.lower()
    if kw in pairs:
        return kw
    substring_hits = [label for label in pairs if kw in label]
    if substring_hits:
        # Shortest label containing the keyword is the least "polluted".
        return min(substring_hits, key=len)
    return None


# --------------------------------------------------------------------------- #
# DOM extraction (async, needs a live Page)
# --------------------------------------------------------------------------- #
async def extract_label_value_pairs(page: "Page") -> dict[str, str]:
    """Collect ``label -> value`` pairs from the page using several DOM shapes.

    Handles: HTML tables (``th``/``td`` or two-column ``td``), definition lists
    (``dt``/``dd``), and inline "Label: value" text nodes. Runs entirely in the
    browser context via a single ``evaluate`` call for speed.
    """
    return await page.evaluate(
        r"""() => {
            const pairs = {};
            const put = (k, v) => {
                k = (k || '').replace(/\s+/g, ' ').trim().replace(/[:•]+$/, '').trim();
                v = (v || '').replace(/\s+/g, ' ').trim();
                if (k && v && k.length < 60 && !(k in pairs)) pairs[k] = v;
            };

            // 1) Tables: header cell + value cell, or two-column rows.
            document.querySelectorAll('table tr').forEach(tr => {
                const th = tr.querySelector('th');
                const tds = tr.querySelectorAll('td');
                if (th && tds.length >= 1) put(th.innerText, tds[tds.length - 1].innerText);
                else if (tds.length >= 2) put(tds[0].innerText, tds[1].innerText);
            });

            // 2) Definition lists.
            document.querySelectorAll('dl').forEach(dl => {
                const dts = dl.querySelectorAll('dt');
                const dds = dl.querySelectorAll('dd');
                for (let i = 0; i < Math.min(dts.length, dds.length); i++) {
                    put(dts[i].innerText, dds[i].innerText);
                }
            });

            // 3) Generic "Label: value" blocks inside list items / rows / paras.
            document.querySelectorAll('li, p, div.row, .field, .detail').forEach(el => {
                const strong = el.querySelector('strong, b, .label, .field-label');
                if (strong) {
                    const label = strong.innerText;
                    const full = el.innerText;
                    const value = full.slice(full.indexOf(label) + label.length);
                    put(label, value.replace(/^[:\s]+/, ''));
                    return;
                }
                const text = el.innerText || '';
                const m = text.match(/^([A-Za-z][A-Za-z0-9 /()'&.-]{1,50}?)\s*[:：]\s*(.+)$/);
                if (m) put(m[1], m[2]);
            });

            return pairs;
        }"""
    )


async def parse_company_page(
    page: "Page",
    field_label_map: dict[str, tuple[str, ...]],
    *,
    source_url: str,
    fallback_name: str = "",
) -> CompanyRecord:
    """Parse a company detail page into a :class:`CompanyRecord`.

    ``fallback_name`` is used when no obvious title/heading is found.
    """
    pairs = await extract_label_value_pairs(page)
    mapped = map_labels_to_fields(pairs, field_label_map)

    name = await _extract_company_name(page)
    record = CompanyRecord(
        company_name=name or _clean(fallback_name),
        source_url=source_url,
        company_number=mapped.get("company_number", ""),
        company_status=mapped.get("company_status", ""),
        company_type=mapped.get("company_type", ""),
        incorporation_date=mapped.get("incorporation_date", ""),
        registered_address=mapped.get("registered_address", ""),
        directors=mapped.get("directors", ""),
        company_secretary=mapped.get("company_secretary", ""),
        business_nature=mapped.get("business_nature", ""),
        previous_names=mapped.get("previous_names", ""),
        remarks=mapped.get("remarks", ""),
    )
    return record


async def _extract_company_name(page: "Page") -> str:
    """Best-effort extraction of the company name from the detail page."""
    for selector in ("h1", "h1.company-name", ".company-name", "header h1", "title"):
        try:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            text = _clean(await locator.inner_text())
            if text:
                return text
        except Exception:  # noqa: BLE001 - best effort, never fatal
            continue
    return ""
