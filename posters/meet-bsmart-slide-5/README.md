# Meet BSmart — Slide 5 (Coming Soon)

Final slide of the "Meet BSmart" carousel: a 1080×1350 (4:5) social poster with the
"BSmart is just the beginning / The new BBCIncorp is coming" coming-soon CTA.

Imported from the Claude Design project **BSmart comet poster** and reimplemented as a
standalone, self-contained page (the original `Meet BSmart - Slide 5-print.dc.html` relied
on the Claude Design `<x-dc>` runtime + `support.js`; this version needs neither).

## Files

- `index.html` — the slide, laid out on a fixed 1080×1350 stage.
- `assets/bbcincorp-logo-white.svg` — top-left brand logo.
- `assets/bsmart-badge.svg` — the BSmart mascot badge (flying toward the gold horizon).

## Usage

Open `index.html` in a browser to view. It needs outbound access to Google Fonts
(Plus Jakarta Sans); without it, it falls back to the system sans-serif.

### Export to PDF / image

This is the `-print` variant. Append `?print=1` to the URL (e.g.
`index.html?print=1`) to auto-open the browser print dialog once fonts and images have
loaded — print to PDF with margins set to none for a pixel-accurate 1080×1350 export.
The `@media print` block already pins the background colors and freezes the float
animation so the printed output matches the on-screen frame.
