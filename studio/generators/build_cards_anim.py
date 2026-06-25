import sys; sys.path.insert(0,"videos/edit/brand")
from kit import *
def expo(t):
    t=max(0.0,min(1.0,t)); return 1.0 if t>=1 else 1-2**(-10*t)

def tile_text(text,font,fill,tr=0):
    w=int(tw(text,font,tr))+6; top,ih=vbox(text,font); h=ih+6
    im=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(im)
    if tr:
        x=3
        for c in text: d.text((x,3-top),c,font=font,fill=fill+(255,)); x+=d.textlength(c,font=font)+tr
    else:
        d.text((3,3-top),text,font=font,fill=fill+(255,))
    return im

def tile_line(w,h,fill):
    im=Image.new("RGBA",(w+2,h+2),(0,0,0,0)); ImageDraw.Draw(im).rounded_rectangle([1,1,w,h],radius=h//2,fill=fill+(255,)); return im

def build_card(rows, padx=64, pady=52, radius=16):
    tiles=[r["tile"] for r in rows]
    contentw=max(t.width for t in tiles); cardw=contentw+2*padx
    total=sum(t.height for t in tiles)+sum(r.get("gap",0) for r in rows)
    cardh=int(total+2*pady)
    bg=Image.new("RGBA",(cardw,cardh),(0,0,0,0))
    ImageDraw.Draw(bg).rounded_rectangle([0,0,cardw-1,cardh-1],radius=radius,fill=WHITE+(255,))
    els=[]; cx=cardw/2; y=pady
    for r in rows:
        t=r["tile"]; els.append((t,int(cx-t.width/2),int(y))); y+=t.height+r.get("gap",0)
    return cardw,cardh,bg,els

def render_seq(rows,bg_color,outdir,T=3.0):
    cardw,cardh,bg,els=build_card(rows)
    full_bg,pad=add_shadow(bg,color=(37,37,37,60),blur=12,dy=6)
    ox=int((W-cardw)/2-pad); oy=int((H-cardh)/2-pad)         # placement of shadowed bg
    cx0=int((W-cardw)/2); cy0=int((H-cardh)/2)               # placement of card content
    N=int(T*FPS)
    for f in range(N):
        t=f/FPS
        if t<2.6: obg=expo(t/0.45); outp=0.0
        else: outp=expo((t-2.6)/0.4); obg=1-outp
        canvas=Image.new("RGBA",(W,H),bg_color+(255,))
        # card bg + shadow (fades with obg)
        canvas=over(canvas,full_bg,ox,oy,obg)
        for i,(tile,ex,ey) in enumerate(els):
            if t<2.6:
                p=expo((t-i*0.08)/0.5); a=p; dy=14*(1-p)
            else:
                a=1-outp; dy=-6*outp
            canvas=over(canvas,tile,cx0+ex,cy0+ey+dy,a*0.999+ (0 if a<1 else 0.001))
        canvas.convert("RGB").save(f"{outdir}/{f:04d}.png")
    return N

# TITLE rows
trows=[
 {"tile":pill("OUR CLIENT",F(14,600),ACCENT,BG2),"gap":22},
 {"tile":tile_text("PNKSmart",F(40,700),TEXT),"gap":12},
 {"tile":tile_text("and Key Outcome",F(18,600),ACCENT),"gap":20},
 {"tile":tile_line(56,3,ACCENT),"gap":18},
 {"tile":tile_text("FROM BBCINCORP · SINGAPORE",F(14,600),MUTE,tr=3)},
]
n=render_seq(trows,BG1,"videos/edit/brand/title_seq"); print("title_seq",n)
# OUTRO rows
orows=[
 {"tile":pill("BBCINCORP SINGAPORE",F(14,600),ACCENT,BG2),"gap":24},
 {"tile":tile_text("Fast. Reliable.",F(40,700),TEXT),"gap":10},
 {"tile":tile_text("Done in 3 days.",F(40,700),ACCENT),"gap":20},
 {"tile":tile_line(56,3,AMBER),"gap":18},
 {"tile":tile_text("FAST · RELIABLE · DONE IN 3 DAYS",F(14,600),MUTE,tr=3)},
]
n=render_seq(orows,BG1,"videos/edit/brand/outro_seq"); print("outro_seq",n)
