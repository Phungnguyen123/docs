import sys; sys.path.insert(0,"videos/edit/brand")
from kit import *
def eoc(t): return 1-(1-t)**3

def check_badge(d_circle=56):
    im=Image.new("RGBA",(d_circle,d_circle),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([0,0,d_circle-1,d_circle-1],fill=ACCENT+(255,))
    r=d_circle
    pts=[(0.30*r,0.53*r),(0.44*r,0.67*r),(0.73*r,0.36*r)]
    d.line(pts,fill=WHITE+(255,),width=max(3,int(r*0.09)),joint="curve")
    return im

def build_stat_base():
    padx,pady=40,30; gap=22
    fm=F(30,700); fs=F(18,500)
    badge=check_badge(58)
    seg=[("DONE IN ",ACCENT),("3",AMBER),(" DAYS",ACCENT)]
    fm_w=sum(tw(t,fm) for t,_ in seg); _,mh=vbox("DONE IN 3 DAYS",fm)
    sub="Fast incorporation"; sw=tw(sub,fs); _,sh=vbox(sub,fs)
    textw=int(max(fm_w,sw))
    cardw=int(padx+badge.width+gap+textw+padx)
    underline_h=4; m_to_u=10; u_to_s=14
    cardh=int(pady+mh+m_to_u+underline_h+u_to_s+sh+pady)
    card=Image.new("RGBA",(cardw,cardh),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cardw-1,cardh-1],radius=16,fill=WHITE+(245,))
    d.rounded_rectangle([0,0,cardw-1,cardh-1],radius=16,outline=BG2+(255,),width=2)
    # badge vertically centered
    by=int((cardh-badge.height)/2); card.alpha_composite(badge,(padx,by))
    tx=padx+badge.width+gap
    # main text (multicolor), top aligned within text block
    ty=pady
    x=tx; topm,_=vbox("DONE IN 3 DAYS",fm)
    for t,c in seg:
        d.text((x,ty-topm),t,font=fm,fill=c+(255,)); x+=tw(t,fm)
    # sub
    sy=ty+mh+m_to_u+underline_h+u_to_s
    tops,_=vbox(sub,fs); d.text((tx,sy-tops),sub,font=fs,fill=MUTE+(255,))
    # underline geometry (for animated sweep): under main text
    uy=ty+mh+m_to_u
    return card,(tx,uy,int(fm_w),underline_h)

base,(ux,uy,uw,uh)=build_stat_base()

# rest position: lower-center, clear of the face (face is upper-center)
def place(t):
    if t<0.4: a=min(1.0,t/0.3); off=18*(1-eoc(min(1.0,t/0.4)))
    elif t<3.4: a=1.0; off=0.0
    else: a=max(0.0,1.0-(t-3.4)/0.35); off=-12*((t-3.4)/0.35)
    sw=max(0.0,min(1.0,(t-0.12)/0.5)); sw=eoc(sw)
    return a,off,sw

n=int(3.75*FPS)
CARD_BOTTOM=624
def render(i, on_bg=None):
    t=i/FPS; a,off,sw=place(t)
    card=base.copy(); dc=ImageDraw.Draw(card)
    if sw>0:
        dc.rounded_rectangle([ux,uy,ux+int(uw*sw),uy+uh],radius=2,fill=AMBER+(255,))
    full,pad=add_shadow(card,color=(119,119,119,77),blur=11,dy=2)  # soft glow, tech
    x=(W-full.width)/2; y=CARD_BOTTOM-full.height+off
    canvas=Image.new("RGBA",(W,H),(0,0,0,0))
    sc=Image.new("RGBA",(W,H),DARK+(int(22*a),)); canvas=Image.alpha_composite(canvas,sc)
    canvas=over(canvas,full,x,y,a)
    if on_bg is not None:
        bg=Image.open(on_bg).convert("RGBA")
        return Image.alpha_composite(bg,canvas)
    return canvas

for i in range(n):
    render(i).save(f"videos/edit/brand/stat/{i:04d}.png")
# preview at hold over footage frame
render(50, on_bg="videos/edit/brand/_bg8.png").convert("RGB").save("videos/edit/brand/preview_stat2.png")
print("stat frames",n,"card",base.size)
