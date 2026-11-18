"""Build the FC 327 enclosed bend tester in Blender and export the same parts to both players.

Run python with --contract or --textures, then blender -b -P on this file.
The drawing coordinates (u, v, d) are right, up and outward on the instrument face.
The exported contract uses the carriage's ordinary glTF axes.
"""
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "web/assets/fracture"
UNITY = ROOT / "unity/Assets/Upwell/Resources/Fracture"
ART = ROOT / "blender/equipment/fracture"
SURFACES = ROOT / "art/fracture"
for folder in (SITE, UNITY, ART):
    folder.mkdir(parents=True, exist_ok=True)


def web(u,v,d):
    return [round(-u,8),round(v,8),round(-d,8)]


def blender(u,v,d):
    return (-u,d,v)


def finish(name,color,metal,rough,alpha=1,texture="",emission=0):
    return dict(name="FC_"+name,color=color,metal=metal,rough=rough,alpha=alpha,map=texture,emission=emission)


FINISHES = [
    finish("Casting","#ffffff",.58,.43,texture="casting"),finish("Edge","#a5ada9",.76,.32),
    finish("Anodized","#343e42",.67,.39),finish("Steel","#b8c1bf",.85,.26),
    finish("Seal","#25292b",.02,.69),finish("Lever","#bc5833",.34,.42),
    finish("Grip","#363c3c",.06,.62),finish("Cartridge","#6b8589",.46,.44),
    finish("Ceramic","#c3b9a3",.0,.63),finish("FreshBreak","#e5dfc9",.0,.80),
    finish("Pointer","#373d41",.31,.44),finish("Witness","#b54e34",.23,.46),
    finish("Markings","#ffffff",.17,.54,texture="markings"),
    finish("CouponFace","#ffffff",0,.53,texture="markings"),
    finish("Guard","#b0d8df",.05,.11,alpha=.075),finish("Lamp","#f8dfac",0,.41,emission=1.40)
]
CU,CV,CD=-.048,.007,.074
THICKNESS=.0042
POLYGONS=[
    [(-67,-19),(-17,-19),(-10,-6),(-15,1),(-4,9),(-9,19),(-67,19)],
    [(-17,-19),(14,-19),(6,-9),(14,-1),(1,-3),(-10,-6)],
    [(-10,-6),(1,-3),(-2,4),(2,10),(-9,19),(-4,9),(-15,1)],
    [(1,-3),(14,-1),(10,8),(18,19),(-9,19),(2,10),(-2,4)],
    [(14,-19),(67,-19),(67,19),(18,19),(10,8),(14,-1),(6,-9)],
]


def polygon_mass_centroid(poly):
    sums=[(x*v-u*y,x+u,y+v) for (x,y),(u,v) in zip(poly,poly[1:]+poly[:1])]
    twice=sum(q[0] for q in sums)
    return abs(twice)/2/1e6, sum(a*x for a,x,_ in sums)/(3*twice)/1000, sum(a*y for a,_,y in sums)/(3*twice)/1000


def contract():
    shards=[]
    # Internal strain is released outward from the two scored webs. Centre
    # velocities in m/s, with deliberately different overturning axes.
    impulses=[(-.092,.036,.034),(-.037,-.091,.059),(.016,.103,-.048),(.047,.068,.074),(.092,-.017,-.029)]
    spins=[(1.6,-2.0,.8),(-2.7,3.2,-2.1),(3.2,1.7,2.8),(-2.1,-2.9,1.8),(.9,2.0,-1.1)]
    for i,poly in enumerate(POLYGONS):
        area,cx,cy=polygon_mass_centroid(poly)
        vertices=[web(x/1000-cx,y/1000-cy,z) for z in (-THICKNESS/2,THICKNESS/2) for x,y in poly]
        shards.append(dict(name=f"fracture_shard_{i+1:02}",pivot=web(CU+cx,CV+cy,CD),
            massKg=round(area*THICKNESS*3870,7),vertices=vertices,
            velocity=web(*impulses[i]),spin=list(spins[i])))
    assert abs(sum(polygon_mass_centroid(p)[0] for p in POLYGONS)-.134*.038)<1e-9
    return dict(schema=1,origin=[-1.55,1.48,5.405],chamberMin=web(.084,-.069,.110),
        chamberMax=web(-.182,.085,.034),couponCenter=web(CU,CV,CD),
        breakLoadN=320,dialMaxN=400,holdSeconds=.94,snapFraction=.87,
        press=dict(name="fracture_press",pivot=web(.165,-.018,.076),axis=[0,0,-1],degrees=-51),
        punch=dict(name="fracture_punch",pivot=web(CU,CV,.095),travel=web(0,0,-.0036),clearance=.0029,deflection=.0007),
        needle=dict(name="fracture_needle",pivot=web(.163,.074,.052),axis=[0,0,-1],degrees=-270),
        peakNeedle=dict(name="fracture_peak_needle",pivot=web(.163,.074,.051),axis=[0,0,-1],degrees=-270),
        reload=dict(name="fracture_reload",pivot=web(-.133,-.115,.056),travel=web(.027,0,0)),
        reloadSeconds=1.,exchangeAt=.49,
        shutters=[dict(name=f"fracture_shutter_{i+1:02}",travel=web(0,.041+.032*i,0)) for i in range(5)],
        supports=[dict(center=web(CU+offset,CV,.064),radius=.0075,halfHeight=.023) for offset in (-.052,.052)],
        shards=shards,finishes=FINISHES)


