"""Author Aster Reach, a counterline car and the receiving vault's working head.

Run with system Python --textures, then with Blender -b -P on this file.
The Blender source and both engine exports share the same panels, terrain,
pressure glazing, movable parts, UVs and finish survey.
"""
from pathlib import Path
from math import sin, cos, pi
import json
import random
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import orbital_valley as valley

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"web/assets/orbital"
NATIVE=ROOT/"unity/Assets/Upwell/Resources/OrbitalHardware"
ART=ROOT/"blender/orbital"
TAU=2*pi


def finish(name,color,metal,rough,*,image=None,emit=None,gain=0,alpha=1):
    return dict(name=name,color=color,metal=metal,rough=rough,image=image or "",emit=emit or "#000000",gain=gain,alpha=alpha)


MATERIALS=[
    finish("Aster_Shell","#d7d5cc",.41,.46,image="armor"),
    finish("Aster_Recoat","#b2b7b3",.37,.50,image="armor"),
    finish("Aster_BlueGrey","#677d89",.56,.38,image="armor"),
    finish("Aster_Structure","#97a6a6",.63,.34),
    finish("Aster_Frame","#414d55",.61,.41),
    finish("Aster_Gasket","#272e31",.12,.70),
    finish("Aster_Foil","#b79a67",.65,.49,image="foil"),
    finish("Aster_Radiator","#596268",.46,.59,image="radiator"),
    finish("Aster_Mirror","#b8cbc9",.78,.16,image="mirror"),
    finish("Aster_Glass","#729fa9",.29,.17,alpha=.115),
    finish("Aster_Soil","#ffffff",.02,.91,image="valley",emit="#ffeece",gain=.64),
    finish("Aster_Water","#42868c",.41,.23,emit="#295158",gain=.27),
    finish("Aster_Timber","#718058",.01,.95,emit="#74835a",gain=.44),
    finish("Aster_Building","#ced0ba",.13,.72,emit="#b9b99e",gain=.37),
    finish("Aster_Roof","#a79179",.14,.72,emit="#9c8968",gain=.42),
    finish("Aster_Greenhouse","#a2c3b5",.29,.32,emit="#859f84",gain=.43),
    finish("Aster_TowerGlass","#799698",.32,.32,emit="#7d9992",gain=.37),
    finish("Aster_LitWindow","#d7b37b",.06,.52,emit="#ffe2ac",gain=1.35),
    finish("Aster_Navigation","#b5d5cf",.08,.43,emit="#cce7e3",gain=2),
    finish("Aster_Orange","#ac5e32",.31,.58),
    finish("Aster_CarSkin","#ffffff",.37,.44,image="car-skin"),
    finish("Aster_CarGlass","#75939e",.32,.19,alpha=.22),
    finish("Aster_Seat","#596b71",.04,.81),
    finish("Aster_Mark","#ffffff",.17,.57,image="mark"),
    finish("Aster_PaleStone","#c1b496",.05,.83,emit="#a39578",gain=.32),
    finish("Aster_WindowBank","#678386",.35,.27,emit="#99afa5",gain=.45),
    finish("Aster_Liner","#5c6461",.13,.70),
    finish("Aster_LandShadow","#273c3d",.02,.94,alpha=.33),
]


