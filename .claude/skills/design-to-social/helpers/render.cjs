#!/usr/bin/env node
/*
 * render.cjs — render a self-contained design HTML to per-slide PNGs.
 *
 * Slide detection (in order):
 *   1. Elements with [data-document-role="page"]  (Claude Design carousel exports)
 *   2. Elements matching --selector (if provided)
 *   3. Direct <div> children of <body> whose box is >= 200x200 px (single slides,
 *      e.g. a .dc.html stage like #printslide5)
 *
 * Each slide is screenshotted at its exact CSS-pixel box, times --scale for crispness.
 * Writes slide-01.png, slide-02.png, ... and a sizes.json describing each slide.
 *
 * Usage:
 *   node render.cjs INPUT.html --outdir DIR [--scale 2] [--selector ".slide"]
 *
 * PDF assembly is done separately (topdf.py) so it works regardless of @page/@media
 * print quirks — screenshots are the single source of truth.
 */
const path = require('path');

function loadPlaywright() {
  const candidates = [
    'playwright',
    'playwright-core',
    '/opt/node22/lib/node_modules/playwright',
    '/opt/node22/lib/node_modules/playwright-core',
  ];
  for (const c of candidates) {
    try { return require(c); } catch (_) { /* keep trying */ }
  }
  console.error('ERROR: playwright not found. Install with: npm i -g playwright');
  process.exit(2);
}

function parseArgs(argv) {
  const a = { scale: 2, outdir: 'out', selector: null, _: [] };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t === '--scale') a.scale = parseFloat(argv[++i]);
    else if (t === '--outdir') a.outdir = argv[++i];
    else if (t === '--selector') a.selector = argv[++i];
    else a._.push(t);
  }
  a.input = a._[0];
  return a;
}

(async () => {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) { console.error('usage: node render.cjs INPUT.html --outdir DIR [--scale 2]'); process.exit(1); }
  const fs = require('fs');
  fs.mkdirSync(args.outdir, { recursive: true });

  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1800 }, deviceScaleFactor: args.scale });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

  const fileUrl = 'file://' + path.resolve(args.input);
  await page.goto(fileUrl, { waitUntil: 'networkidle' });
  try { await page.evaluate(() => document.fonts.ready); } catch (_) {}
  await page.waitForTimeout(300);

  const boxes = await page.evaluate((selector) => {
    let nodes = Array.from(document.querySelectorAll('[data-document-role="page"]'));
    if (!nodes.length && selector) nodes = Array.from(document.querySelectorAll(selector));
    if (!nodes.length) {
      nodes = Array.from(document.body.children).filter((el) => {
        if (el.tagName !== 'DIV') return false;
        const r = el.getBoundingClientRect();
        return r.width >= 200 && r.height >= 200;
      });
      if (!nodes.length) {
        const first = Array.from(document.body.children).find((el) => el.tagName === 'DIV');
        if (first) nodes = [first];
      }
    }
    return nodes.map((el, i) => {
      const r = el.getBoundingClientRect();
      el.setAttribute('data-d2s-idx', String(i));
      const label = el.getAttribute('data-label') || el.getAttribute('id') || ('slide-' + (i + 1));
      return { i, x: r.left + window.scrollX, y: r.top + window.scrollY,
               w: Math.round(r.width), h: Math.round(r.height), label };
    });
  }, args.selector);

  if (!boxes.length) { console.error('ERROR: no slides detected'); await browser.close(); process.exit(3); }

  const sizes = [];
  for (const b of boxes) {
    const el = await page.$(`[data-d2s-idx="${b.i}"]`);
    const n = String(b.i + 1).padStart(2, '0');
    const out = path.join(args.outdir, `slide-${n}.png`);
    await el.screenshot({ path: out });
    sizes.push({ index: b.i + 1, file: `slide-${n}.png`, width: b.w, height: b.h, label: b.label });
    console.log(`slide ${n}: ${b.w}x${b.h}  ${b.label}`);
  }
  fs.writeFileSync(path.join(args.outdir, 'sizes.json'), JSON.stringify(sizes, null, 2));
  console.log(`OK ${sizes.length} slide(s) @scale ${args.scale}` + (errors.length ? `  (warnings: ${errors.length})` : ''));
  if (errors.length) console.error('warnings:', JSON.stringify(errors.slice(0, 5)));
  await browser.close();
})();