def write_contract():
    data=json.dumps(contract(),indent=2)+"\n"
    for folder in SITE,UNITY:
        (folder/"cartridge.json").write_text(data,encoding="utf-8")


if "--contract" in sys.argv:
    write_contract()
    sys.exit(0)

ATLAS_SIZE=(2048,1536)
RECTS={"header":(24,20,1824,160),"bed":(24,200,1094,850),"dial":(1130,180,1810,860),
       "index":(24,895,1110,1003),"coupon":(24,1040,1054,1332),"load":(1144,905,1784,1041),
       "serial":(1144,1080,1904,1212)}

def dial_illumination():
    from PIL import Image, ImageOps
    # A light guide illuminates only the dial stock. The ink interrupts it,
    # and there is no light behind the neighboring chamber grid or name plate.
    with Image.open(SURFACES/"markings.png") as printing:
        rect=RECTS["dial"]
        paper=ImageOps.colorize(printing.crop(rect).convert("L"),(0,0,0),(249,237,214))
        atlas=Image.new("RGB",ATLAS_SIZE,(0,0,0));atlas.paste(paper,(rect[0],rect[1]))
        atlas.resize((1024,768),Image.Resampling.LANCZOS).save(SURFACES/"dial_lume.png",optimize=True)
    shutil.copyfile(SURFACES/"dial_lume.png",UNITY/"dial_lume.png")


