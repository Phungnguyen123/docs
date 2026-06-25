#!/usr/bin/env python3
# Portrait (720x1280) overlay track for the BBCIncorp affiliate UGC clip.
# Renders one full-canvas RGBA PNG sequence with every motion-graphics element
# baked in, synced to the Vietnamese voiceover timeline. Composited in one ffmpeg pass.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import hx, ACCENT, AMBER, DARK, WHITE
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Be Vietnam Pro — full Vietnamese glyph coverage (kit's Poppins lacks stacked diacritics)
_BVP = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".fonts", "bevietnampro")
_WMAP = {500: "Medium", 600: "SemiBold", 700: "Bold", 800: "Black", 900: "Black"}
_FCACHE = {}
def F(size, weight):
    key = (size, weight)
    if key not in _FCACHE:
        _FCACHE[key] = ImageFont.truetype(f"{_BVP}/BeVietnamPro-{_WMAP[weight]}.ttf", size)
    return _FCACHE[key]
_DR = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
def tw(text, font): return _DR.textlength(text, font=font)
def vbox(text, font):
    bb = _DR.textbbox((0, 0), text, font=font); return bb[1], bb[3] - bb[1]

W, H, FPS = 720, 1280, 24
DUR = 10.041667
N = round(DUR * FPS)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "overlays_portrait", "track")
os.makedirs(OUT, exist_ok=True)

NAVY = DARK            # #002a66
BLUE = ACCENT          # #007eff
GOLD = AMBER           # #ffab00

# ---------- easing ----------
def cl(t): return max(0.0, min(1.0, t))
def expo(t):
    t = cl(t); return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)
def eob(t, s=1.70):
    t = cl(t)
    if t >= 1: return 1.0
    t -= 1; return 1 + (s + 1) * t ** 3 + s * t ** 2
def eoc(t): t = cl(t); return 1 - (1 - t) ** 3

# window helper: returns (alpha, scale, prog) for an element shown in [t0,t1]
def win(t, t0, t1, tin=0.22, tout=0.30, pop=True):
    if t < t0 or t > t1: return None
    if t < t0 + tin:
        k = (t - t0) / tin
        a = expo(k); s = eob(k) if pop else (0.96 + 0.04 * a)
    elif t > t1 - tout:
        k = (t - (t1 - tout)) / tout
        o = expo(k); a = 1 - o; s = 1.0 - 0.10 * o
    else:
        a = 1.0; s = 1.0
    return a, s, cl((t - t0) / (t1 - t0))

def paste_center(canvas, im, cx, cy, a=1.0):
    if a < 1.0:
        al = im.split()[3].point(lambda v: int(v * a)); im = im.copy(); im.putalpha(al)
    x = int(round(cx - im.width / 2)); y = int(round(cy - im.height / 2))
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); tmp.paste(im, (x, y), im)
    return Image.alpha_composite(canvas, tmp)

def scaled(im, s):
    if abs(s - 1) < 1e-3: return im
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)

def shadow(card, blur=14, dy=7, op=0.30, color=(0, 30, 80)):
    pad = blur * 3
    full = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", full.size, (0, 0, 0, 0))
    solid = Image.new("RGBA", card.size, color + (255,))
    sh.paste(solid, (pad, pad + dy), card.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh = Image.alpha_composite(Image.new("RGBA", full.size, (0, 0, 0, 0)),
                               Image.eval(sh, lambda v: v))
    a = sh.split()[3].point(lambda v: int(v * op)); sh.putalpha(a)
    full = Image.alpha_composite(full, sh)
    full.alpha_composite(card, (pad, pad))
    return full

def coin(sz, fs):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, sz - 1, sz - 1], fill=GOLD + (255,))
    d.ellipse([3, 3, sz - 4, sz - 4], outline=(255, 255, 255, 150), width=2)
    f = F(fs, 700); t, ih = vbox("$", f); w = tw("$", f)
    d.text((sz / 2 - w / 2, sz / 2 - ih / 2 - t), "$", font=f, fill=NAVY + (255,))
    return im

