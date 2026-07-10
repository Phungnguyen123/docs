# Meet BSmart — LinkedIn carousel (5 slides)

Full "Meet BSmart" carousel exported as a print-ready, 5-page PDF for posting as a
LinkedIn **document / carousel** post.

- **Format:** 1080 × 1350 px (4:5 portrait), 5 pages — S1 Hook → S2 Intro → S3 Demo →
  S4 24/7 → S5 Coming soon.
- **Deliverable:** `Meet-BSmart-carousel.pdf`

Imported from the Claude Design project **BSmart comet poster**
(`export/src/carousel-meet-bsmart-print.html`) and made self-contained:
the Google Fonts `<link>` was replaced with **Plus Jakarta Sans embedded as base64
`@font-face`**, so the PDF renders identically offline (no system-font fallback).

## Files

- `carousel-meet-bsmart-print.html` — the 5-slide carousel, fonts embedded. Uses
  `@page { size: 1080px 1350px; margin: 0 }` + `break-after: page` per slide.
- `assets/` — `bbcincorp-logo-white.svg`, `bsmart-badge.svg`, `bsmart-chat.png`.
- `Meet-BSmart-carousel.pdf` — the exported carousel (what you upload to LinkedIn).

## Regenerate the PDF

Render the HTML to PDF at native size with a headless Chromium (e.g. Playwright):

```js
await page.goto('file://…/carousel-meet-bsmart-print.html', { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
await page.pdf({
  path: 'Meet-BSmart-carousel.pdf',
  width: '1080px', height: '1350px',
  printBackground: true, pageRanges: '1-5',
  margin: { top: '0', right: '0', bottom: '0', left: '0' },
});
```

## Posting on LinkedIn

Start a post → **Add a document** → upload `Meet-BSmart-carousel.pdf` → give it a
title. LinkedIn renders the pages as a swipeable carousel. 4:5 portrait fills the most
feed height on mobile.
