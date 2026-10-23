#!/usr/bin/env python3
"""Build a seven-slide truthful Mezo MUSD pitch PDF from real pinned JSON and live screenshot."""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import math
import re
import textwrap

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'docs/latest.json').read_text())
OLDER=json.loads((ROOT/'evidence/20261023_mezo_first_pinned.json').read_text())
DIFF=json.loads((ROOT/'docs/comparison.json').read_text())
assert DATA['schemaVersion']=='mezo-musd-proofdesk-v1'
assert DATA['network']['chainId']==31612
assert DATA['block']['number']>OLDER['block']['number']
assert len(DATA['pools'])==3
assert len(DIFF['contractsAndPools'])==5
assert sum(x['runtimeChanged'] for x in DIFF['contractsAndPools'])==0
screen=ROOT/'media/live_mainnet_dashboard_20261024.png'
assert screen.exists()
W,H=1280,720
BG="#07151a";CARD="#0e2429";CARD2="#12353a";FG="#e7f1e9";AQUA="#b3ebda"
DIM="#91b6b0";YEL="#e9bd78";LINE="#2c484c";GREEN="#8bd6af"
REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F=lambda sz,b=False,m=False:ImageFont.truetype(MONO if m else (BOLD if b else REG),sz)

FRAMES=ROOT/'media/deck_frames';FRAMES.mkdir(exist_ok=True,parents=True)
slides=[]

def text(draw,pt,x,y,s=25,c=FG,b=False,m=False):
    draw.text((x,y),str(pt),font=F(s,b,m),fill=c)
def rule(draw,x1,y,x2,color=LINE,width=2):
    draw.line((x1,y,x2,y),fill=color,width=width)
def wrap(draw,t,x,y,max_width,size=22,c=DIM,dy=None,b=False):
    words=t.split(' ');lines=[];line=''
    font=F(size,b)
    for w in words:
        test=(line+' '+w).strip()
        if line and draw.textbbox((0,0),test,font=font)[2] > max_width:
            lines.append(line);line=w
        else:line=test
    if line:lines.append(line)
    dy=dy or int(size*1.6)
    for z in lines: text(draw,z,x,y,size,c,b);y+=dy
    return y
def rounded(draw,box,fill=CARD,outline=LINE,r=12,width=2):
    draw.rounded_rectangle(box,radius=r,fill=fill,outline=outline,width=width)
def start(n,tag,title,sub=None):
    im=Image.new('RGB',(W,H),BG)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,7),fill=AQUA)
    text(d,"M·  MUSD PROOF DESK",50,24,18,AQUA,True)
    text(d,"MEZO MAINNET  /  EVIDENCE NOT INFERENCE",745,27,14,DIM,False,True)
    rule(d,50,74,1230)
    text(d,tag.upper(),56,104,14,AQUA,False,True)
    text(d,title,55,139,39,FG,True)
    if sub:wrap(d,sub,56,205,1160,19,DIM,30)
    rule(d,50,662,1230)
    text(d,"SOURCE: GITHUB.COM/LIVASTIC-VM2-PRIMARY-20260911/MEZO-MUSD-PROOF-DESK",52,676,11,DIM,False,True)
    text(d,f"{n:02d} / 07",1150,674,14,AQUA,False,True)
    return im,d
def save(im,n):
    p=FRAMES/f"slide_{n:02d}.png"
    if p.exists():
        # Rebuild produces a deterministic replacement of our own generated image.
        p.unlink()
    im.save(p,optimize=True)
    slides.append(im)
    return p