def textures():
    from PIL import Image,ImageDraw,ImageFont,ImageFilter
    import numpy as np
    SITE.mkdir(parents=True,exist_ok=True);NATIVE.mkdir(parents=True,exist_ok=True)
    img=Image.open(ROOT/"web/assets/world/habitat-hull.webp").convert("RGB")
    rng=random.Random(67023);rs=np.random.default_rng(67023)
    def save(im,name):
        im.convert("RGB").save(NATIVE/(name+".jpg"),quality=92,subsampling=0,optimize=True)
    def stippled(im,grain):
        a=np.asarray(im,dtype=float);height,width=a.shape[:2]
        coarse=Image.fromarray(rs.integers(98,157,(25,18),dtype=np.uint8)).resize((width,height),Image.Resampling.BICUBIC)
        n=(np.asarray(coarse,dtype=float)-128)*grain*.052+rs.normal(0,grain,(height,width))
        return Image.fromarray(np.clip(a+n[:,:,None],0,255).astype(np.uint8))
    # Use the existing orbital structure's measured-detail atlas for worn
    # pressure panels. Only sample the uninterrupted armoured portion.
    armor=img.crop((246,0,404,1254)).resize((384,1024),Image.Resampling.LANCZOS)
    a=np.asarray(armor,dtype=float);q=np.clip(a*.40+143,0,255).astype(np.uint8)
    armor=Image.fromarray(q);d=ImageDraw.Draw(armor)
    for y in (8,179,439,728,1014):
        d.line((0,y,384,y),fill=(92,100,100),width=2);d.line((0,y+2,384,y+2),fill=(211,214,203))
    for x in (6,157,368):d.line((x,0,x,1024),fill=(146,152,149))
    save(stippled(armor,2.6),"armor")
    for name,base in [('foil',(154,150,138)),('radiator',(147,161,158)),('mirror',(198,214,214))]:
        tex=Image.new("RGB",(512,512),base);d=ImageDraw.Draw(tex)
        if name=='foil':
            for _ in range(330):
                x=rng.randrange(516);y=rng.randrange(516);k=rng.uniform(-.7,.7);l=rng.randrange(9,68)
                c=rng.randrange(115,171);d.line([(x,y),(x+l*.48,y+k*l*.2),(x+l,y+k*l)],fill=(c,c-2,c-11))
        else:
            for y in range(0,512,18 if name=='radiator' else 82):
                d.line((0,y,512,y),fill=(80,100,105) if name=='radiator' else (150,163,166),width=2)
                d.line((0,y+2,512,y+2),fill=(160,171,176) if name=='radiator' else (207,222,230))
            for x in (3,256,508):d.line((x,0,x,512),fill=(105,118,119))
        save(stippled(tex,1.8 if name=='mirror' else 3.0),name)
    valley.terrain_texture(ROOT/'art/orbital-valley',NATIVE/'valley.jpg')
    body=Image.new("RGB",(1024,1024),(189,194,188));d=ImageDraw.Draw(body)
    for y in (28,210,490,735,1001):
        d.line((0,y,1024,y),fill=(112,119,119),width=2);d.line((0,y+2,1024,y+2),fill=(209,212,203))
    for x in (0,102,297,508,677,911):
        d.line((x,0,x,1024),fill=(128,135,133),width=2)
        for y in range(16,1023,46): d.ellipse((x+5,y,x+8,y+3),fill=(114,123,121))
    ar=np.asarray(stippled(body,2.8)).astype(float);yy=np.arange(1024)[:,None]
    for _ in range(60):
        x=rng.randrange(1022);top=rng.choice([30,209,492,737]);length=rng.uniform(4,75)
        fade=np.where(yy>top,np.exp(-np.maximum(yy-top,0)/length),0);ar[:,x:x+2,:]-=fade[:,:,None]*rng.uniform(3,11)
    save(Image.fromarray(np.clip(ar,0,255).astype(np.uint8)),"car-skin")
    mark=Image.new("RGB",(1024,256),(192,196,183));d=ImageDraw.Draw(mark)
    fontpath="C:/Windows/Fonts/bahnschrift.ttf"
    d.rectangle((0,0,20,256),fill=(163,68,35));d.text((54,29),"ASTER  REACH",fill=(31,46,49),font=ImageFont.truetype(fontpath,108))
    d.text((65,164),"AXIAL TRANSFER   /   STATION  07",fill=(61,77,77),font=ImageFont.truetype(fontpath,36))
    save(stippled(mark,1.6),"mark")
    registrations()
    survey=json.dumps(dict(materials=MATERIALS),indent=2)
    for path in (SITE,NATIVE):(path/"finishes.json").write_text(survey)


def registrations():
    from PIL import Image,ImageDraw,ImageFont
    fontpath="C:/Windows/Fonts/bahnschrift.ttf"
    for identity in ('C12','F04','F18','F26','C19','F11','T03','C21','F22','F16','C25','F28','T06','C15','F31','F24'):
        card=Image.new("RGB",(768,192),(198,200,191));d=ImageDraw.Draw(card)
        d.rectangle((0,0,17,192),fill=(169,83,54));d.rectangle((685,25,737,42),fill=(169,83,54))
        d.text((43,20),'TL  /  '+identity,fill=(41,54,58),font=ImageFont.truetype(fontpath,86))
        d.text((45,135),'COUNTERLINE   /   TETHER AUTHORITY',fill=(41,54,58),font=ImageFont.truetype(fontpath,24))
        card.save(NATIVE/('registration-'+identity+'.jpg'),quality=92,subsampling=0)


if "--registrations" in sys.argv:
    registrations();raise SystemExit
if "--valley-texture" in sys.argv:
    valley.terrain_texture(ROOT/'art/orbital-valley',NATIVE/'valley.jpg')
    survey=json.dumps(dict(materials=MATERIALS),indent=2)
    for path in (SITE,NATIVE):(path/"finishes.json").write_text(survey)
    raise SystemExit
if "--textures" in sys.argv:
    textures();raise SystemExit

import bpy
from mathutils import Vector

def library_layout():
    for name in ("AsterReach","CounterCar","Receiver"):
        coll=bpy.data.collections.get(name)
        if coll and not coll.asset_data:coll.asset_mark()
        layer=bpy.context.view_layer.layer_collection.children.get(name)
        if layer:layer.hide_viewport=name!="AsterReach"
    bpy.ops.object.select_all(action='DESELECT')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                view=area.spaces.active;view.region_3d.view_distance=61
                view.region_3d.view_location=(0,0,0);view.region_3d.view_rotation=Vector((30,-49,29)).to_track_quat('Z','Y')
                view.shading.color_type='MATERIAL'

if "--library-layout" in sys.argv:
    bpy.context.preferences.filepaths.save_version=0
    library_layout();bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
    raise SystemExit

# Design vectors use the glTF basis, with a vertical +Y axle. Keeping this
# conversion at the face boundary gives FBX and GLB the same local pivots.
def V(a):return Vector(a)
def p(a,y,r):return V((r*sin(a),y,r*cos(a)))
def radial(a):return V((sin(a),0,cos(a)))
def tangent(a):return V((cos(a),0,-sin(a)))
Y=V((0,1,0))

def linear(s):
    rgb=[int(s[1+i:3+i],16)/255 for i in (0,2,4)]
    return tuple(x/12.92 if x<.04045 else ((x+.055)/1.055)**2.4 for x in rgb)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