# ---------- elements ----------
def logo_pill():
    f1 = F(30, 700); f2 = F(30, 600)
    s1, s2 = "BBC", "Incorp"
    w1, w2 = tw(s1, f1), tw(s2, f2)
    padx, pady = 22, 13; gap = 0
    th = vbox(s1, f1)[1]
    cw = int(padx * 2 + w1 + w2); ch = int(th + pady * 2)
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=ch // 2, fill=(255, 255, 255, 230))
    t1 = vbox(s1, f1)[0]; t2 = vbox(s2, f2)[0]
    d.text((padx, pady - t1), s1, font=f1, fill=BLUE + (255,))
    d.text((padx + w1, pady - t2), s2, font=f2, fill=NAVY + (255,))
    return shadow(card, blur=10, dy=4, op=0.22)

def chip(text, fs=40):
    f = F(fs, 800); padx, pady = 30, 18; cz = int(fs * 1.15); gap = 16
    tw_, th = tw(text, f), vbox(text, f)[1]
    ci = coin(cz, int(fs * 0.72))
    cw = int(padx * 2 + cz + gap + tw_); ch = int(max(cz, th) + pady * 2)
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=ch // 2, fill=NAVY + (255,))
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=ch // 2, outline=GOLD + (255,), width=3)
    card.alpha_composite(ci, (padx, (ch - cz) // 2))
    tt = vbox(text, f)[0]
    d.text((padx + cz + gap, ch / 2 - th / 2 - tt), text, font=f, fill=WHITE + (255,))
    return shadow(card, blur=16, dy=8, op=0.34)

def stat_card(num):
    cw, ch = 430, 300
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=28, fill=(255, 255, 255, 240))
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=28, outline=hx("e4f2ff") + (255,), width=3)
    # top label
    fl = F(24, 600); lab = "HOA HỒNG MỖI KHÁCH"
    tl = vbox(lab, fl)[0]; d.text((cw / 2 - tw(lab, fl) / 2, 34 - tl), lab, font=fl, fill=BLUE + (255,))
    # big number
    s = f"${num}"
    fn = F(140, 800); tnum, nh = vbox(s, fn)
    d.text((cw / 2 - tw(s, fn) / 2, 150 - nh / 2 - tnum), s, font=fn, fill=GOLD + (255,))
    # sub
    fs = F(30, 600); sub = "cho mỗi đơn thành công"
    ts = vbox(sub, fs)[0]; d.text((cw / 2 - tw(sub, fs) / 2, 234 - ts), sub, font=fs, fill=NAVY + (255,))
    return shadow(card, blur=22, dy=10, op=0.30)

def cta_card():
    cw, ch = 560, 250
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=30, fill=NAVY + (255,))
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=30, outline=GOLD + (255,), width=3)
    f1 = F(38, 800); l1 = "ĐĂNG KÝ AFFILIATE"
    t1 = vbox(l1, f1)[0]; d.text((cw / 2 - tw(l1, f1) / 2, 52 - t1), l1, font=f1, fill=WHITE + (255,))
    f2 = F(26, 500); l2 = "Giới thiệu là có tiền"
    t2 = vbox(l2, f2)[0]; d.text((cw / 2 - tw(l2, f2) / 2, 104 - t2), l2, font=f2, fill=hx("9fd0ff") + (255,))
    # website pill
    fw = F(34, 700); site = "bbcincorp.com"
    pw = int(tw(site, fw) + 56); ph = 64; px = (cw - pw) // 2; py = 150
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph // 2, fill=GOLD + (255,))
    tt = vbox(site, fw)[0]
    d.text((cw / 2 - tw(site, fw) / 2, py + ph / 2 - vbox(site, fw)[1] / 2 - tt), site, font=fw, fill=NAVY + (255,))
    return shadow(card, blur=20, dy=10, op=0.34)

