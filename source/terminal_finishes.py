"""Prepare the dockyard finish tiles and terminal instrumentation print master."""
from pathlib import Path
import json
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"unity"/"Assets"/"Upwell"/"Terminals"/"Textures"
OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(57612);rs=random.Random(457)
s=512;xx,yy=np.meshgrid(np.arange(s),np.arange(s))
def noise(gx,gy):
    b=rng.integers(0,256,(gy,gx),dtype=np.uint8);b=np.pad(b,2,mode="wrap")
    tile=Image.fromarray(b).resize((math.ceil((gx+4)*s/gx),math.ceil((gy+4)*s/gy)),Image.Resampling.BICUBIC)
    ox,oy=round(2*s/gx),round(2*s/gy)
    return (np.asarray(tile.crop((ox,oy,ox+s,oy+s)),float)-127)/128
materials={}
for name,rgb,rgh,met,kind in [
        ("Marine_Primer",(72,99,96),.51,.46,"paint"),("Marine_Vermilion",(159,75,50),.49,.41,"paint"),
        ("Tidal_Deck",(67,75,77),.54,.56,"deck"),("Structural_Galvanized",(146,154,150),.38,.78,"metal"),
        ("Orbital_Porcelain",(176,180,172),.44,.33,"ceramic"),("Capture_Blue",(39,69,85),.39,.52,"paint")]:
    low=noise(5,7);mid=noise(17,16);grain=rng.normal(size=(s,s))
    streak=np.maximum(0,noise(75,6)-.39)*(0.47+noise(6,9)*.26)
    pits=np.clip((noise(91,86)+.18*mid-.55)*1.8,0,1)
    damp=np.maximum(0,mid+.39*low-.4)
    scratches=Image.new("L",(s,s));dr=ImageDraw.Draw(scratches)
    for j in range(148 if kind!="ceramic" else 50):
        x=rs.randrange(s);y=rs.randrange(s);ang=rs.uniform(-1.6,1.6);ln=rs.expovariate(1/8)
        for dx in (-s,0,s):
            for dy in (-s,0,s):dr.line((x+dx,y+dy,x+dx+math.cos(ang)*ln,y+dy+math.sin(ang)*ln),fill=rs.randrange(45,170))
    sc=np.asarray(scratches,float)/255
    detail=low*7+mid*3+grain*1.7-streak*17-pits*11-sc*26
    height=mid*.12+grain*.08-pits*.55-sc*.8
    if kind=="metal":detail=noise(45,53)*10+grain*2.1+low*7-sc*25;height=grain*.10+mid*.13
    elif kind=="deck":
        diamond=(np.minimum((xx+yy)%32,(-xx-yy)%32)<2)&(np.abs(((xx-yy)%64)-32)<14)
        detail+=diamond*12-damp*11;height+=diamond*1.2
    elif kind=="ceramic":detail*=.50;height*=.53
    base=np.array(rgb)[None,None,:]+detail[:,:,None]
    if kind=="paint":base+=np.stack((damp*5,-damp*1.4,-damp*3.7),axis=-1)
    rough=np.clip(rgh*255+low*14+mid*9+streak*13+sc*27-(damp*47 if kind=="deck" else 0),35,242)
    ddx=(np.roll(height,-1,1)-np.roll(height,1,1))*.28;ddy=(np.roll(height,-1,0)-np.roll(height,1,0))*.28
    norm=np.stack((-ddx,ddy,np.ones_like(ddx)),axis=-1);norm/=np.linalg.norm(norm,axis=2,keepdims=True)
    fcolor=name+"_Color.jpg";fnormal=name+"_Normal.jpg";frough=name+"_Roughness.jpg"
    Image.fromarray(base.clip(0,255).astype("uint8")).save(OUT/fcolor,quality=88)
    Image.fromarray(((norm*.5+.5)*255).astype("uint8")).save(OUT/fnormal,quality=87)
    Image.fromarray(rough.astype("uint8")).save(OUT/frough,quality=87)
    materials[name]=dict(rgb=rgb,alpha=1,metallic=met,roughness=rgh,baseColor=fcolor,roughnessMap=frough,normal=fnormal)