SITE.mkdir(parents=True,exist_ok=True);NATIVE.mkdir(parents=True,exist_ok=True);ART.mkdir(parents=True,exist_ok=True)
mats={}
for spec in MATERIALS:
    material=bpy.data.materials.new(spec['name']);material.use_nodes=True
    material.diffuse_color=(*linear(spec['color']),spec['alpha'])
    node=material.node_tree.nodes.get("Principled BSDF");node.inputs['Base Color'].default_value=material.diffuse_color
    node.inputs['Metallic'].default_value=spec['metal'];node.inputs['Roughness'].default_value=spec['rough']
    node.inputs['Emission Color'].default_value=(*linear(spec['emit']),1);node.inputs['Emission Strength'].default_value=spec['gain']
    if spec['image']:
        img=bpy.data.images.load(str(NATIVE/(spec['image']+'.jpg')),check_existing=True)
        tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img;material.node_tree.links.new(tex.outputs['Color'],node.inputs['Base Color'])
        if spec['name']=='Aster_Soil': material.node_tree.links.new(tex.outputs['Color'],node.inputs['Emission Color'])
    if spec['alpha']<1:
        node.inputs['Alpha'].default_value=spec['alpha'];material.surface_render_method='DITHERED'
    material.use_backface_culling=True;mats[spec['name'].removeprefix('Aster_')]=material

class Piece:
    def __init__(self,name):
        self.name=name;self.vertices=[];self.faces=[];self.uv=[];self.materials=[];self.ids=[];self.normals=[]
    def face(self,pts,mat,normal,uv=None,normals=None):
        pts=[V(q) for q in pts];uv=uv or [(0,0),(1,0),(1,1),(0,1)][:len(pts)]
        plane=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
        if plane.dot(V(normal))<0:
            pts.reverse();uv=uv[::-1];plane=-plane
            if normals:normals=normals[::-1]
        for n in normals or [plane]*len(pts):self.normals.append((n.x,-n.z,n.y))
        offset=len(self.vertices);self.vertices.extend((v.x,-v.z,v.y) for v in pts);self.faces.append(tuple(range(offset,offset+len(pts))))
        self.uv.extend(uv)
        if mat not in self.materials:self.materials.append(mat)
        self.ids.append(self.materials.index(mat))
    def block(self,c,axes,dims,mat):
        x,y,z=[V(a)*s*.5 for a,s in zip(axes,dims)];c=V(c)
        for n,a,b in ((x,y,z),(-x,y,z),(y,z,x),(-y,z,x),(z,x,y),(-z,x,y)):
            self.face([c+n-a-b,c+n+a-b,c+n+a+b,c+n-a+b],mat,n)
    def obox(self,a,y,r,w,h,depth,mat):
        self.block(p(a,y,r),(tangent(a),Y,radial(a)),(w,h,depth),mat)
    def rod(self,a,b,r,mat,n=7,r2=None):
        a,b=V(a),V(b);v=(b-a).normalized();ax=v.cross(Y if abs(v.y)<.93 else V((1,0,0))).normalized();az=v.cross(ax).normalized()
        edges=[ax*cos(TAU*i/n)+az*sin(TAU*i/n) for i in range(n)];rr=r if r2 is None else r2
        for i,q in enumerate(edges):
            t=edges[(i+1)%n];self.face([a+q*r,a+t*r,b+t*rr,b+q*rr],mat,q+t,normals=[q,t,t,q])
    def lid(self,center,axis,r,mat,segments=32):
        c=V(center);axis=V(axis).normalized();u=axis.cross(Y if abs(axis.y)<.93 else V((1,0,0))).normalized();v=axis.cross(u)
        for i in range(segments):
            a=i*TAU/segments;b=(i+1)*TAU/segments
            self.face([c,c+r*(u*cos(a)+v*sin(a)),c+r*(u*cos(b)+v*sin(b))],mat,axis)
    def arc(self,a,b,y,z,r,mat,steps=12,uvbounds=(0,1,0,1),inside=False,endr=None):
        u0,u1,v0,v1=uvbounds;rr=r if endr is None else endr
        for i in range(steps):
            t=i/steps;t1=(i+1)/steps;aa=a+(b-a)*t;bb=a+(b-a)*t1
            sign=(-1 if inside else 1);slope=(rr-r)/(z-y) if abs(z-y)>.00001 else 0
            na=(radial(aa)-Y*slope).normalized()*sign;nb=(radial(bb)-Y*slope).normalized()*sign
            self.face([p(aa,y,r),p(bb,y,r),p(bb,z,rr),p(aa,z,rr)],mat,radial((aa+bb)/2)*sign,
                      [(u0+(u1-u0)*t,v0),(u0+(u1-u0)*t1,v0),(u0+(u1-u0)*t1,v1),(u0+(u1-u0)*t,v1)], [na,nb,nb,na])
    def ring(self,y,r,thick,mat,steps=80,depth=None):
        self.arc(0,TAU,y-thick*.5,y+thick*.5,r,mat,steps)
        if depth:
            self.arc(0,TAU,y+thick*.5,y+thick*.5+.012,r,mat,steps,endr=r-depth)
    def make(self):
        mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.vertices,[],self.faces)
        for mat in self.materials:mesh.materials.append(mats[mat])
        mesh.polygons.foreach_set('material_index',self.ids);layer=mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set('uv',[v for point in self.uv for v in point]);mesh.update()
        if hasattr(self,"diameters"):
            section=mesh.uv_layers.new(name="MemberDiameter")
            section.data.foreach_set('uv',[x for diameter in self.diameters for x in (diameter,0.)])
            mesh.uv_layers.active=layer
        mesh.polygons.foreach_set('use_smooth',[True]*len(self.faces));mesh.normals_split_custom_set_from_vertices(self.normals)
        ob=bpy.data.objects.new(self.name,mesh);bpy.context.collection.objects.link(ob);return ob

