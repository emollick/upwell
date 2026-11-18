"""Shared measured finishes and hull markings for the Pelagic Anchor fleet."""
from pathlib import Path
import json
import math
import random

ROOT=Path(__file__).resolve().parents[1]
TEX=ROOT/'unity/Assets/Upwell/Resources/Harbor'
WEB=ROOT/'web/assets/harbor'

def finish(name,color,metal,rough,image='',normal='',strength=0.,alpha=1.,emit='#000000',gain=0.):
    return dict(name='Harbor_'+name,color=color,metal=metal,rough=rough,image=image,
                normal=normal,normalStrength=strength,alpha=alpha,emit=emit,gain=gain)

MATERIALS=[finish('CoatedPlate','#ffffff',.12,.60,'harbor-paint','harbor-grain',.18),
    finish('Deck','#ffffff',.11,.78,'harbor-deck','harbor-grain',.47),
    finish('Rubber','#272b2a',.035,.81),finish('DampRubber','#363e3d',.08,.58),
    finish('Alloy','#8b9290',.77,.36),finish('Enamel','#d5d9ce',.22,.48),
    finish('Graphite','#343f43',.48,.46),finish('Safety','#d76d35',.19,.49),
    finish('Ochre','#cda650',.32,.55),finish('Rope','#98866c',.02,.84),
    finish('Glass','#39535c',.18,.23,alpha=.74),finish('Mark','#ffffff',.08,.57,'harbor-signs'),
    finish('Lens','#efddb1',.06,.24,emit='#ffe3b1',gain=.35),
    finish('Port','#c13e32',.06,.28,emit='#ff4736',gain=.5),
    finish('Starboard','#468363',.07,.28,emit='#75c7a4',gain=.53)]

PALETTE={'navy':(43,70,80),'tug-red':(160,61,43),'antifoul':(94,58,50),'slime':(76,81,64),
         'ivory':(209,211,193),'orange':(205,102,44),'psv-blue':(52,99,133),'ochre':(191,155,86),
         'green':(54,117,88),'slate':(91,108,109),'rust':(118,74,48),'black':(59,67,66),
         'cyan':(70,135,132),'rescue':(203,176,78),'yellow':(210,169,74),'grey':(153,161,157),
         'timber0':(101,96,78),'timber1':(112,105,85),'timber2':(108,102,85),'timber3':(96,94,81)}
SLOTS=list(PALETTE)