scanroot=ROOT/"art"/"surface-scans"
if (scanroot/"hangar_concrete_floor"/"albedo.jpg").is_file():
    for name,source,rgb,rough,met in (("Pier_Concrete","hangar_concrete_floor",(120,126,124),.73,.07),
        ("Marine_Primer","blue_metal_plate",(72,99,96),.51,.46)):
        files={}
        for key,src,suf in (("baseColor","albedo","Color"),("roughnessMap","roughness","Roughness"),("normal","normal","Normal")):
            data=np.asarray(Image.open(scanroot/source/(src+".jpg")).convert("RGB").resize((768,768),Image.Resampling.LANCZOS),float)
            if key=="baseColor":
                lum=data.mean(axis=2);data=np.array(rgb)[None,None,:]+(lum-lum.mean())[:,:,None]*(.46 if name=="Pier_Concrete" else .24)
            elif key=="roughnessMap":data=rough*255+(data-data.mean())*.53
            elif name=="Marine_Primer":
                n=data/127.5-1;n[:,:,:2]*=.45;n[:,:,2]=1;n/=np.linalg.norm(n,axis=2,keepdims=True);data=(n*.5+.5)*255
            file=name+"_"+suf+".jpg";Image.fromarray(np.uint8(data.clip(0,255))).save(OUT/file,quality=88);files[key]=file
        materials[name]=dict(rgb=rgb,alpha=1,metallic=met,roughness=rough,**files)

fontroot=Path("C:/Windows/Fonts")
def font(sz,typ="regular"):
    for nm in ({"regular":"bahnschrift.ttf","mono":"consola.ttf","bold":"arialbd.ttf"}[typ],"DejaVuSans.ttf"):
        for f in (fontroot/nm,Path(nm)):
            try:return ImageFont.truetype(str(f),sz)
            except OSError:pass
    return ImageFont.load_default(size=sz)
sheet=Image.new("RGB",(2048,2048),(41,50,49));rects={}
signs=[
    ("anchor","PELAGIC ANCHOR","EQUATORIAL TETHER AUTHORITY   /   SEA LEVEL","ground","04"),
    ("aster","ASTER REACH","ROTATIONAL HABITAT   /   RECEIVING VAULT","station","A"),
    ("dispatch","DISPATCH CONTROL","UPWELL   /   BERTH 04","ground","D"),
    ("arrival","ARRIVAL CONTROL","ASTER REACH   /   PASSENGER TRANSFER","station","06"),
    ("launch","UPBOUND","GUIDE YARD  /  PASSENGER PLATFORM","red","↑"),
    ("dock","DOCKING COLLAR","KEEP CLEAR   /   PROXIMITY CONTROL","station","07"),
    ("pump","PUMP ROOM","SEA INTAKE    /    SYSTEM 02","ground","P2"),
    ("load","MAX LOAD","GANTRY G04  /  16.0 t SWL","red","16"),
    ("hyd","HYDRAULICS","SEALED LOOP  /  210 BAR","ground","H"),
    ("service","SERVICE ACCESS","RESTRICTED   /   LOCAL CREW","ground","B"),
    ("vac","VACUUM MANIFOLD","ASTER REACH  /  ISOLATION CIRCUIT","station","V3"),
    ("transfer","HABITAT TRANSFER","PRESSURIZED GALLERY    /    RING A","station","→"),
    ("hatch","BERTH INTERFACE","EXTEND ONLY UNDER POSITIVE LOCK","red","05"),
    ("spool","WINCH 04","HOLDING BRAKE   /   INSPECT WEEKLY","ground","04"),
    ("rack","POWER CONDITIONING","SERVICE DISTRIBUTION  /  480 VAC","ground","21"),
    ("cold","THERMAL RETURN","LIQUID LOOP    /    RESERVOIR","station","R8"),
    ("gate","SHAFT 04","ASCENT ENVELOPE   /   KEEP CLEAR","red","04"),
    ("number","04","ANCHOR  /  LAUNCH DECK","ground","↑"),
    ("air","PRESSURE GALLERY","WHEEL SEAL  /  FOLDING BRIDGE","station","A4"),
    ("crane","CRANEWAY","SECTOR C   /   HOIST CONTROL","red","C"),
    ("sensor","GUIDE SENSOR","OPTICAL ALIGNMENT   /   U-07","station","09"),
    ("cargo","SEALED FREIGHT","UPWELL LOGISTICS    /    UNIT 17","ground","17"),
    ("tower","TETHER PIER","WEST ACCESS   /   ANCHOR 04","ground","W"),
    ("orbit","ASTER / RING A","BERTH 07    /    RECEIVE ONLY","station","07")]