class PressureStructure(Piece):
    """Keep the original manufactured members plus a survey of their real section."""
    def __init__(self):
        super().__init__("rotating_habitat")
        self.near=Piece("pressure_members");self.near.diameters=[];self.survey=[]
    def register_section(self,diameter):
        self.near.diameters.extend([diameter]*(len(self.near.vertices)-len(self.near.diameters)))
    def member(self,a,b,u,v,shape,mat):
        self.survey.append((*a,*b,*u,*v,shape,next(i for i,s in enumerate(MATERIALS) if s['name']=='Aster_'+mat)))
    def rod(self,a,b,r,mat,n=7,r2=None):
        if r2 is not None or mat not in ("Structure","Frame","BlueGrey","Shell") or r>.115:
            return super().rod(a,b,r,mat,n,r2)
        d=(V(b)-V(a)).normalized();basis=d.cross(Y if abs(d.y)<.93 else V((1,0,0))).normalized()
        self.member(a,b,basis*r,d.cross(basis)*r,0,mat)
        self.near.rod(a,b,r,mat,n,r2)
        self.register_section(2*r)
    def block(self,c,axes,dims,mat):
        long=max(range(3),key=lambda i:dims[i]);other=[i for i in range(3) if i!=long]
        if mat!="Structure" or dims[long]<.45 or max(dims[i] for i in other)>.13:
            return super().block(c,axes,dims,mat)
        axis=V(axes[long])*dims[long]*.5;c=V(c)
        self.member(c-axis,c+axis,V(axes[other[0]])*dims[other[0]]*.5,V(axes[other[1]])*dims[other[1]]*.5,1,mat)
        self.near.block(c,axes,dims,mat)
        self.register_section(max(dims[i] for i in other))
    def write_survey(self):
        data=struct.pack("<4sI",b"ASR1",len(self.survey))
        data+=b"".join(struct.pack("<12fBBxx",*record) for record in self.survey)
        (SITE/"members.bin").write_bytes(data);(NATIVE/"members.bytes").write_bytes(data)

