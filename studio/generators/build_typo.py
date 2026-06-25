import sys; sys.path.insert(0,"videos/edit/brand")
from kit import *
def expo(t):
    t=max(0.0,min(1.0,t)); return 1.0 if t>=1 else 1-2**(-10*t)
def eob(t,s=1.5):
    t=max(0.0,min(1.0,t)); 
    if t>=1: return 1.0
    t-=1; return 1+(s+1)*t**3+s*t**2

def fit_font(word, target_w=480, hi=180):
    s=hi
    while s>40:
        f=F(s,700)
        if tw(word,f)<=target_w: return f,s
        s-=4
    return F(40,700),40

def glyph_tile(ch,font,pad=18):
    w=int(tw(ch,font))+2*pad; top,ih=vbox(ch,font); h=ih+2*pad
    im=Image.new("RGBA",(max(w,2),max(h,2)),(0,0,0,0)); d=ImageDraw.Draw(im)
    # soft shadow
    sh=Image.new("RGBA",im.size,(0,0,0,0)); ds=ImageDraw.Draw(sh)
    ds.text((pad,pad-top),ch,font=font,fill=(0,42,102,150))
    sh=sh.filter(__import__("PIL.ImageFilter",fromlist=["ImageFilter"]).GaussianBlur(5))
    im=Image.alpha_composite(im,sh)
    d=ImageDraw.Draw(im)
    d.text((pad,pad-top),ch,font=font,fill=ACCENT+(255,),stroke_width=4,stroke_fill=(255,255,255,255))
    return im

def build(word, outdir, T=2.4, right=W-70, topy=92, stagger=0.045):
    import os; os.makedirs(outdir,exist_ok=True)
    f,sz=fit_font(word)
    # x positions (right-aligned block), using advance widths
    advs=[tw(c,f) for c in word]; total=sum(advs)
    xs=[]; x=right-total
    for a in advs: xs.append(x); x+=a
    tiles=[glyph_tile(c,f) for c in word]
    n_in=len(word)*stagger+0.5
    hold_end=n_in+1.0
    N=int(T*FPS)
    for fr in range(N):
        t=fr/FPS
        canvas=Image.new("RGBA",(W,H),(0,0,0,0))
        out_a=expo((t-hold_end)/0.35) if t>hold_end else 0.0
        for i,(c,tile) in enumerate(zip(word,tiles)):
            if t<=hold_end:
                p=eob((t-i*stagger)/0.5); a=max(0.0,min(1.0,(t-i*stagger)/0.32)); dy=-46*(1-p)
            else:
                a=1-out_a; dy=-34*out_a
            if a<=0: continue
            # tile internal pad=18; place so glyph ink-top near topy
            canvas=over(canvas,tile,xs[i]-18,topy-18+dy,a)
        canvas.save(f"{outdir}/{fr:04d}.png")
    return N,sz

n,sz=build("FAST.","videos/edit/brand/typo_FAST"); print("FAST",n,sz)
n,sz=build("RELIABLE.","videos/edit/brand/typo_REL",T=2.2); print("RELIABLE",n,sz)
