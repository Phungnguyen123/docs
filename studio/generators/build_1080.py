import sys, math; sys.path.insert(0,"videos/edit/brand")
from kit1080 import *
from PIL import ImageFilter
def expo(t): t=max(0.0,min(1.0,t)); return 1.0 if t>=1 else 1-2**(-10*t)
def eob(t,s=1.7):
    t=max(0.0,min(1.0,t))
    if t>=1: return 1.0
    t-=1; return 1+(s+1)*t**3+s*t**2
def lerp(a,b,p): return tuple(int(a[i]+(b[i]-a[i])*p) for i in range(3))
def draw_check(d,cx,cy,r,col):
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=col+(255,))
    d.line([(cx-r*0.42,cy+r*0.02),(cx-r*0.10,cy+r*0.36),(cx+r*0.46,cy-r*0.34)],fill=WHITE+(255,),width=max(2,int(r*0.22)),joint="curve")

# ===== TITLE / OUTRO =====
def tile_text(text,font,fill,tr=0):
    w=int(tw(text,font,tr))+Q(6); top,ih=vbox(text,font); h=ih+Q(6)
    im=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(im); pad=Q(3)
    if tr:
        x=pad; trs=tr*S
        for c in text: d.text((x,pad-top),c,font=font,fill=fill+(255,)); x+=d.textlength(c,font=font)+trs
    else: d.text((pad,pad-top),text,font=font,fill=fill+(255,))
    return im
