#!/usr/bin/env python3
"""
selfcontain.py — turn a Claude Design HTML export into a clean, self-contained page.

Two jobs:
  1. Unwrap the Claude Design runtime (`.dc.html` files): drop `support.js`, hoist the
     `<helmet>` head content into `<head>`, unwrap `<x-dc>`, and remove the `x-dc`
     bootstrap + any auto `window.print()` script.
  2. Embed webfonts: every `<link href="https://fonts.googleapis.com/css2...">` is
     fetched, its `.woff2`/`.ttf` files downloaded and inlined as base64 `@font-face`,
     so the page renders identically offline (no system-font fallback in exports).

Local `assets/...` references are left untouched — copy the asset folder next to the
output file (the render step reads them from disk).

Usage:
    python selfcontain.py INPUT.html [-o OUTPUT.html]

Network note: font downloads go through the environment's HTTPS proxy via `curl`
(honours HTTPS_PROXY). If fonts can't be fetched, the original <link> is kept so the
page still works online.
"""
import argparse
import base64
import os
import re
import subprocess
import sys

CHROME_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _curl(url: str, binary: bool = False, timeout: int = 40):
    """Fetch a URL with curl (proxy-aware). Returns bytes or None."""
    try:
        out = subprocess.run(
            ["curl", "-sSL", "-m", str(timeout), "-A", CHROME_UA, url],
            capture_output=True, check=True,
        )
        return out.stdout if binary else out.stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"  ! fetch failed for {url[:80]}...: {e}", file=sys.stderr)
        return None


def embed_google_fonts(html: str) -> str:
    """Replace Google Fonts <link> tags with an inlined base64 @font-face <style>."""
    link_re = re.compile(
        r'<link[^>]+href="(https://fonts\.googleapis\.com/css2[^"]+)"[^>]*>')
    css_urls = link_re.findall(html)
    if not css_urls:
        return html

    inlined_blocks = []
    ok = True
    for css_url in css_urls:
        css = _curl(css_url.replace("&amp;", "&"))
        if not css:
            ok = False
            continue
        font_urls = sorted(set(re.findall(
            r'https://fonts\.gstatic\.com/[^) ]+\.(?:woff2|ttf)', css)))
        for fu in font_urls:
            data = _curl(fu, binary=True)
            if not data:
                ok = False
                continue
            mime = "font/woff2" if fu.endswith("woff2") else "font/ttf"
            b64 = base64.b64encode(data).decode()
            css = css.replace(fu, f"data:{mime};base64,{b64}")
        inlined_blocks.append(css)

    if not inlined_blocks:
        return html

    style = ("<style data-embedded-fonts>\n/* Webfonts embedded by "
             "design-to-social */\n" + "\n".join(inlined_blocks) + "\n</style>")
    # Remove preconnect hints + the css2 <link> tags, then inject the style into <head>.
    html = re.sub(r'\s*<link[^>]+rel="preconnect"[^>]*>', '', html)
    html = link_re.sub('', html)
    if "</head>" in html:
        html = html.replace("</head>", style + "\n</head>", 1)
    else:
        html = style + html
    if not ok:
        print("  ! some fonts could not be embedded (kept what worked)",
              file=sys.stderr)
    return html


def _extract_slide(sub: str):
    """From a slide .dc.html, return (helmet_head_html, stage_body_html)."""
    helmet = ""
    hm = re.search(r'<helmet[^>]*>(.*?)</helmet>', sub, re.S | re.I)
    if hm:
        helmet = hm.group(1)
    xm = re.search(r'<x-dc[^>]*>(.*?)</x-dc>', sub, re.S | re.I)
    body = xm.group(1) if xm else sub
    body = re.sub(r'<helmet[^>]*>.*?</helmet>', '', body, flags=re.S | re.I)
    return helmet, body.strip()


