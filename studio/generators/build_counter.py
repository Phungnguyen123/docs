import sys; sys.path.insert(0,"videos/edit/brand")
from kit import *
from PIL import ImageFilter
def expo(t):
    t=max(0.0,min(1.0,t)); return 1.0 if t>=1 else 1-2**(-10*t)
def eob(t,s=1.7):
    t=max(0.0,min(1.0,t))
    if t>=1: return 1.0
    t-=1; return 1+(s+1)*t**3+s*t**2
def eoc(t): t=max(0.0,min(1.0,t)); return 1-(1-t)**3

def up_icon(sz=34):
    im=Image.new("RGBA",(sz,sz),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([0,0,sz-1,sz-1],fill=BG2+(255,))
    cx=sz/2
    d.polygon([(cx,sz*0.26),(sz*0.74,sz*0.56),(sz*0.26,sz*0.56)],fill=ACCENT+(255,))
    d.rectangle([cx-sz*0.06,sz*0.5,cx+sz*0.06,sz*0.74],fill=ACCENT+(255,))
    return im

def render_card(num_str, desc):
    padx,pady=24,18; gap=12
    fn=F(50,700); fd=F(16,500); ic=up_icon(34)
    numw=tw(num_str,fn); _,numh=vbox(num_str,fn)
    descw=tw(desc,fd); _,desch=vbox(desc,fd)
    row1w=ic.width+gap+numw
    cw=int(padx+max(row1w,descw)+padx); ch=int(pady+max(ic.height,numh)+10+desch+pady)
    card=Image.new("RGBA",(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cw-1,ch-1],radius=12,fill=(255,255,255,235))
    d.rounded_rectangle([0,0,cw-1,ch-1],radius=12,outline=BG2+(255,),width=2)
    r1y=pady; card.alpha_composite(ic,(padx,int(r1y+(numh-ic.height)/2)))
    tnum,_=vbox(num_str,fn); d.text((padx+ic.width+gap,r1y-tnum),num_str,font=fn,fill=ACCENT+(255,))
    tdsc,_=vbox(desc,fd); d.text((padx,r1y+numh+10-tdsc),desc,font=fd,fill=(85,85,85,255))
    return card

def build(target,suffix,desc,outdir,anchor,T=3.4,count_dur=0.9):
    import os; os.makedirs(outdir,exist_ok=True)
    ax,ay=anchor; N=int(T*FPS); out_start=T-0.4
    for fr in range(N):
        t=fr/FPS
        prog=eoc((t-0.1)/count_dur); val=int(round(target*prog))
        done = t>=0.1+count_dur
        num_str=f"{val}{suffix if done else ''}"
        if t<0.4: s=eob(t/0.4); a=expo(t/0.3)
        elif t<out_start: s=1.0; a=1.0
        else: o=expo((t-out_start)/0.4); s=1.0-0.12*o; a=1-o
        card=render_card(num_str,desc)
        cw,ch=card.size
        if abs(s-1)>1e-3: card=card.resize((max(1,int(cw*s)),max(1,int(ch*s))),Image.LANCZOS)
        cwh=card.size; pos=(int(ax),int(ay-cwh[1]))   # bottom-left anchor
        canvas=Image.new("RGBA",(W,H),(0,0,0,0))
        # shadow
        shm=Image.new("L",(W,H),0); sq=Image.new("L",cwh,0); ImageDraw.Draw(sq).rounded_rectangle([0,0,cwh[0]-1,cwh[1]-1],radius=12,fill=255)
        shm.paste(sq,(pos[0],pos[1]+5)); shm=shm.filter(ImageFilter.GaussianBlur(10)); shm=shm.point(lambda v:int(v*0.28*a))
        shl=Image.new("RGBA",(W,H),(37,37,37,255)); shl.putalpha(shm); canvas=Image.alpha_composite(canvas,shl)
        canvas=over(canvas,card,pos[0],pos[1],a)
        canvas.save(f"{outdir}/{fr:04d}.png")
    return N

n=build(40,"%","Revenue growth","videos/edit/brand/kpi40",anchor=(72,300),T=3.4); print("kpi40",n)
n=build(3000,"+","Active users","videos/edit/brand/kpi3000",anchor=(72,470),T=2.8); print("kpi3000",n)