def textures():
    import numpy as np
    from PIL import Image,ImageDraw,ImageFont,ImageFilter
    TEX.mkdir(parents=True,exist_ok=True);WEB.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(18416);paint=Image.new('RGB',(1024,1280));data={}
    scan=Image.open(ROOT/'art/surface-scans/blue_metal_plate/albedo.jpg').convert('L')
    surface=np.asarray(scan.resize((256,256),Image.Resampling.LANCZOS),float)
    base=(surface-np.asarray(Image.fromarray(surface.astype('uint8')).filter(ImageFilter.GaussianBlur(6)),float))
    base=np.clip(base,-19,19)*.30
    for i,(key,col) in enumerate(PALETTE.items()):
        x=(i%4)*256;y=(i//4)*256
        cloud=np.asarray(Image.fromarray(rng.integers(80,170,(18,18),dtype='uint8')).resize((256,256),Image.Resampling.BICUBIC),float)
        lum=base+(cloud-125)*.12+rng.normal(0,1.6,(256,256))
        if key.startswith('timber'):
            vertical=np.asarray(Image.fromarray(rng.integers(70,180,(13,256),dtype='uint8')).resize((256,256),Image.Resampling.BICUBIC),float)
            lum+=(vertical-125)*.32
        pixels=np.uint8(np.clip(np.array(col)[None,None,:]+lum[:,:,None],0,255));tile=Image.fromarray(pixels);d=ImageDraw.Draw(tile)
        rr=random.Random(98+i)
        for k in range(24 if key in ('tug-red','psv-blue','antifoul','rust','green') else 8):
            xx=rr.randrange(7,242);yy=rr.randrange(15,242);dl=rr.randrange(2,18)
            tone=tuple(max(18,int(v*(.81+rr.random()*.12))) for v in col)
            d.line((xx,yy,xx+rr.choice((0,0,1)),yy+dl),fill=tone,width=1)
        paint.paste(tile,(x,y));data[key]=[x+3,y+3,250,250]
    paint.save(TEX/'harbor-paint.jpg',quality=90,subsampling=0,optimize=True)
    grain=Image.open(ROOT/'art/surface-scans/blue_metal_plate/normal.jpg').convert('RGB').resize((384,384),Image.Resampling.LANCZOS)
    mod=np.asarray(grain,float)/127.5-1.;mod[:,:,:2]-=np.mean(mod[:,:,:2],axis=(0,1));mod[:,:,:2]*=.37
    mod[:,:,2]=np.sqrt(np.maximum(.004,1-np.sum(mod[:,:,:2]**2,axis=2)));mod/=np.linalg.norm(mod,axis=2,keepdims=True)
    Image.fromarray(np.uint8(np.clip((mod*.5+.5)*255,0,255))).save(TEX/'harbor-grain.jpg',quality=89,subsampling=0)
    deck=Image.new('RGB',(768,768));dd=np.array((73,82,78))[None,None,:]+rng.normal(0,6.7,(768,768,1))
    deck=Image.fromarray(np.uint8(np.clip(dd,0,255)));d=ImageDraw.Draw(deck);rr=random.Random(840)
    for k in range(295):
        x=rr.randrange(768);y=rr.randrange(768);size=rr.randrange(1,6);tone=rr.choice(((101,103,90),(50,62,62),(91,96,87)))
        d.line((x,y,x+size,y+rr.randrange(-1,3)),fill=tone)
    deck.save(TEX/'harbor-deck.jpg',quality=89,optimize=True)

    atlas=Image.new('RGB',(1024,1024));rect={};rows=[('tug','NEREID','PE L A G I C   /   T O W A G E',PALETTE['navy']),
        ('tugcall','PA  07','ANCHOR HARBOUR',PALETTE['ivory']),('supply','CEIBA','P E L A G I C   /   O F F S H O R E',PALETTE['psv-blue']),
        ('pilot','PILOT','TRANSFER  /  12',PALETTE['orange']),('pilothull','P 12','PELAGIC ANCHOR',PALETTE['navy']),
        ('cargo','H039','TIDAL SERVICE',PALETTE['cyan']),('buoy','P  4','PELAGIC',PALETTE['green']),('raft','6 PERSON','LIFERAFT  /  SERVICE',PALETTE['ivory'])]
    def font(px,bold):
        return ImageFont.truetype('C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'bahnschrift.ttf'),px)
    for i,(key,title,sub,col) in enumerate(rows):
        x,y=(i%2)*512,(i//2)*225;im=Image.new('RGB',(512,225),col);dr=ImageDraw.Draw(im)
        light=sum(col)>440 and key!='pilot';ink=(42,54,57) if light else (224,222,194)
        scale=124
        while dr.textbbox((0,0),title,font=font(scale,True))[2]>464:scale-=3
        dr.text((256,93),title,font=font(scale,True),fill=ink,anchor='mm',stroke_width=0)
        dr.text((256,173),sub,font=font(23,False),fill=ink,anchor='mm')
        atlas.paste(im,(x,y));rect[key]=[x+3,y+3,506,219]
    for pos,key,title,sub,col in ((0,'tughouse','NEREID','HARBOUR ASSIST  /  07',PALETTE['ivory']),(512,'transom','CEIBA','PELAGIC ANCHOR',PALETTE['psv-blue'])):
        im=Image.new('RGB',(512,120),col);dr=ImageDraw.Draw(im);ink=(42,55,59) if pos==0 else (221,223,204)
        dr.text((256,45),title,font=font(76,True),fill=ink,anchor='mm');dr.text((256,99),sub,font=font(17,False),fill=ink,anchor='mm')
        atlas.paste(im,(pos,902));rect[key]=[pos+3,904,506,114]
    atlas.save(TEX/'harbor-signs.jpg',quality=94,subsampling=0,optimize=True)
    (TEX/'fleet-atlas.json').write_text(json.dumps(dict(size=[1024,1024],paintSize=[1024,1280],paint=data,marks=rect),indent=2))
    recipe=dict(units='m',materials=MATERIALS)
    for target in (WEB,TEX):(target/'finishes.json').write_text(json.dumps(recipe,indent=2))

if __name__=='__main__':textures()