def make_textures():
    import numpy as np
    from PIL import Image,ImageDraw,ImageFont,ImageFilter
    from scipy.ndimage import gaussian_filter
    rng=np.random.default_rng(327)
    SURFACES.mkdir(exist_ok=True)
    def write(im,name):
        im.save(SURFACES/name,optimize=True)
        shutil.copyfile(SURFACES/name,UNITY/name)
    metal=Image.open(ROOT/"art/surface-scans/blue_metal_plate/albedo.jpg").convert("L")
    grains=np.asarray(metal.resize((768,768),Image.Resampling.LANCZOS),dtype=float)
    grain=grains-gaussian_filter(grains,5);smooth=gaussian_filter(grains,24)-np.mean(grains)
    rnd=rng.normal(0,1,(768,768));press=gaussian_filter(rnd,1);press/=press.std()
    y,x=np.indices(rnd.shape);rim=np.minimum.reduce([x,767-x,y,767-y]);edge=np.exp(-rim/10.)
    nick=Image.new("L",(768,768));pen=ImageDraw.Draw(nick)
    for i in range(370):
        a,b=rng.integers(0,768,2);t=rng.uniform(-.5,.4);n=rng.uniform(2,19)
        pen.line((a,b,a+n,b+t*n),fill=int(rng.uniform(23,90)),width=1)
    scratches=np.asarray(nick.filter(ImageFilter.GaussianBlur(.36)))/255.
    wear=np.clip(.33*edge*(np.maximum(0,press+.36))+scratches,0,1)
    pigment=np.array([89,104,113])+(grain*.41+smooth*.23+press*1.45)[:,:,None]
    pigment=pigment*(1-wear[:,:,None]*.69)+np.array([159,164,157])*wear[:,:,None]*.69
    write(Image.fromarray(np.uint8(np.clip(pigment,0,255))),"casting.png")
    write(Image.fromarray(np.uint8(np.clip((.45+.019*press-.14*wear)*255,0,255))),"casting_roughness.png")
    dy,dx=np.gradient(.26*press+grain*.036+wear*.66);n=np.stack((-dx*.12,dy*.12,np.ones_like(dx)),axis=2)
    n/=np.linalg.norm(n,axis=2)[:,:,None]
    write(Image.fromarray(np.uint8((n*.5+.5)*255)),"casting_normal.png")
    atlas=Image.new("RGB",ATLAS_SIZE,(44,53,56))
    fontMain=Path("C:/Windows/Fonts/bahnschrift.ttf");fontMono=Path("C:/Windows/Fonts/consola.ttf")
    def panel(key,rgb,spread):
        l,t,r,b=RECTS[key];w,h=r-l,b-t
        g=np.asarray(metal.resize((w,h),Image.Resampling.LANCZOS),dtype=float)
        field=(g-gaussian_filter(g,4))*.19+rng.normal(0,spread,(h,w))
        img=Image.fromarray(np.uint8(np.clip(np.array(rgb)+field[:,:,None],0,255)))
        return img,ImageDraw.Draw(img)
    def add(key,img):
        l,t,r,b=RECTS[key];atlas.paste(img,(l,t))
        # Filled gutters keep high mip levels from pulling unrelated ink into a plate.
        atlas.paste(img.crop((0,0,1,img.height)).resize((8,img.height)),(l-8,t))
        atlas.paste(img.crop((img.width-1,0,img.width,img.height)).resize((8,img.height)),(r,t))
    def txt(d,xy,s,size,col,anchor="lm",mono=False):
        d.text(xy,s,font=ImageFont.truetype(str(fontMono if mono else fontMain),size),fill=col,anchor=anchor,stroke_width=0)
    ink=(39,48,50);pale=(204,213,205);muted=(137,154,150);orange=(175,84,49)
    im,dr=panel("header",(180,186,183),1.5)
    txt(dr,(28,69),"MATERIALS LAB",66,ink);dr.line((625,30,625,112),fill=(121,131,130),width=3)
    txt(dr,(676,69),"BEND TEST",72,ink);txt(dr,(1580,66),"FC / 327",58,ink,"rm",True);add("header",im)
    im,dr=panel("bed",(48,59,61),1.7);w,h=im.size
    for i in range(25):
        xx=62+i*(w-124)/24;sz=30 if i%4==0 else 15
        dr.line((xx,h-77,xx,h-77-sz),fill=muted,width=3)
        if i%4==0:txt(dr,(xx,h-58),str((i-12)*5),17,muted,"mm",True)
    dr.line((55,h-78,w-55,h-78),fill=muted,width=2)
    for xx in (166,w-166):
        for j in range(-2,3):
            dr.line((xx-21,250+j*28,xx+21,250+j*28),fill=(103,122,119),width=2)
        dr.line((xx,177,xx,325),fill=(103,122,119),width=2)
    txt(dr,(38,42),"03  /  FLEXURE",21,muted,mono=True);txt(dr,(w-33,h-25),"mm",18,muted,"rm",True);add("bed",im)
    im,dr=panel("dial",(206,203,181),.85);w,h=im.size;cx,cy=w/2,h/2
    dial_ink=(19,24,24)
    for k in range(41):
        a=math.radians(225-270*k/40);co,si=math.cos(a),math.sin(a)
        outer=.452*w;inner=(.391 if k%5==0 else .418)*w
        dr.line((cx+inner*co,cy-inner*si,cx+outer*co,cy-outer*si),fill=dial_ink,width=8 if k%5==0 else 4)
        if k%10==0:txt(dr,(cx+.305*w*co,cy-.305*w*si),str(k*10),53,dial_ink,"mm")
    a=math.radians(225-270*.80);co,si=math.cos(a),math.sin(a)
    dr.line((cx+.40*w*co,cy-.40*w*si,cx+.46*w*co,cy-.46*w*si),fill=orange,width=9)
    txt(dr,(cx,cy+.143*w),"N",57,ink,"mm");txt(dr,(cx,cy+.25*w),"TYPE 4  /  400",18,(97,103,97),"mm",True);add("dial",im)
    im,dr=panel("index",(63,78,82),1.1);txt(dr,(16,51),"INDEX",48,pale);txt(dr,(1055,55),"SEALED COUPON CASSETTE",35,pale,"rm",True);add("index",im)
    im,dr=panel("coupon",(218,208,183),1.9);w,h=im.size
    for xx in (int(w*.154),int(w*.847)):
        dr.rectangle((xx,0,xx+13,h),fill=(47,78,103));dr.rectangle((xx+19,0,xx+22,h),fill=(67,95,109))
    txt(dr,(int(w*.208),h*.40),"A96",52,(79,92,89),mono=True);txt(dr,(w*.72,h*.76),"07",35,(74,88,87),"mm",True)
    for yy in range(16,h-12,20):dr.line((w*.49,yy,w*.49,yy+8),fill=(140,135,121),width=2)
    add("coupon",im)
    im,dr=panel("load",(47,58,63),1.3);txt(dr,(18,48),"APPLY LOAD",45,pale);txt(dr,(20,102),"RELEASE TO UNLOAD",26,muted,mono=True);add("load",im)
    im,dr=panel("serial",(153,160,154),1.5);txt(dr,(16,42),"TL / METROLOGY",39,ink);txt(dr,(17,100),"CAR 07    LOT 327-4B",32,ink,mono=True)
    for j in range(36):
        xx=534+j*5;dr.rectangle((xx,26,xx+(2 if j%5 else 4),101),fill=ink)
    add("serial",im);write(atlas,"markings.png")