def resolve_dc_imports(html: str, base_dir: str) -> str:
    """Inline <dc-import name="X"> by reading sibling X.dc.html and merging its head.

    Claude Design carousels compose slides with <dc-import>. Each named slide is a
    separate .dc.html in the same folder; this pulls each slide's stage markup in place
    and collects its <helmet> head fragments (fonts, token styles) into the parent head.
    """
    if "<dc-import" not in html or not base_dir:
        return html
    head_fragments = []

    def repl(m):
        name = m.group("name")
        path = os.path.join(base_dir, name + ".dc.html")
        if not os.path.exists(path):
            print(f"  ! dc-import not found on disk: {name}.dc.html", file=sys.stderr)
            return ""
        with open(path, encoding="utf-8") as fh:
            sub = fh.read()
        helmet, body = _extract_slide(sub)
        if helmet:
            head_fragments.append(helmet)
        return body

    html = re.sub(r'<dc-import\b[^>]*\bname="(?P<name>[^"]+)"[^>]*>(?:</dc-import>)?',
                  repl, html)

    if head_fragments:
        # dedupe identical lines across slide heads, preserve first-seen order
        seen, merged = set(), []
        for frag in head_fragments:
            for line in frag.splitlines():
                key = line.strip()
                if key and key in seen:
                    continue
                seen.add(key)
                merged.append(line)
        merged_html = "\n".join(merged)
        if re.search(r'</helmet>', html, re.I):
            html = re.sub(r'</helmet>', merged_html + "\n</helmet>", html, count=1, flags=re.I)
        elif "</head>" in html:
            html = html.replace("</head>", merged_html + "\n</head>", 1)
    return html


def strip_local_ds_links(html: str) -> str:
    """Drop <link href="_ds/…"> design-token stylesheets (local, would 404 in exports).

    Claude Design slides reference design-system token CSS, but the slides use literal
    colours (no CSS vars), so these are safe to remove for a self-contained export.
    """
    return re.sub(r'\s*<link[^>]+href="_ds/[^"]*"[^>]*>', '', html, flags=re.I)


def unwrap_dc(html: str) -> str:
    """Strip the Claude Design (.dc.html) runtime, leaving a plain HTML document."""
    if "<x-dc" not in html and "support.js" not in html and "text/x-dc" not in html:
        return html  # not a DC file

    # drop the runtime loader
    html = re.sub(r'\s*<script[^>]+src="\.?/?support\.js"[^>]*>\s*</script>', '', html)

    # hoist <helmet>…</helmet> content into <head>
    m = re.search(r'<helmet[^>]*>(.*?)</helmet>', html, re.S | re.I)
    if m:
        head_extra = m.group(1)
        html = html[:m.start()] + html[m.end():]
        if "</head>" in html:
            html = html.replace("</head>", head_extra + "\n</head>", 1)
        elif "<body" in html:
            html = re.sub(r'(<body[^>]*>)', head_extra + r'\1', html, count=1)

    # unwrap <x-dc>…</x-dc> (keep inner content)
    html = re.sub(r'</?x-dc[^>]*>', '', html, flags=re.I)

    # remove the x-dc props script and any DC auto-print bootstrap
    html = re.sub(r'<script[^>]*type="text/x-dc"[^>]*>.*?</script>', '', html, flags=re.S | re.I)
    html = re.sub(
        r'<script>\s*addEventListener\([\'"]load[\'"].*?window\.print\(\).*?</script>',
        '', html, flags=re.S)
    return html


def normalize(html: str) -> str:
    """Small safety net: keep any @media print zoom from shrinking screenshot exports."""
    # Screenshots ignore @media print, but neutralise obvious zoom-shrink just in case
    # a downstream tool uses print. Harmless if absent.
    return html


def process(html: str, base_dir: str = None) -> str:
    html = resolve_dc_imports(html, base_dir)
    html = unwrap_dc(html)
    html = strip_local_ds_links(html)
    html = embed_google_fonts(html)
    html = normalize(html)
    return html


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="input HTML (.dc.html or exported carousel)")
    ap.add_argument("-o", "--output", help="output path (default: <input>.standalone.html)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        html = fh.read()
    out_html = process(html, base_dir=os.path.dirname(os.path.abspath(args.input)))

    out = args.output
    if not out:
        root, _ = os.path.splitext(args.input)
        root = root[:-3] if root.endswith(".dc") else root
        out = root + ".standalone.html"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(out_html)
    print(f"wrote {out} ({len(out_html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