pal={"ground":((184,184,149),(38,59,56),(142,78,44)),"red":((153,65,44),(241,228,197),(235,165,82)),
     "station":((191,199,196),(46,63,69),(68,115,129))}
for k,(id,title,sub,theme,code) in enumerate(signs):
    w,h=497,145;bg,fg,ac=pal[theme];im=Image.new("RGB",(w,h),bg);d=ImageDraw.Draw(im)
    d.rectangle((4,4,w-5,h-5),outline=ac,width=2);d.rectangle((9,9,17,h-10),fill=ac)
    size=min(46,int(570/(len(title)+.5)))
    d.text((29,15),title,font=font(size,"bold"),fill=fg)
    d.text((w-18,14),code,anchor="rt",font=font(46,"bold"),fill=ac)
    d.line((26,80,w-21,80),fill=ac,width=2);d.text((29,95),sub,font=font(14,"mono"),fill=fg)
    b=np.asarray(im).astype(float)+rng.normal(0,2.1,(h,w,1))
    im=Image.fromarray(b.clip(0,255).astype("uint8"));x=8+510*(k%4);y=7+152*(k//4);sheet.paste(im,(x,y));rects[id]=(x+1,y+1,w-2,h-2)
for ix,id in enumerate(("anchor_screen","aster_screen","scada","oscilloscope")):
    w,h=492,303;im=Image.new("RGB",(w,h),(13,26,29));d=ImageDraw.Draw(im)
    main=(123,209,210) if ix%2 else (164,209,160);faint=(56,96,92);amber=(218,158,77)
    for x in range(14,w,21):d.line((x,11,x,h-11),fill=(27,47,48))
    for y in range(12,h,21):d.line((11,y,w-12,y),fill=(27,47,48))
    title=("GUIDE / DISPATCH","CAPTURE / OPTICS","DISTRIBUTION","LOAD / SPECTRUM")[ix]
    d.text((15,11),title,font=font(21,"mono"),fill=main);d.line((13,41,w-13,41),fill=faint,width=2)
    if ix<2:
        for j in range(5):d.ellipse((34+j*16,63+j*16,207-j*16,236-j*16),outline=faint,width=2)
        d.line((22,151,214,151),fill=main);d.line((119,49,119,248),fill=faint)
        d.polygon(((109,153),(123,136),(128,155)),fill=amber)
        for k,t in enumerate(("ALIGN   +0.22","LOAD     41.2","LINK      A-7","SEALED    YES")):
            d.text((240,72+k*41),t,font=font(19,"mono"),fill=main if k!=2 else amber)
    else:
        for i in range(4):
            pts=[(x,74+i*50+math.sin(x*.029+i)*11+math.cos(x*.112)*3) for x in range(22,w-23,3)]
            d.line(pts,fill=main if i%2 else amber,width=2)
    d.text((17,266),"UPWELL    /    INSTRUMENT BUS  07",font=font(13,"mono"),fill=faint)
    x=10+ix*509;y=950;sheet.paste(im,(x,y));rects[id]=(x+1,y+1,w-2,h-2)
# Yellow-black guards, cargo-labels and a route-sector legend share this atlas.
haz=Image.new("RGB",(990,94),(194,141,65));d=ImageDraw.Draw(haz)
for x in range(-120,1100,95):d.polygon(((x,0),(x+50,0),(x-10,94),(x-60,94)),fill=(37,49,49))
sheet.paste(haz,(12,1310));rects["hazard"]=(13,1311,988,92)
sheet.save(OUT/"Terminal_Atlas.jpg",quality=90)
for name,emit in (("Terminal_Print",0),("Terminal_Display",.67)):
    materials[name]=dict(rgb=(255,255,255),baseColor="Terminal_Atlas.jpg",roughness=.51,metallic=.1,alpha=1,emission=emit)
(OUT/"materials.json").write_text(json.dumps(materials,indent=2))
(OUT/"atlas.json").write_text(json.dumps({"size":[2048,2048],"rects":rects},indent=2))
