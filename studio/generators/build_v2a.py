import sys; sys.path.insert(0,"videos/edit/brand")
from kit import *
from PIL import ImageFilter
def expo(t):
    t=max(0.0,min(1.0,t)); return 1.0 if t>=1 else 1-2**(-10*t)

# ---------- TITLE card (LaunchStack story) ----------
def tile_text(text,font,fill,tr=0):
    w=int(tw(text,font,tr))+6; top,ih=vbox(text,font); h=ih+6
    im=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(im)
    if tr:
        x=3
        for c in text: d.text((x,3-top),c,font=font,fill=fill+(255,)); x+=d.textlength(c,font=font)+tr
    else: d.text((3,3-top),text,font=font,fill=fill+(255,))
    return im
def tile_line(w,h,fill):
    im=Image.new("RGBA",(w+2,h+2),(0,0,0,0)); ImageDraw.Draw(im).rounded_rectangle([1,1,w,h],radius=h//2,fill=fill+(255,)); return im
def build_card(rows,padx=64,pady=52,radius=16):
    tiles=[r["tile"] for r in rows]; contentw=max(t.width for t in tiles); cardw=contentw+2*padx
    total=sum(t.height for t in tiles)+sum(r.get("gap",0) for r in rows); cardh=int(total+2*pady)
    bg=Image.new("RGBA",(cardw,cardh),(0,0,0,0)); ImageDraw.Draw(bg).rounded_rectangle([0,0,cardw-1,cardh-1],radius=radius,fill=WHITE+(255,))
    els=[]; cx=cardw/2; y=pady
    for r in rows:
        t=r["tile"]; els.append((t,int(cx-t.width/2),int(y))); y+=t.height+r.get("gap",0)
    return cardw,cardh,bg,els
def render_seq(rows,bg_color,outdir,T=3.0):
    cardw,cardh,bg,els=build_card(rows); full_bg,pad=add_shadow(bg,color=(37,37,37,60),blur=12,dy=6)
    ox=int((W-cardw)/2-pad); oy=int((H-cardh)/2-pad); cx0=int((W-cardw)/2); cy0=int((H-cardh)/2)
    N=int(T*FPS)
    for f in range(N):
        t=f/FPS
        if t<2.6: obg=expo(t/0.45); outp=0.0
        else: outp=expo((t-2.6)/0.4); obg=1-outp
        canvas=Image.new("RGBA",(W,H),bg_color+(255,)); canvas=over(canvas,full_bg,ox,oy,obg)
        for i,(tile,ex,ey) in enumerate(els):
            if t<2.6: p=expo((t-i*0.08)/0.5); a=p; dy=14*(1-p)
            else: a=1-outp; dy=-6*outp
            canvas=over(canvas,tile,cx0+ex,cy0+ey+dy,a)
        canvas.convert("RGB").save(f"{outdir}/{f:04d}.png")
    return N
trows=[
 {"tile":pill("CLIENT STORY",F(14,600),ACCENT,BG2),"gap":22},
 {"tile":tile_text("LaunchStack",F(40,700),TEXT),"gap":12},
 {"tile":tile_text("Marcus Tan · Co-founder",F(18,600),ACCENT),"gap":20},
 {"tile":tile_line(56,3,ACCENT),"gap":18},
 {"tile":tile_text("INCORPORATED WITH BBCINCORP",F(14,600),MUTE,tr=3)},
]
print("title_seq",render_seq(trows,BG1,"videos/edit/brand/title_seq"))

# ---------- LOWER-THIRD frosted: Marcus Tan / Co-founder, LaunchStack ----------
def make_logo(letters="LS",sz=58):
    g=Image.new("RGBA",(sz,sz),(0,0,0,0)); px=g.load()
    for y in range(sz):
        f=y/(sz-1); r=int(ACCENT[0]+(AMBER[0]-ACCENT[0])*f); gg=int(ACCENT[1]+(AMBER[1]-ACCENT[1])*f); b=int(ACCENT[2]+(AMBER[2]-ACCENT[2])*f)
        for x in range(sz): px[x,y]=(r,gg,b,255)
    m=Image.new("L",(sz,sz),0); ImageDraw.Draw(m).rounded_rectangle([0,0,sz-1,sz-1],radius=14,fill=255); g.putalpha(m)
    fs=30
    while tw(letters,F(fs,700))>sz-16 and fs>14: fs-=2
    f=F(fs,700); d=ImageDraw.Draw(g); txw=tw(letters,f); top,ih=vbox(letters,f)
    d.text(((sz-txw)/2,(sz-ih)/2-top),letters,font=f,fill=WHITE+(255,))
    return g
def make_bar(w,h):
    b=Image.new("RGBA",(w,h),(0,0,0,0)); px=b.load()
    for y in range(h):
        f=y/(h-1); r=int(ACCENT[0]+(AMBER[0]-ACCENT[0])*f); gg=int(ACCENT[1]+(AMBER[1]-ACCENT[1])*f); bl=int(ACCENT[2]+(AMBER[2]-ACCENT[2])*f)
        for x in range(w): px[x,y]=(r,gg,bl,255)
    m=Image.new("L",(w,h),0); ImageDraw.Draw(m).rounded_rectangle([0,0,w-1,h-1],radius=w//2,fill=255); b.putalpha(m); return b
padx,pady=26,20; gap1=14; barw=6; gap2=18
fname=F(36,700); fsub=F(18,400); LOGO=make_logo("LS",58)
name="Marcus Tan"; sub="Co-founder, LaunchStack"
nw=tw(name,fname); _,nh=vbox(name,fname); sw=tw(sub,fsub); _,sh=vbox(sub,fsub)
textw=int(max(nw,sw)); inner_h=max(LOGO.height,int(nh+8+sh))
cw=int(padx+LOGO.width+gap1+barw+gap2+textw+padx); ch=int(inner_h+2*pady)
BAR=make_bar(barw,inner_h); TEXTX=padx+LOGO.width+gap1+barw+gap2
LOGOY=int((ch-LOGO.height)/2); BARY=int((ch-inner_h)/2); ny=int((ch-(nh+8+sh))/2)
TILE=Image.new("L",(cw,ch),0); ImageDraw.Draw(TILE).rounded_rectangle([0,0,cw-1,ch-1],radius=16,fill=255)
CX=70+cw/2; CY=H-70-ch/2
def render_content(barfrac,txtoff,txt_a):
    card=Image.new("RGBA",(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cw-1,ch-1],radius=16,fill=WHITE+(166,))
    card.alpha_composite(LOGO,(padx,LOGOY))
    bh=max(1,int(inner_h*barfrac)); card.alpha_composite(BAR.crop((0,0,barw,bh)),(padx+LOGO.width+gap1,BARY))
    tl=Image.new("RGBA",(cw,ch),(0,0,0,0)); dt=ImageDraw.Draw(tl); tn,_=vbox(name,fname); ts,_=vbox(sub,fsub)
    dt.text((TEXTX,ny-tn),name,font=fname,fill=(34,34,34,255)); dt.text((TEXTX,ny+nh+8-ts),sub,font=fsub,fill=(85,85,85,255))
    if txt_a<1.0: tl.putalpha(tl.split()[3].point(lambda v:int(v*txt_a)))
    tl2=Image.new("RGBA",(cw,ch),(0,0,0,0)); tl2.paste(tl,(int(-txtoff),0),tl); card.alpha_composite(tl2)
    return card
def state(t):
    if t<0.4: e=expo(t/0.4); O=e; s=0.85+0.15*e
    elif t<4.5: O=1.0; s=1.0
    else: e=expo((t-4.5)/0.25); O=max(0.0,1-e); s=1.0-0.10*e
    barfrac=max(0.0,min(1.0,(t-0.15)/0.2)); tp=expo((t-0.10)/0.35)
    return O,s,barfrac,20*(1-tp),tp
N=120
for i in range(N):
    t=i/24; O,s,barfrac,txtoff,txt_a=state(t)
    base=Image.open(f"videos/edit/brand/ltsrc/{i+1:04d}.png").convert("RGBA")
    blurred=base.filter(ImageFilter.GaussianBlur(14)); content=render_content(barfrac,txtoff,txt_a); shape=TILE
    if abs(s-1)>1e-3:
        content=content.resize((int(cw*s),int(ch*s)),Image.LANCZOS); shape=shape.resize((int(cw*s),int(ch*s)),Image.LANCZOS)
    cwh=content.size; pos=(int(CX-cwh[0]/2),int(CY-cwh[1]/2)); over_=Image.new("RGBA",(W,H),(0,0,0,0))
    shm=Image.new("L",(W,H),0); shm.paste(shape,(pos[0],pos[1]+6)); shm=shm.filter(ImageFilter.GaussianBlur(12)); shm=shm.point(lambda v:int(v*0.30*O))
    shl=Image.new("RGBA",(W,H),(37,37,37,255)); shl.putalpha(shm); over_=Image.alpha_composite(over_,shl)
    bdmask=Image.new("L",(W,H),0); bdmask.paste(shape,pos); bdmask=bdmask.point(lambda v:int(v*O)); bd=blurred.copy(); bd.putalpha(bdmask); over_=Image.alpha_composite(over_,bd)
    cl=Image.new("RGBA",(W,H),(0,0,0,0)); cl.paste(content,pos,content)
    if O<1.0: cl.putalpha(cl.split()[3].point(lambda v:int(v*O)))
    over_=Image.alpha_composite(over_,cl); over_.save(f"videos/edit/brand/lt2/{i:04d}.png")
print("lt2",N,"card",(cw,ch))
