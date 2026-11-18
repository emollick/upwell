"""Print artwork and finishes for hand-scale interactive equipment."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter

root=Path(__file__).resolve().parents[1];out=root/"unity"/"Assets"/"Upwell"/"SourceModels"/"Textures"
meta=json.loads((out/"materials.json").read_text());atlas=Image.new("RGB",(2048,2048),(42,48,49));rects={}
fontdir=Path("C:/Windows/Fonts")
def f(px,style="regular"):
    for nm in ({"regular":"bahnschrift.ttf","bold":"arialbd.ttf","mono":"consola.ttf"}[style],"DejaVuSans.ttf"):
        for path in (fontdir/nm,Path(nm)):
            try:return ImageFont.truetype(str(path),px)
            except OSError:pass
    return ImageFont.load_default(size=px)
def put(k,im,x,y):
    atlas.paste(im,(x,y));rects[k]=(x+1,y+1,im.width-2,im.height-2)
def bar(d,x,y,w,h,seed,color):
    for j in range(w//4):
        if ((j*seed+j*j*7)%11)<6:d.rectangle((x+j*4,y,x+j*4+1+(j*3)%3,y+h), fill=color)
for j,(id,label,minor) in enumerate((("card_face","SERVICE CREDENTIAL","ACCESS   /   OPERATE   /   MAINTAIN"),
                                      ("card_reverse","B. MORA","LIFT ENGINEERING    /    SERVICE LOCK"))):
    w,h=987,624;im=Image.new("RGB",(w,h),(42,48,51));d=ImageDraw.Draw(im)
    for k in range(23):
        d.line((810+k*9,-4,1010,155-k*5),fill=(57,65,67),width=3)
    d.line((31,148,937,148),fill=(111,126,124),width=2);d.line((26,379,959,379),fill=(171,68,43),width=9)
    d.text((142,36),"UPWELL",font=f(53,"bold"),fill=(214,220,215))
    d.text((794,43),"07",font=f(68,"bold"),fill=(201,210,205));d.text((144,107),"EQUATORIAL VEHICLE SYSTEMS",font=f(15,"mono"),fill=(151,171,174))
    if j==0:
        d.text((271,196),"UPWELL 07",font=f(74),fill=(152,172,173))
        d.text((79,422),label,font=f(41,"regular"),fill=(213,221,213))
        d.text((82,493),minor,font=f(20,"mono"),fill=(138,164,166))
    else:
        d.text((103,195),label,font=f(78,"bold"),fill=(219,225,216))
        d.text((105,300),minor,font=f(23,"mono"),fill=(152,177,178))
        d.text((90,421),"AUTHORIZED SYSTEMS",font=f(31,"bold"),fill=(203,218,214))
        d.text((91,480),"J-BUS   •   P-H01   •   RING A",font=f(25,"mono"),fill=(146,167,171))
    d.text((82,560),"UW07-SVC-884726    /    IC 07-C",font=f(16,"mono"),fill=(142,156,155));bar(d,728,517,190,45,37,(182,193,187))
    put(id,im,6+j*1016,7)
w,h=1364,783;im=Image.new("RGB",(w,h),(15,26,31));d=ImageDraw.Draw(im);mint=(152,217,206);fg=(197,209,201);dim=(100,145,146)
d.text((35,28),"UPWELL",font=f(43,"bold"),fill=mint);d.text((398,37),"CARRIAGE FLIGHT LOG",font=f(33,"mono"),fill=fg)
d.text((1139,43),"UP / 07",font=f(27,"bold"),fill=(214,120,77));d.line((28,101,w-30,101),fill=(74,104,103),width=2)
d.text((36,127),"ENGINEERING WATCH",font=f(21,"mono"),fill=dim);d.text((495,127),"N. IBARRA",font=f(22,"bold"),fill=fg)
d.text((902,127),"LOCAL   /   BUS A",font=f(21,"mono"),fill=mint)
for k,(tm,title,status) in enumerate((("02:46","Optical guide heads cleared","LOGGED"),("03:10","Counterline return verified","NOMINAL"),
                ("03:32","Dock seal held at 101.3 kPa","SEALED"),("03:55","Fiber loop continuity checked","NOMINAL"),
                ("04:09","Blue loom witness stripe holding","NOMINAL"),("04:12","Spare key returned to crew tray","LOGGED"))):
    y=196+k*77;d.line((33,y-10,w-36,y-10),fill=(43,63,68),width=2)
    d.text((41,y+7),tm,font=f(27,"mono"),fill=dim);d.text((227,y+4),title,font=f(31),fill=fg);d.text((1118,y+8),status,font=f(22,"mono"),fill=mint)
d.rectangle((29,681,w-29,741),outline=(62,106,105),width=2);d.text((46,699),"UPLINK READY       /       WATCH 07-A       /       ASTER REACH",font=f(22,"mono"),fill=mint)
put("log_display",im,9,654)
w,h=594,383;im=Image.new("RGB",(w,h),(206,205,186));d=ImageDraw.Draw(im)
d.text((20,16),"PRE-ASCENT  /  07",font=f(35,"bold"),fill=(57,68,67));d.text((21,69),"ENGINEERING WATCH    /    N. IBARRA",font=f(15,"mono"),fill=(83,99,93))
for j,(t,val) in enumerate((("GUIDE OPTICS","CLEAN"),("PRESSURE SEAL","101.3 kPa"),("SERVICE KEY","IN TRAY"),("CAPTURE INDEX","SET"))):
    y=117+52*j;d.line((19,y-6,w-19,y-6),fill=(135,148,137));d.rectangle((22,y+5,40,y+23),outline=(62,80,70),width=2)
    d.line((24,y+12,30,y+19,39,y+6),fill=(108,66,46),width=2);d.text((58,y),t,font=f(19,"mono"),fill=(52,68,63));d.text((371,y),val,font=f(18,"mono"),fill=(68,80,74))
d.text((23,344),"FORM 07-B   /   RETAIN WITH VEHICLE",font=f(14,"mono"),fill=(91,101,92));put("log_checklist",im,1396,658)
specs=[
("optics","UPWELL","FIELD OPTICS    /    8 × 42  •  FG-01"),("focus","FG-01","SEALED   /   OPTICAL ALIGNMENT"),("vessel","UPWELL  07","CREW WATER VESSEL   /   PRESSURE RATED"),
("valve","LOCK   /   VENT","RELIEVE PRESSURE BEFORE OPENING"),("driver","UTA / TQ 04","2.0–9.0 N·m   •   CAL 190-07"),("wallet","UPWELL SERVICE","MECHANICAL SET 04  •  7 PIECES"),
("log_shell","FLIGHT LOG","UP-07    /    ENGINEERING WATCH"),("log_paper","WATCH CARD","01 GUIDE     02 SEAL     03 CAPTURE"),
("optic_lcd","1 072 m","RANGE  /  OPTICS ALIGNED"),("cup_lcd","26.1 °C","SEAL OK     /     101.3 kPa"),
("case_lid","CALIBRATION","TQ-04   /   LOCKOUT AND VERIFY"),("bit_tag","BIT SET","T15    T20    HEX    4 mm")]
for k,(id,title,sub) in enumerate(specs):
    w,h=484,121;dark=id in ("optic_lcd","cup_lcd","case_lid","bit_tag")
    bg=(22,33,36) if dark else (184,190,183); ink=(160,222,207) if dark else (45,58,60)
    im=Image.new("RGB",(w,h),bg);d=ImageDraw.Draw(im);d.rectangle((5,6,11,h-8),fill=(154,67,44))
    d.text((22,11),title,font=f(min(43,500//(len(title)+1)),"bold"),fill=ink)
    d.line((23,70,w-17,70),fill=(113,137,134),width=1);d.text((23,82),sub,font=f(14,"mono"),fill=ink)
    put(id,im,8+(k%4)*510,1483+(k//4)*155)
atlas.save(out/"Handheld_Atlas.jpg",quality=93);(out/"handheld_atlas.json").write_text(json.dumps({"size":[2048,2048],"rects":rects},indent=2))
ink=Image.new("RGBA",atlas.size,(0,0,0,0))
for key in ("vessel","optics","focus","driver","log_shell","valve","log_paper"):
    x,y,w,h=rects[key];tile=np.asarray(atlas.crop((x,y,x+w,y+h))).astype(float)
    coverage=(np.linalg.norm(tile-np.array([184,190,183])[None,None,:],axis=-1)/72).clip(0,1)
    rgba=np.dstack((tile,255*coverage)).astype("uint8");ink.paste(Image.fromarray(rgba),(x,y))
ink.save(out/"Handheld_Ink.png")
meta["Handheld_Markings"]=dict(rgb=[255]*3,baseColor="Handheld_Ink.png",alpha=1,alphaFromMap=True,roughness=.50,metallic=.08)
gy,gx=np.meshgrid(np.linspace(-1,1,384),np.linspace(-1,1,384),indexing="ij")
rad=np.hypot(gx,gy).clip(0,1);inc=np.clip(rad+.045*gx-.035*gy,0,1)
levels=[0,.36,.67,.86,1.];tints=np.array([[24,41,51],[29,64,73],[36,84,82],[63,78,96],[103,74,113]])
coating=np.stack([np.interp(inc,levels,tints[:,i]) for i in range(3)],-1)
# A multilayer objective's residual sheen changes hue from centre to rim.
# This is a coating lookup only; the live environment still supplies reflected scene detail.
edge=np.exp(-((rad-.83)/.12)**2)*(.54+.46*np.sin(np.arctan2(gy,gx)+.22))
coating+=edge[:,:,None]*np.array([15,30,24])[None,None,:]
Image.fromarray(coating.astype("uint8")).save(out/"Optical_Interference.jpg",quality=94)
for name,emit in (("Service_Print",0),("Handheld_Display",.63)):
    meta[name]=dict(rgb=[255,255,255],alpha=1,metallic=.12,roughness=.43,baseColor="Handheld_Atlas.jpg",emission=emit)
for name,rgb,rough,metal,alpha in (("Optical_Coating",[24,70,78],.068,.62,1),("Optical_Laminate",[87,121,133],.047,.31,.105),
              ("Credential_Contacts",[154,135,82],.27,.86,1)):
    meta[name]=dict(rgb=rgb,alpha=alpha,metallic=metal,roughness=rough)
meta["Optical_Coating"].update(baseColor="Optical_Interference.jpg",coat=.91,coatRoughness=.055,iridescence=.42,emission=.18)
meta["Optical_Laminate"].update(coat=.82,coatRoughness=.05,transmission=.38)
meta["Handheld_Display"].update(roughness=.34,metallic=.035,specular=.20)
for name,src,rgb in (("Grip_Elastomer","Black_Rubber",[42,46,44]),("Wallet_Canvas","Technical_Twill",[69,76,74])):
    base=meta[src];d={**base,"rgb":rgb}
    for k,suf in (("baseColor","Color"),("roughnessMap","Roughness"),("normal","Normal")):
        if k not in base:continue
        dest=name+"_"+suf+".jpg";(out/dest).write_bytes((out/base[k]).read_bytes());d[k]=dest
    meta[name]=d
for name,src,scan,norm,metal in (("Precision_Titanium","Titanium","metal_plate",.19,.84),("Anodized_Frame","Graphite_Alloy","metal_plate",.16,.63),
                                 ("Handheld_Shell","Ceramic_Pearl","blue_metal_plate",.14,.30)):
    # Hand-scale parts use a clean region from the measured finish. Large floor-
    # and plate-scale embossing would imply centimetre dents in a millimetre bezel.
    scan_dir=root/"art"/"surface-scans"/scan;al=Image.open(scan_dir/"albedo.jpg").convert("RGB")
    tile=320;proxy=np.asarray(al.convert("L"),float);candidates=[]
    for yy in range(64,al.height-tile-32,147):
        for xx in range(64,al.width-tile-32,147):
            patch=proxy[yy:yy+tile,xx:xx+tile];score=patch.std()+1.8*np.std(np.diff(patch,axis=0))
            candidates.append((score,xx,yy))
    _,xx,yy=min(candidates);d={**meta[src],"normalStrength":norm,"metallic":metal}
    for key,suf,channel in (("baseColor","Color","albedo"),("normal","Normal","normal"),("roughnessMap","Roughness","roughness")):
        im=Image.open(scan_dir/(channel+".jpg")).convert("RGB").crop((xx,yy,xx+tile,yy+tile));a=np.asarray(im,float)
        if key=="baseColor":
            lum=np.mean(a,axis=2);low=np.asarray(Image.fromarray(lum.astype("uint8")).filter(ImageFilter.GaussianBlur(12)),float)
            value=(lum-low)*.41+(low-low.mean())*.10;a=np.array(d["rgb"])[None,None,:]+value[:,:,None]
        elif key=="normal":
            normal=(a-127.5)/127.5;normal[:,:,:2]-=np.mean(normal[:,:,:2],axis=(0,1));normal[:,:,:2]*=.38;normal[:,:,2]=1
            normal/=np.linalg.norm(normal,axis=2,keepdims=True);a=(normal*.5+.5)*255
        else:a=np.clip(d["roughness"]*255+(a-a.mean(axis=(0,1)))*.21,26,235)
        a=np.uint8(np.clip(a,0,255));top=np.concatenate((a,np.flip(a,axis=1)),axis=1);seam=np.concatenate((top,np.flip(top,axis=0)),axis=0)
        fn=name+"_"+suf+".jpg";Image.fromarray(seam).save(out/fn,quality=90);d[key]=fn
    meta[name]=d
meta["Grip_Elastomer"]["normalStrength"]=.22;meta["Wallet_Canvas"]["normalStrength"]=.34
(out/"materials.json").write_text(json.dumps(meta,indent=2))