# 01
im,d=start(1,"builder presentation / track 2","Proof first. Price later.")
text(d,"An on-chain MUSD / MEZO evidence desk",57,230,29,AQUA,True)
wrap(d,"Reproducible supplies, basic-pool MUSD reserves and contract SHA-256 evidence from one pinned Mezo block.",57,290,640,23,FG,36)
rounded(d,(56,429,698,559),CARD2,"#4e8983",16)
text(d,"ONE BLOCK  →  VERIFIED CONTRACTS",79,455,23,AQUA,True,True)
text(d,"THREE BASIC POOLS  →  READ-ONLY JSON",79,507,18,FG,False,True)
for y,l in [(258,"31612"),(355,"3 POOLS"),(455,"28 TESTS")]:
    rounded(d,(804,y,1193,y+78),CARD,"#4b7977",10)
    text(d,l,847,y+20,27,AQUA,True)
text(d,"Independent and AI-assisted  •  no wallet  •  no deposits",57,593,18,YEL)
save(im,1)

# 02
im,d=start(2,"the problem","Numbers without provenance.", "DeFi users should know which chain, token, block, contracts and assumptions produced the figures they see.")
cards=[
 ("01","MIXED BLOCKS","A dashboard might mix changing values from multiple moments."),
 ("02","TOKEN AMBIGUITY","Addresses, decimals, pool order and bridged units are easy to confuse."),
 ("03","FALSE CERTAINTY","AMM reserves do not, by themselves, prove peg, solvency or swap price."),
]
for i,(num,title,desc) in enumerate(cards):
    x=55+i*405
    rounded(d,(x,319,x+378,534),CARD,LINE,12)
    text(d,num,x+25,343,17,YEL,True,True)
    text(d,title,x+24,389,23,AQUA,True)
    wrap(d,desc,x+24,437,330,17,DIM,31)
rounded(d,(55,573,1220,622),CARD2,"#47756f",8)
text(d,"OUR ANSWER  /  source-pinned, no-wallet public evidence",82,584,20,FG,True)
save(im,2)

# 03 actual screenshot
im,d=start(3,"a working deployment","Try the live public dashboard.", "Actual Chrome screenshot of the published GitHub Pages app: no Photoshop balances, no synthetic wallet.")
scr=Image.open(screen).convert('RGB')
# Cropping only the screenshot viewport; actual site remains unchanged.
cropped=scr.crop((0,0,scr.width,min(scr.height,1100)))
cropped=ImageOps.contain(cropped,(784,428))
im.paste(cropped,(430,226))
d.rounded_rectangle((426,222,426+cropped.width+8,222+cropped.height+8),radius=9,outline="#649f94",width=3)
text(d,"MEZO MAINNET",65,268,19,AQUA,True)
text(d,"CHAIN 31612",65,305,19,FG,True,True)
text(d,"REAL PINNED BLOCK",65,354,15,DIM)
text(d,f"#{DATA['block']['number']:,}",65,391,25,AQUA,True)
text(d,"LIVE SITE",65,474,15,DIM)
wrap(d,"livastic-vm2-primary-20260911.github.io/mezo-musd-proof-desk/",65,503,330,14,FG,23)
save(im,3)

# 04 architecture
im,d=start(4,"technical implementation","Every input has an origin.", "Python standard library. Official published contract/pool addresses. Strict read-only RPC allowlist.")
steps=[
 ("1","PIN","chain 31612","block + hash"),
 ("2","READ","ERC-20 supply","pool reserves"),
 ("3","VALIDATE","pair addresses","runtime SHA256"),
 ("4","PUBLISH","immutable JSON","static dashboard"),
]
for idx,(num,title,a,b) in enumerate(steps):
    x=55+idx*302
    rounded(d,(x,295,x+275,525),CARD if idx%2==0 else CARD2,"#426f6d",14)
    text(d,num,x+17,319,19,YEL,True,True)
    text(d,title,x+22,374,29,AQUA,True)
    text(d,a,x+22,438,18,FG)
    text(d,b,x+22,477,18,DIM)
    if idx<3:
        text(d,"→",x+274,382,25,YEL,True)
text(d,"CHAIN ID MISMATCH / RPC ERROR / TOKEN PAIR DRIFT / MISSING CODE  →  STOP",62,585,16,YEL,False,True)
save(im,4)

