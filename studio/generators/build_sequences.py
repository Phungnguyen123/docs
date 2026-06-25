import sys; sys.path.insert(0,"videos/edit/brand")
from kit import *

def eoc(t): return 1-(1-t)**3
def eob(t,s=1.6):
    t-=1; return 1+(s+1)*t**3+s*t**2

def lower_third_card():
    padx,pady=30,22; bar=6; gapbar=18
    fh=F(40,700); fs=F(18,600)
    main="PNKSmart"; sub="SaaS Company · Our Client"
    mw=tw(main,fh); sw=tw(sub,fs); _,mh=vbox(main,fh); _,sh=vbox(sub,fs)
    contentw=int(max(mw,sw)); cardw=int(bar+gapbar+contentw+padx); cardh=int(mh+10+sh+2*pady)
    card=Image.new("RGBA",(cardw,cardh),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cardw-1,cardh-1],radius=12,fill=WHITE+(255,))
    d.rounded_rectangle([12,pady-2,12+bar,cardh-pady+2],radius=3,fill=ACCENT+(255,))
    tx=bar+gapbar+12
    tm,_=vbox(main,fh); d.text((tx,pady-tm),main,font=fh,fill=TEXT+(255,))
    ts,_=vbox(sub,fs); d.text((tx,pady+mh+10-ts),sub,font=fs,fill=ACCENT+(255,))
    return card

def stat_card():
    padx,pady=56,40
    fm=F(30,700); fs=F(18,600)
    main="DONE IN 3 DAYS"; sub="Fast incorporation"
    mw=tw(main,fm); sw=tw(sub,fs); _,mh=vbox(main,fm); _,sh=vbox(sub,fs)
    contentw=int(max(mw,sw)); cardw=contentw+2*padx; cardh=int(mh+14+3+14+sh+2*pady)
    card=Image.new("RGBA",(cardw,cardh),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cardw-1,cardh-1],radius=16,fill=WHITE+(255,))
    cx=cardw/2; y=pady
    y+=put_center(d,cx,y,main,fm,ACCENT+(255,)); y+=14
    d.line([(cx-46,y),(cx+46,y)],fill=AMBER+(255,),width=3); y+=3+14
    put_center(d,cx,y,sub,fs,MUTE+(255,))
    return card

# ---- LOWER THIRD sequence: slide in (0.5s), hold 4s, fade out 0.5s ----
lt=lower_third_card(); full,pad=add_shadow(lt)
Y = H - lt.height - 78 - pad
X_END = 70 - pad
X_START = -full.width - 10
n=int(5.0*FPS)
for i in range(n):
    t=i/FPS
    if t<0.5: x=X_START+(X_END-X_START)*eoc(t/0.5); a=1.0
    elif t<4.5: x=X_END; a=1.0
    else: x=X_END; a=max(0.0,1.0-(t-4.5)/0.5)
    c=over(Image.new("RGBA",(W,H),(0,0,0,0)),full,x,Y,a)
    c.save(f"videos/edit/brand/lt/{i:04d}.png")
print("lt frames",n)

# ---- STAT sequence: pop in (0.4s), hold 3s, fade out 0.35s ----
st=stat_card(); full,pad=add_shadow(st)
n=int(3.75*FPS)
for i in range(n):
    t=i/FPS
    if t<0.4: s=0.6+0.4*eob(t/0.4); a=min(1.0,t/0.25)
    elif t<3.4: s=1.0; a=1.0
    else: fo=(t-3.4)/0.35; s=1.0+0.05*fo; a=max(0.0,1.0-fo)
    canvas=Image.new("RGBA",(W,H),(0,0,0,0))
    scrim=Image.new("RGBA",(W,H),DARK+(int(46*a),))   # #002a66 contrast scrim
    canvas=Image.alpha_composite(canvas,scrim)
    rb=full.resize((max(1,int(full.width*s)),max(1,int(full.height*s))),Image.LANCZOS)
    canvas=over(canvas,rb,(W-rb.width)/2,(H-rb.height)/2,a)
    canvas.save(f"videos/edit/brand/stat/{i:04d}.png")
print("stat frames",n)
