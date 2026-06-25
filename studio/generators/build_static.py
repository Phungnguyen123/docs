import sys; sys.path.insert(0,"videos/edit/brand")
from kit import *

def card_centered_block(rows, padx=64, pady=52, radius=16, bg=WHITE):
    """rows: list of dicts {kind:'pill'|'text'|'line', ...}. Returns card RGBA."""
    # measure
    widths=[]; 
    for r in rows:
        if r["kind"]=="pill": widths.append(r["img"].width)
        elif r["kind"]=="text": widths.append(tw(r["text"],r["font"],r.get("tr",0)))
        elif r["kind"]=="line": widths.append(r["w"])
    contentw=int(max(widths)); cardw=contentw+2*padx
    # height
    total=0
    for i,r in enumerate(rows):
        if r["kind"]=="pill": total+=r["img"].height
        elif r["kind"]=="text": total+=vbox(r["text"],r["font"])[1]
        elif r["kind"]=="line": total+=r["h"]
        total+=r.get("gap",0)
    cardh=int(total+2*pady)
    card=Image.new("RGBA",(cardw,cardh),(0,0,0,0)); d=ImageDraw.Draw(card)
    d.rounded_rectangle([0,0,cardw-1,cardh-1],radius=radius,fill=bg+(255,))
    cx=cardw/2; y=pady
    for r in rows:
        if r["kind"]=="pill":
            card.alpha_composite(r["img"],(int(cx-r["img"].width/2),int(y))); y+=r["img"].height
        elif r["kind"]=="text":
            ih=put_center(d,cx,y,r["text"],r["font"],r["fill"]+(255,),r.get("tr",0)); y+=ih
        elif r["kind"]=="line":
            d.line([(cx-r["w"]/2,y),(cx+r["w"]/2,y)],fill=r["fill"]+(255,),width=r["h"]); y+=r["h"]
        y+=r.get("gap",0)
    return card

# ---------- TITLE ----------
title_rows=[
    {"kind":"pill","img":pill("OUR CLIENT",F(14,600),ACCENT,BG2),"gap":22},
    {"kind":"text","text":"PNKSmart","font":F(40,700),"fill":TEXT,"gap":12},
    {"kind":"text","text":"and Key Outcome","font":F(18,600),"fill":ACCENT,"gap":20},
    {"kind":"line","w":56,"h":3,"fill":ACCENT,"gap":18},
    {"kind":"text","text":"FROM BBCINCORP · SINGAPORE","font":F(14,600),"fill":MUTE,"tr":3},
]
card=card_centered_block(title_rows)
full,pad=add_shadow(card)
img=frame(BG1); img=over(img,full,(W-full.width)/2,(H-full.height)/2)
img.convert("RGB").save("videos/edit/brand/title.png"); print("title",card.size)

# ---------- OUTRO ----------
outro_rows=[
    {"kind":"pill","img":pill("BBCINCORP SINGAPORE",F(14,600),ACCENT,BG2),"gap":24},
    {"kind":"text","text":"Fast. Reliable.","font":F(40,700),"fill":TEXT,"gap":10},
    {"kind":"text","text":"Done in 3 days.","font":F(40,700),"fill":ACCENT,"gap":20},
    {"kind":"line","w":56,"h":3,"fill":AMBER,"gap":18},
    {"kind":"text","text":"FAST · RELIABLE · DONE IN 3 DAYS","font":F(14,600),"fill":MUTE,"tr":3},
]
card=card_centered_block(outro_rows)
full,pad=add_shadow(card)
img=frame(BG1); img=over(img,full,(W-full.width)/2,(H-full.height)/2)
img.convert("RGB").save("videos/edit/brand/outro.png"); print("outro",card.size)

# ---------- LOWER THIRD card ----------
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
lt=lower_third_card(); full,pad=add_shadow(lt)
bg=Image.open("videos/edit/brand/_bg3.png").convert("RGBA")
prev=over(bg,full,70-pad,H-lt.height-78-pad)
prev.convert("RGB").save("videos/edit/brand/preview_lt.png"); print("lt",lt.size)

# ---------- STAT card ----------
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
st=stat_card(); full,pad=add_shadow(st)
bg=Image.open("videos/edit/brand/_bg8.png").convert("RGBA")
prev=over(bg,full,(W-full.width)/2,(H-full.height)/2)
prev.convert("RGB").save("videos/edit/brand/preview_stat.png"); print("stat",st.size)