# 05 measured pool evidence
im,d=start(5,"real public mezo data","Three pools. Measured at one block.")
text(d,"MEZO BLOCK",58,256,16,DIM)
text(d,f"#{DATA['block']['number']:,}",56,288,39,AQUA,True)
text(d,"3-POOL MUSD RESERVE TOTAL",557,256,16,DIM)
total=Decimal(DATA['measuredPoolMUSDReserves'])
text(d,f"{total:,.2f} MUSD",552,288,38,FG,True)
for k,p in enumerate(DATA["pools"]):
    y=403+k*77
    amount=Decimal(p["musdReserve"])
    pct=amount/total*100
    text(d,p["name"],60,y,18,FG,True)
    text(d,f"{amount:,.2f} MUSD",732,y,18,AQUA,False,True)
    d.rectangle((60,y+36,1130,y+48),fill=LINE)
    d.rectangle((60,y+36,60+int(1070*float(pct/100)),y+48),fill=AQUA)
text(d,"Reserves != swap prices, market depth or backing assurance.",61,636,16,YEL)
save(im,5)

# 06 trust evidence
im,d=start(6,"reproducibility and risk limits","What we verify. What we don't.")
left=(55,275,621,578);right=(646,275,1215,578)
rounded(d,left,CARD2,"#417d73",12);rounded(d,right,CARD,"#6e634d",12)
text(d,"VERIFIED",84,299,22,AQUA,True)
for i,s in enumerate([
 "Two pinned real mainnet blocks",
 "28 offline regression tests passed",
 "5 runtime SHA256 fingerprints compared",
 "No wallet signing, gas or transaction",
]):
    text(d,"✓",84,362+i*48,23,AQUA,True)
    text(d,s,119,368+i*48,18,FG)
text(d,"NOT VERIFIED",675,299,22,YEL,True)
for i,s in enumerate([
 "MUSD peg or full BTC backing",
 "Yield, expected profit or solvency",
 "An executable trade price",
 "Security audit or immutable consensus proof",
]):
    text(d,"—",676,362+i*48,22,YEL,True)
    text(d,s,711,368+i*48,17,FG)
save(im,6)

# 07 roadmap and honest economic status
im,d=start(7,"independent one-human builder","A tool now. An ecosystem path next.", "Track 2: MUSD/MEZO access and discovery. Live product first, not a hypothetical yield strategy.")
for i,(n,title,detail) in enumerate([
 ("01","NOW","Production public website, open source, pinned Mezo mainnet evidence and silent 104s demo."),
 ("02","NEXT","Buyer-validated historical snapshots, source-linked alerts, usability tests."),
 ("03","LATER","Optional independent paid release QA; exact human contract and payee terms first."),
]):
    y=292+i*98
    text(d,n,58,y,20,YEL,True,True)
    text(d,title,135,y-1,21,AQUA,True)
    wrap(d,detail,269,y-1,900,17,FG,29)
text(d,"PROJECT",60,606,12,DIM,False,True)
text(d,"livastic-vm2-primary-20260911.github.io/mezo-musd-proof-desk/",180,602,16,AQUA)
text(d,"Status: PUBLIC DEMO. NOT SUBMITTED TO CONTEST. NOT FUNDED. CUSTOMERS = 0.",57,635,14,YEL)
save(im,7)

assert len(slides)==7
pdf=ROOT/'docs/pitch.pdf'
if pdf.exists():raise SystemExit('Refusing to overwrite existing public pitch.pdf')
slides[0].save(pdf,"PDF",save_all=True,append_images=slides[1:],resolution=150,quality=89)
raw=pdf.read_bytes()
assert raw.startswith(b'%PDF-') and len(raw)>50000
print("PITCH_DECK",pdf,"slides",len(slides),"bytes",len(raw),"sha256",hashlib.sha256(raw).hexdigest())
