#!/usr/bin/env python3
"""Captioned, silent 104-second pitch using REAL deployed-site screenshot + pinned Mezo evidence.

No fabricated product interactions, no wallet, no AI speech synthesis, no claims of bounty winnings.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import hashlib, json, subprocess

ROOT=Path(__file__).resolve().parents[1]
FRAMES=ROOT/'media/frames'
FRAMES.mkdir(exist_ok=True,parents=True)
SCREEN=ROOT/'media/live_mainnet_dashboard_20261024.png'
assert SCREEN.is_file()
snap=json.loads((ROOT/'docs/latest.json').read_text())
older=json.loads((ROOT/'evidence/20261023_mezo_first_pinned.json').read_text())
comparison=json.loads((ROOT/'docs/comparison.json').read_text())
assert snap['network']['chainId']==31612
assert snap['block']['number']>older['block']['number']
assert len(snap['pools'])==3 and len(comparison['contractsAndPools'])==5
assert all(not x['runtimeChanged'] for x in comparison['contractsAndPools'])

W,H=1280,720
BG='#07151a';PANEL='#0e252a';FG='#e7f1ed';AQUA='#b3ebda';MUTED='#97b8b3';YELLOW='#e9bd78';LINE='#2c484d'
FONTPATH='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MONO='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
font=lambda sz,b=False,mono=False:ImageFont.truetype(MONO if mono else (BOLD if b else FONTPATH),sz)

def frame(n,topic):
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,7),fill=AQUA)
    d.text((45,30),'MUSD  /  PROOF DESK',font=font(20,True),fill=AQUA)
    d.text((W-45,33),'MEZO MAINNET 31612',font=font(14,mono=True),fill=MUTED,anchor='ra')
    d.line((45,82,W-45,82),fill=LINE,width=2)
    d.text((45,670),topic.upper(),font=font(14,mono=True),fill=AQUA)
    d.text((W-45,670),f'{n:02d} / 08',font=font(15,mono=True),fill=MUTED,anchor='ra')
    return im,d

def write(d,lines,x=54,y=170,size=36,dy=54,color=FG,bold=False):
    for line in lines:
        d.text((x,y),line,font=font(size,bold),fill=color)
        y+=dy
    return y

def save(n,im):
    p=FRAMES/f'slide_{n:02d}.png'
    assert not p.exists()
    im.save(p,optimize=True)

im,d=frame(1,'independent original one-person finance infrastructure')
write(d,['On-chain evidence','you can reproduce.'],x=58,y=173,size=58,dy=88,bold=True)
write(d,['MUSD + MEZO supplies. Three verified Mezo pools.','One block, source references, bytecode fingerprints.'],x=60,y=420,size=24,dy=42,color=AQUA)
write(d,['No wallet connection. No transaction. No promises of yield.'],x=60,y=555,size=20,dy=33,color=YELLOW)
save(1,im)

im,d=frame(2,'the problem and the user journey')
write(d,['DeFi dashboards show numbers.','Evidence needs a block.'],x=50,y=137,size=43,dy=68,bold=True)
write(d,['Mezo users can inspect what MUSD / MEZO contracts','actually reported at a known moment, with exact','official pool identities and reproducible source code.'],x=53,y=333,size=24,dy=39,color=MUTED)
d.rectangle((50,508,1220,596),fill=PANEL,outline='#47776f',width=2)
d.text((77,537),'READ  →  PIN  →  VALIDATE  →  EXPLAIN',font=font(27,True,mono=True),fill=AQUA)
save(2,im)

im,d=frame(3,'actual published site screenshot, no mock account')
screen=Image.open(SCREEN).convert('RGB')
# Actual production screenshot, not an AI-created hypothetical UI.
region=screen.crop((0,0,1400,690))
region=ImageOps.contain(region,(1150,535))
im.paste(region,((W-region.width)//2,111))
d.rectangle(((W-region.width)//2,111,(W+region.width)//2,111+region.height),outline='#4f8e84',width=2)
d.rectangle((50,591,1230,625),fill=BG)
d.text((63,597),'Actual HTTPS live page  •  GitHub Pages  •  public read-only JSON',font=font(19),fill=AQUA)
save(3,im)

im,d=frame(4,'real documented on-chain measurements')
write(d,['Real Mezo block',f'#{snap["block"]["number"]:,}'],x=55,y=133,size=50,dy=75,bold=True)
d.text((55,318),'MUSD TOTAL SUPPLY',font=font(17,mono=True),fill=MUTED)
d.text((55,349),f'{float(snap["assets"]["MUSD"]["totalSupply"]):,.0f} MUSD',font=font(36,True),fill=FG)
d.text((55,425),'MEZO TOTAL SUPPLY',font=font(17,mono=True),fill=MUTED)
d.text((55,456),f'{float(snap["assets"]["MEZO"]["totalSupply"]):,.0f} MEZO',font=font(36,True),fill=FG)
d.text((55,568),'All values read from official deployed contracts at one pinned block.',font=font(18),fill=AQUA)
save(4,im)

im,d=frame(5,'three official basic pools measured, not price')
d.text((55,121),'Measured MUSD reserves',font=font(41,True),fill=FG)
sum_bal=float(snap['measuredPoolMUSDReserves'])
d.text((55,188),f'{sum_bal:,.2f} MUSD',font=font(45,True),fill=AQUA)
for idx,p in enumerate(snap['pools']):
    y=282+idx*94
    d.text((55,y),p['name'],font=font(22,True),fill=FG)
    d.text((625,y),f'{float(p["musdReserve"]):,.2f} MUSD',font=font(22,mono=True),fill=AQUA)
    d.rectangle((55,y+41,1195,y+55),fill=LINE)
    d.rectangle((55,y+41,55+int(1140*float(p['musdReserve'])/sum_bal),y+55),fill=AQUA)
d.text((55,615),'Not a swap price, dollar valuation, or solvency statement.',font=font(18),fill=YELLOW)
save(5,im)

im,d=frame(6,'real two-block change check')
write(d,['Two pinned blocks.','Code fingerprints compared.'],x=55,y=129,size=41,dy=69,bold=True)
d.text((55,317),f'#{older["block"]["number"]:,}  →  #{snap["block"]["number"]:,}',font=font(31,mono=True),fill=AQUA)
d.text((55,394),'MUSD + MEZO + three named pool contracts',font=font(24),fill=MUTED)
d.text((55,446),'Runtime SHA-256 drift observed:',font=font(24),fill=MUTED)
d.text((55,484),'NONE ACROSS THESE TWO SAMPLES',font=font(26,True,mono=True),fill=AQUA)
d.text((55,581),'Does NOT prove zero intermediate changes or code safety.',font=font(19),fill=YELLOW)
save(6,im)

im,d=frame(7,'technical proof and rejection gates')
write(d,['Zero wallet permissions.','Twenty-eight tests.'],x=55,y=124,size=48,dy=75,bold=True)
write(d,['Read-only RPC allowlist. Explicit chain ID 31612.','Fail-closed token-pair and ABI validation.','No price guess, trading instruction, signer or gas.'],x=58,y=354,size=23,dy=48,color=MUTED)
d.text((55,596),'Source: github.com/livastic-vm2-primary-20260911/mezo-musd-proof-desk',font=font(17),fill=AQUA)
save(7,im)

im,d=frame(8,'original builder; prize eligibility not claimed')
write(d,['A useful start for','one-person Bitcoin DeFi.'],x=56,y=130,size=47,dy=75,bold=True)
write(d,['MUSD/MEZO discoverability + verifiable release observations.','Track 2: access and distribution for the Mezo ecosystem.'],x=55,y=344,size=22,dy=43,color=MUTED)
d.text((55,489),'Explore the open-source dashboard:',font=font(22),fill=FG)
d.text((55,529),'livastic-vm2-primary-20260911.github.io/mezo-musd-proof-desk/',font=font(16,mono=True),fill=AQUA)
d.text((55,599),'No contest entry, jury award or paying customer is claimed.',font=font(18),fill=YELLOW)
save(8,im)

output=ROOT/'docs/demo.mp4'
assert not output.exists()
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','1/13','-start_number','1',
     '-i',str(FRAMES/'slide_%02d.png'),'-c:v','libx264','-preset','medium','-crf','21','-pix_fmt','yuv420p',
     '-r','24','-movflags','+faststart',str(output)]
subprocess.run(cmd,check=True,timeout=115)
probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',str(output)],capture_output=True,text=True,check=True,timeout=15)
info=json.loads(probe.stdout)['format']
sec=float(info['duration'])
assert 103<=sec<=106,info
print('ORIGINAL_104_SECOND_CAPTIONED_DEMO',str(output),'duration',sec,'bytes',output.stat().st_size,'sha256',hashlib.sha256(output.read_bytes()).hexdigest())