if "--textures" in sys.argv:
    make_textures()
    dial_illumination()
    sys.exit(0)
if "--dial-lume" in sys.argv:
    dial_illumination()
    sys.exit(0)

import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

bpy.ops.wm.read_factory_settings(use_empty=True)
V=Vector
TAU=2*math.pi
MATS={}
for spec in FINISHES:
    m=bpy.data.materials.new(spec["name"]);m.use_nodes=True
    n=m.node_tree.nodes.get("Principled BSDF")
    def linear(x):
        s=int(x,16)/255
        return s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
    col=[linear(spec["color"][j:j+2]) for j in (1,3,5)]
    n.inputs["Base Color"].default_value=(*col,1);n.inputs["Metallic"].default_value=spec["metal"]
    n.inputs["Roughness"].default_value=spec["rough"];n.inputs["Alpha"].default_value=spec["alpha"]
    if spec["map"]:
        tx=m.node_tree.nodes.new("ShaderNodeTexImage");tx.image=bpy.data.images.load(str(SURFACES/(spec["map"]+".png")),check_existing=True)
        m.node_tree.links.new(tx.outputs["Color"],n.inputs["Base Color"])
    if spec["name"]=="FC_Casting":
        for name in ("roughness","normal"):
            tx=m.node_tree.nodes.new("ShaderNodeTexImage");tx.image=bpy.data.images.load(str(SURFACES/("casting_"+name+".png")),check_existing=True)
            tx.image.colorspace_settings.name="Non-Color"
            if name=="normal":
                nm=m.node_tree.nodes.new("ShaderNodeNormalMap");nm.inputs["Strength"].default_value=.52
                m.node_tree.links.new(tx.outputs["Color"],nm.inputs["Color"]);m.node_tree.links.new(nm.outputs["Normal"],n.inputs["Normal"])
            else:m.node_tree.links.new(tx.outputs["Color"],n.inputs["Roughness"])
    if spec["name"]=="FC_Markings":
        glow=m.node_tree.nodes.new("ShaderNodeTexImage")
        glow.image=bpy.data.images.load(str(SURFACES/"dial_lume.png"),check_existing=True)
        m.node_tree.links.new(glow.outputs["Color"],n.inputs["Emission Color"])
        n.inputs["Emission Strength"].default_value=.105
    if spec["emission"]:
        n.inputs["Emission Color"].default_value=(*col,1);n.inputs["Emission Strength"].default_value=spec["emission"]
    if spec["alpha"]<1:m.surface_render_method='DITHERED'
    MATS[spec["name"][3:]]=m


def atlas_uv(key,s,t):
    l,top,r,b=RECTS[key]
    return ((l+s*(r-l))/ATLAS_SIZE[0],1-(b-t*(b-top))/ATLAS_SIZE[1])


