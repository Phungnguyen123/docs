import sys, math; sys.path.insert(0,"videos/edit/brand")
from kit import *
from PIL import ImageFilter
def expo(t): t=max(0.0,min(1.0,t)); return 1.0 if t>=1 else 1-2**(-10*t)
def eob(t,s=1.7):
    t=max(0.0,min(1.0,t))
    if t>=1: return 1.0
    t-=1; return 1+(s+1)*t**3+s*t**2
def eoc(t): t=max(0.0,min(1.0,t)); return 1-(1-t)**3
def lerp(a,b,p): return tuple(int(a[i]+(b[i]-a[i])*p) for i in range(3))
def draw_check(d,cx,cy,r,col):
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=col+(255,))
    d.line([(cx-r*0.42,cy+r*0.02),(cx-r*0.10,cy+r*0.36),(cx+r*0.46,cy-r*0.34)],fill=WHITE+(255,),width=max(2,int(r*0.22)),joint="curve")

# ---------- BBCIncorp logo placeholder (full-canvas, top-right) ----------
def build_logo():
    canvas=Image.new("RGBA",(W,H),(0,0,0,0))
    fw=F(30,700); txt="BBCIncorp"; mk=44; padx=18; gap=14
    twd=tw(txt,fw); _,th=vbox(txt,fw)
    pillw=padx+mk+gap+int(twd)+padx; pillh=mk+24
    pill_im=Image.new("RGBA",(pillw,pillh),(0,0,0,0)); d=ImageDraw.Draw(pill_im)
    d.rounded_rectangle([0,0,pillw-1,pillh-1],radius=pillh//2,fill=(255,255,255,210))
    # mark: blue gradient circle + white aperture dot
    mk_im=Image.new("RGBA",(mk,mk),(0,0,0,0)); px=mk_im.load()
    for y in range(mk):
        f=y/(mk-1); c=lerp(hx("00c2ff"),ACCENT,f)
        for x in range(mk): px[x,y]=(c[0],c[1],c[2],255)
    cm=Image.new("L",(mk,mk),0); ImageDraw.Draw(cm).ellipse([0,0,mk-1,mk-1],fill=255); mk_im.putalpha(cm)
    dm=ImageDraw.Draw(mk_im); dm.ellipse([mk*0.34,mk*0.34,mk*0.66,mk*0.66],fill=(255,255,255,255))
    my=(pillh-mk)//2; pill_im.alpha_composite(mk_im,(padx,my))
    top,_=vbox(txt,fw); d.text((padx+mk+gap,(pillh-th)//2-top),txt,font=fw,fill=(26,26,26,255))
    pos=(W-pillw-46,40)
    tmp=Image.new("RGBA",(W,H),(0,0,0,0)); tmp.alpha_composite(pill_im,pos)
    canvas=Image.alpha_composite(canvas,tmp); canvas.save("videos/edit/brand/bbclogo.png"); print("logo",pill_im.size)
build_logo()

# ---------- "3 days" hero (center flash) ----------
def build_threedays(T=3.0):
    f=F(120,700); txt="3 days"; pad=26
    w=int(tw(txt,f))+2*pad; top,ih=vbox(txt,f); h=ih+2*pad
    base=Image.new("RGBA",(w,h),(0,0,0,0))
    sh=Image.new("RGBA",base.size,(0,0,0,0)); ImageDraw.Draw(sh).text((pad,pad-top),txt,font=f,fill=(0,42,102,150)); sh=sh.filter(ImageFilter.GaussianBlur(7))
    base=Image.alpha_composite(base,sh); d=ImageDraw.Draw(base)
    d.text((pad,pad-top),txt,font=f,fill=ACCENT+(255,),stroke_width=5,stroke_fill=(255,255,255,255))
    cx,cy=W/2,int(H*0.60); N=int(T*FPS)
    for fr in range(N):
        t=fr/FPS
        if t<0.3: s=0.8+0.2*eob(t/0.3); a=min(1.0,t/0.22)
        elif t<2.6: s=1.0; a=1.0
        else: o=expo((t-2.6)/0.4); s=1.0+0.06*o; a=1-o
        im=base if abs(s-1)<1e-3 else base.resize((int(w*s),int(h*s)),Image.LANCZOS)
        canvas=Image.new("RGBA",(W,H),(0,0,0,0)); canvas=over(canvas,im,cx-im.width/2,cy-im.height/2,a)
        canvas.save(f"videos/edit/brand/threedays/{fr:04d}.png")
    return N
print("threedays",build_threedays())

# ---------- Incorporation status panel (flat floating, checklist ticks) ----------
def render_panel(progs):
    cw,ch=448,300; pad=28
    card=Image.new("RGBA",(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cw-1,ch-1],radius=16,fill=(255,255,255,250)); d.rounded_rectangle([0,0,cw-1,ch-1],radius=16,outline=BG2+(255,),width=2)
    # header
    ic=Image.new("RGBA",(40,40),(0,0,0,0)); di=ImageDraw.Draw(ic); di.rounded_rectangle([0,0,39,39],radius=10,fill=ACCENT+(255,))
    fi=F(16,700); tn=tw("SG",fi); tp,ti=vbox("SG",fi); di.text(((40-tn)/2,(40-ti)/2-tp),"SG",font=fi,fill=WHITE+(255,))
    card.alpha_composite(ic,(pad,pad))
    th=F(20,700); top,_=vbox("Singapore Pte Ltd",th); d.text((pad+52,pad-top+2),"Singapore Pte Ltd",font=th,fill=TEXT+(255,))
    ts=F(13,500); top2,_=vbox("Incorporation status",ts); d.text((pad+52,pad+24-top2),"Incorporation status",font=ts,fill=(140,150,165,255))
    items=["Company registered","Corporate bank account","Compliance & secretary"]
    fr=F(17,500); y0=108
    for i,it in enumerate(items):
        cy=y0+i*46+13; cxp=pad+13; p=progs[i]
        if p>0.5: draw_check(d,cxp,cy,13,ACCENT)
        else: d.ellipse([cxp-13,cy-13,cxp+13,cy+13],outline=(200,206,214,255),width=3)
        col=lerp((150,156,166),(51,51,51),p); top,ih=vbox(it,fr); d.text((pad+40,cy-ih/2-top),it,font=fr,fill=col+(255,))
    # footer chip
    fc=F(14,600); ct="✓ Done in 3 days · 100% remote".replace("✓","").strip()
    chx,chy=pad, ch-pad-34
    cw2=cw-2*pad; d.rounded_rectangle([chx,chy,chx+cw2,chy+34],radius=10,fill=BG3+(255,))
    draw_check(d,chx+22,chy+17,9,ACCENT); top,ih=vbox(ct,fc); d.text((chx+40,chy+17-ih/2-top),ct,font=fc,fill=ACCENT+(255,))
    return card
def build_panel(T=4.5):
    cw,ch=448,300; bx=W-60-cw; by=int((H-ch)/2-6); N=int(T*FPS)
    for fr in range(N):
        t=fr/FPS
        if t<0.5: xoff=(1-expo(t/0.5))*540; a=expo(t/0.5)
        elif t<4.2: xoff=0; a=1.0
        else: o=expo((t-4.2)/0.3); xoff=o*540; a=1-o
        yoff=7*math.sin(2*math.pi*t/3.0)
        progs=[max(0.0,min(1.0,(t-(0.9+i*0.55))/0.3)) for i in range(3)]
        card=render_panel(progs); pos=(int(bx+xoff),int(by+yoff))
        canvas=Image.new("RGBA",(W,H),(0,0,0,0))
        shm=Image.new("L",(W,H),0); sq=Image.new("L",(cw,ch),0); ImageDraw.Draw(sq).rounded_rectangle([0,0,cw-1,ch-1],radius=16,fill=255)
        shm.paste(sq,(pos[0],pos[1]+8)); shm=shm.filter(ImageFilter.GaussianBlur(14)); shm=shm.point(lambda v:int(v*0.26*a))
        shl=Image.new("RGBA",(W,H),(20,40,70,255)); shl.putalpha(shm); canvas=Image.alpha_composite(canvas,shl)
        canvas=over(canvas,card,pos[0],pos[1],a); canvas.save(f"videos/edit/brand/panel/{fr:04d}.png")
    return N
print("panel",build_panel())

# ---------- Close tag (bottom-center pill) ----------
def build_closetag(T=4.0):
    fc=F(18,600); txt="100% Remote  ·  Singapore incorporated"; padx,pady=26,16; chk=22; gap=14
    twd=int(tw(txt,fc)); top,ih=vbox(txt,fc)
    pillw=padx+chk*2+gap+twd+padx; pillh=ih+2*pady+8
    pill_im=Image.new("RGBA",(pillw,pillh),(0,0,0,0)); d=ImageDraw.Draw(pill_im)
    d.rounded_rectangle([0,0,pillw-1,pillh-1],radius=pillh//2,fill=(255,255,255,250))
    draw_check(d,padx+chk,pillh//2,chk-4,ACCENT)
    d.text((padx+chk*2+gap,(pillh-ih)//2-top),txt,font=fc,fill=(51,51,51,255))
    full,pad=add_shadow(pill_im,color=(37,37,37,55),blur=11,dy=4)
    bx=int((W-pillw)/2-pad); by=int(H-96-pad); N=int(T*FPS)
    for fr in range(N):
        t=fr/FPS; p=expo(t/0.4); a=p; dy=16*(1-p)
        canvas=Image.new("RGBA",(W,H),(0,0,0,0)); canvas=over(canvas,full,bx,by+dy,a)
        canvas.save(f"videos/edit/brand/closetag/{fr:04d}.png")
    return N
print("closetag",build_closetag())