def tile_line(w,h,fill):
    im=Image.new("RGBA",(w+2,h+2),(0,0,0,0)); ImageDraw.Draw(im).rounded_rectangle([1,1,w,h],radius=h//2,fill=fill+(255,)); return im
def build_card(rows,padx,pady,radius):
    tiles=[r["tile"] for r in rows]; contentw=max(t.width for t in tiles); cardw=contentw+2*padx
    total=sum(t.height for t in tiles)+sum(r.get("gap",0) for r in rows); cardh=int(total+2*pady)
    bg=Image.new("RGBA",(cardw,cardh),(0,0,0,0)); ImageDraw.Draw(bg).rounded_rectangle([0,0,cardw-1,cardh-1],radius=radius,fill=WHITE+(255,))
    els=[]; cx=cardw/2; y=pady
    for r in rows:
        t=r["tile"]; els.append((t,int(cx-t.width/2),int(y))); y+=t.height+r.get("gap",0)
    return cardw,cardh,bg,els
def render_seq(rows,bg_color,outdir,T=3.0):
    cardw,cardh,bg,els=build_card(rows,Q(64),Q(52),Q(16)); full_bg,pad=add_shadow(bg,color=(37,37,37,60),blur=12,dy=6)
    ox=int((W-cardw)/2-pad); oy=int((H-cardh)/2-pad); cx0=int((W-cardw)/2); cy0=int((H-cardh)/2)
    N=int(T*FPS)
    for f in range(N):
        t=f/FPS
        if t<2.6: obg=expo(t/0.45); outp=0.0
        else: outp=expo((t-2.6)/0.4); obg=1-outp
        canvas=Image.new("RGBA",(W,H),bg_color+(255,)); canvas=over(canvas,full_bg,ox,oy,obg)
        for i,(tile,ex,ey) in enumerate(els):
            if t<2.6: p=expo((t-i*0.08)/0.5); a=p; dy=Q(14)*(1-p)
            else: a=1-outp; dy=-Q(6)*outp
            canvas=over(canvas,tile,cx0+ex,cy0+ey+dy,a)
        canvas.convert("RGB").save(f"{outdir}/{f:04d}.png")
    return N
trows=[
 {"tile":pill("CLIENT STORY",F(14,600),ACCENT,BG2),"gap":Q(22)},
 {"tile":tile_text("LaunchStack",F(40,700),TEXT),"gap":Q(12)},
 {"tile":tile_text("Marcus Tan · Co-founder",F(18,600),ACCENT),"gap":Q(20)},
 {"tile":tile_line(Q(56),Q(3),ACCENT),"gap":Q(18)},
 {"tile":tile_text("INCORPORATED WITH BBCINCORP",F(14,600),MUTE,tr=3)},
]
print("title",render_seq(trows,BG1,"videos/edit/brand/title_seq"))
orows=[
 {"tile":pill("BBCINCORP SINGAPORE",F(14,600),ACCENT,BG2),"gap":Q(24)},
 {"tile":tile_text("Fast. Reliable.",F(40,700),TEXT),"gap":Q(10)},
 {"tile":tile_text("Done in 3 days.",F(40,700),ACCENT),"gap":Q(20)},
 {"tile":tile_line(Q(56),Q(3),AMBER),"gap":Q(18)},
 {"tile":tile_text("FAST · RELIABLE · DONE IN 3 DAYS",F(14,600),MUTE,tr=3)},
]
print("outro",render_seq(orows,BG1,"videos/edit/brand/outro_seq"))

# ===== LOWER-THIRD frosted =====
def make_logo(letters,sz):
    g=Image.new("RGBA",(sz,sz),(0,0,0,0)); px=g.load()
    for y in range(sz):
        f=y/(sz-1); c=lerp(ACCENT,AMBER,f)
        for x in range(sz): px[x,y]=(c[0],c[1],c[2],255)
    m=Image.new("L",(sz,sz),0); ImageDraw.Draw(m).rounded_rectangle([0,0,sz-1,sz-1],radius=Q(14),fill=255); g.putalpha(m)
    fs=30
    while tw(letters,F(fs,700))>sz-Q(16) and fs>14: fs-=2
    f=F(fs,700); d=ImageDraw.Draw(g); txw=tw(letters,f); top,ih=vbox(letters,f)
    d.text(((sz-txw)/2,(sz-ih)/2-top),letters,font=f,fill=WHITE+(255,)); return g
def make_bar(w,h):
    b=Image.new("RGBA",(w,h),(0,0,0,0)); px=b.load()
    for y in range(h):
        f=y/(h-1); c=lerp(ACCENT,AMBER,f)
        for x in range(w): px[x,y]=(c[0],c[1],c[2],255)
    m=Image.new("L",(w,h),0); ImageDraw.Draw(m).rounded_rectangle([0,0,w-1,h-1],radius=w//2,fill=255); b.putalpha(m); return b
padx,pady=Q(26),Q(20); gap1=Q(14); barw=Q(6); gap2=Q(18)
fname=F(36,700); fsub=F(18,400); LOGO=make_logo("LS",Q(58))
name="Marcus Tan"; sub="Co-founder, LaunchStack"
nw=tw(name,fname); _,nh=vbox(name,fname); sw=tw(sub,fsub); _,sh=vbox(sub,fsub)
textw=int(max(nw,sw)); inner_h=max(LOGO.height,int(nh+Q(8)+sh))
cw=int(padx+LOGO.width+gap1+barw+gap2+textw+padx); ch=int(inner_h+2*pady)
BAR=make_bar(barw,inner_h); TEXTX=padx+LOGO.width+gap1+barw+gap2
LOGOY=int((ch-LOGO.height)/2); BARY=int((ch-inner_h)/2); ny=int((ch-(nh+Q(8)+sh))/2)
TILE=Image.new("L",(cw,ch),0); ImageDraw.Draw(TILE).rounded_rectangle([0,0,cw-1,ch-1],radius=Q(16),fill=255)
CX=Q(70)+cw/2; CY=H-Q(70)-ch/2
def render_content(barfrac,txtoff,txt_a):
    card=Image.new("RGBA",(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cw-1,ch-1],radius=Q(16),fill=WHITE+(166,))
    card.alpha_composite(LOGO,(padx,LOGOY))
    bh=max(1,int(inner_h*barfrac)); card.alpha_composite(BAR.crop((0,0,barw,bh)),(padx+LOGO.width+gap1,BARY))
    tl=Image.new("RGBA",(cw,ch),(0,0,0,0)); dt=ImageDraw.Draw(tl); tn,_=vbox(name,fname); ts,_=vbox(sub,fsub)
    dt.text((TEXTX,ny-tn),name,font=fname,fill=(34,34,34,255)); dt.text((TEXTX,ny+nh+Q(8)-ts),sub,font=fsub,fill=(85,85,85,255))
    if txt_a<1.0: tl.putalpha(tl.split()[3].point(lambda v:int(v*txt_a)))
    tl2=Image.new("RGBA",(cw,ch),(0,0,0,0)); tl2.paste(tl,(int(-txtoff),0),tl); card.alpha_composite(tl2)
    return card
def lstate(t):
    if t<0.4: e=expo(t/0.4); O=e; s=0.85+0.15*e
    elif t<4.5: O=1.0; s=1.0
    else: e=expo((t-4.5)/0.25); O=max(0.0,1-e); s=1.0-0.10*e
    barfrac=max(0.0,min(1.0,(t-0.15)/0.2)); tp=expo((t-0.10)/0.35)
    return O,s,barfrac,Q(20)*(1-tp),tp
for i in range(120):
    t=i/24; O,s,barfrac,txtoff,txt_a=lstate(t)
    base=Image.open(f"videos/edit/brand/ltsrc1080/{i+1:04d}.png").convert("RGBA")
    blurred=base.filter(ImageFilter.GaussianBlur(Q(14))); content=render_content(barfrac,txtoff,txt_a); shape=TILE
    if abs(s-1)>1e-3:
        content=content.resize((int(cw*s),int(ch*s)),Image.LANCZOS); shape=shape.resize((int(cw*s),int(ch*s)),Image.LANCZOS)
    cwh=content.size; pos=(int(CX-cwh[0]/2),int(CY-cwh[1]/2)); over_=Image.new("RGBA",(W,H),(0,0,0,0))
    shm=Image.new("L",(W,H),0); shm.paste(shape,(pos[0],pos[1]+Q(6))); shm=shm.filter(ImageFilter.GaussianBlur(Q(12))); shm=shm.point(lambda v:int(v*0.30*O))
    shl=Image.new("RGBA",(W,H),(37,37,37,255)); shl.putalpha(shm); over_=Image.alpha_composite(over_,shl)
    bdmask=Image.new("L",(W,H),0); bdmask.paste(shape,pos); bdmask=bdmask.point(lambda v:int(v*O)); bd=blurred.copy(); bd.putalpha(bdmask); over_=Image.alpha_composite(over_,bd)
    cl=Image.new("RGBA",(W,H),(0,0,0,0)); cl.paste(content,pos,content)
    if O<1.0: cl.putalpha(cl.split()[3].point(lambda v:int(v*O)))
    over_=Image.alpha_composite(over_,cl); over_.save(f"videos/edit/brand/lt2/{i:04d}.png")
print("lt2 done")

# ===== BBCIncorp logo placeholder =====
def build_logo():
    canvas=Image.new("RGBA",(W,H),(0,0,0,0)); fw=F(30,700); txt="BBCIncorp"; mk=Q(44); padx=Q(18); gap=Q(14)
    twd=tw(txt,fw); _,th=vbox(txt,fw); pillw=padx+mk+gap+int(twd)+padx; pillh=mk+Q(24)
    pi=Image.new("RGBA",(pillw,pillh),(0,0,0,0)); d=ImageDraw.Draw(pi)
    d.rounded_rectangle([0,0,pillw-1,pillh-1],radius=pillh//2,fill=(255,255,255,210))
    mk_im=Image.new("RGBA",(mk,mk),(0,0,0,0)); px=mk_im.load()
    for y in range(mk):
        f=y/(mk-1); c=lerp(hx("00c2ff"),ACCENT,f)
        for x in range(mk): px[x,y]=(c[0],c[1],c[2],255)
    cm=Image.new("L",(mk,mk),0); ImageDraw.Draw(cm).ellipse([0,0,mk-1,mk-1],fill=255); mk_im.putalpha(cm)
    dm=ImageDraw.Draw(mk_im); dm.ellipse([mk*0.34,mk*0.34,mk*0.66,mk*0.66],fill=(255,255,255,255))
    pi.alpha_composite(mk_im,(padx,(pillh-mk)//2)); top,_=vbox(txt,fw); d.text((padx+mk+gap,(pillh-th)//2-top),txt,font=fw,fill=(26,26,26,255))
    canvas.alpha_composite(pi,(W-pillw-Q(46),Q(40))); canvas.save("videos/edit/brand/bbclogo.png")
build_logo(); print("logo done")

# ===== "3 days" hero (raised) =====
def build_threedays(T=2.5):
    f=F(120,700); txt="3 days"; pad=Q(26)
    w=int(tw(txt,f))+2*pad; top,ih=vbox(txt,f); h=ih+2*pad
    base=Image.new("RGBA",(w,h),(0,0,0,0))
    sh=Image.new("RGBA",base.size,(0,0,0,0)); ImageDraw.Draw(sh).text((pad,pad-top),txt,font=f,fill=(0,42,102,150)); sh=sh.filter(ImageFilter.GaussianBlur(Q(7)))
    base=Image.alpha_composite(base,sh); d=ImageDraw.Draw(base)
    d.text((pad,pad-top),txt,font=f,fill=ACCENT+(255,),stroke_width=Q(5),stroke_fill=(255,255,255,255))
    cx,cy=W/2,int(H*0.47); N=int(T*FPS)
    for fr in range(N):
        t=fr/FPS
        if t<0.3: s=0.8+0.2*eob(t/0.3); a=min(1.0,t/0.22)
        elif t<T-0.4: s=1.0; a=1.0
        else: o=expo((t-(T-0.4))/0.4); s=1.0+0.06*o; a=1-o
        im=base if abs(s-1)<1e-3 else base.resize((int(w*s),int(h*s)),Image.LANCZOS)
        canvas=over(Image.new("RGBA",(W,H),(0,0,0,0)),im,cx-im.width/2,cy-im.height/2,a); canvas.save(f"videos/edit/brand/threedays/{fr:04d}.png")
    return N
print("threedays",build_threedays())

# ===== Incorporation panel =====
def render_panel(progs):
    cw,ch=Q(448),Q(300); pad=Q(28)
    card=Image.new("RGBA",(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cw-1,ch-1],radius=Q(16),fill=(255,255,255,250)); d.rounded_rectangle([0,0,cw-1,ch-1],radius=Q(16),outline=BG2+(255,),width=2)
    isz=Q(40); ic=Image.new("RGBA",(isz,isz),(0,0,0,0)); di=ImageDraw.Draw(ic); di.rounded_rectangle([0,0,isz-1,isz-1],radius=Q(10),fill=ACCENT+(255,))
    fi=F(16,700); tn=tw("SG",fi); tp,ti=vbox("SG",fi); di.text(((isz-tn)/2,(isz-ti)/2-tp),"SG",font=fi,fill=WHITE+(255,)); card.alpha_composite(ic,(pad,pad))
    th=F(20,700); top,_=vbox("Singapore Pte Ltd",th); d.text((pad+isz+Q(12),pad-top+Q(2)),"Singapore Pte Ltd",font=th,fill=TEXT+(255,))
    ts=F(13,500); top2,_=vbox("Incorporation status",ts); d.text((pad+isz+Q(12),pad+Q(24)-top2),"Incorporation status",font=ts,fill=(140,150,165,255))
    items=["Company registered","Corporate bank account","Compliance & secretary"]; fr=F(17,500); y0=Q(108)
    for i,it in enumerate(items):
        cy=y0+i*Q(46)+Q(13); cxp=pad+Q(13); p=progs[i]
        if p>0.5: draw_check(d,cxp,cy,Q(13),ACCENT)
        else: d.ellipse([cxp-Q(13),cy-Q(13),cxp+Q(13),cy+Q(13)],outline=(200,206,214,255),width=3)
        col=lerp((150,156,166),(51,51,51),p); top,ih=vbox(it,fr); d.text((pad+Q(40),cy-ih/2-top),it,font=fr,fill=col+(255,))
    fc=F(14,600); ct="Done in 3 days · 100% remote"; chx=pad; chy=ch-pad-Q(34); cw2=cw-2*pad
    d.rounded_rectangle([chx,chy,chx+cw2,chy+Q(34)],radius=Q(10),fill=BG3+(255,))
    draw_check(d,chx+Q(22),chy+Q(17),Q(9),ACCENT); top,ih=vbox(ct,fc); d.text((chx+Q(40),chy+Q(17)-ih/2-top),ct,font=fc,fill=ACCENT+(255,))
    return card
def build_panel(T=3.6):
    cw,ch=Q(448),Q(300); bx=W-Q(60)-cw; by=int((H-ch)/2-Q(6)); N=int(T*FPS)
    for fr in range(N):
        t=fr/FPS
        if t<0.5: xoff=(1-expo(t/0.5))*Q(540); a=expo(t/0.5)
        elif t<T-0.3: xoff=0; a=1.0
        else: o=expo((t-(T-0.3))/0.3); xoff=o*Q(540); a=1-o
        yoff=Q(7)*math.sin(2*math.pi*t/3.0)
        progs=[max(0.0,min(1.0,(t-(0.6+i*0.5))/0.3)) for i in range(3)]
        card=render_panel(progs); pos=(int(bx+xoff),int(by+yoff))
        canvas=Image.new("RGBA",(W,H),(0,0,0,0))
        shm=Image.new("L",(W,H),0); sq=Image.new("L",(cw,ch),0); ImageDraw.Draw(sq).rounded_rectangle([0,0,cw-1,ch-1],radius=Q(16),fill=255)
        shm.paste(sq,(pos[0],pos[1]+Q(8))); shm=shm.filter(ImageFilter.GaussianBlur(Q(14))); shm=shm.point(lambda v:int(v*0.26*a))
        shl=Image.new("RGBA",(W,H),(20,40,70,255)); shl.putalpha(shm); canvas=Image.alpha_composite(canvas,shl)
        canvas=over(canvas,card,pos[0],pos[1],a); canvas.save(f"videos/edit/brand/panel/{fr:04d}.png")
    return N
print("panel",build_panel())

# ===== Close tag =====
def build_closetag(T=3.0):
    fc=F(18,600); txt="100% Remote  ·  Singapore incorporated"; padx,pady=Q(26),Q(16); chk=Q(22); gap=Q(14)
    twd=int(tw(txt,fc)); top,ih=vbox(txt,fc); pillw=padx+chk*2+gap+twd+padx; pillh=ih+2*pady+Q(8)
    pi=Image.new("RGBA",(pillw,pillh),(0,0,0,0)); d=ImageDraw.Draw(pi)
    d.rounded_rectangle([0,0,pillw-1,pillh-1],radius=pillh//2,fill=(255,255,255,250))
    draw_check(d,padx+chk,pillh//2,chk-Q(4),ACCENT); d.text((padx+chk*2+gap,(pillh-ih)//2-top),txt,font=fc,fill=(51,51,51,255))
    full,pad=add_shadow(pi,color=(37,37,37,55),blur=11,dy=4)
    bx=int((W-pillw)/2-pad); by=int(H-Q(96)-pad); N=int(T*FPS)
    for fr in range(N):
        t=fr/FPS; p=expo(t/0.4); a=p; dy=Q(16)*(1-p)
        canvas=over(Image.new("RGBA",(W,H),(0,0,0,0)),full,bx,by+dy,a); canvas.save(f"videos/edit/brand/closetag/{fr:04d}.png")
    return N
print("closetag",build_closetag())