def caption(text, hl=None, fs=50):
    # white bold text, navy stroke + drop shadow; highlight token drawn gold.
    f = F(fs, 700)
    parts = []  # (substr, color)
    if hl and hl in text:
        i = text.index(hl)
        if text[:i]: parts.append((text[:i], WHITE))
        parts.append((hl, GOLD))
        if text[i + len(hl):]: parts.append((text[i + len(hl):], WHITE))
    else:
        parts.append((text, WHITE))
    total = sum(tw(s, f) for s, _ in parts)
    th = vbox(text, f)[1]; tt = vbox(text, f)[0]
    pad = 24
    card = Image.new("RGBA", (int(total + pad * 2), int(th + pad * 2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    x = pad
    for s, col in parts:
        d.text((x, pad - tt), s, font=f, fill=col + (255,),
               stroke_width=7, stroke_fill=NAVY + (255,))
        x += tw(s, f)
    return shadow(card, blur=10, dy=5, op=0.40, color=(0, 0, 0))

# pre-render static pieces
LOGO = logo_pill()
HOOK = chip("KIẾM TIỀN KHÔNG CẦN VỐN", 38)
CTA = cta_card()
CAPS = {
    "c1": (caption("Giới thiệu khách"),                       0.50, 1.90),
    "c2": (caption("mở công ty cho BBCIncorp", "BBCIncorp"),  1.90, 3.95),
    "c3": (caption("Mỗi đơn thành công"),                     4.05, 5.40),
    "c4": (caption("nhận ngay 50 đô!", "50 đô"),              5.40, 7.15),
}
STAT_CACHE = {}
def stat(num):
    if num not in STAT_CACHE: STAT_CACHE[num] = stat_card(num)
    return STAT_CACHE[num]

# bottom scrim for caption legibility
def scrim():
    sc = Image.new("RGBA", (W, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(sc)
    for i in range(300):
        a = int(120 * (i / 300) ** 1.4)
        d.line([(0, i), (W, i)], fill=(0, 12, 36, a))
    return sc
SCRIM = scrim()

# ---------- per-frame ----------
for fr in range(N):
    t = fr / FPS
    cv = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # bottom scrim (fades with caption activity 0.4-7.3)
    sa = 0.0
    if 0.4 <= t <= 7.3:
        sa = expo((t - 0.4) / 0.4) if t < 0.8 else (1 - expo((t - 6.9) / 0.4) if t > 6.9 else 1.0)
    if sa > 0.01:
        cv = paste_center(cv, SCRIM, W / 2, H - 150, 0.85 * sa)

    # logo bug top-left (0.3 -> end)
    lw = win(t, 0.30, DUR, tin=0.4, tout=0.2)
    if lw:
        a, s, _ = lw
        im = scaled(LOGO, s)
        x = 40 + im.width / 2; y = 70 + im.height / 2
        cv = paste_center(cv, im, x, y, a)

    # hook chip top-center (0.35 -> 4.1)
    hw = win(t, 0.35, 4.10, tin=0.26, tout=0.30)
    if hw:
        a, s, _ = hw
        cv = paste_center(cv, scaled(HOOK, s), W / 2, 215, a)

    # captions bottom
    for key, (img, t0, t1) in CAPS.items():
        cw_ = win(t, t0, t1, tin=0.16, tout=0.18)
        if cw_:
            a, s, _ = cw_
            cv = paste_center(cv, scaled(img, s), W / 2, H - 215, a)

    # center $50 stat (5.0 -> 7.45) with count-up
    sw = win(t, 5.00, 7.45, tin=0.26, tout=0.30)
    if sw:
        a, s, prog = sw
        val = int(round(50 * eoc((t - 5.10) / 0.85)))
        val = max(0, min(50, val))
        cv = paste_center(cv, scaled(stat(val), s), W / 2, 590, a)

    # CTA end card (7.30 -> end) rises in
    cw2 = win(t, 7.30, DUR, tin=0.34, tout=0.15, pop=False)
    if cw2:
        a, s, _ = cw2
        rise = (1 - expo(cl((t - 7.30) / 0.34))) * 40
        im = scaled(CTA, s)
        cv = paste_center(cv, im, W / 2, 720 + rise, a)

    cv.save(f"{OUT}/{fr:04d}.png")

print("frames:", N, "->", OUT)
