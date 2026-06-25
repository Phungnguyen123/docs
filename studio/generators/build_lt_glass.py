import sys; sys.path.insert(0,"videos/edit/brand")
from kit import *
from PIL import ImageFilter

def expo(t): 
    t=max(0.0,min(1.0,t));  return 1-2**(-10*t) if t<1 else 1.0

SRC="videos/edit/brand/ltsrc"; OUT="videos/edit/brand/lt2"
N=120; FPSc=24

# ---- logo placeholder: rounded square, blue->amber gradient, white "P" ----
def make_logo(sz=58):
    g=Image.new("RGBA",(sz,sz),(0,0,0,0)); px=g.load()
    for y in range(sz):
        f=y/(sz-1)
        r=int(ACCENT[0]+(AMBER[0]-ACCENT[0])*f); gg=int(ACCENT[1]+(AMBER[1]-ACCENT[1])*f); b=int(ACCENT[2]+(AMBER[2]-ACCENT[2])*f)
        for x in range(sz): px[x,y]=(r,gg,b,255)
    mask=Image.new("L",(sz,sz),0); ImageDraw.Draw(mask).rounded_rectangle([0,0,sz-1,sz-1],radius=14,fill=255)
    g.putalpha(mask)
    d=ImageDraw.Draw(g); f=F(34,700); tx=tw("P",f); bb=g_=vbox("P",f)
    d.text(((sz-tx)/2,(sz-bb[1])/2-bb[0]),"P",font=f,fill=WHITE+(255,))
    return g
LOGO=make_logo(58)

# ---- gradient vertical bar (blue->amber) ----
def make_bar(w,h):
    b=Image.new("RGBA",(w,h),(0,0,0,0)); px=b.load()
    for y in range(h):
        f=y/(h-1)
        r=int(ACCENT[0]+(AMBER[0]-ACCENT[0])*f); gg=int(ACCENT[1]+(AMBER[1]-ACCENT[1])*f); bl=int(ACCENT[2]+(AMBER[2]-ACCENT[2])*f)
        for x in range(w): px[x,y]=(r,gg,bl,255)
    m=Image.new("L",(w,h),0); ImageDraw.Draw(m).rounded_rectangle([0,0,w-1,h-1],radius=w//2,fill=255); b.putalpha(m)
    return b

# ---- card geometry ----
padx,pady=26,20; gap1=14; barw=6; gap2=18
fname=F(36,700); fsub=F(18,400)
name="PNKSmart"; sub="SaaS Company · Our Client"
nw=tw(name,fname); _,nh=vbox(name,fname); sw=tw(sub,fsub); _,sh=vbox(sub,fsub)
textw=int(max(nw,sw)); inner_h=max(LOGO.height, int(nh+8+sh))
cw=int(padx+LOGO.width+gap1+barw+gap2+textw+padx); ch=int(inner_h+2*pady)
BAR=make_bar(barw,inner_h)
TEXTX=padx+LOGO.width+gap1+barw+gap2
LOGOY=int((ch-LOGO.height)/2); BARY=int((ch-inner_h)/2)
ny=int((ch-(nh+8+sh))/2); 
TILE=Image.new("L",(cw,ch),0); ImageDraw.Draw(TILE).rounded_rectangle([0,0,cw-1,ch-1],radius=16,fill=255)

# fixed card placement (bottom-left)
CX = 70 + cw/2; CY = H - 70 - ch/2

def render_content(barfrac, txtoff, txt_a):
    card=Image.new("RGBA",(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cw-1,ch-1],radius=16,fill=WHITE+(166,))      # frosted tint ~65%
    card.alpha_composite(LOGO,(padx,LOGOY))
    bh=max(1,int(inner_h*barfrac)); card.alpha_composite(BAR.crop((0,0,barw,bh)),(padx+LOGO.width+gap1,BARY))
    tl=Image.new("RGBA",(cw,ch),(0,0,0,0)); dt=ImageDraw.Draw(tl)
    tn,_=vbox(name,fname); ts,_=vbox(sub,fsub)
    dt.text((TEXTX,ny-tn),name,font=fname,fill=(34,34,34,255))
    dt.text((TEXTX,ny+nh+8-ts),sub,font=fsub,fill=(85,85,85,255))
    if txt_a<1.0:
        al=tl.split()[3].point(lambda v:int(v*txt_a)); tl.putalpha(al)
    # slide whole text layer by txtoff (from left)
    tl2=Image.new("RGBA",(cw,ch),(0,0,0,0)); tl2.paste(tl,(int(-txtoff),0),tl)
    card.alpha_composite(tl2)
    return card

def state(t):
    # in (0..0.4), hold, out (4.5..4.75)
    if t<0.4: e=expo(t/0.4); O=e; s=0.85+0.15*e
    elif t<4.5: O=1.0; s=1.0
    else: e=expo((t-4.5)/0.25); O=max(0.0,1-e); s=1.0-0.10*e
    barfrac=max(0.0,min(1.0,(t-0.15)/0.2))
    tp=expo((t-0.10)/0.35); txtoff=20*(1-tp); txt_a=tp
    return O,s,barfrac,txtoff,txt_a

for i in range(N):
    t=i/FPSc
    O,s,barfrac,txtoff,txt_a=state(t)
    base=Image.open(f"{SRC}/{i+1:04d}.png").convert("RGBA")
    blurred=base.filter(ImageFilter.GaussianBlur(14))
    content=render_content(barfrac,txtoff,txt_a)
    shape=TILE
    if abs(s-1.0)>1e-3:
        nw_,nh_=int(cw*s),int(ch*s)
        content=content.resize((nw_,nh_),Image.LANCZOS); shape=shape.resize((nw_,nh_),Image.LANCZOS)
    cwh=content.size; pos=(int(CX-cwh[0]/2),int(CY-cwh[1]/2))
    over_=Image.new("RGBA",(W,H),(0,0,0,0))
    # shadow
    shm=Image.new("L",(W,H),0); shm.paste(shape,(pos[0],pos[1]+6)); shm=shm.filter(ImageFilter.GaussianBlur(12))
    shm=shm.point(lambda v:int(v*0.30*O)); shl=Image.new("RGBA",(W,H),(37,37,37,255)); shl.putalpha(shm)
    over_=Image.alpha_composite(over_,shl)
    # frosted backdrop (blurred footage clipped to card shape, *O)
    bdmask=Image.new("L",(W,H),0); bdmask.paste(shape,pos); bdmask=bdmask.point(lambda v:int(v*O))
    bd=blurred.copy(); bd.putalpha(bdmask); over_=Image.alpha_composite(over_,bd)
    # content (tint+bar+logo+text), *O
    cl=Image.new("RGBA",(W,H),(0,0,0,0)); cl.paste(content,pos,content)
    if O<1.0:
        al=cl.split()[3].point(lambda v:int(v*O)); cl.putalpha(al)
    over_=Image.alpha_composite(over_,cl)
    over_.save(f"{OUT}/{i:04d}.png")
print("lt glass frames",N,"card",(cw,ch))