class Part:
    def __init__(self,name,pivot=(0,0,0)):
        self.name=name;self.pivot=V(pivot);self.verts=[];self.faces=[];self.uv=[];self.norm=[];self.materials=[];self.ids=[]

    def face(self,points,mat,normal,uv=None,norm=None):
        pts=[V(v) for v in points]
        uv=list(uv) if uv is not None else [((v.x+.253)/.506,(v.y+.161)/.322) for v in pts]
        face_normal=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
        if face_normal.dot(V(normal))<0:
            pts.reverse();uv.reverse();face_normal=-face_normal
            if norm is not None:norm=list(reversed(norm))
        at=len(self.verts);self.verts.extend(blender(*(v-self.pivot)) for v in pts)
        self.faces.append(tuple(range(at,at+len(pts))));self.uv.extend(uv)
        self.norm.extend(blender(*v) for v in (norm if norm is not None else [face_normal]*len(pts)))
        if mat not in self.materials:self.materials.append(mat)
        self.ids.append(self.materials.index(mat))

    def side(self,a,b,mat):
        for i in range(len(a)):
            j=(i+1)%len(a);p,q,r,s=a[i],a[j],b[j],b[i]
            self.face([p,q,r,s],mat,(V(q)-p).cross(V(s)-p))

    def plate(self,u,v,d,w,h,th,r,mat,bevel=.0015):
        b=min(bevel,th*.42,min(w,h)*.12)
        layers=[(d-th/2,b),(d-th/2+b,0),(d+th/2-b,0),(d+th/2,b)]
        rings=[contour(u,v,z,w-2*inset,h-2*inset,max(.0002,r-inset)) for z,inset in layers]
        for a,c in zip(rings,rings[1:]):self.side(a,c,mat)
        self.face(rings[0],mat,(0,0,-1));self.face(rings[-1],mat,(0,0,1))

    def ring(self,u,v,d,w,h,r,rim,depth,mat):
        outer=contour(u,v,d,w,h,r);back=contour(u,v,d-depth,w,h,r)
        inside=contour(u,v,d,w-2*rim,h-2*rim,max(.001,r-rim))
        innerBack=contour(u,v,d-depth,w-2*rim,h-2*rim,max(.001,r-rim))
        self.side(back,outer,mat)
        for i in range(len(outer)):
            j=(i+1)%len(outer);self.face([outer[i],outer[j],inside[j],inside[i]],mat,(0,0,1))
        self.side(inside,innerBack,mat)

    def cylinder(self,a,b,rad,mat,sides=28,endrad=None):
        a,b=V(a),V(b);axis=(b-a).normalized();ref=V((0,1,0)) if abs(axis.y)<.93 else V((1,0,0))
        x=axis.cross(ref).normalized();y=axis.cross(x).normalized();q=[x*math.cos(TAU*i/sides)+y*math.sin(TAU*i/sides) for i in range(sides)]
        lo=[a+rad*v for v in q];hi=[b+(rad if endrad is None else endrad)*v for v in q]
        self.face(lo,mat,-axis);self.face(hi,mat,axis)
        for i in range(sides):
            j=(i+1)%sides;self.face([lo[i],lo[j],hi[j],hi[i]],mat,q[i]+q[j],norm=[q[i],q[j],q[j],q[i]])

    def spin(self,u,v,profile,sides=60):
        # Each radius/depth pair shares a machined land with the next ring.
        for (r,z,mat),(r2,z2,_) in zip(profile,profile[1:]):
            for i in range(sides):
                a,b=TAU*i/sides,TAU*(i+1)/sides
                p=(u+r*math.cos(a),v+r*math.sin(a),z);q=(u+r*math.cos(b),v+r*math.sin(b),z)
                s=(u+r2*math.cos(a),v+r2*math.sin(a),z2);t=(u+r2*math.cos(b),v+r2*math.sin(b),z2)
                norm1=V(((z2-z)*math.cos(a),(z2-z)*math.sin(a),r-r2)).normalized()
                norm2=V(((z2-z)*math.cos(b),(z2-z)*math.sin(b),r-r2)).normalized()
                self.face([p,q,t,s],mat,norm1+norm2,norm=[norm1,norm2,norm2,norm1])

    def screw(self,u,v,d,r,clock=0):
        sides=24
        self.spin(u,v,[(r*.96,d-.0008,"Anodized"),(r,d,"Steel"),(r*.84,d+.0009,"Edge")],sides)
        outside=[];recess=[];bottom=[]
        for i in range(sides):
            a=TAU*i/sides+clock
            def point(rad,z):return (u+rad*math.cos(a),v+rad*math.sin(a),z)
            rad=r*(.32+.16*math.cos(6*(a-clock)))
            outside.append(point(.84*r,d+.0009));recess.append(point(rad,d+.0009));bottom.append(point(rad*.88,d-.0008))
        for i in range(sides):
            j=(i+1)%sides
            self.face([outside[i],outside[j],recess[j],recess[i]],"Steel",(0,0,1))
            self.face([recess[i],recess[j],bottom[j],bottom[i]],"Anodized",(u-recess[i][0],v-recess[i][1],.001))
        self.face(bottom,"Seal",(0,0,1))

    def decal(self,u,v,d,w,h,key):
        pts=[(u-w/2,v-h/2,d),(u+w/2,v-h/2,d),(u+w/2,v+h/2,d),(u-w/2,v+h/2,d)]
        self.face(pts,"Markings",(0,0,1),[atlas_uv(key,s,t) for s,t in [(0,0),(1,0),(1,1),(0,1)]])

    def polygon(self,poly,z0,z1,mat,edge=None):
        lo=[V((x,y,z0)) for x,y in poly];hi=[V((x,y,z1)) for x,y in poly]
        self.face(lo,mat,(0,0,-1));self.face(hi,mat,(0,0,1));self.side(lo,hi,edge or mat)

    def make(self):
        mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.verts,[],self.faces)
        for mat in self.materials:mesh.materials.append(MATS[mat])
        mesh.polygons.foreach_set("material_index",self.ids)
        layer=mesh.uv_layers.new(name="Material UV")
        for i,uv in enumerate(self.uv):layer.data[i].uv=uv
        mesh.normals_split_custom_set(self.norm)
        ob=bpy.data.objects.new(self.name,mesh);bpy.context.scene.collection.objects.link(ob);ob.location=blender(*self.pivot)
        return ob


