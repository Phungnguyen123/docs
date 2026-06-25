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

# "3 days" -> RIGHT side over the window, vertical center ~0.47H (clear of face & hands)
def build_threedays(T=2.5):
    f=F(108,700); txt="3 days"; pad=Q(26)
    w=int(tw(txt,f))+2*pad; top,ih=vbox(txt,f); h=ih+2*pad
    base=Image.new("RGBA",(w,h),(0,0,0,0))
    sh=Image.new("RGBA",base.size,(0,0,0,0)); ImageDraw.Draw(sh).text((pad,pad-top),txt,font=f,fill=(0,42,102,160)); sh=sh.filter(ImageFilter.GaussianBlur(Q(8)))
    base=Image.alpha_composite(base,sh); d=ImageDraw.Draw(base)
    d.text((pad,pad-top),txt,font=f,fill=ACCENT+(255,),stroke_width=Q(5),stroke_fill=(255,255,255,255))
    RX=W-Q(64); VC=int(H*0.47); N=int(T*FPS)
    for fr in range(N):
        t=fr/FPS
        if t<0.3: s=0.8+0.2*eob(t/0.3); a=min(1.0,t/0.22)
        elif t<T-0.4: s=1.0; a=1.0
        else: o=expo((t-(T-0.4))/0.4); s=1.0+0.06*o; a=1-o
        im=base if abs(s-1)<1e-3 else base.resize((int(w*s),int(h*s)),Image.LANCZOS)
        x=RX-im.width; y=VC-im.height/2
        canvas=over(Image.new("RGBA",(W,H),(0,0,0,0)),im,x,y,a); canvas.save(f"videos/edit/brand/threedays/{fr:04d}.png")
    return N
print("threedays",build_threedays())

# Panel -> pushed further right (clear of subject)
def render_panel(progs):
    cw,ch=Q(420),Q(300); pad=Q(28)
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
    cw,ch=Q(420),Q(300); bx=W-Q(40)-cw; by=int((H-ch)/2-Q(6)); N=int(T*FPS)
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
