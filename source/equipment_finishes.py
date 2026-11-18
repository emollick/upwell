"""Author the galley vessel's registered enamel and the hand tools' moulded grip."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/"unity/Assets/Upwell/SourceModels/Textures"
SCAN=ROOT/"art/surface-scans"
rng=np.random.default_rng(33207)


def normal_map(height,strength):
    dy,dx=np.gradient(height)
    normal=np.stack((-dx*strength,dy*strength,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    return Image.fromarray(np.uint8(np.clip((normal*.5+.5)*255,0,255)))


def write(name,albedo,rough,height,strength):
    Images=(Image.fromarray(np.uint8(np.clip(albedo,0,255))),Image.fromarray(np.uint8(np.clip(rough*255,0,255))),normal_map(height,strength))
    for suffix,img in zip(("Color","Roughness","Normal"),Images):
        img.save(LIB/f"{name}_{suffix}.jpg",quality=93,subsampling=0,optimize=True)


def enamel():
    w,h=2048,896
    y,x=np.mgrid[0:h,0:w];u=(x+.5)/w;v=1-(y+.5)/h
    grain=rng.normal(size=(h,w)).astype(np.float32)
    # Use the scan's high-frequency reflectance, separating its photographed light.
    scan=Image.open(SCAN/"blue_metal_plate/albedo.jpg").convert("L")
    tile=np.asarray(scan.resize((w,h),Image.Resampling.LANCZOS),dtype=np.float32)
    tooth=np.clip(tile-gaussian_filter(tile,9),-16,16)
    peel=gaussian_filter(grain,1.35,mode="wrap");peel/=peel.std()
    slow=gaussian_filter(grain,22,mode="wrap");slow/=slow.std()
    def stamp(cu,cv,ru,rv):
        du=np.minimum(np.abs(u-cu),1-np.abs(u-cu))
        return np.exp(-.5*((du/ru)**2+((v-cv)/rv)**2))
    thumb=stamp(.68,.70,.075,.16)+stamp(.85,.37,.052,.145)
    circumference=.292; height=.125
    base=np.array([184.,192.,185.])+(.64*slow+.34*tooth+.78*peel)[:,:,None]
    rough=np.clip(.48+.021*peel+.015*slow-.108*thumb,.26,.58)
    relief=.40*peel+.105*tooth
    # Burnishing follows the attachment and the restraint foot. Hairlines are
    # interrupted, sparse and strongest in the real contact zones.
    marks=Image.new("L",(w,h));d=ImageDraw.Draw(marks)
    for j in range(245):
        cx=rng.uniform(0,w);at=rng.choice((.12,.19,.76,.86),p=[.45,.18,.12,.25])
        cy=(1-at+rng.normal(0,.027))*h
        length=rng.uniform(.0007,.0044)*w/circumference;rise=rng.normal(0,.0011)*h/height
        d.line((cx,cy,cx+.48*length,cy+.33*rise,cx+length,cy+rise),fill=int(rng.uniform(16,101)),width=1)
    scratch=np.asarray(marks.filter(ImageFilter.GaussianBlur(.36)),dtype=float)/255
    base-=scratch[:,:,None]*34;rough-=.15*scratch;relief-=scratch*1.9
    # Residual contact marks change the specular lobe under a passing light.
    du=(u-.69)*circumference;dv=(v-.70)*height
    radius=np.sqrt((du+.30*dv)**2+(dv*.72)**2)
    ridge=.5+.5*np.cos(2*np.pi*radius/.00043+.46*np.sin(dv*180))
    rough-=.028*stamp(.69,.70,.039,.071)*ridge
    ink=Image.new("L",(w,h));pen=ImageDraw.Draw(ink)
    font=ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf",30)
    micro=ImageFont.truetype("C:/Windows/Fonts/consola.ttf",19)
    pen.text((195,476),"GALLEY  /  320 mL",font=font,fill=173,stroke_width=0)
    pen.line((197,520,462,520),fill=129,width=2)
    pen.text((197,528),"HB-332   |   CAR 07",font=micro,fill=150)
    mask=np.asarray(ink,dtype=float)/255
    base=base*(1-mask[:,:,None])+np.array([53,65,66])*mask[:,:,None]
    rough+=mask*.058
    write("Vessel_Enamel",base,rough,relief,.32)


def elastomer():
    size=768
    base=np.asarray(Image.open(SCAN/"rubber_tiles/albedo.jpg").convert("L").resize((size,size)),dtype=np.float32)
    grain=np.clip(base-gaussian_filter(base,7),-12,12)
    random=rng.normal(size=(size,size)).astype(np.float32)
    stipple=gaussian_filter(random,1.18,mode="wrap");stipple/=stipple.std()
    fine=.72*stipple+.14*grain
    shade=np.array([45.,51.,49.])+fine[:,:,None]*1.48
    write("Grip_Elastomer",shade,np.clip(.72+fine*.025,.60,.81),fine,.52)


def keeper():
    size=640
    yy,xx=np.mgrid[0:size,0:size];x=(xx-size/2)/size;y=(yy-size/2)/size
    radius=np.hypot(x,y);angle=np.arctan2(y,x)
    tool=np.sin(2*np.pi*radius*158+.21*np.sin(angle*3))*1.8+np.sin(radius*444)*.8
    grain=gaussian_filter(rng.normal(size=(size,size)),.75)
    base=np.array([132.,141.,139.])+(tool+grain*.64)[:,:,None]
    ink=Image.new("L",(size,size));p=ImageDraw.Draw(ink)
    p.text((320,270),"HB 332 / 07",font=ImageFont.truetype("C:/Windows/Fonts/bahnschrift.ttf",34),fill=143,anchor="mm")
    p.line((215,303,425,303),fill=123,width=2)
    p.text((320,332),"MAGNETIC FOOT",font=ImageFont.truetype("C:/Windows/Fonts/consola.ttf",20),fill=150,anchor="mm")
    stamp=np.asarray(ink)/255; base=base*(1-stamp[:,:,None])+np.array([45,53,54])*stamp[:,:,None]
    rough=np.clip(.33+.027*tool+.012*grain+.18*stamp,.20,.58)
    write("Vessel_Keeper",base,rough,.27*tool+.19*grain-1.7*stamp,.39)


if __name__=="__main__":
    enamel();elastomer();keeper()
    index=LIB/"materials.json";materials=json.loads(index.read_text())
    materials["Vessel_Enamel"]={"rgb":[184,192,185],"roughness":.48,"metallic":.035,"alpha":1,"family":"coating",
        "normalStrength":.55,"baseColor":"Vessel_Enamel_Color.jpg","roughnessMap":"Vessel_Enamel_Roughness.jpg","normal":"Vessel_Enamel_Normal.jpg"}
    materials["Grip_Elastomer"].update(roughness=.72,normalStrength=.47)
    materials["Vessel_Keeper"]={"rgb":[132,141,139],"roughness":.33,"metallic":.83,"alpha":1,"family":"metal",
        "normalStrength":.48,"baseColor":"Vessel_Keeper_Color.jpg","roughnessMap":"Vessel_Keeper_Roughness.jpg","normal":"Vessel_Keeper_Normal.jpg"}
    index.write_text(json.dumps(materials,indent=2),encoding="utf-8")
