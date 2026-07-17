"""Phase 1 helper: inspect the live LTDDir site and report its structure.

Run this once from an environment with network access to confirm (or correct)
the selector strategies in ``config.py`` before a full crawl. It never guesses:
it reports exactly what it observes.

    python inspect.py                       # inspect search page
    python inspect.py --query "HELENA LIMITED"   # also run a sample search

Findings printed:
  * whether the page loaded and its HTTP-ish signals
  * anti-bot fingerprints (Cloudflare / CAPTCHA / JS challenge)
  * candidate search-box / submit selectors that actually exist
  * whether results are server-rendered or fetched via XHR/fetch (hidden API)
  * observed result item + link selectors
  * a sample detail page's label -> value pairs
"""

from __future__ import annotations

import argparse
import asyncio
import json

from playwright.async_api import async_playwright

import config
from scraper.parser import extract_label_value_pairs

ANTIBOT_SIGNALS = (
    "just a moment",
    "checking your browser",
    "cloudflare",
    "captcha",
    "are you a robot",
    "access denied",
)


async def inspect(query: str | None, show: bool) -> None:
    """Probe the site and print a structured report to stdout."""
    s = config.SETTINGS
    xhr_urls: list[str] = []

    async with async_playwright() as pw:
        launch_kwargs: dict[str, object] = {"headless": not show}
        if s.chromium_executable_path:
            launch_kwargs["executable_path"] = s.chromium_executable_path
        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(user_agent=s.user_agent, locale=s.locale)
        page = await context.new_page()

        # Capture background API calls to reveal any hidden JSON endpoint.
        page.on(
            "request",
            lambda req: xhr_urls.append(f"{req.method} {req.url}")
            if req.resource_type in ("xhr", "fetch")
            else None,
        )

        print(f"\n=== Navigating to {s.search_url} ===")
        resp = await page.goto(s.search_url, wait_until="domcontentloaded")
        print(f"HTTP status: {resp.status if resp else 'unknown'}")
        print(f"Final URL:   {page.url}")

        body = (await page.evaluate("() => document.body.innerText")).lower()
        blocks = [sig for sig in ANTIBOT_SIGNALS if sig in body]
        print(f"Anti-bot signals: {blocks or 'none detected'}")

        print("\n--- Search box candidates that EXIST on the page ---")
        await _report_existing(page, s.search_input_selectors)
        print("\n--- Submit button candidates that EXIST ---")
        await _report_existing(page, s.search_submit_selectors)

        if query:
            print(f"\n=== Running sample search: {query!r} ===")
            xhr_urls.clear()
            box = await _first_existing(page, s.search_input_selectors)
            if box is None:
                print("No search box found; cannot run sample search.")
            else:
                await box.fill(query)
                await box.press("Enter")
                try:
                    await page.wait_for_load_state("networkidle", timeout=15_000)
                except Exception:  # noqa: BLE001
                    pass
                print(f"Results URL: {page.url}")
                print("XHR/fetch during search (possible hidden API):")
                for u in dict.fromkeys(xhr_urls):
                    print(f"  {u}")

                print("\n--- Result item selectors that matched ---")
                await _report_existing(page, s.result_item_selectors, want_count=True)

                first_link = await _first_detail_link(page, s)
                if first_link:
                    print(f"\n=== Opening first detail page: {first_link} ===")
                    await page.goto(first_link, wait_until="domcontentloaded")
                    pairs = await extract_label_value_pairs(page)
                    print("Extracted label -> value pairs:")
                    print(json.dumps(pairs, indent=2, ensure_ascii=False))

        await context.close()
        await browser.close()


async def _report_existing(page, selectors, *, want_count: bool = False) -> None:  # noqa: ANN001
    """Print which of ``selectors`` exist on the current page."""
    found = False
    for sel in selectors:
        count = await page.locator(sel).count()
        if count:
            found = True
            suffix = f"  (matched {count})" if want_count else ""
            print(f"  [OK] {sel}{suffix}")
    if not found:
        print("  (none of the configured selectors matched)")


async def _first_existing(page, selectors):  # noqa: ANN001
    """Return the first existing locator among ``selectors``, else None."""
    for sel in selectors:
        loc = page.locator(sel).first
        if await loc.count() > 0:
            return loc
    return None


async def _first_detail_link(page, s) -> str | None:  # noqa: ANN001
    """Return the first anchor URL that looks like a company detail page."""
    from urllib.parse import urljoin

    anchors = page.locator("a[href]")
    for i in range(await anchors.count()):
        href = (await anchors.nth(i).get_attribute("href")) or ""
        if any(p in href for p in s.detail_link_href_patterns):
            return urljoin(s.base_url, href)
    return None


def main() -> None:
    """CLI wrapper."""
    p = argparse.ArgumentParser(description="Inspect the LTDDir site structure")
    p.add_argument("--query", type=str, default=None, help="run a sample search")
    p.add_argument("--show", action="store_true", help="visible browser")
    args = p.parse_args()
    asyncio.run(inspect(args.query, args.show))


if __name__ == "__main__":
    main()
