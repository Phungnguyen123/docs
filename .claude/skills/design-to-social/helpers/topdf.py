#!/usr/bin/env python3
"""
topdf.py — assemble rendered slide PNGs into one multi-page PDF.

Image-per-page: each PNG becomes one PDF page at its own aspect ratio, so the output
is pixel-faithful regardless of any @page / @media print rules in the source. Ideal
for LinkedIn document/carousel posts (upload as a "document").

Usage:
    python topdf.py OUTDIR/slide-*.png -o OUTDIR/carousel.pdf [--dpi 96]
    python topdf.py --from-sizes OUTDIR -o OUTDIR/carousel.pdf   # uses sizes.json order
"""
import argparse
import glob
import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: uv pip install --system pillow")


def collect(args):
    if args.from_sizes:
        sj = os.path.join(args.from_sizes, "sizes.json")
        with open(sj) as fh:
            order = json.load(fh)
        return [os.path.join(args.from_sizes, s["file"]) for s in order]
    files = []
    for pat in args.images:
        files.extend(sorted(glob.glob(pat)) if any(c in pat for c in "*?[") else [pat])
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="*", help="PNG files or globs, in page order")
    ap.add_argument("--from-sizes", help="OUTDIR containing sizes.json (uses its order)")
    ap.add_argument("-o", "--output", required=True, help="output PDF path")
    ap.add_argument("--dpi", type=int, default=96, help="PDF resolution hint (default 96)")
    args = ap.parse_args()

    files = collect(args)
    if not files:
        sys.exit("no images to assemble")

    pages = []
    for f in files:
        im = Image.open(f)
        if im.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.convert("RGBA").split()[-1] if im.mode != "P" else None)
            im = bg
        else:
            im = im.convert("RGB")
        pages.append(im)

    first, rest = pages[0], pages[1:]
    first.save(args.output, "PDF", save_all=True, append_images=rest,
               resolution=float(args.dpi))
    print(f"wrote {args.output} ({len(pages)} page(s), {os.path.getsize(args.output):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
