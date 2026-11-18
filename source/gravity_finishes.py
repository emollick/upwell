"""Print and finish masters for the carriage's mechanical load and fluid instruments."""
from pathlib import Path
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"unity"/"Assets"/"Upwell"/"SourceModels"/"Textures"
atlas=Image.new("RGB",(2048,2048),(44,51,52));rects={}
def font(px,kind="normal"):
    for nm in ({"normal":"bahnschrift.ttf","bold":"arialbd.ttf","mono":"consola.ttf"}[kind],"DejaVuSans.ttf"):
        for p in (Path("C:/Windows/Fonts")/nm,Path(nm)):
            try:return ImageFont.truetype(str(p),px)
            except OSError:pass
    return ImageFont.load_default(size=px)
def tile(key,im,x,y):
    atlas.paste(im,(x,y));rects[key]=[x+1,y+1,im.width-2,im.height-2]
def label(key,head,sub,x,y,w=655,h=137,dark=False):
    bg=(43,52,53) if dark else (195,200,192);fg=(224,232,218) if dark else (40,56,58);accent=(186,91,53)
    im=Image.new("RGB",(w,h),bg);d=ImageDraw.Draw(im)
    d.rectangle((8,10,17,h-11),fill=accent)
    d.text((30,7),head,font=font(min(60,int((w-70)*1.43/len(head))),"bold"),fill=fg)
    d.line((30,int(h*.62),w-14,int(h*.62)),fill=(130,147,143),width=2)
    d.text((30,int(h*.71)),sub,font=font(max(12,min(24,int((w-59)*1.62/max(1,len(sub))))),"mono"),fill=fg)
    tile(key,im,x,y)

w,h=416,1334
im=Image.new("RGB",(w,h),(209,210,193));d=ImageDraw.Draw(im)
ylo,yhi=1.117,1.412
def vpx(value):return round((yhi-(1.349-value*.162))/(yhi-ylo)*(h-1))
d.rectangle((4,4,w-5,h-5),outline=(129,142,136),width=3)
d.rectangle((10,vpx(-.18),18,vpx(0)),fill=(173,86,62))
d.rectangle((10,vpx(0)+1,18,vpx(1.18)),fill=(74,101,96))
d.text((32,17),"AXIAL  /  g",font=font(38,"mono"),fill=(58,78,76))
for i in range(-18,119,2):
    g=i/100;yy=vpx(g);l=65 if i%10==0 else 32
    d.line((20,yy,20+l,yy),fill=(43,62,60),width=4 if i%10==0 else 2)
for value,txt in ((-.15,"−.15"),(0,"0"),(.25,"+.25"),(.5,"+.50"),(.75,"+.75"),(1,"+1.00"),(1.15,"+1.15")):
    yy=vpx(value);d.line((19,yy,109,yy),fill=(147,64,45) if value<0 else (44,60,60),width=5)
    d.text((122,yy),txt,anchor="lm",font=font(64 if value in (0,1) else 44,"bold"),fill=(145,67,49) if value<0 else (45,60,59))
d.text((30,h-72),"AX-07   /   g",font=font(27,"mono"),fill=(77,94,89))
tile("load_scale",im,6,6)

side=840;im=Image.new("RGB",(side,side),(190,203,185));d=ImageDraw.Draw(im);c=side/2
for x in range(0,side,15):
    for y in range(0,side,15):
        if math.hypot(x-c,y-c)<c-5:d.ellipse((x,y,x+2,y+2),fill=(149,168,153))
for q in (.26,.51,.77,.963):
    r=c*q;d.ellipse((c-r,c-r,c+r,c+r),outline=(114,141,127),width=3)
for j in range(72):
    a=j*math.tau/72;r=c*.948;end=r-(22 if j%6==0 else 9)
    d.line((c+math.cos(a)*r,c+math.sin(a)*r,c+math.cos(a)*end,c+math.sin(a)*end),fill=(38,72,69),width=5 if j%6==0 else 3)
for y,lab in ((.29,"40"),(.50,"0"),(.71,"40")):
    yp=int(side*y);d.line((side*.62,yp,side*.72,yp),fill=(53,80,70),width=5)
    d.text((side*.73,yp),lab,anchor="lm",font=font(31,"mono"),fill=(52,77,70))
