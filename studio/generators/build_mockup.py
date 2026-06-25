import sys, math, os; sys.path.insert(0,"videos/edit/brand")
import numpy as np
from kit import *
from PIL import ImageFilter
def expo(t):
    t=max(0.0,min(1.0,t)); return 1.0 if t>=1 else 1-2**(-10*t)

# ---------- fake SaaS dashboard (rendered 2x then warped down) ----------
def dashboard(W2=960,H2=600):
    im=Image.new("RGBA",(W2,H2),(255,255,255,255)); d=ImageDraw.Draw(im)
    rad=22
    mask=Image.new("L",(W2,H2),0); ImageDraw.Draw(mask).rounded_rectangle([0,0,W2-1,H2-1],radius=rad,fill=255)
    # top bar
    d.rectangle([0,0,W2,64],fill=(244,249,255,255))
    for i,c in enumerate([(255,95,86),(255,189,46),(39,201,63)]):
        d.ellipse([24+i*26,26,24+i*26+14,40],fill=c+(255,))
    d.text((130,22),"PNKSmart · Dashboard",font=F(22,600),fill=TEXT+(255,))
    # sidebar
    d.rectangle([0,64,200,H2],fill=(244,249,255,255))
    items=["Overview","Revenue","Users","Reports","Settings"]
    for i,it in enumerate(items):
        y=96+i*64
        if i==1:
            d.rounded_rectangle([16,y-10,184,y+34],radius=10,fill=ACCENT+(255,)); col=(255,255,255)
        else: col=(120,130,145)
        d.text((36,y),it,font=F(20,600 if i==1 else 500),fill=col+(255,))
    # main: title
    d.text((236,92),"Revenue",font=F(30,700),fill=TEXT+(255,))
    d.text((238,134),"Last 30 days",font=F(18,400),fill=(140,150,165,255))
    # KPI tiles
    tiles=[("$128K","+18%"),("3,000+","Users"),("99.9%","Uptime")]
    for i,(big,small) in enumerate(tiles):
        x=236+i*238; y=180
        d.rounded_rectangle([x,y,x+210,y+96],radius=14,fill=(248,251,255,255),outline=(228,242,255,255),width=2)
        d.text((x+18,y+16),big,font=F(30,700),fill=ACCENT+(255,))
        d.text((x+18,y+58),small,font=F(16,500),fill=(120,130,145,255))
    # area chart
    cx0,cy0,cw,chh=236,320,684,236
    d.rounded_rectangle([cx0,cy0,cx0+cw,cy0+chh],radius=14,fill=(250,252,255,255),outline=(228,242,255,255),width=2)
    pts=[]; import random; random.seed(7)
    vals=[0.35,0.5,0.42,0.6,0.55,0.72,0.68,0.85,0.8,0.95]
    n=len(vals)
    for i,v in enumerate(vals):
        px=cx0+24+i*(cw-48)/(n-1); py=cy0+chh-24-(chh-60)*v; pts.append((px,py))
    poly=pts+[(pts[-1][0],cy0+chh-20),(pts[0][0],cy0+chh-20)]
    ov=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(ov).polygon(poly,fill=(0,126,255,46)); im=Image.alpha_composite(im,ov)
    d=ImageDraw.Draw(im)
    d.line(pts,fill=ACCENT+(255,),width=5,joint="curve")
    for p in pts: d.ellipse([p[0]-5,p[1]-5,p[0]+5,p[1]+5],fill=(255,255,255,255),outline=ACCENT+(255,),width=3)
    im.putalpha(mask)
    # subtle border
    bd=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(bd).rounded_rectangle([0,0,W2-1,H2-1],radius=rad,outline=(220,232,248,255),width=3)
    im=Image.alpha_composite(im,bd)
    return im
DASH=dashboard(); SW2,SH2=DASH.size

def find_coeffs(dest,source):
    M=[]
    for (x,y),(X,Y) in zip(dest,source):
        M.append([x,y,1,0,0,0,-X*x,-X*y]); M.append([0,0,0,x,y,1,-Y*x,-Y*y])
    A=np.array(M,dtype=float); B=np.array(source,dtype=float).reshape(8)
    return np.linalg.solve(A,B)

sx,sy,sw,sh=744,150,480,300
src=[(0,0),(SW2,0),(SW2,SH2),(0,SH2)]
def corners(theta,xoff,yoff):
    k=math.sin(math.radians(theta))
    NW=(sx+0.10*sw*k+xoff, sy+0.11*sh*k+yoff)
    NE=(sx+sw+xoff, sy+yoff)
    SE=(sx+sw+xoff, sy+sh+yoff)
    SW=(sx+0.10*sw*k+xoff, sy+sh-0.11*sh*k+yoff)
    return [NW,NE,SE,SW]

def build(outdir,T=4.2):
    os.makedirs(outdir,exist_ok=True); N=int(T*FPS); out_start=T-0.3
    for fr in range(N):
        t=fr/FPS
        if t<0.5: e=expo(t/0.5); xoff=(1-e)*640; theta=15*(1-e); a=e
        elif t<out_start: xoff=0; theta=0; a=1.0
        else: o=expo((t-out_start)/0.3); xoff=o*640; theta=0; a=1-o
        yoff=8*math.sin(2*math.pi*t/3.0)
        dst=corners(theta,xoff,yoff)
        coeffs=find_coeffs(dst,src)
        warped=DASH.transform((W,H),Image.PERSPECTIVE,coeffs,resample=Image.BICUBIC,fillcolor=(0,0,0,0))
        canvas=Image.new("RGBA",(W,H),(0,0,0,0))
        # shadow from quad
        shm=Image.new("L",(W,H),0); ImageDraw.Draw(shm).polygon([(p[0],p[1]+22) for p in dst],fill=255)
        shm=shm.filter(ImageFilter.GaussianBlur(18)); shm=shm.point(lambda v:int(v*0.28*a))
        shl=Image.new("RGBA",(W,H),(20,40,70,255)); shl.putalpha(shm); canvas=Image.alpha_composite(canvas,shl)
        if a<1.0:
            al=warped.split()[3].point(lambda v:int(v*a)); warped.putalpha(al)
        canvas=Image.alpha_composite(canvas,warped)
        canvas.save(f"{outdir}/{fr:04d}.png")
    return N
n=build("videos/edit/brand/mockup"); print("mockup",n,"dash",DASH.size)
