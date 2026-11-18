"""Create the packed carriage's seamless finish library and print/display atlas."""
from pathlib import Path
import json
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "unity" / "Assets" / "Upwell" / "SourceModels" / "Textures"
OUT.mkdir(parents=True, exist_ok=True)
S = 512
rng = np.random.default_rng(7701)
random.seed(317)
xx, yy = np.meshgrid(np.arange(S), np.arange(S))


def noise(cell):
    """Periodic bicubic noise with two extra points surrounding the tile."""
    base = rng.integers(0, 256, (cell, cell), dtype=np.uint8)
    base = np.pad(base, 2, mode="wrap")
    sm = Image.fromarray(base).resize(((cell + 4) * S // cell,) * 2, Image.Resampling.BICUBIC)
    lent = 2 * S // cell
    return (np.asarray(sm.crop((lent, lent, lent + S, lent + S)), float) - 127.5) / 128


def scratched():
    layer = Image.new("L", (S, S))
    dr = ImageDraw.Draw(layer)
    for _ in range(78):
        x, y = random.randrange(S), random.randrange(S)
        ln = max(1, random.expovariate(1/9))
        ang = random.uniform(-math.pi, math.pi)
        dx, dy = ln * math.cos(ang), ln * math.sin(ang)
        bright = random.randrange(28, 152)
        for i in (-S, 0, S):
            for j in (-S, 0, S):
                dr.line((x+i, y+j, x+dx+i, y+dy+j), fill=bright, width=1)
    return np.asarray(layer, float)/255


definitions = {
    "Ceramic_Pearl": ((190,196,193), .41, .30, "paint"),
    "Composite_Slate": ((91,102,106), .47, .40, "paint"),
    "Carbon_Ceramic": ((40,46,49), .37, .46, "paint"),
    "Safety_Amber": ((190,102,48), .38, .35, "paint"),
    "Signal_Orange": ((183,73,38), .4, .4, "paint"),
    "Aluminum": ((159,165,167), .30, .85, "metal"),
    "Graphite_Alloy": ((73,80,86), .38, .78, "metal"),
    "Titanium": ((143,151,154), .27, .81, "metal"),
    "Black_Rubber": ((33,38,36), .76, .03, "rubber"),
    "Floor_Rubber": ((58,63,60), .71, .08, "floor"),
    "Pressure_Fabric": ((69,87,91), .89, .0, "weave"),
    "Technical_Twill": ((145,155,154), .86, .0, "weave"),
    "Aramid_Webbing": ((112,102,87), .83, .01, "weave"),
    "Harness_Grip": ((45,49,49), .68, .03, "rubber"),
    "Paper": ((196,188,156), .87, .0, "paper"),
    "Data_Jacket": ((93,81,74), .86, .0, "weave"),
    "Smoked_Display": ((20,33,28), .22, .32, "glass"),
    "Cable_Cyan": ((53,113,132),.54,.10,"rubber"),
    "Cable_Orange": ((166,84,43),.58,.08,"rubber"),
    "Cable_Blue": ((53,72,106),.57,.08,"rubber"),
    "Restraint_Webbing": ((132,53,43),.88,.0,"weave"),
}
materials = {}
for name, (rgb, rough, metal, typ) in definitions.items():
    fine = rng.standard_normal((S,S)).clip(-2,2)
    macro, mottled, patch = noise(4), noise(16), noise(64)
    marks = scratched()
    if typ == "weave":
        twill = np.sin(2*np.pi*(xx+yy)/8)
        warp = np.sin(2*np.pi*xx/4) * (.58+.3*twill)
        weft = np.cos(2*np.pi*yy/4) * (.55-.3*twill)
        relief = (warp+weft)*.69 + fine*.11 + patch*.17
        variation = macro*6 + mottled*3.4 + relief*8 + fine*2.6
    elif typ == "metal":
        brushing = rng.normal(0,1,(S,1)) + np.sin(2*np.pi*(xx+yy*10)/S)*.15
        relief = brushing*.11 + fine*.14 + marks*.78
        variation = macro*6 + mottled*3.4 + brushing*3.6 + fine*1.6 - marks*31
    elif typ == "floor":
        stagger = (xx + (yy//32 % 2)*16) % 32
        studs = np.hypot(stagger-16, yy%32-16)
        relief = (studs<8)*.7 + fine*.21 + marks*.75
        variation = macro*7 + patch*2.4 + fine*1.8 + (studs<8)*4 + (studs<6)*2 - marks*28
    else:
        relief = fine*(.20 if typ=="paint" else .29) + patch*.19 - marks*.78
        variation = macro*5.2 + mottled*3.4 + patch*1.9 + fine*1.6 - marks*(36 if typ == "paint" else 20)
    dirt = np.maximum(0, -macro - mottled*.42 - .35) * (4 if typ=="paint" else 3)
    if typ=="paint": variation *= .50
    color = np.clip(np.array(rgb)[None,None,:]+variation[:,:,None]-dirt[:,:,None]*[.6,.82,1.03], 0, 255)
    rr = np.clip(rough*255 + macro*13 + patch*7 + fine*3 + marks*34, 12, 253)
    dx = (np.roll(relief,-1,axis=1)-np.roll(relief,1,axis=1))*.24
    dy = (np.roll(relief,-1,axis=0)-np.roll(relief,1,axis=0))*.24
    norm = np.stack((-dx, dy, np.ones_like(dx)), -1)
    norm /= np.linalg.norm(norm,axis=-1,keepdims=True)
    basecolor = name+"_Color.jpg"
    roughfile = name+"_Roughness.jpg"
    normal = name+"_Normal.jpg"
    Image.fromarray(color.astype("uint8")).save(OUT/basecolor, quality=88)
    Image.fromarray(rr.astype("uint8")).save(OUT/roughfile, quality=85)
    Image.fromarray(((norm*.5+.5)*255).astype("uint8")).save(OUT/normal, quality=88)
    materials[name] = dict(baseColor=basecolor,roughnessMap=roughfile,normal=normal,
                           roughness=rough,metallic=metal,alpha=1, rgb=rgb)

for name, rgb, strength in [
    ("Opal_Emitter", (244,235,209), 2.2), ("Mint_Emitter",(107,215,221),1.5),
    ("Amber_Emitter",(251,170,56),1.9), ("Red_Emitter",(218,62,31),1.35),
    ("Blue_Emitter",(158,197,214),1.4)]:
    materials[name] = dict(rgb=rgb,roughness=.34,metallic=.06,alpha=1,emission=strength)
materials["Clear_Glass"] = dict(rgb=(148,177,166),roughness=.13,metallic=.18,alpha=.037)

FONTS=Path("C:/Windows/Fonts")
def font(px, style="normal"):
    names = {"normal":["bahnschrift.ttf","Arial.ttf","DejaVuSans.ttf"],"bold":["arialbd.ttf","DejaVuSans-Bold.ttf"],
             "mono":["consola.ttf","DejaVuSansMono.ttf"],"serif":["georgiai.ttf","DejaVuSerif.ttf"]}
    for nm in names[style]:
        for candidate in (FONTS/nm, Path(nm)):
            try: return ImageFont.truetype(str(candidate),px)
            except OSError: pass
    return ImageFont.load_default(size=px)


aw,ah=2048,2048
atlas = Image.new("RGB", (aw,ah), (55,57,50))
rects={}
panels=[
    ("car07","UPWELL","07","TETHER VEHICLE      /      UP-07","dark"),
    ("window","OBSERVATION","01","PRESSURE GLAZING  /  450 kPa","light"),
    ("saloon","OBSERVATION","01","CAR 07     /     FORWARD","dark"),
    ("sleeper","CREW SLEEPER","02","LOWER BERTH    /    CAR 07","dark"),
    ("service","SERVICE LOCK","03","AUTHORIZED CREW ACCESS","orange"),
    ("assettag","UPWELL     UTA","07","MASS  42.6 t     •     REFIT 68-04","light"),
    ("warning","CAUTION","","MOVING EQUIPMENT    /    KEEP CLEAR","orange"),
    ("manual","EXT CAMERA","","HORIZON  /  GUIDE  /  COUNTERLINE","light"),
    ("life","AIR SYSTEM","","DIFFERENTIAL PRESSURE   04","dark"),
    ("number","07","UP","ASTER REACH   /   EQUATOR TETHER","orange"),
    ("card","SERVICE","07","B. MORA     /     ENGINEERING","light"),
    ("drawer","PERSONAL EFFECTS","B","LIFT LATCH TO OPEN","light"),
    ("utility","UTILITY BANK","B","INSPECTION POWER   /   24V","dark"),
    ("screenname","ROUTE / GUIDANCE","","UPPER TERMINAL   .   ASTER REACH","dark"),
    ("cardreader","INSERT PASS","","SERVICE  /  AUTHORIZATION","dark"),
    ("book","CLIMBER LOG","","CAR 07   •   ENGINEERING RECORD","dark"),
    ("mug","UTA","07","TRANSIT SERVICE","light"),
    ("station","ASTER REACH","↑","UPPER TERMINAL  /  CAR 07","light"),
    ("stow","EMERGENCY STOW","01","KEEP THIS AREA CLEAR","orange"),
    ("comms","CREW LINE","","PUSH TO CALL  /  CHANNEL 03","dark"),
    ("water","POTABLE WATER","","2.6 BAR    /    CREW GALLEY","light"),
    ("tether","GUIDEWAY","","TETHER CONTACT SYSTEM","dark"),
    ("berthsign","BERTH 02","B","CARRIAGE SLEEPING QUARTER","light"),
    ("airlock","PRESSURE DOOR","03","SEAL CONTROL   /   LOCAL","orange"),
    ("civil","UPWELL SYSTEMS","","PRESSURE MODULE 6   /   S/N 9017","dark"),
    ("wheel","DOCK CLAMP","","TURN CLOCKWISE TO ENGAGE","light"),
    ("shades","SUN FILTER","","TRAVEL LIMIT / MANUAL OVERRIDE","light"),
    ("optic","BINOCULAR","8×","SURVEY INSTRUMENTS   •   8×42","dark"),
    ("cablea","HV-04","A","FEEDER   /   380 V DC","orange"),
    ("cableb","FO-02","B","DUPLEX FIBER    /    BUS 2","light"),
    ("cablec","RET-06","C","THERMAL RETURN    /    J6","dark"),
    ("cabled","NET-08","D","OPTICAL RING    /    AUX 8","light"),
]
palette={"dark":((41,47,51),(205,220,220),(129,176,184)),"light":((190,196,191),(43,53,55),(95,116,119)),
         "orange":((174,75,43),(239,230,207),(232,182,131))}
for i,(key,label,no,sub,theme) in enumerate(panels):
    w,h=493,99
    im=Image.new("RGB",(w,h),palette[theme][0]); d=ImageDraw.Draw(im)
    bg,fg,accent=palette[theme]
    d.line((10,9,w-10,9),fill=accent,width=2)
    sz = min(40, int(535/(len(label)+.7)))
    d.text((12,13), label, font=font(sz,"bold"), fill=fg)
    d.text((12,64),sub,font=font(16,"mono"),fill=fg)
    if no:
        d.text((w-12,14), no, anchor="rt",font=font(45,"bold"),fill=fg)
    d.line((10,87,w-10,87),fill=accent,width=1)
    arr=np.asarray(im).astype(float)+rng.normal(0,3,(h,w,1))
    im=Image.fromarray(np.uint8(np.clip(arr,0,255)))
    u=8+(i%4)*510; v=6+(i//4)*107
    atlas.paste(im,(u,v)); rects[key]=(u+1,v+1,w-2,h-2)

def draw_screen(k, size=(686,411)):
    w,h=size; im=Image.new("RGB",size,(15,31,26)); d=ImageDraw.Draw(im)
    fg=(136,219,221); low=(76,132,147); dim=(39,68,82); orange=(232,147,83)
    d.rectangle((0,0,w,h),fill=(13,22,28))
    for x in range(12,w-8,24):d.line((x,9,x,h-9), fill=(23,39,47))
    for y in range(9,h-6,24):d.line((9,y,w-10,y), fill=(23,39,47))
    d.line((15,43,w-15,43), fill=low,width=2)
    d.line((15,h-28,w-15,h-28), fill=low,width=2)
    def tx(x,y,t,sz=17, c=fg):d.text((x,y),t, font=font(sz,"mono"),fill=c)
    if k=="route":
        tx(18,12,"UPWELL   /   TRAJECTORY",19); tx(514,15,"NAV 07 · A",15,orange)
        cx,cy=177,209
        for rad in (30,65,102,135):d.ellipse((cx-rad,cy-rad,cx+rad,cy+rad),outline=low,width=2)
        for a in range(0,360,5):
            t=math.radians(a); r=12 if a%30==0 else 5
            d.line((cx+math.cos(t)*135,cy+math.sin(t)*135,cx+math.cos(t)*(135-r),cy+math.sin(t)*(135-r)),fill=fg,width=1)
        for a in (-1,-.53,.4):
            by=20+a*30
            pts=[(cx+i,cy+by+math.sin(i/83+a)*54-i*.7) for i in range(-103,104,3)]
            d.line(pts, fill=fg if a==-.53 else dim,width=2)
        d.line((cx-150,cy,cx+148,cy),fill=low); d.line((cx,cy-147,cx,cy+148),fill=low)
        d.polygon([(cx+7,cy-16),(cx+3,cy-2),(cx+13,cy-7)],fill=orange)
        tx(339,77,"DESTINATION",16,low); tx(337,102,"ASTER REACH",31)
        tx(340,164,"TETHER TRACK",17,low); tx(340,193,"000.217",45)
        for j in range(14): d.rectangle((344+j*20,262,357+j*20,278),fill=fg if j<9 else dim)
        tx(340,304,"GUIDANCE LOCKED",20,orange)
        tx(17,h-24,"CAR 07   /   CARRIER LINK ACTIVE",13,low)
    elif k=="diagnostics":
        tx(15,9,"SYSTEMS / BUS A",23)
        for j,(name,reading) in enumerate([("CABIN PRESS","101.3 kPa"),("CONTACT","LOCK"),("DRIVE TEMP","+42.1 C"),("DOOR SEAL","NOMINAL")]):
            y=63+j*67;tx(19,y,name,20);tx(361,y,reading,21,orange if j==1 else fg)
            d.line((18,y+41,w-17,y+41),fill=dim,width=2)
        tx(15, h-26,"CARRIAGE DIAGNOSTICS  07",14,low)
    else:
        tx(16,9,"TRAC / MOTOR CURRENT",22)
        pts=[]
        for j in range(15,w-18,2):
            v=math.sin(j/43)*17+math.sin(j/11)*4+math.sin(j/6)*2
            pts.append((j,145+v + 42*math.sin(j/170)))
        d.line(pts,fill=fg,width=3)
        tx(23,226,"DRIVE A   42.1",30);tx(24,293,"CONTACT   98.7",30)
        tx(19,h-23,"MAGNETIC TRACTION",14,low)
    ar=np.asarray(im).astype(float)
    ar[::3]*=.91
    return Image.fromarray(np.uint8(ar))

for i,k in enumerate(("route","diagnostics","motor")):
    im=draw_screen(k,(652,401));u=12+i*678;v=780
    atlas.paste(im,(u,v));rects[k]=(u+2,v+2,648,397)

im=Image.new("RGB",(491,323),(168,177,173));d=ImageDraw.Draw(im);ink=(45,62,65)
d.rectangle((7,7,483,315),outline=ink,width=2);d.text((19,13),"J-BUS   /   ROUTING",font=font(26,"bold"),fill=ink)
d.text((18,49),"CARRIAGE 07   //   FEEDER & OPTICAL",font=font(13,"mono"),fill=ink)
for i in range(5):
    x=42+i*90; d.rectangle((x-16,79,x+17,101),outline=ink,width=2)
    d.text((x-9,81),str(i+1),font=font(13,"mono"),fill=ink)
    y=125+i*15;d.line((x,101,x,y,65+i*64,y,65+i*64,220),fill=(119,68,51) if i<2 else ink,width=3)
    d.ellipse((61+i*64,216,69+i*64,224),outline=ink,width=2)
for j,name in enumerate(("HV-04","FO-02","RET-6","NET-8")):
    x=23+j*115; d.text((x,245),name,font=font(18,"mono"),fill=ink)
d.line((18,275,473,275),fill=ink,width=2);d.text((20,283),"ISOLATE HIGH VOLTAGE BEFORE SERVICE",font=font(17,"mono"),fill=ink)
atlas.paste(im,(1539,1219));rects["cablemap"]=(1540,1220,489,321)
# Satin-laminate credential artwork is proportioned to the inspection model's face.
im=Image.new("RGB",(474,305),(205,211,204));d=ImageDraw.Draw(im)
d.rectangle((9,9,464,295),outline=(97,114,110),width=2)
d.text((22,16),"UPWELL  /  VEHICLE SYSTEMS",font=font(17,"mono"),fill=(49,71,72))
d.line((21,46,451,46),fill=(85,108,108),width=2)
d.text((19,54),"SERVICE",font=font(59,"bold"),fill=(40,58,64))
d.text((400,60),"07",font=font(34,"bold"),fill=(146,62,45))
d.text((23,139),"B. MORA",font=font(31,"bold"),fill=(47,65,69))
d.text((24,186),"ENGINEERING    /    SERVICE LOCK",font=font(18,"mono"),fill=(62,77,79))
d.line((22,224,451,224),fill=(129,145,139),width=2)
d.text((24,247),"AUTH 07-311     ·     CLASS C",font=font(15,"mono"),fill=(62,77,77))
for j in range(17):
    for k in range(7):
        if (j*17+k*7+j*k)%5<2:d.rectangle((360+j*5,244+k*5,363+j*5,247+k*5),fill=(59,76,76))
atlas.paste(im,(1540,1581));rects["credential"]=(1541,1582,472,303)

# Extra printed dial and route plate. The dial's face is seen through a brass bezel.
for idx,k in enumerate(("dial","dial_amber")):
    w=h=424; im=Image.new("RGB",(w,h),(40,45,39)); d=ImageDraw.Draw(im)
    fg=(212,202,169) if idx==0 else (176,196,157)
    d.ellipse((7,7,w-7,h-7),fill=(174,173,147) if idx==0 else (37,54,46))
    ink=(42,54,43) if idx==0 else fg
    cx=cy=w//2
    for j in range(61):
        a=math.radians(137+j*4.45)
        r=176; l=22 if j%5==0 else 9
        d.line((cx+math.cos(a)*r,cy+math.sin(a)*r,cx+math.cos(a)*(r-l),cy+math.sin(a)*(r-l)),fill=ink,width=3)
        if j%10==0:
            d.text((cx+math.cos(a)*(r-43),cy+math.sin(a)*(r-43)),str(j//10),font=font(22,"bold"), fill=ink,anchor="mm")
    d.text((cx,cy+64),"BAR" if idx==0 else "kPa",fill=ink,font=font(25,"bold"),anchor="mm")
    d.text((cx,cy+93),"UTA  INSTRUMENTS",fill=ink,font=font(13,"mono"),anchor="mm")
    d.polygon([(cx-5,cy+5),(cx+99,cy-127),(cx+5,cy+3)],fill=(154,68,37))
    d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=ink)
    u=15+idx*450;v=1205;atlas.paste(im,(u,v));rects[k]=(u+2,v+2,w-4,h-4)

# Woven route strip poster showing the equatorial tether, drift rings, and cylinder terminal.
w,h=511,735; im=Image.new("RGB",(w,h),(178,173,149)); d=ImageDraw.Draw(im)
d.rectangle((16,14,w-17,h-15),outline=(69,78,66),width=3)
d.text((38,37),"UPWELL",font=font(58,"bold"),fill=(53,73,60));d.text((40,108),"EQUATORIAL TRANSIT",font=font(22,"mono"),fill=(64,73,62))
d.rectangle((38,157,w-38,160),fill=(105,90,65))
cx=149
d.line((cx,199,cx,603),fill=(61,81,67),width=5)
for j,(a,b) in enumerate([("04","ASTER REACH"),("03","TRANSFER RING"),("02","UPPER AIR"),("01","EQUATOR BASE")]):
    y=212+j*122;d.ellipse((cx-11,y-11,cx+11,y+11),fill=(169,93,54),outline=(65,63,47),width=3)
    d.text((59,y-12),a,font=font(22,"mono"),fill=(70,77,66));d.text((179,y-12),b,font=font(23,"bold"),fill=(45,66,54))
d.text((39,649),"EASTERN MERIDIAN   /   CAR 07",font=font(18,"mono"),fill=(65,72,59))
d.text((39,676),"PASSENGER GUIDE     09.68",font=font(16,"mono"),fill=(77,81,68))
u,v=1005,1217;atlas.paste(im,(u,v));rects["poster"]=(u+1,v+1,w-2,h-2)
atlas.save(OUT/"Carriage_Print.jpg",quality=93)
marks=Image.new("RGBA",(2048,1024),(0,0,0,0));md=ImageDraw.Draw(marks);markrects={}
mark_data=[
    ("identity","UPWELL","PRESSURE SYSTEMS    /    ASCENT DIVISION"),
    ("carid","07","EQUATORIAL CLIMBER   //   U-07"),
    ("glazing","GL-03","LAMINATE / 2.8.4   TQ 14 N.m"),
    ("collar","C-07","ASTER REACH    /    INTERFACE B"),
    ("bunkmark","SLEEP CELL","TYPE B    /    RESTRAINT REQUIRED"),
    ("emergency","P-H01","PRESSURE DOOR   /   HOLD TO RELEASE"),
    ("servicebay","J-BUS","FEEDER   /   FIBER   /   RETURN"),
    ("serial","190.07","EQUIPMENT ID  07-193-464"),
]
for j,(k,a,b) in enumerate(mark_data):
    x=(j%2)*1024+12;y=(j//2)*256+12;w,h=990,214
    ink=(150,57,38,250) if k in ("carid","glazing","emergency","collar") else (57,69,72,248)
    md.polygon([(x+15,y+86),(x+63,y+14),(x+91,y+14),(x+43,y+86)],fill=(157,67,51,248))
    md.polygon([(x+53,y+86),(x+99,y+14),(x+124,y+14),(x+80,y+86)],fill=(157,67,51,248))
    md.text((x+144,y+3),a,font=font(102 if k in ("carid","serial","collar") else 88,"bold"),fill=ink)
    md.text((x+14,y+127),b,font=font(29,"mono"),fill=(64,77,77,250))
    md.line((x+15,y+184,x+866,y+184),fill=(94,104,100,200),width=3)
    for i in range(20):
        sw=2+(i*7+j)%6
        md.rectangle((x+877+i*5,y+153,x+877+i*5+sw,y+182),fill=(58,68,69,234))
    markrects[k]=(x,y,w,h)
marks.save(OUT/"Hull_Stencils.png")
materials["Hull_Stencils"]=dict(baseColor="Hull_Stencils.png",rgb=(255,255,255),
    roughness=.47,metallic=.06,alpha=1,alphaFromMap=True)
(OUT/"stencils.json").write_text(json.dumps({"size":[2048,1024],"rects":markrects},indent=2))
draw_screen("route",(652,401)).save(OUT/"Nav_Active_Pixels.jpg",quality=92)
materials["Nav_Active_Pixels"]=dict(baseColor="Nav_Active_Pixels.jpg",rgb=(255,255,255),
    roughness=.24,metallic=.1,alpha=1,emission=.48)
for mat in ("Carriage_Print","Display_Phosphor"):
    materials[mat]=dict(baseColor="Carriage_Print.jpg",rgb=(255,255,255),roughness=.67 if mat=="Carriage_Print" else .24,
                        metallic=.1,alpha=1,emission=.48 if mat=="Display_Phosphor" else 0)
surface_dir=ROOT/"art"/"textures"
for prop in json.loads((surface_dir/"materials.json").read_text()):
    id=prop["id"]
    mat="Surface_"+id
    d=dict(rgb=prop["base_color_srgb"],roughness=prop["roughness"],metallic=prop["metallic"],
           family=prop["family"],alpha=.037 if id=="window" else 1)
    for key,suf in (("baseColor","basecolor"),("roughnessMap","roughness"),("normal","normal")):
        dest=mat+"_"+suf+".jpg"
        Image.open(surface_dir/(id+"_"+suf+".png")).save(OUT/dest,quality=88)
        d[key]=dest
    if id=="lamp":d["emission"]=2.8
    materials[mat]=d
(OUT/"materials.json").write_text(json.dumps(materials,indent=2))
(OUT/"atlas.json").write_text(json.dumps({"size":[aw,ah],"rects":rects},indent=2))
print(f"{len(materials)} finishes, {len(rects)} print/display regions -> {OUT}")