def habitat():
    drum=PressureStructure();axle=Piece("stationary_axle");tram=Piece("maintenance_train")
    r=7.45;half=20.5;rand=random.Random(7747)
    for sector in range(3):
        angle=sector*TAU/3
        # Opaque land sectors back onto the exterior armour. Across the
        # axis, each transparent sector is a real aperture onto this landscape.
        lo,hi=angle-.559,angle+.559
        drum.arc(lo,hi,-half,half,r,'Shell',18)
        drum.arc(lo,hi,-half+.10,half-.10,r-.23,'Soil',26,inside=True)
        # Curved terraces and buildings rise *towards* the rotation axis.
        # Their silhouettes and parallax are visible through the opposite glazing.
        for j in range(17):
            y=-18+j*2.17;river=angle+valley.river(y)
            for k in range(4):
                z=y+k*.55;river=angle+valley.river(z)
                river2=angle+valley.river(z+.55)
                w=.021+.004*sin(z*.55)
                drum.face([p(river-w,z,r-.234),p(river+w,z,r-.234),p(river2+w,z+.553,r-.234),p(river2-w,z+.553,r-.234)],
                          "Water",-radial(river))
            for side in (-1,1):
                if (j+sector+(1 if side<0 else 0))%3==0:continue
                center=river+side*(.15+rand.random()*.17)
                for b in range(rand.randint(8,14)):
                    a=center+rand.uniform(-.070,.070);z=y+rand.uniform(-.58,.62);h=rand.uniform(.075,.32)
                    w=rand.uniform(.062,.20);l=rand.uniform(.12,.31)
                    valley.village_house(drum,p,Y,radial,tangent,a,z,angle,w,l,h,b)
                if j%4==1:
                    for b in range(4):
                        a=center+side*(.077+b*.016)
                        drum.obox(a,y+.22,r-.31,.077,.64,.096,'Greenhouse')
            if j%3==1:
                # Civic centres are tall enough to throw a silhouette over
                # the distant fields. Glazed storeys sit below stepped roofs.
                for b in range(3):
                    a=river+(.16+b*.036)*(1 if j%2 else -1);z=y+(b-1)*.34
                    hh=.48-.09*b;drum.obox(a,z,r-.24-hh*.5,.22,.32,hh,'TowerGlass')
                    for level in range(3):
                        drum.obox(a,z,r-.27-.115*level,.234,.339,.024,'Building')
                    drum.obox(a,z,r-.26-hh,.243,.35,.029,'Roof')
                    drum.obox(a,z+.024,r-.295-hh,.154,.17,.070,'Building')
            for q in range(7):
                yy=y+rand.uniform(-.80,.81);a=river+rand.choice((-1,1))*rand.uniform(.038,.102)
                ht=rand.uniform(.085,.19);rr=rand.uniform(.050,.105)
                drum.rod(p(a,yy,r-.24),p(a,yy,r-.24-ht*.52),rr*.47,'Timber',6,r2=rr)
                drum.rod(p(a,yy,r-.24-ht*.52),p(a,yy,r-.24-ht),rr,'Timber',6,r2=rr*.27)
            # One service bore and twin feed trunks visibly run along land-edge beams.
            for side in (-1,1):
                a=angle+side*.551
                if j<16:drum.rod(p(a,y,r-.27),p(a,y+2.19,r-.27),.059,'BlueGrey',7)
        # The sun collectors illuminate the inner valleys. Glass is kept
        # optically thin so the far side reads at acquisition-camera distance.
        wa=hi+.017;wb=angle+TAU/3-.559-.017
        drum.arc(wa,wb,-half,half,r+.009,'Glass',20)
        # Two inhabited galleries flank the central atrium below each
        # observation window. Their terraced roof gardens are seen at an
        # oblique angle while the full valley is seen through the open centre.
        for edge,hand in ((wa,1),(wb,-1)):
            g0=edge+hand*.027;g1=edge+hand*.217;rr=r-.91
            drum.arc(min(g0,g1),max(g0,g1),-half+.40,half-.40,rr,'Soil',8,(.05,.41,0,1))
            drum.arc(min(g0,g1),max(g0,g1),-half+.40,half-.40,rr-.14,'Recoat',8,inside=True)
            for a in (g0,g1):
                drum.rod(p(a,-19.9,rr),p(a,19.9,rr),.069,'Structure',8)
            for j in range(16):
                y=-18.9+j*2.52;ga=edge+hand*(.105+.019*sin(j))
                drum.obox(ga,y,rr+.070,.27,.52,.15,'Building')
                drum.obox(ga,y,rr+.167,.30,.55,.049,'Greenhouse' if j%3 else 'Roof')
                drum.obox(ga+.011*hand,y-.19,rr+.202,.082,.13,.033,'LitWindow')
                for jx in range(3):
                    aa=ga+hand*(.049+.011*jx)
                    drum.rod(p(aa,y-.55+jx*.43,rr+.014),p(aa,y-.55+jx*.43,rr+.175),.073,'Timber',6,r2=.031)
                drum.rod(p(edge,y,r-.03),p(g0,y+.21,rr-.09),.068,'Structure',8)
                drum.rod(p(g1,y,rr-.08),p(edge,y+.69,r-.08),.035,'Frame',6)
        for k in range(5):
            a=wa+(wb-wa)*k/4
            drum.rod(p(a,-half-.12,r+.040),p(a,half+.12,r+.040),.039 if k not in (0,4) else .077,'Structure',8)
        for j in range(22):
            y=-half+j*1.94
            for i in range(8):
                a=wa+(wb-wa)*i/8;b=wa+(wb-wa)*(i+1)/8
                drum.rod(p(a,y,r+.028),p(b,y,r+.028),.024 if j%4 else .045,"Frame",5)
        # Service galleries, access covers, axial conduits and insulated seams.
        for edge in (-1,1):
            a=angle+edge*.46
            drum.rod(p(a,-19.75,r+.081),p(a,19.75,r+.081),.063,'BlueGrey',8)
        for j in range(12):
            y=-18.9+j*3.43
            drum.obox(angle-.29,y,r+.074,1.62,2.50,.13,'Radiator')
            for k in range(6):drum.obox(angle-.29,y-.92+k*.365,r+.16,1.43,.085,.050,'Structure')
            drum.obox(angle+.228,y-.47,r+.085,.87,1.04,.15,'BlueGrey')
            drum.obox(angle+.23,y-.45,r+.17,.61,.74,.032,'Foil' if j%3==0 else 'Shell')
            drum.obox(angle+.42,y+.97,r+.085,.16,.40,.072,'Orange')
        # Three mirror banks, mounted beyond the silhouette on folded triangular trusses.
        a=angle+.45;rad=radial(a);tan=tangent(a);mid=rad*(r+3.69)-tan*.25
        tilt=.89;wing=tan*cos(tilt)+rad*sin(tilt);back=rad*cos(tilt)-tan*sin(tilt)
        for j in range(8):
            y=-15.75+4.51*j
            for k in (-1,0,1):
                kt=tilt+.080*k+.016*sin(j*.6)
                facet=tan*cos(kt)+rad*sin(kt);facing=rad*cos(kt)-tan*sin(kt)
                ctr=mid+Y*y+wing*(k*1.52)+back*(abs(k)*.062)
                drum.block(ctr,(facet,Y,facing),(1.43,4.36,.078),'Mirror')
                drum.block(ctr-facing*.086,(facet,Y,facing),(1.42,4.33,.10),'Radiator')
                for side in (-1,1):
                    drum.rod(ctr+facet*(side*.722)-Y*2.17,ctr+facet*(side*.722)+Y*2.17,.016,'Structure',5)
            drum.rod(mid+Y*(y-2.20)-wing*2.33,mid+Y*(y-2.20)+wing*2.33,.044,'Structure',6)
            if j%2==0:
                base=p(a,y,r+.13);joint=mid+Y*y
                for side in (-1,1):
                    drum.rod(base+Y*(side*.72),joint+wing*(side*1.83),.107,'Shell',8)
                    drum.rod(base+tan*(side*.41)+Y*(side*.85),joint-wing*(side*1.19),.050,'Structure',7)
                drum.rod(joint-wing*.52,joint+wing*.52,.19,'Foil',10)
        for edge in (-1,1):drum.rod(mid-wing*2.28*edge-Y*17.93,mid-wing*2.28*edge+Y*17.93,.071,'Frame',7)
    for y in (-20.52,-13.73,-6.88,0,6.88,13.73,20.52):
        drum.ring(y,r+.127,.153,'Structure',84,.21)
        for j in range(24):
            a=j*TAU/24;drum.obox(a,y,r+.126,.22,.28,.11,'BlueGrey')
    for s in (-1,1):
        # A shallow pressure dome resolves into discrete overlapping whaleback panels.
        for j in range(48):
            a=TAU*j/48;b=TAU*(j+1)/48
            for k,(y0,y1,r0,r1) in enumerate(((20.49,21.65,7.45,7.04),(21.65,22.70,7.04,5.82),(22.70,23.67,5.82,3.94),(23.67,24.05,3.94,2.10))):
                drum.arc(a+.001,b-.001,y0*s,y1*s,r0,('Shell' if (j//3+k)%9 else 'Recoat'),1,endr=r1)
            if j%3==0:
                drum.rod(p(a,s*20.54,7.50),p(a,s*21.68,7.08),.047,'Structure',6)
                drum.rod(p(a,s*21.68,7.08),p(a,s*23.70,3.95),.046,'Structure',6)
        # Inner pressure bulkhead closes the view through the windows, instead of open space.
        drum.arc(0,TAU,s*20.43,s*20.45,r-.22,'Liner',72,endr=.15,inside=True)
        drum.ring(s*24.0,2.27,.33,'Foil',56,.36)
        axle.arc(0,TAU,s*23.91,s*26.35,1.87,'Frame',48)
        axle.ring(s*24.80,2.02,.43,'Structure',48,.19);axle.ring(s*25.91,2.04,.57,'Foil',48,.25)
        axle.arc(0,TAU,s*26.18,s*26.62,1.42,'BlueGrey',40,endr=1.18)
        axle.lid((0,s*26.61,0),Y*s,1.17,'Gasket',48)
        axle.ring(s*26.59,1.19,.19,'Structure',48,.15)
        for j in range(12):
            a=j*TAU/12
            axle.obox(a,s*25.44,1.94,.31,.34,.13,'Navigation' if j%3==0 else 'Structure')
            axle.rod(p(a,s*23.75,2.23),p(a,s*25.81,2.08),.046,'Structure',6)
        for j in range(18):
            a=j*TAU/18
            drum.obox(a,s*21.2,7.26,.86,.32,.068,'Frame')
            drum.obox(a,s*21.2,7.303,.68,.205,.033,'LitWindow' if j%4 else 'TowerGlass')
        if s<0:
            for arm in range(2):
                a=arm*TAU/3+.32;c=p(a,-25.57,2.15)
                axle.rod(c,c+radial(a)*1.63,.30,'Structure',20)
                end=c+radial(a)*1.27
                reach=1.75+arm*.77
                axle.rod(end-Y*reach,end+Y*1.33,.61,'Shell',24)
                for q in (-reach+.25,-.4,1.08):axle.rod(end+Y*q,end+Y*(q+.17),.65,'Foil',24)
                axle.rod(end-Y*reach,end-Y*(reach+.27),.61,'BlueGrey',24,r2=.34)
                axle.lid(end-Y*(reach+.27),-Y,.34,'Frame',24)
                for i in range(3):
                    ctr=end+radial(a)*.58+Y*(i*.41-.61)
                    axle.block(ctr,(tangent(a),Y,radial(a)),(.45,.15,.09),'Frame')
                    axle.block(ctr+radial(a)*.05,(tangent(a),Y,radial(a)),(.37,.09,.04),'LitWindow')
    # Transit train attached to the underside of a valley. Its carriage
    # lights advance along the land strip beneath the pressure glazing.
    for a in (.167,.193):
        drum.rod(p(a,-18.45,r-.305),p(a,18.45,r-.305),.025,'Structure',7)
    for j in range(20):drum.obox(.18,-18.2+j*1.90,r-.275,.24,.076,.06,'BlueGrey')
    for i in range(4):
        tram.obox(0,(i-1.5)*.37,r-.36,.16,.33,.12,'Building')
        tram.obox(0,(i-1.5)*.37,r-.43,.106,.21,.025,'LitWindow')
    valley.fixtures(drum,axle,tram,p,Y,radial,tangent)
    drum.write_survey()
    return [drum.make(),axle.make(),tram.make(),drum.near.make()]


def car():
    body=Piece("counter_body");cargo=Piece("counter_freight");wheels=Piece("counter_wheels")
    profile=[(-4.43,.18),(-4.31,.55),(-4.05,.86),(-3.56,1.13),(-3.12,1.27),(-2.83,1.31),
             (-1.75,1.31),(-.44,1.31),(.13,1.31),(1.42,1.31),(2.70,1.30),(3.10,1.22),
             (3.63,1.03),(4.02,.81),(4.33,.41),(4.42,.13)]
    for i,((y0,r0),(y1,r1)) in enumerate(zip(profile,profile[1:])):
        if i in (6,8):continue
        body.arc(0,TAU,y0,y1,r0,'CarSkin',64,(0,1,(y0+4.5)/9,(y1+4.5)/9),endr=r1)
    for y in (-3.13,-2.74,-1.76,-.41,.11,1.44,2.66):
        body.ring(y,1.326 if -3<y<2.8 else 1.282,.045,"Gasket",60,.028)
    for bottom,top in ((-1.75,-.44),(.13,1.42)):
        y=(bottom+top)*.5
        # Continuous sills with individual sealed window reveals. Interior
        # seats and ceiling luminaires are real geometry behind the glazing.
        body.arc(0,TAU,bottom+.11,top-.11,.96,'BlueGrey',48,inside=False)
        body.arc(0,TAU,bottom,bottom+.14,1.313,'CarSkin',60);body.arc(0,TAU,top-.20,top,1.313,'CarSkin',60)
        for i in range(10):
            a=i*TAU/10;lo=a-TAU/20+.029;hi=a+TAU/20-.029
            body.arc(hi,lo+TAU/10,bottom,top,1.314,'CarSkin',3)
            body.arc(lo,hi,bottom+.145,bottom+.20,1.304,'Gasket',5)
            body.arc(lo,hi,top-.26,top-.20,1.304,'Gasket',5)
            for edge in (lo+.028,hi-.028):body.rod(p(edge,bottom+.19,1.325),p(edge,top-.25,1.325),.024,'Frame',7)
            body.arc(lo+.045,hi-.045,bottom+.19,top-.245,1.334,'CarGlass',5)
            pane=(lo+hi)/2
            body.obox(pane,y-.12,1.065,.36,.36,.114,'Seat')
            body.obox(pane,y+.099,1.09,.22,.11,.094,'Seat')
            for side in (-1,1):body.obox(pane+side*.135,y-.23,1.14,.054,.047,.22,'BlueGrey')
            body.obox(pane,y+.31,1.23,.53,.029,.019,'LitWindow')
            body.obox(pane+.15,y-.19,1.255,.024,.21,.012,'Frame')
    for s in (-1,1):
        for j in range(10):
            a=TAU*j/10
            body.rod(p(a,s*3.10,1.242),p(a,s*3.61,1.042),.020,'BlueGrey',6)
            body.rod(p(a,s*3.61,1.042),p(a,s*4.06,.777),.018,'BlueGrey',6)
        body.ring(s*3.81,.956,.093,'Foil',48,.073);body.ring(s*4.35,.40,.119,'Frame',32,.095)
        body.arc(0,TAU,s*4.40,s*4.46,.24,'Foil',36,endr=.035)
    for a in (0,.76,1.53,2.61,3.2,4.1,5.55):
        for y in (-2.23,1.99,2.52):
            body.obox(a,y,1.323,.50,.325,.032,'BlueGrey');body.obox(a,y,1.346,.43,.267,.018,'Radiator')
            for k in (-1,1):
                body.obox(a+k*.155,y,1.36,.032,.126,.016,'Structure')
        body.obox(a,-2.66,1.321,.18,.055,.023,'Orange')
    for aa in (-1.08,-.96):
        for lo,hi in ((-2.65,-1.86),(-.38,.06),(1.55,2.62)):
            body.rod(p(aa,lo,1.362),p(aa,hi,1.362),.025,'Structure' if aa< -1 else 'Foil',8)
            for y in (lo+.07,hi-.065):body.obox(aa,y,1.359,.086,.043,.047,'Frame')
    # Contact yokes saddle the paired guide surfaces and carry the two
    # independent drive bogies on the inboard side of the pressure shell.
    for hand in (-1,1):
        body.block((-1.27,.01,hand*.48),((1,0,0),Y,(0,0,1)),(.24,5.65,.18),'Frame')
        for y in (-2.50,2.46):
            body.block((-1.32,y,hand*.47),((1,0,0),Y,(0,0,1)),(.45,.68,.32),'Orange')
            body.rod((-1.25,y-.50,hand*.55),(-1.60,y+.16,hand*.55),.075,'Structure',9)
    # Four wheels have their own rolling pivots. Export one wheel and
    # instantiate its other positions in both runtimes.
    wheels.rod((0,0,-.099),(0,0,.099),.269,'Gasket',24)
    for z in (-.101,.101):
        wheels.rod((0,0,z-.016),(0,0,z+.016),.205,'BlueGrey',24)
        for j in range(6):
            a=j*TAU/6;wheels.rod((.04*cos(a),.04*sin(a),z),(.194*cos(a),.194*sin(a),z),.021,'Structure',6)
        wheels.rod((0,0,z-.018),(0,0,z+.018),.060,'Foil',12)
    for s in (-1,1):
        a=s*.97+1.94 # Cylindrical vacuum casks on the outboard carrier.
        for y in (-1.19,1.14):
            c=p(a,y,1.42);tan=tangent(a);rad=radial(a)
            cargo.block(c,(tan,Y,rad),(.81,1.82,.38),'Frame')
            for j in (-1,1):
                ctr=c+tan*(j*.187)+rad*.22
                cargo.rod(ctr-Y*.75,ctr+Y*.75,.178,'Foil',12)
                cargo.rod(ctr+Y*.75,ctr+Y*.81,.178,'Structure',16,r2=.065)
                cargo.rod(ctr+Y*.81,ctr+Y*.83,.065,'Frame',10,r2=.004)
                cargo.rod(ctr-Y*.75,ctr-Y*.81,.178,'BlueGrey',16,r2=.009)
                for v in (-.70,-.26,.27,.72):cargo.rod(ctr+Y*(v-.040),ctr+Y*(v+.040),.189,'Structure',12)
                cargo.rod(ctr+rad*.144-Y*.60,ctr+rad*.144+Y*.62,.026,'Structure',7)
            for yoff in (-.68,0,.68):cargo.block(c+rad*.427+Y*yoff,(tan,Y,rad),(.81,.090,.070),'Orange' if yoff else 'BlueGrey')
    return [body.make(),cargo.make(),wheels.make()]


def receiver():
    frame=Piece("survey_head");scan=Piece("survey_gimbal");cab=Piece("receiver_carriage");track=Piece("receiver_track")
    axes=((1,0,0),Y,(0,0,1))
    # A stereoscopic range finder. The stationary fork is bolted to the
    # near pressure portal; the separately exported optics yaw on trunnions.
    frame.block((0,-.029,0),axes,(.59,.060,.48),'Frame')
    for x in (-.235,.235):
        frame.block((x,.16,0),axes,(.082,.32,.32),'BlueGrey')
        for z in (-.15,.15):frame.rod((x,0,z),(x,.080,z),.039,'Structure',6)
    scan.block((0,.244,0),axes,(.51,.25,.265),'Shell');scan.block((0,.23,.147),axes,(.49,.212,.076),'Frame')
    for x in (-.148,.148):
        scan.rod((x,.247,.15),(x,.247,.265),.081,'Structure',16)
        scan.rod((x,.247,.266),(x,.247,.277),.064,'Gasket',16)
        scan.rod((x,.247,.277),(x,.247,.279),.043,'Navigation',16)
    # A captive inspection carrier on a fixed longitudinal rail. Its motor
    # and cable drum remain under the ledge, with a small working amber lamp.
    cab.block((0,.09,0),axes,(.71,.18,1.14),'BlueGrey')
    cab.block((.018,.27,-.03),axes,(.56,.27,.67),'Shell')
    for x in (-.34,.34):
        for z in (-.39,.39):cab.rod((x-.038,.074,z),(x+.038,.074,z),.133,'Gasket',12)
    cab.rod((-.12,.34,.21),(-.12,.57,.21),.067,'Frame',8)
    cab.rod((-.12,.55,.21),(-.12,.61,.21),.075,'LitWindow',12)
    for i in range(5):cab.block((.24,.30,-.24+i*.094),axes,(.062,.095,.040),'Radiator')
    for x in (-.34,.34):
        track.block((x,.019,0),axes,(.078,.042,3.90),'Structure')
        for z in (-1.90,1.90):track.block((x,.086,z),axes,(.097,.162,.084),'Orange')
    for z in (-1.65,-.84,0,.84,1.65):track.block((0,.009,z),axes,(.85,.018,.077),'BlueGrey')
    return [frame.make(),scan.make(),cab.make(),track.make()]


def export(name,pieces,write_models=True):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in pieces:ob.select_set(True)
    bpy.context.view_layer.objects.active=pieces[0]
    if write_models:
        bpy.ops.export_scene.gltf(filepath=str(SITE/(name+'.glb')),export_format='GLB',use_selection=True,
                                 export_apply=True,export_yup=True,export_animations=False,export_texcoords=True,
                                 export_normals=True,export_materials='EXPORT',export_image_format='AUTO')
        bpy.ops.export_scene.fbx(filepath=str(NATIVE/(name+'.fbx')),use_selection=True,axis_forward='-Z',axis_up='Y',
                                 object_types={'MESH'},bake_space_transform=True,bake_anim=False,
                                 apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,
                                 path_mode='STRIP',use_mesh_modifiers=True)
    collection=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(collection)
    for ob in pieces:
        for c in tuple(ob.users_collection):c.objects.unlink(ob)
        collection.objects.link(ob)
    return {'name':name,'meshes':[dict(name=p.name,vertices=len(p.data.vertices),faces=len(p.data.polygons)) for p in pieces]}

if "--habitat-only" in sys.argv or "--sync-habitat-library" in sys.argv:
    parts=habitat();report=export('AsterReach',parts,"--sync-habitat-library" not in sys.argv)
    # Update this collection inside the shared artist library. Both other
    # assemblies and their survey placement remain their existing .blend data.
    previous=ART/'OrbitalHardware.blend'
    if previous.is_file():
        with bpy.data.libraries.load(str(previous),link=False) as (available,selected):
            selected.collections=[k for k in ("CounterCar","Receiver") if k in available.collections]
        for collection in selected.collections:
            bpy.context.scene.collection.children.link(collection)
            for ob in collection.all_objects:
                if ob.type!='MESH':continue
                for slot in ob.material_slots:
                    if slot.material:
                        canonical=slot.material.name.partition('.')[0].removeprefix('Aster_')
                        if canonical in mats:slot.material=mats[canonical]
        parts[-1].parent=parts[0];library_layout()
        for im in bpy.data.images:
            if im.filepath and not im.packed_file and im.users:im.pack()
        staged=previous.with_name("Aster-library-stage.blend")
        bpy.ops.wm.save_as_mainfile(filepath=str(staged),compress=True)
        staged.replace(previous)
        index=ART/'geometry.json';history=json.loads(index.read_text())
        index.write_text(json.dumps([report if q['name']=='AsterReach' else q for q in history],indent=2))
    raise SystemExit
report=[export('AsterReach',habitat()),export('CounterCar',car()),export('Receiver',receiver())]
bpy.data.objects["pressure_members"].parent=bpy.data.objects["rotating_habitat"]
for im in bpy.data.images:
    if im.filepath:im.pack()
library_layout()
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'OrbitalHardware.blend'),compress=True)
(ART/'geometry.json').write_text(json.dumps(report,indent=2))