def contour(u,v,d,w,h,r):
    r=min(r,w*.49,h*.49);points=[]
    for a,b,s in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)):
        for k in range(6):
            angle=math.radians(s+k*18)
            points.append(V((u+a*(w*.5-r)+r*math.cos(angle),v+b*(h*.5-r)+r*math.sin(angle),d)))
    return points


def coupon(name,poly,pivot):
    part=Part(name,pivot)
    front=[V((CU+x/1000,CV+y/1000,CD+THICKNESS/2)) for x,y in poly]
    back=[V((p.x,p.y,CD-THICKNESS/2)) for p in front]
    tris=tessellate_polygon([front])
    for indices in tris:
        part.face([front[i] for i in indices],"CouponFace",(0,0,1),
                  [atlas_uv("coupon",(poly[i][0]+67)/134,(poly[i][1]+19)/38) for i in indices])
        part.face([back[i] for i in indices],"Ceramic",(0,0,-1))
    for i in range(len(poly)):
        j=(i+1)%len(poly);a,b=poly[i],poly[j]
        perimeter=(a[0]==b[0] and abs(a[0])==67) or (a[1]==b[1] and abs(a[1])==19)
        part.face([back[i],back[j],front[j],front[i]],"Ceramic" if perimeter else "FreshBreak",
            (b[1]-a[1],a[0]-b[0],0))
    return part


def intact_coupon():
    # Cross sections preserve the printed face and the free overhangs when the
    # centre deflects. The two roller lines are 104 mm apart.
    part=Part("fracture_coupon",(CU,CV,CD))
    sections=[-67,-60,-52,-44,-36,-28,-20,-12,-6,0,6,12,20,28,36,44,52,60,67]
    for x0,x1 in zip(sections,sections[1:]):
        rim=[(x0,-19),(x1,-19),(x1,19),(x0,19)]
        def layer(z):return [V((CU+x/1000,CV+y/1000,CD+z)) for x,y in rim]
        top,bottom=layer(THICKNESS/2),layer(-THICKNESS/2)
        part.face(top,"CouponFace",(0,0,1),[atlas_uv("coupon",(x+67)/134,(y+19)/38) for x,y in rim])
        part.face(bottom,"Ceramic",(0,0,-1))
        for i,j,normal in [(0,1,(0,-1,0)),(2,3,(0,1,0))]:
            part.face([bottom[i],bottom[j],top[j],top[i]],"Ceramic",normal)
        if x0==sections[0]:part.face([bottom[3],bottom[0],top[0],top[3]],"Ceramic",(-1,0,0))
        if x1==sections[-1]:part.face([bottom[1],bottom[2],top[2],top[1]],"Ceramic",(1,0,0))
    return part