d.line((c-14,c,c+14,c),fill=(96,124,113),width=2);d.line((c,c-14,c,c+14),fill=(96,124,113),width=2)
d.text((c,side*.802),"CX / 07",font=font(24,"mono"),anchor="mm",fill=(85,107,97))
tile("cell_screen",im,435,10)
label("load_title","AXIAL LOAD","MECHANICAL ACCELEROMETER    /    AX-07",1304,10,722,157)
label("load_test","TEST  +0.10 g","SPRING RETURN",1304,183,722,140)
label("load_serial","AX-07 / 214","FLEXURE SUSPENSION     •     CAL 04",1304,340,722,127,True)
label("cell_title","CAPILLARY CELL","CX-07    /    CLOSED FLUID LOOP",435,874,840,150)
label("cell_volume","FILL  77%","LIQUID CHARGE   /   20 °C",435,1040,454,137)
label("cell_prime","PRIME","ONE PULSE",1304,510,350,125)
label("service_power","PWR / 6","FLEXIBLE SERVICE RETURN",1304,669,703,110)
label("service_fiber","FO / 11","OPTICAL SERVICE LOOP",1304,802,703,110)
label("quilt_tag","UPWELL / 02","BERTH RESTRAINT     •     B-217",435,1210,744,126)
label("fluid_serial","CX-07 / 031","77 : 23     /     E-02 GALLEY CIRCUIT",1304,946,722,124,True)
atlas.save(OUT/"Gravity_Instruments.jpg",quality=94)
(OUT/"gravity_atlas.json").write_text(json.dumps({"size":list(atlas.size),"rects":rects},indent=2))
specs=json.loads((OUT/"materials.json").read_text())
extra={
"Gravity_Print":dict(rgb=[255]*3,roughness=.53,metallic=.16,alpha=1,baseColor="Gravity_Instruments.jpg"),
"Cell_Diffuser":dict(rgb=[255]*3,roughness=.49,metallic=.02,alpha=1,baseColor="Gravity_Instruments.jpg",emission=.61),
"Cell_Backlight":dict(rgb=[243,218,153],roughness=.38,metallic=.06,alpha=1,emission=1.38),
"Cell_Optical_Glass":dict(rgb=[194,217,214],roughness=.105,metallic=.10,alpha=.065,transmission=.28,coat=.69,coatRoughness=.09),
"Cell_Liquid":dict(rgb=[213,164,62],roughness=.065,metallic=0,alpha=.47,transmission=.70,coat=.34,coatRoughness=.045,ior=1.333),
"Cell_Gas":dict(rgb=[203,217,205],roughness=.065,metallic=0,alpha=.09,transmission=.77,coat=.35,coatRoughness=.05,ior=1.05),
"Cell_Meniscus":dict(rgb=[137,155,124],roughness=.105,metallic=.19,alpha=.80,coat=.74,coatRoughness=.06),
"Load_Index":dict(rgb=[220,100,49],roughness=.36,metallic=.33,alpha=1,emission=.12),
"Load_Mass":dict(rgb=[91,96,92],roughness=.29,metallic=.82,alpha=1),
"Cell_Etch":dict(rgb=[45,70,65],roughness=.65,metallic=.11,alpha=1),
"Wick_Mesh":dict(rgb=[139,125,88],roughness=.48,metallic=.65,alpha=1)}
def measured_cloth(name,source,rgb,rough,contrast,reinforced=False):
    directory=ROOT/"art"/"surface-scans"/source;size=1024
    def channel(n,mode):
        return Image.open(directory/(n+".jpg")).convert(mode).resize((size,size),Image.Resampling.LANCZOS)
    col=channel("albedo","L");broad=np.asarray(col.filter(ImageFilter.GaussianBlur(29)),float)
    yarn=np.asarray(col,float)-broad;stitched=False
    normal=np.asarray(channel("normal","RGB"),float)/127.5-1
    if reinforced:
        # A fine paired-yarn ripstop grid is woven through the captured cloth.
        # This full tile is 302 mm wide, and each pair is 5.4 mm on centre.
        y,x=np.mgrid[:size,:size]/size
        def pair(t,warp):
            phase=(t*56+.032*np.sin(2*np.pi*warp*7))%1
            def pulse(c):return np.exp(-(((phase-c+.5)%1-.5)/.045)**2)
            return pulse(.32)+.68*pulse(.46)
        stitched=np.maximum(pair(x,y),pair(y,x));sgy,sgx=np.gradient(stitched)
        normal[:,:,0]-=.29*sgx;normal[:,:,1]+=.29*sgy
    lum=np.clip(yarn*contrast/max(1,np.std(yarn))+.42*(broad-np.median(broad)),-39,39)
    color=np.array(rgb)[None,None,:]+lum[:,:,None]+(stitched[:,:,None]*7.0 if reinforced else 0)
    measured=np.asarray(channel("roughness","L"),float)/255
    r=np.clip(rough+(measured-np.median(measured))*.72-.022*stitched,.72,.99)
    normal/=np.maximum(.001,np.linalg.norm(normal,axis=2,keepdims=True))
    d=dict(rgb=rgb,roughness=rough,metallic=0.,alpha=1.,normalStrength=.76,specular=.24,sheen=.24,sheenRoughness=.65)
    for key,suffix,ar in (("baseColor","Color",color),("normal","Normal",(normal*.5+.5)*255),("roughnessMap","Roughness",r*255)):
        fn=name+"_"+suffix+".jpg";Image.fromarray(np.uint8(np.clip(ar,0,255))).save(OUT/fn,quality=94,subsampling=0);d[key]=fn
    extra[name]=d

measured_cloth("Quilt_Ripstop","terlenka",[88,104,101],.89,11.8,True)
measured_cloth("Quilt_Lining","terlenka",[140,147,135],.88,9.)
measured_cloth("Curtain_Acoustic","denim_fabric_06",[111,127,123],.91,13.8)
measured_cloth("Berth_Bias_Tape","denim_fabric_06",[67,78,77],.86,9.5)
specs.update(extra)
(OUT/"materials.json").write_text(json.dumps(specs,indent=2))
