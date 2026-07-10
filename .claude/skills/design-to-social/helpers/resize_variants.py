#!/usr/bin/env python3
"""
resize_variants.py — retarget rendered slides to other social sizes/ratios.

Claude Design slides are fixed-canvas (absolutely-positioned elements), so they can't
reflow responsively. Instead this keeps the design at its own aspect and re-frames it
into each target size without cropping text:

  fit = contain (default): scale the whole design to fit inside the target, center it,
        and fill the surrounding space (letterbox) with a backdrop.
  fit = cover: scale to fill the target and center-crop the overflow.

Backdrop (`--fill`, for the letterbox area):
  blur   (default) — a cover-scaled, blurred, slightly darkened copy of the design.
                     Looks intentional, especially 4:5 -> 9:16 story.
  auto   — solid colour sampled from the design's border pixels.
  #RRGGBB — a solid colour you pick.

Presets (name -> WxH):
  ig-square 1080x1080 · ig-portrait 1080x1350 · ig-landscape 1080x566 ·
  ig-story/reel/tiktok/fb-story 1080x1920 · li-landscape/fb-feed 1200x628 ·
  li-square 1200x1200 · x-feed 1200x675 · pin 1000x1500
Also accepts explicit `1080x1080` or a ratio `1:1`, `9:16`, `16:9`, `4:5`, `1.91:1`.

Usage:
  # a whole rendered directory (uses sizes.json order) -> variants/<name>/…
  python resize_variants.py --from-dir OUT --targets ig-square,ig-story [--fit contain] [--fill blur] [--pdf]
  # a single image
  python resize_variants.py slide-01.png --targets 1:1,9:16 --outdir OUT
"""
import argparse
import glob
import json
import os
import sys

try:
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit("Pillow is required: uv pip install --system pillow")

PRESETS = {
    "ig-square": (1080, 1080), "ig-portrait": (1080, 1350), "ig-landscape": (1080, 566),
    "ig-story": (1080, 1920), "reel": (1080, 1920), "tiktok": (1080, 1920),
    "fb-story": (1080, 1920), "story": (1080, 1920),
    "li-landscape": (1200, 628), "fb-feed": (1200, 630), "li-square": (1200, 1200),
    "x-feed": (1200, 675), "twitter": (1200, 675), "pin": (1000, 1500),
    "square": (1080, 1080),
}
RATIO_SIZES = {
    (1, 1): (1080, 1080), (9, 16): (1080, 1920), (4, 5): (1080, 1350),
    (16, 9): (1200, 675), (2, 3): (1000, 1500),
}


def parse_target(tok: str):
    """Return (name, (W, H)) for a preset name, WxH, or W:H ratio token."""
    t = tok.strip().lower()
    if t in PRESETS:
        return t, PRESETS[t]
    if "x" in t and t.replace("x", "").isdigit():
        w, h = t.split("x")
        return f"{w}x{h}", (int(w), int(h))
    if ":" in t:
        a, b = t.split(":")
        rw, rh = float(a), float(b)
        key = (int(rw), int(rh)) if rw.is_integer() and rh.is_integer() else None
        if key in RATIO_SIZES:
            return t.replace(":", "x"), RATIO_SIZES[key]
        # derive a canonical size on a 1080/1200 base
        if rw <= rh:
            W = 1080; H = round(W * rh / rw)
        else:
            H = 675; W = round(H * rw / rh)
        return t.replace(":", "x"), (W, H)
    raise SystemExit(f"unknown target: {tok}")


def _border_color(img: "Image.Image"):
    im = img.convert("RGB")
    px = im.load()
    w, h = im.size
    step = max(1, w // 60)
    cols = [px[x, 0] for x in range(0, w, step)] + [px[x, h - 1] for x in range(0, w, step)]
    step = max(1, h // 60)
    cols += [px[0, y] for y in range(0, h, step)] + [px[w - 1, y] for y in range(0, h, step)]
    n = len(cols)
    return tuple(sum(c[i] for c in cols) // n for i in range(3))


def _backdrop(img, W, H, fill):
    if fill == "blur":
        scale = max(W / img.width, H / img.height)
        big = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        left = (big.width - W) // 2
        top = (big.height - H) // 2
        bg = big.crop((left, top, left + W, top + H)).convert("RGB")
        bg = bg.filter(ImageFilter.GaussianBlur(radius=max(12, int(max(W, H) * 0.035))))
        # gentle darken so the foreground pops
        return Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.10)
    if fill == "auto":
        return Image.new("RGB", (W, H), _border_color(img))
    color = fill if fill.startswith("#") else "#" + fill
    return Image.new("RGB", (W, H), color)


def reframe(img, W, H, fit="contain", fill="blur"):
    img = img.convert("RGB")
    if fit == "cover":
        scale = max(W / img.width, H / img.height)
        scaled = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        left = (scaled.width - W) // 2
        top = (scaled.height - H) // 2
        return scaled.crop((left, top, left + W, top + H))
    # contain
    scale = min(W / img.width, H / img.height)
    scaled = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas = _backdrop(img, W, H, fill)
    canvas.paste(scaled, ((W - scaled.width) // 2, (H - scaled.height) // 2))
    return canvas


def _save_pdf(images, path, dpi=96):
    first, rest = images[0], images[1:]
    first.save(path, "PDF", save_all=True, append_images=rest, resolution=float(dpi))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="*", help="PNG file(s)/glob (page order) if not --from-dir")
    ap.add_argument("--from-dir", help="a render outdir containing sizes.json")
    ap.add_argument("--targets", required=True, help="comma list of presets / WxH / W:H")
    ap.add_argument("--outdir", help="base output dir (default: <from-dir>/variants or ./variants)")
    ap.add_argument("--fit", choices=["contain", "cover"], default="contain")
    ap.add_argument("--fill", default="blur", help="blur | auto | #RRGGBB (default blur)")
    ap.add_argument("--pdf", action="store_true", help="also assemble a PDF per target")
    ap.add_argument("--pdf-name", default="carousel.pdf")
    args = ap.parse_args()

    if args.from_dir:
        sj = os.path.join(args.from_dir, "sizes.json")
        order = json.load(open(sj))
        files = [os.path.join(args.from_dir, s["file"]) for s in order]
        base_out = args.outdir or os.path.join(args.from_dir, "variants")
    else:
        files = []
        for pat in args.images:
            files.extend(sorted(glob.glob(pat)) if any(c in pat for c in "*?[") else [pat])
        base_out = args.outdir or "variants"
    if not files:
        sys.exit("no input images")

    targets = [parse_target(t) for t in args.targets.split(",") if t.strip()]
    srcs = [Image.open(f) for f in files]

    for name, (W, H) in targets:
        odir = os.path.join(base_out, name)
        os.makedirs(odir, exist_ok=True)
        out_imgs = []
        for i, im in enumerate(srcs):
            out = reframe(im, W, H, fit=args.fit, fill=args.fill)
            fn = os.path.join(odir, f"slide-{i + 1:02d}.png")
            out.save(fn)
            out_imgs.append(out)
        line = f"  {name:>12}  {W}x{H}  x{len(out_imgs)}"
        if args.pdf:
            pdf = os.path.join(odir, args.pdf_name)
            _save_pdf(out_imgs, pdf)
            line += f"  + {os.path.basename(pdf)}"
        print(line)

    print(f"DONE -> {base_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