def build():
    parts=[];frame=Part("fracture_frame");mark=Part("fracture_markings");guard=Part("fracture_guard")
    # Two fixed bridge channels clear both the hatch leaf and the service risers.
    for v in (-.105,.105):
        frame.plate(0,v,-.007,.724,.036,.019,.012,"Anodized")
        for u in (-.341,.341):
            frame.plate(u,v,-.239,.062,.074,.009,.012,"Edge")
            frame.cylinder((u,v,-.236),(u,v,-.021),.012,"Anodized",24)
            frame.cylinder((u,v,-.027),(u,v,-.012),.019,"Edge",24)
            frame.screw(u,v,.004,.008,1.4+v)
    frame.plate(0,0,.005,.503,.323,.034,.032,"Seal",.003)
    frame.plate(0,0,.020,.498,.315,.040,.032,"Casting",.0045)
    frame.ring(0,0,.041,.490,.308,.031,.004,.005,"Edge")
    frame.plate(-.007,.133,.042,.430,.032,.003,.005,"Anodized",.0007)
    mark.decal(-.007,.133,.0437,.425,.0295,"header")
    for s in (-1,1):
        for v in (-.127,.120):frame.screw(s*.233,v,.043,.0085,5*s*v)
    # Transparent guard has a physical seat, retainer, compressed seal and a short chamfer.
    u,v=-.049,.008
    frame.ring(u,v,.106,.302,.198,.026,.016,.067,"Anodized")
    frame.ring(u,v,.110,.295,.193,.023,.010,.006,"Seal")
    frame.ring(u,v,.117,.304,.203,.029,.009,.008,"Edge")
    frame.ring(u,v,.1185,.285,.184,.019,.005,.006,"Anodized")
    guard.plate(u,v,.1118,.279,.177,.0032,.018,"Guard",.0006)
    mark.decal(u,v,.041,.267,.158,"bed")
    for sx in (-1,1):
        for yy in (v-.075,v,v+.075):frame.screw(u+sx*.1447,yy,.116,.0049,sx*.41+yy)
    for xx in (u-.088,u+.045): 
        for sy in (-1,1):frame.screw(xx,v+sy*.0965,.116,.0048,xx*9+sy)
    for ix in (-.052,.052):
        x=CU+ix
        frame.plate(x,CV,.050,.020,.058,.014,.004,"Anodized")
        frame.cylinder((x,CV-.025,.064),(x,CV+.025,.064),.004,"Steel",18)
        frame.cylinder((x,CV-.023,.064),(x,CV+.023,.064),.0075,"Steel",32)
        for k in (-1,1):
            frame.plate(x,CV+k*.025,.058,.016,.005,.021,.001,"Edge",.0007)
    # A tiny warm luminaire bounces off the chamber back and both fracture faces.
    frame.plate(u+.078,.084,.072,.048,.011,.029,.003,"Anodized")
    frame.plate(u+.078,.077,.071,.041,.0028,.021,.001,"Lamp",.00045)
    for i in range(4):
        x=u+.062+i*.010;frame.cylinder((x,.077,.058),(x,.077,.084),.0006,"Steel",8)
    frame.plate(CU,.087,.089,.028,.017,.028,.004,"Edge",.001)
    punch=Part("fracture_punch",(CU,CV,.095))
    punch.plate(CU,.051,.094,.013,.071,.007,.003,"Steel")
    punch.cylinder((CU,CV+.019,.094),(CU,CV,.094),.0055,"Steel",24)
    punch.cylinder((CU,CV,.094),(CU,CV,.079),.0067,"Steel",32,.0049)
    # Witness dial: retained red follower behind an independently moving black pointer.
    du,dv=.163,.074
    frame.spin(du,dv,[(.057,.038,"Anodized"),(.058,.044,"Steel"),(.055,.055,"Edge"),(.051,.057,"Anodized"),(.048,.053,"Seal"),(.0475,.049,"Seal")])
    pts=[(du+.050*math.cos(TAU*i/80),dv+.050*math.sin(TAU*i/80),.0495) for i in range(80)]
    mark.face(pts,"Markings",(0,0,1),[atlas_uv("dial",.5+(x-du)/.100,.5+(y-dv)/.100) for x,y,_ in pts])
    glass=[(du+.049*math.cos(TAU*i/64),dv+.049*math.sin(TAU*i/64),.0558) for i in range(64)]
    guard.face(glass,"Guard",(0,0,1))
    a=math.radians(225);c,s=math.cos(a),math.sin(a)
    def pointer(name,z,mat,length,back):
        n=Part(name,(du,dv,z));shape=[(-back,-.0017),(.027,-.0014),(length,0),(.027,.0014),(-back,.0017)]
        poly=[(du+x*c-y*s,dv+x*s+y*c) for x,y in shape];n.polygon(poly,z,z+.0008,mat)
        return n
    needle=pointer("fracture_needle",.052,"Pointer",.042,.007)
    peak=pointer("fracture_peak_needle",.051,"Witness",.045,.003)
    frame.cylinder((du,dv,.053),(du,dv,.0553),.0048,"Steel",32,.0036)
    pu,pv=.165,-.018
    frame.spin(pu,pv,[(.031,.039,"Anodized"),(.032,.050,"Edge"),(.029,.060,"Seal"),(.020,.065,"Steel")],48)
    lever=Part("fracture_press",(pu,pv,.076))
    shape=[(-.019,.003),(-.014,-.029),(.002,-.044),(.014,-.089),(.025,-.097),(.039,-.095),(.047,-.085),
           (.040,-.064),(.022,-.034),(.021,-.010),(.018,.009),(.009,.017),(-.007,.018)]
    lever.polygon([(pu+x,pv+y) for x,y in shape],.066,.081,"Lever")
    lever.cylinder((pu,pv,.062),(pu,pv,.083),.0187,"Lever",48,.017)
    lever.screw(pu,pv,.084,.0107,.21)
    for j in range(7):
        q=j*.007
        lever.cylinder((pu+.008+q*.39,pv-.045-q,.0814),(pu+.022+q*.38,pv-.040-q,.0814),.0033,"Grip",12)
    mark.decal(.156,-.139,.041,.136,.024,"load")
    for j in range(7):
        a=math.radians(-72-j*8.5)
        frame.cylinder((pu+.037*math.cos(a),pv+.037*math.sin(a),.0415),
                       (pu+.041*math.cos(a),pv+.041*math.sin(a),.0415),.00065,"Edge",8)
    # Moving cassette shutter blades nest behind the lower apron when open.
    shutters=[]
    for i in range(5):
        y=-.094;z=.1017+i*.00115
        b=Part(f"fracture_shutter_{i+1:02}",(u,y,z));b.plate(u,y,z,.268,.035,.0010,.002,"Cartridge",.00022)
        b.plate(u,y+.0154,z+.0007,.262,.0014,.0006,.0003,"Edge",.00012);shutters.append(b)
    frame.plate(u,-.117,.109,.285,.047,.015,.009,"Casting")
    mark.decal(u+.020,-.121,.1167,.178,.0176,"index")
    ru,rv=-.133,-.115
    frame.plate(ru+.011,rv,.119,.071,.029,.006,.010,"Seal")
    reload=Part("fracture_reload",(ru,rv,.056))
    reload.plate(ru,rv,.128,.039,.025,.015,.008,"Cartridge")
    for j in range(6):
        x=ru+(j-2.5)*.0047
        reload.cylinder((x,rv-.008,.136),(x,rv+.008,.136),.0011,"Grip",10)
    # Short serial plate on the lower casting, visible from a crouched/glancing angle.
    mark.decal(.025,-.150,.041,.103,.0132,"serial")
    sleeve=intact_coupon()
    shards=[]
    for i,poly in enumerate(POLYGONS):
        _,cx,cy=polygon_mass_centroid(poly);shards.append(coupon(f"fracture_shard_{i+1:02}",poly,(CU+cx,CV+cy,CD)))
    parts=[frame,guard,mark,lever,punch,needle,peak,reload,sleeve,*shutters,*shards]
    objects=[part.make() for part in parts]
    strip=next(ob for ob in objects if ob.name=="fracture_coupon")
    strip.shape_key_add(name="Basis")
    flex=strip.shape_key_add(name="BeamFlex")
    for vert in flex.data:
        x=abs(vert.co.x)/.052
        factor=(1-1.5*x*x+.5*x**3) if x<1 else -1.5*(x-1)
        vert.co.y-=.0007*factor
    return objects


def export(parts):
    write_contract()
    for im in bpy.data.images:
        if im.filepath:im.pack()
    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:ob.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.export_scene.gltf(filepath=str(SITE/"FractureCartridge.glb"),export_format='GLB',use_selection=True,
        export_apply=True,export_yup=True,export_animations=False,export_texcoords=True,export_normals=True,export_materials='EXPORT')
    bpy.ops.export_scene.fbx(filepath=str(UNITY/"FractureCartridge.fbx"),use_selection=True,axis_forward='-Z',axis_up='Y',
        object_types={'MESH'},bake_space_transform=True,bake_anim=False,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',path_mode='STRIP',use_mesh_modifiers=False,add_leaf_bones=False)
    # The editable assembly opens intact. The five actual fracture alternatives
    # remain independently selectable in their own collection.
    alternatives=bpy.data.collections.new("Fractured specimen");bpy.context.scene.collection.children.link(alternatives)
    for ob in parts:
        if ob.name.startswith("fracture_shard_"):
            for coll in tuple(ob.users_collection):coll.objects.unlink(ob)
            alternatives.objects.link(ob)
    alternatives.hide_viewport=True;alternatives.hide_render=True
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/"FractureCartridge.blend"),compress=True)


export(build())
