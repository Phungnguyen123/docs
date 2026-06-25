from PIL import Image, ImageDraw, ImageFont, ImageFilter
# 1080p kit: every dimension/font auto-scales by S relative to the 720 design.
S = 1.5
import os
FD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".fonts", "poppins")
_M = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}
def F(s, w): return ImageFont.truetype(f"{FD}/Poppins-{_M[w]}.ttf", max(1, int(round(s * S))))
def hx(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
ACCENT, AMBER, TEXT, DARK, MUTE = hx("007eff"), hx("ffab00"), hx("333333"), hx("002a66"), hx("898989")
WHITE = (255, 255, 255); BG1 = hx("f4f9ff"); BG2 = hx("e4f2ff"); BG3 = hx("eaf1ff")
W, H = int(1280 * S), int(720 * S)   # 1920 x 1080
FPS = 24
def Q(v): return int(round(v * S))
_d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))

def tw(text, font, tr=0):
    w = _d.textlength(text, font=font)
    if tr and len(text) > 1: w += tr * S * (len(text) - 1)
    return w
def vbox(text, font):
    bb = _d.textbbox((0, 0), text, font=font); return bb[1], bb[3] - bb[1]

def put_center(draw, cx, y_ink_top, text, font, fill, tr=0):
    top, ih = vbox(text, font)
    if tr:
        trs = tr * S; total = tw(text, font, tr); x = cx - total / 2
        for c in text:
            draw.text((x, y_ink_top - top), c, font=font, fill=fill); x += draw.textlength(c, font=font) + trs
    else:
        x = cx - tw(text, font) / 2
        draw.text((x, y_ink_top - top), text, font=font, fill=fill)
    return ih

def pill(text, font, txt, bg, padx=16, pady=9):
    padx, pady = Q(padx), Q(pady)
    ih = vbox(text, font)[1]; w = int(tw(text, font)); Wp = w + 2 * padx; Hp = ih + 2 * pady
    im = Image.new("RGBA", (Wp, Hp), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, Wp - 1, Hp - 1], radius=Hp // 2, fill=bg + (255,))
    put_center(d, Wp / 2, pady, text, font, txt + (255,))
    return im

def add_shadow(card, color=(37, 37, 37, 64), blur=9, dx=0, dy=4, pad=46):
    blur, dx, dy, pad = Q(blur), Q(dx), Q(dy), Q(pad)
    w, h = card.size
    full = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", full.size, (0, 0, 0, 0))
    solid = Image.new("RGBA", (w, h), color)
    sh.paste(solid, (pad + dx, pad + dy), card.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    full = Image.alpha_composite(full, sh)
    full.alpha_composite(card, (pad, pad))
    return full, pad

def over(canvas, im, x, y, a=1.0):
    if a < 1.0:
        al = im.split()[3].point(lambda v: int(v * a)); im = im.copy(); im.putalpha(al)
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); tmp.paste(im, (int(round(x)), int(round(y))), im)
    return Image.alpha_composite(canvas, tmp)
