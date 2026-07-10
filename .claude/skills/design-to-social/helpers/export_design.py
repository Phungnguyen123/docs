#!/usr/bin/env python3
"""
export_design.py — one command: Claude Design HTML -> PNG(s) + PDF.

Pipeline:
    selfcontain.py   (unwrap .dc runtime, embed webfonts)
      -> render.cjs  (screenshot each slide at native px x --scale)
      -> topdf.py    (assemble the PNGs into a multi-page PDF)

Assets: any `assets/...` referenced by the HTML must sit next to the INPUT file
(fetch them from the design project first — see the skill's SKILL.md). They are read
from disk during rendering.

Usage:
    python export_design.py INPUT.html --outdir OUT \
        [--formats png,pdf] [--scale 2] [--pdf-name carousel.pdf] [--no-selfcontain]

Outputs in OUT/:
    <name>.standalone.html   the self-contained page (fonts embedded)
    slide-01.png, slide-02.png, ...   one per detected slide, at native px x scale
    sizes.json               slide dimensions + labels
    <pdf-name>               multi-page PDF (only if 'pdf' in --formats)
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print("  $ " + " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="input HTML (.dc.html or exported carousel)")
    ap.add_argument("--outdir", default="export", help="output directory (default: export)")
    ap.add_argument("--formats", default="png,pdf", help="comma list: png,pdf (default both)")
    ap.add_argument("--scale", type=float, default=2.0, help="pixel scale for PNGs (default 2)")
    ap.add_argument("--selector", help="CSS selector for slides (auto-detected if omitted)")
    ap.add_argument("--pdf-name", default="carousel.pdf", help="PDF filename (default carousel.pdf)")
    ap.add_argument("--dpi", type=int, default=96, help="PDF resolution hint (default 96)")
    ap.add_argument("--targets", help="also emit resized variants: comma list of presets / "
                    "WxH / W:H (e.g. ig-square,ig-story,1:1,9:16). Written to <outdir>/variants/")
    ap.add_argument("--fit", choices=["contain", "cover"], default="contain",
                    help="how variants re-frame the design (default contain = never crop)")
    ap.add_argument("--fill", default="blur", help="variant backdrop: blur | auto | #RRGGBB")
    ap.add_argument("--no-selfcontain", action="store_true",
                    help="skip the unwrap/font-embed step (input is already standalone)")
    args = ap.parse_args()

    formats = {f.strip().lower() for f in args.formats.split(",") if f.strip()}
    os.makedirs(args.outdir, exist_ok=True)

    # copy an adjacent assets/ folder so relative refs resolve during render
    src_assets = os.path.join(os.path.dirname(os.path.abspath(args.input)), "assets")
    if os.path.isdir(src_assets):
        dst_assets = os.path.join(args.outdir, "assets")
        if os.path.abspath(src_assets) != os.path.abspath(dst_assets):
            shutil.copytree(src_assets, dst_assets, dirs_exist_ok=True)
            print(f"  copied assets/ -> {dst_assets}")

    # 1) self-contain
    name = os.path.splitext(os.path.basename(args.input))[0]
    if name.endswith(".dc"):
        name = name[:-3]
    standalone = os.path.join(args.outdir, name + ".standalone.html")
    if args.no_selfcontain:
        shutil.copy(args.input, standalone)
    else:
        print("[1/3] self-contain (unwrap + embed fonts)")
        run([sys.executable, os.path.join(HERE, "selfcontain.py"), args.input, "-o", standalone])

    # 2) render PNGs
    print("[2/3] render slides")
    render = [_node(), os.path.join(HERE, "render.cjs"), standalone,
              "--outdir", args.outdir, "--scale", str(args.scale)]
    if args.selector:
        render += ["--selector", args.selector]
    run(render)

    # 3) PDF
    if "pdf" in formats:
        print("[3/3] assemble PDF")
        pdf_path = os.path.join(args.outdir, args.pdf_name)
        run([sys.executable, os.path.join(HERE, "topdf.py"),
             "--from-sizes", args.outdir, "-o", pdf_path, "--dpi", str(args.dpi)])

    # 4) resized variants (other social sizes/ratios) — done from the native PNGs
    if args.targets:
        print("[4] resize variants:", args.targets)
        variants = [sys.executable, os.path.join(HERE, "resize_variants.py"),
                    "--from-dir", args.outdir, "--targets", args.targets,
                    "--fit", args.fit, "--fill", args.fill]
        if "pdf" in formats:
            variants += ["--pdf", "--pdf-name", args.pdf_name]
        run(variants)

    if "png" not in formats:
        for f in os.listdir(args.outdir):
            if f.startswith("slide-") and f.endswith(".png"):
                os.remove(os.path.join(args.outdir, f))

    print("\nDONE ->", args.outdir)
    return 0


def _node():
    return shutil.which("node") or "node"


if __name__ == "__main__":
    raise SystemExit(main())
