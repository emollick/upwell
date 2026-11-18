"""Build Upwell's three-room carriage. Run in Blender's background Python.

All authoring coordinates here use metres in glTF axes. The mesh writer performs
one basis conversion at the boundary. This also makes the runtime pivots legible.
"""
from pathlib import Path
import json
import math
import random
import sys
import time
import tempfile

import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
scratch=ROOT/"source"/".export-cache"
scratch.mkdir(exist_ok=True)
tempfile.tempdir=str(scratch)
LIB = ROOT / "unity" / "Assets" / "Upwell" / "SourceModels" / "Textures"
WEB = ROOT / "web" / "assets" / "rooms"
FBX = ROOT / "unity" / "Assets" / "Upwell" / "SourceModels"
BLEND = ROOT / "blender"
for directory in (WEB, FBX, BLEND):
    directory.mkdir(parents=True, exist_ok=True)
rooms = ("observation", "berth", "service")
midpoints = dict(zip(rooms,(-3.8,0.,3.8)))
Y = Vector((0,1,0)); X = Vector((1,0,0)); Z = Vector((0,0,1))
T = math.tau
v = Vector
random.seed(107)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
manifest = json.loads((ROOT/"art"/"manifest.json").read_text())
propinfo = {p["id"]: p for room in manifest["rooms"] for p in room["props"]}
atlas = json.loads((LIB/"atlas.json").read_text())
stencils = json.loads((LIB/"stencils.json").read_text())
metadata = json.loads((LIB/"materials.json").read_text())
flex_parts={};mechanisms={};auxiliary_parts={};service_junctions={}
def aux(domain,room,id,parent,pivot):
    auxiliary_parts[id]={"domain":domain,"room":room,"parent":parent}
    return active(room,id,pivot,pivot,parent=parent)
def articulate(room,name,parent,pivot,axis,travel,detents,label):
    mechanisms[name]=dict(room=room,parent=parent,axis=axis,travel=travel,detents=detents,label=label)
    return active(room,name,pivot,pivot,parent=parent)
def remember_flex(room,name,parent,points,pins,width,thickness,material_name,kind,max_offset,support=None,guide=(0,0,1)):
    flex_parts[name]=dict(room=room,parent=parent,points=[v(q) for q in points],pins=pins,width=width,thickness=thickness,
                          material=material_name,kind=kind,limit=max_offset,support=support,guide=v(guide))
M = {}; imgcache={}
def lin(k):
    a=k/255
    return a/12.92 if a <= .04045 else ((a+.055)/1.055)**2.4


def image_source(path, noncolor=False):
    key = (str(path),noncolor)
    if key not in imgcache:
        im=bpy.data.images.load(str(path),check_existing=False)
        if noncolor: im.colorspace_settings.name="Non-Color"
        imgcache[key]=im
    return imgcache[key]


def material(name, settings):
    mat=bpy.data.materials.new(name); M[name]=mat
    mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links
    bs=nodes.get("Principled BSDF"); d=settings
    rgb=tuple(lin(k) for k in d["rgb"])
    mat.diffuse_color=(*rgb,d["alpha"])
    bs.inputs["Base Color"].default_value=(*rgb,1)
    bs.inputs["Roughness"].default_value=d["roughness"]
    bs.inputs["Metallic"].default_value=d["metallic"]
    bs.inputs["Coat Weight"].default_value=d.get("coat",0)
    bs.inputs["Coat Roughness"].default_value=d.get("coatRoughness",.2)
    bs.inputs["Transmission Weight"].default_value=d.get("transmission",0)
    if "ior" in d:bs.inputs["IOR"].default_value=d["ior"]
    bs.inputs["Specular IOR Level"].default_value=d.get("specular",.5)
    if "sheen" in d:
        bs.inputs["Sheen Weight"].default_value=d["sheen"]
        bs.inputs["Sheen Roughness"].default_value=d.get("sheenRoughness",.6)
    if "Iridescence Weight" in bs.inputs:bs.inputs["Iridescence Weight"].default_value=d.get("iridescence",0)
    bs.inputs["Alpha"].default_value=d["alpha"]
    bs.inputs["Emission Strength"].default_value=d.get("emission",0)
    if d.get("emission"):bs.inputs["Emission Color"].default_value=(*rgb,1)
    for key, (sock,noncolor) in {
        "baseColor":("Base Color",False),"normal":("Normal",True),"roughnessMap":("Roughness",True)}.items():
        if key not in d:continue
        tn=nodes.new("ShaderNodeTexImage");tn.image=image_source(LIB/d[key],noncolor)
        tn.location=(-550,{"baseColor":320,"normal":-290,"roughnessMap":10}[key])
        if key=="normal":
            nm=nodes.new("ShaderNodeNormalMap"); nm.location=(-210,-260)
            nm.inputs["Strength"].default_value=d.get("normalStrength",.56);links.new(tn.outputs["Color"],nm.inputs["Color"])
            links.new(nm.outputs["Normal"],bs.inputs[sock])
        else:
            links.new(tn.outputs["Color"],bs.inputs[sock])
        if key=="baseColor" and d.get("alphaFromMap"):
            links.new(tn.outputs["Alpha"],bs.inputs["Alpha"])
            mat.surface_render_method="DITHERED"
        if key=="baseColor" and d.get("emission"):links.new(tn.outputs["Color"],bs.inputs["Emission Color"])
    if d["alpha"]<1:
        mat.surface_render_method="BLENDED"
    return mat


for name,spec in metadata.items(): material(name,spec)
exec(compile((ROOT/"source"/"mesh_primitives.py").read_text(),str(ROOT/"source"/"mesh_primitives.py"),"exec"))
exec(compile((ROOT/"source"/"fabric_profile.py").read_text(),str(ROOT/"source"/"fabric_profile.py"),"exec"))
exec(compile((ROOT/"source"/"flightdeck_controls.py").read_text(),str(ROOT/"source"/"flightdeck_controls.py"),"exec"))


def vent(c,n,w,h,slats=7):
    c=v(c);r,u,n=basis(n)
    plate(c,n,w,h,.022,"Black_Rubber",.008)
    rim(c+n*.018,n,w,h,.025,w-.036,h-.036,.018,.012,"Aluminum")
    for i in range(slats):
        offset=(i-(slats-1)/2)*(h-.05)/slats
        plate(c+n*.016+u*offset,n,w-.057,.012,.017,"Graphite_Alloy",.003)
    for a in (-1,1):
        screw(c+n*.023+r*a*(w/2-.024),n,.009)
def handle(c,n,w,drop=.065,vertical=False,grip="Black_Rubber",radius=.018):
    c=v(c);r,u,n=basis(n);a=u if vertical else r
    for sign in (-1,1):
        p=c+a*w*.5*sign
        rod(p-n*.008,p+n*.014,.044,"Graphite_Alloy",12)
        rod(p+n*.013,p+n*(drop-.014),radius*1.2,"Aluminum",12)
    left=c-a*w*.5+n*drop;right=c+a*w*.5+n*drop
    rod(left,right,radius,"Aluminum",12)
    rod(left+a*.04,right-a*.04,radius*1.24,grip,16)
def fixture(c,n,w,mat="Opal_Emitter"):
    c=v(c);r,u,n=basis(n)
    plate(c,n,w+.12,.112,.049,"Carbon_Ceramic",.023)
    plate(c+n*.024,n,w+.02,.075,.016,"Titanium",.009)
    plate(c+n*.033,n,w-.013,.052,.012,"Black_Rubber",.005)
    plate(c+n*.039,n,w-.022,.037,.004,mat,.0015)
    for k in range(8):
        pp=c+n*.042+r*((k-3.5)*w/9)
        plate(pp,n,.0018,.036,.001,"Ceramic_Pearl")
    for a in (-1,1):
        screw(c+n*.026+r*a*(w/2+.039),n,.009)
def window_assembly(c,n,w,h,target="Clear_Glass",hero=False):
    c=v(c);r,u,n=basis(n)
    def ring(pad,inner,depth,m,ofs):
        rim(c,n,w+pad*2,h+pad*2,.19+pad,w+inner*2,h+inner*2,.19+inner,depth,m,offset=ofs)
    ring(.143,.101,.065,"Black_Rubber",.044)
    ring(.128,.063,.071,"Ceramic_Pearl",.069)
    ring(.085,.023,.061,"Aluminum",.08)
    ring(.045,-.007,.057,"Black_Rubber",.079)
    ring(.007,-.005,.016,"Titanium",.049)
    flat_round(c+n*.044,n,w,h,.188,target)
    for s in (-1,1):
        for j in range(11 if hero else 7):
            t=j/(10 if hero else 6)
            pos=c+r*((t-.5)*(w-.24))+u*s*(h/2+.093)+n*.084
            screw(pos,n,.015 if hero else .012)
        for j in (-1,0,1):
            screw(c+r*s*(w/2+.092)+u*j*(h/2-.2)+n*.084,n,.014)
def wall(room,side,w,h,y,zd):
    cz=midpoints[room];n=X*-side;c=v((side*2.20,y,zd));inset=zd-cz
    # Pressure-liner sheet surrounding the real aperture. The offsets are in the wall's local frame.
    if w:
        r,u,n=basis(n)
        cut=v((side*2.20,1.32,cz))
        delta=(c-cut); offset=(delta.dot(r),delta.dot(u))
        rim(cut,n,3.80,2.69,.012,w+.197,h+.197,.278,.095,"Ceramic_Pearl",
            inner_mat="Graphite_Alloy",center_offset=offset)
        window_assembly(c,n,w,h)
    else:
        cube((side*2.24,1.32,cz),(.105,2.69,3.8),"Ceramic_Pearl",.014)
    for j in range(3):
        z=cz+(j-1)*1.235
        cube((side*2.158,.428,z),(.046,.785,1.198),"Composite_Slate" if room!="service" else "Carbon_Ceramic",.021)
        for dz in (-.512,.512):
            for yb in (.13,.703):screw((side*2.13,yb,z+dz),n,.011,False)
        cube((side*2.125,.804,z),(.066,.043,1.205),"Aluminum",.005)
    cube((side*2.12,.087,cz),(.138,.16,3.79),"Carbon_Ceramic",.012)
    for ybadge in (2.24,2.47):
        for z in (cz-1.60,cz+1.58):screw((side*2.14,ybadge,z),n,.012)
def partition(room,z,style):
    # Solid sill and transom remain attached to the pressure shell when the door moves.
    for side in (-1,1):
        cube((side*1.484,1.32,z),(1.49,2.64,.114),"Ceramic_Pearl",.034)
        for f in (-1,1):
            n=Z*f;d=z+f*.069
            cube((side*1.51,.45,d),(1.32,.76,.038),"Composite_Slate",.023)
            cube((side*.785,1.13,d),(.07,2.23,.062),"Graphite_Alloy",.014)
            for ht in (.20,.76,1.36,2.04):screw((side*.803,ht,d+f*.033),n,.024,False)
            cube((side*.716,1.10,d),(.028,2.19,.054),"Aluminum",.009)
            cube((side*.690,1.09,d),(.020,2.18,.034),"Black_Rubber",.005)
        cube((side*.772,2.208,z),(.21,.17,.19),"Carbon_Ceramic",.043)
    cube((0,2.428,z),(1.60,.43,.135),"Ceramic_Pearl",.035)
    cube((0,2.212,z),(1.55,.062,.170),"Graphite_Alloy",.017)
    for side in (-1,1):
        label((0,2.419,z+side*.070),Z*side,.62,.127,style)
    cube((0,.017,z),(1.46,.034,.19),"Aluminum",.007)
    for i in range(15):cube((-.641+i*.091,.036,z),(.055,.002,.066),"Safety_Amber")
def nadir_port(cz):
    # Walk-on laminated optical port. The machined pressure flange carries the
    # load around the cutout in the keel, under two removable aisle panels.
    c=v((0,.012,cz))
    rim(c,Y,1.66,1.263,.014,1.185,1.12,.155,.036,"Floor_Rubber","Graphite_Alloy")
    rim(c-Y*.002,Y,1.23,1.166,.160,1.066,.996,.135,.077,"Titanium","Graphite_Alloy")
    rim(c-Y*.003,Y,1.087,1.017,.139,1.033,.963,.127,.038,"Black_Rubber")
    rim(c-Y*.066,Y,1.095,1.023,.143,.996,.927,.12,.090,"Graphite_Alloy","Carbon_Ceramic")
    rim(c-Y*.145,Y,1.057,.991,.138,.994,.922,.117,.022,"Titanium","Black_Rubber")
    for depth in (.009,.055,.136):
        flat_round(c-Y*depth,Y,1.044,.978,.131,"Clear_Glass")
    for sx in (-1,1):
        for z in (-.425,-.212,0,.212,.425):
            screw(c+X*sx*.575+Z*z,Y,.013)
        for x in (-.406,-.205,0,.205,.406):
            screw(c+X*x+Z*sx*.537,Y,.013)
        # Index marks on the flange and the insulated leak-test connector.
        for i in range(6):
            cube(c+X*(.649+.019*i)+Z*(sx*.499)+Y*.002,(.008,.002,.043),"Safety_Amber",.001)
    port=c+X*.738-Z*.392
    rim(port,Y,.082,.054,.010,.054,.029,.007,.007,"Titanium","Black_Rubber")
    flat_round(port-Y*.004,Y,.054,.029,.007,"Carbon_Ceramic")

def shell_body(room):
    cz=midpoints[room];active(room,"shell")
    if room=="observation":
        # Continuous keel skins either side of the optical pressure vessel.
        for side in (-1,1):
            cube((side*1.4,-.096,cz),(1.66,.164,3.81),"Carbon_Ceramic",.012)
            cube((0,-.096,cz+side*1.235),(1.144,.164,1.34),"Carbon_Ceramic",.012)
        nadir_port(cz)
    else:
        cube((0,-.096,cz),(4.46,.164,3.81),"Carbon_Ceramic",.025)
    for i in range(6):
        z=cz-1.578+i*.632
        for x,w in ((-1.49,1.24),(0,1.68),(1.49,1.24)):
            if room=="observation" and x==0 and i in (2,3):continue
            cube((x,-.008,z),(w,.048,.611),"Floor_Rubber" if x==0 else "Graphite_Alloy",.013)
            if x:
                for dz in (-.223,.223):
                    screw((x-.49,.019,z+dz),Y,.012,False);screw((x+.49,.019,z+dz),Y,.012,False)
        for s in (-1,1):
            cube((s*.862,.019,z),(.023,.012,.619),"Aluminum",.003)
            cube((s*.944,.022,z),(.018,.002,.45),"Safety_Amber")
    cube((0,2.69,cz),(4.51,.11,3.81),"Carbon_Ceramic",.01)
    for i in range(4):
        z=cz+(i-1.5)*.943
        for x in (-1.03,1.03):
            cube((x,2.625,z),(1.31,.07,.89),"Ceramic_Pearl",.027)
            cube((x,2.585,z),(.91,.012,.62),"Composite_Slate" if room=="service" else "Ceramic_Pearl",.012)
            for dx in (-.53,.53):screw((x+dx,2.582,z),-Y,.014,False)
        cube((0,2.616,z),(.46,.047,.89),"Carbon_Ceramic",.018)
        if i in (1,3):vent((0,2.58,z),-Y,.34,.49,10)
        else:
            for k in (-1,1):cube((k*.091,2.587,z),(.008,.021,.68),"Aluminum",.002)
    for s in (-1,1):
        cube((s*1.90,2.49,cz),(.58,.14,3.78),"Composite_Slate",.025,rot(Z,-s*.58))
        cube((s*2.145,2.259,cz),(.135,.21,3.8),"Carbon_Ceramic",.015)
        for j in range(3):
            x=s*(1.64+j*.037); yy=2.49-j*.023
            rod((x,yy,cz-1.88),(x,yy,cz+1.88),.015 if j else .024,"Graphite_Alloy" if j else "Aluminum",10)
        for off in (-1.5,-.72,.1,.94,1.64):
            cube((s*1.69,2.478,cz+off),(.16,.078,.035),"Carbon_Ceramic",.008)
        for j in (-1,1):
            cube((s*2.105,1.30,cz+j*1.815),(.15,2.56,.098),"Ceramic_Pearl",.028)
            for hh in (.24,.84,1.90,2.28):
                screw((s*2.023,hh,cz+j*1.815),X*-s,.017)
        # Empty braided harnesses and opening chrome trim trace the cabin's upper corners.
        if room!="service":
            for off in (-.93,.93):
                if room=="observation" and s==-1 and off==-.93:continue
                fixture((s*1.96,2.30,cz+off),(-s*.8,-.6,0),.56)
    if room=="observation":
        wall(room,-1,2.42,.8,1.76,-3.8);wall(room,1,2.54,1.,1.76,-3.8)
        rim((0,1.32,-5.73),Z,4.45,2.69,.018,3.74,1.72,.291,.12,"Ceramic_Pearl",center_offset=(0,.27))
        for s in (-1,1):
            cube((s*2.087,1.38,-5.61),(.113,2.44,.099),"Carbon_Ceramic",.035)
            for hh in (.59,1.12,1.86,2.12):screw((s*2.085,hh,-5.551),Z,.022)
        for x in (-1.45,-.49,.49,1.45):
            cube((x,.40,-5.607),(.925,.60,.074),"Composite_Slate",.025)
            vent((x,.40,-5.557),Z,.68,.20)
        cube((0,.756,-5.516),(4.08,.117,.34),"Carbon_Ceramic",.036)
        cube((0,.804,-5.497),(3.96,.026,.333),"Aluminum",.012)
        label((-1.32,.405,-5.506),Z,.31,.063,"assettag")
        partition(room,-1.9,"sleeper")
        label((-1.28,1.82,-1.967),-Z,.58,.119,"saloon")
        label((1.48,1.55,-1.967),-Z,.51,.106,"civil")
    elif room=="berth":
        wall(room,-1,0,0,0,cz);wall(room,1,1.66,.63,1.85,.03)
    else:
        wall(room,-1,.98,.64,1.68,3.68);wall(room,1,0,0,0,cz)
        partition(room,1.90,"service")
        cube((0,1.32,5.73),(4.45,2.67,.11),"Ceramic_Pearl",.027)
        rim((.0,1.27,5.632),-Z,2.11,2.39,.44,1.80,2.11,.35,.055,"Carbon_Ceramic","Black_Rubber")
        rim((.0,1.27,5.602),-Z,1.94,2.25,.39,1.77,2.08,.34,.055,"Aluminum")
        flat_round((0,1.27,5.65),-Z,1.8,2.1,.34,"Composite_Slate")
        label((0,1.97,5.639),-Z,.58,.115,"wheel")
        for sx in (-1,1):
            for ht in (.46,.89,1.35,1.83):
                screw((sx*.965,ht,5.57),-Z,.03,False)
            for h in (.28,.61,1.07,1.69,2.10):
                rod((sx*1.58,h,5.55),(sx*1.58,h,5.47),.06,"Titanium",12)
            for xx,m,r in ((1.34,"Aluminum",.051),(1.51,"Graphite_Alloy",.074),(1.72,"Safety_Amber",.036)):
                rod((sx*xx,.16,5.51),(sx*xx,2.35,5.51),r,m,16)
                for ht in (.38,1.12,1.91):
                    rod((sx*xx,ht-.025,5.51),(sx*xx,ht+.025,5.51),r*1.3,"Carbon_Ceramic",12)
        label((1.56,2.36,5.61),-Z,.61,.124,"tether")


for room in rooms:shell_body(room)


def casing_x(cx,width,profile,mat):
    sides=[[v((cx+s*width/2,y,z)) for y,z in profile] for s in (-1,1)]
    center=sum(sides[0]+sides[1],v((0,0,0)))/(2*len(profile))
    for s,pts in zip((-1,1),sides):face(pts,mat,X*s)
    for i in range(len(profile)):
        j=(i+1)%len(profile);q=[sides[0][i],sides[0][j],sides[1][j],sides[1][i]]
        face(q,mat,sum(q,v((0,0,0)))/4-center)
def upholstered(c,dim,mat,rotation=None,ex=.37):
    c=v(c);hs=v(dim)*.5
    orient=(lambda a:rotation@a) if rotation else (lambda a:a)
    rows=[];ns=[]
    signed=lambda x,e:math.copysign(abs(x)**e,x)
    for i in range(13):
        co=math.cos(-math.pi/2+math.pi*i/12);si=math.sin(-math.pi/2+math.pi*i/12)
        row=[];nr=[]
        for j in range(32):
            a=T*j/32; q=v((signed(co*math.cos(a),ex),signed(si,ex),signed(co*math.sin(a),ex)))
            nl=v([signed(q[k],2/ex-1)/hs[k] for k in range(3)]).normalized()
            row.append(c+orient(v([q[k]*hs[k] for k in range(3)])));nr.append(orient(nl))
        rows.append(row);ns.append(nr)
    for i in range(12):
        for j in range(32):
            k=(j+1)%32
            inds=[(i,j),(i,k),(i+1,k),(i+1,j)]
            if i==0:inds.pop(1)
            elif i==11:inds.pop(2)
            vv=[rows[a][b] for a,b in inds];nn=[ns[a][b] for a,b in inds];face(vv,mat,sum(nn,v((0,0,0))),normals=nn)
def push(c,n,kind="Mint_Emitter",w=.035,h=.024):
    c=v(c);r,u,n=basis(n)
    plate(c,n,w+.013,h+.013,.015,"Black_Rubber",.004)
    plate(c+n*.009,n,w,h,.012,kind,.003)
def observation_props():
    room="observation"
    active(room,"window",(0,1.59,-5.706),(0,1.60,-5.66))
    window_assembly((0,1.59,-5.706),Z,3.52,1.5,P("window"),True)
    shell(room)
    label((1.56,2.415,-5.644),Z,.32,.065,"window")
    # Roller barrel remains attached to the roof; only the fabric travels with the web interaction.
    rod((-1.82,2.39,-5.47),(1.82,2.39,-5.47),.061,"Aluminum",24)
    for ss in (-1,1):
        cube((ss*1.81,2.39,-5.49),(.085,.19,.175),"Carbon_Ceramic",.017)
        screw((ss*1.81,2.42,-5.393),Z,.014)
    active(room,"roller_shade",(0,2.36,-5.43),(1.35,2.28,-5.43),add_anim("scale","y",13.1))
    cube((0,2.305,-5.43),(3.49,.111,.013),P("roller_shade"),.003)
    cube((0,2.252,-5.421),(3.49,.011,.015),"Aluminum",.002)
    active(room,"pilot_console",(.78,.72,-5.0),(.77,.90,-4.97))
    active(room,"nav_screen",(.71,1.15,-5.186),(.68,1.235,-5.005))
    shell(room)
    # Cast quadrant stays bolted to the console as the lever's arm rotates.
    cube((1.488,.996,-5.11),(.18,.19,.27),"Safety_Amber",.045)
    rod((1.368,1.048,-5.09),(1.58,1.048,-5.09),.083,"Graphite_Alloy",24)
    active(room,"ascent_lever",(1.461,1.048,-5.09),(1.46,1.17,-5.00),add_anim("rotate","x",-27.0))
    a=v((1.461,1.047,-5.09));b=a+v((0,.174,.073))
    rod(a,b,.021,P("ascent_lever"),14)
    rod(b-X*.069,b+X*.069,.031,"Black_Rubber",18)
    for t in (-.074,.074):rod(b+X*(t-.005),b+X*(t+.005),.032,"Aluminum",12)
    active(room,"lounge_seat",(-1.70,.63,-3.70),(-1.57,.80,-3.62))
    active(room,"lamp",(-1.928,2.31,-4.73),(-1.90,2.31,-4.68))
    fixture((-1.96,2.30,-4.73),(.8,-.6,0),.58,P("lamp"))
    shell(room)
    # Instrument shelf uses a raised anti-slip rim, a rubber pad and two underslung gussets.
    cube((-1.177,.919,-5.20),(1.28,.065,.58),"Ceramic_Pearl",.022)
    cube((-1.177,.957,-5.18),(1.17,.018,.467),"Black_Rubber",.009)
    for xxv in (-1.61,-.76):
        tube([(xxv,.938,-4.98),(xxv,.87,-5.01),(xxv,.669,-5.37),(xxv,.669,-5.52)],.018,"Graphite_Alloy",8)
    active(room,"field_glasses",(-1.17,1.03,-5.13),(-1.17,1.045,-5.13))


observation_props()


def belt(path,width,mat="Harness_Grip",widthdir=Z):
    path=[v(p) for p in path];guide=v(widthdir).normalized()
    for a,b in zip(path[:-1],path[1:]):
        t=(b-a).normalized();perp=(guide-t*guide.dot(t)).normalized()*width/2
        normal=t.cross(perp).normalized()
        face([a-perp,a+perp,b+perp,b-perp],mat,normal)
        for s in (-1,1):
            p1=a+perp*s*.86;p2=b+perp*s*.86
            tube([p1,p2],.00115,"Technical_Twill",4)


def aerospace_fitout():
    room="observation"
    shell(room)
    # Laminated spar caps narrow toward the glazing sill, giving the nose an engineered pressure frame.
    for s in (-1,1):
        for z in (-5.48,-2.09):
            tube([(s*2.066,.104,z),(s*2.059,1.34,z),(s*1.988,2.045,z),
                  (s*1.773,2.371,z),(s*1.398,2.552,z)],.054,"Graphite_Alloy",8)
            tube([(s*2.007,.153,z+.006),(s*2.002,1.35,z+.006),(s*1.937,2.03,z+.006),
                  (s*1.73,2.33,z+.006),(s*1.39,2.51,z+.006)],.018,"Titanium",8)
        for yyv in (.871,2.301):
            pp=v((s*1.91,yyv,-5.55));rod(pp-Z*.032,pp+Z*.018,.047,"Graphite_Alloy",8)
            screw(pp+Z*.020,Z,.024,False)
    for i in range(3):
        ang=-.30+i*.29;pp=v((1.588,1.05+math.cos(ang)*.085,-5.093+math.sin(ang)*.09))
        cube(pp,(.008,.018,.012),"Ceramic_Pearl",.002)
    # Locking socket and elastic tether keep the optics on the shelf during maneuvers.
    for xxv in (-1.243,-1.097):
        cube((xxv,.979,-5.154),(.021,.024,.165),"Graphite_Alloy",.005)
    cube((-1.171,.975,-5.238),(.16,.025,.018),"Signal_Orange",.004)
    label((-.76,.967,-5.19),Y,.27,.056,"optic")
    # Layered curved gasket gives the forward pressure laminate a very thin second reflection.
    rim((0,1.59,-5.693),Z,3.537,1.519,.191,3.51,1.486,.18,.007,"Graphite_Alloy")


def berth_props():
    room="berth";shell(room)
    # A recessed sleep cell, including a pressure liner and a triangulated launch restraint frame.
    cube((-1.87,.38,.0),(.48,.74,2.48),"Carbon_Ceramic",.052)
    for zz in (-.85,.0,.85):
        cube((-1.579,.402,zz),(.575,.60,.803),"Composite_Slate",.033)
        plate((-1.280,.46,zz),X,.63,.064,.027,"Graphite_Alloy",.012)
        for ds in (-.32,.32):screw((-1.262,.37,zz+ds),X,.011)
    for zz in (-1.24,1.24):
        cube((-1.73,1.24,zz),(.88,1.95,.081),"Ceramic_Pearl",.045)
        tube([(-2.04,.173,zz),(-1.305,.45,zz),(-1.276,1.85,zz),(-1.53,2.15,zz),(-2.07,2.22,zz)],.027,"Titanium",10)
    cube((-1.77,2.225,.0),(.86,.105,2.52),"Carbon_Ceramic",.042)
    cube((-1.78,2.163,.0),(.76,.037,2.30),"Composite_Slate",.018)
    rod((-1.229,2.152,-1.225),(-1.229,2.152,1.225),.023,"Titanium",16)
    label((-1.251,1.9,1.24),X,.20,.042,"berthsign")
    active(room,"bunk",(-1.66,.82,.0),(-1.61,.87,.09))
    cube((-1.679,.726,0),(.915,.154,2.425),"Ceramic_Pearl",.047)
    cube((-1.673,.795,.0),(.865,.059,2.275),"Black_Rubber",.022)
    upholstered((-1.687,.858,.0),(.85,.148,2.23),P("bunk"),ex=.39)
    upholstered((-1.69,.974,-.862),(.66,.158,.397),"Pressure_Fabric",rot(Y,-.07),.53)
    # Recessed pins locate both ends of the restraint webbing below the pad.
    for zz in (-.461,.533):
        for xx in (-2.104,-1.259):
            cube((xx,.828,zz),(.023,.055,.084),"Anodized_Frame",.006)
            rod((xx,.841,zz-.033),(xx,.841,zz+.033),.0045,"Titanium",12)
    # Bolted fixed rail stop retains an ordinary prop mesh and hit target while
    # the full textile, each carrier and the leading handle move independently.
    active(room,"privacy_curtain",(-1.228,2.155,-1.207),(-1.225,1.57,-1.034))
    cube((-1.229,2.151,-1.221),(.065,.067,.018),"Anodized_Frame",.005)
    screw((-1.192,2.151,-1.222),X,.007,False)
    # Right-hand fold-down utility counter wraps around the accessible pass drawer.
    shell(room)
    for zz in (-1.10,.486):
        cube((1.835,.449,zz),(.675,.846,.685),"Composite_Slate",.028)
        plate((1.488,.422,zz),-X,.594,.70,.026,"Ceramic_Pearl",.017)
        handle((1.466,.61,zz),-X,.200,.038,False)
        for ds in (-.25,.25):
            for h in (.149,.715):screw((1.471,h,zz+ds),-X,.009)
    cube((1.883,.389,-.31),(.482,.740,.86),"Carbon_Ceramic",.022)
    cube((1.773,.888,-.307),(.862,.087,2.38),"Ceramic_Pearl",.025)
    cube((1.763,.937,-.307),(.827,.017,2.348),"Graphite_Alloy",.009)
    cube((1.344,.941,-.307),(.028,.052,2.37),"Titanium",.009)
    for zz in (-1.477,.861):
        cube((1.765,.943,zz),(.844,.035,.018),"Titanium",.006)
    for off in (-.672,.047):
        cube((1.72,.687,off),(.67,.019,.032),"Titanium",.004)
    active(room,"locker_drawer",(1.397,.657,-.31),(1.364,.708,-.31),add_anim("translate","x",-.42))
    cube((1.684,.675,-.31),(.566,.033,.64),"Graphite_Alloy",.009)
    cube((1.688,.694,-.31),(.506,.009,.593),"Black_Rubber",.003)
    for zz in (-.63,.012):
        cube((1.681,.724,zz),(.598,.10,.027),"Titanium",.005)
    cube((1.979,.731,-.31),(.025,.112,.649),"Composite_Slate",.008)
    cube((1.39,.676,-.31),(.059,.28,.741),P("locker_drawer"),.016)
    handle((1.350,.705,-.32),-X,.245,.055,False)
    label((1.357,.593,-.312),-X,.365,.066,"drawer")
    for zz in (-.626,.006):screw((1.357,.773,zz),-X,.010)
    active(room,"access_card",(1.67,.713,-.31),(1.67,.717,-.31),parent="locker_drawer")
    shell(room)
    plate((-2.147,1.48,-.91),X,.23,.203,.061,"Graphite_Alloy",.024)
    a=v((-2.106,1.483,-.92));b=v((-1.988,1.562,-.858));c=v((-1.916,1.567,-.761))
    tube([a,b,c],.017,"Titanium",12)
    for pnt in (a,b):rod(pnt-Z*.034,pnt+Z*.034,.033,"Carbon_Ceramic",16)
    pp=c+Z*.081;plate(pp,-Y,.120,.228,.044,P("reading_lamp"),.018)
    plate(pp-Y*.024,-Y,.082,.181,.01,"Berth_Diffuser",.004)
    p=v((-2.106,1.438,-.846));plate(p,X,.044,.054,.011,"Black_Rubber",.005)
    telltale(p+Y*.037+X*.006,X,"reading_lamp",(244,172,94),.025,.004)
    berth_panel=v((-2.129,1.48,-.441))
    plate(berth_panel,X,.274,.130,.052,"Graphite_Alloy",.011)
    live_panel("Berth",berth_panel+X*.027,X,.244,.099)
    moving_control(room,"reading_lamp",p+X*.007,p+X*.016,"rotate",Z,-21)
    plate(p+X*.012,X+Y*.18,.037,.043,.012,"Carbon_Ceramic",.004)
    plate(p+X*.020-Y*.010,X,.022,.003,.002,"Ceramic_Pearl",.001)
    active(room,"logbook",(1.71,.970,.19),(1.71,.985,.19))
    active(room,"mug",(1.80,.998,-.934),(1.80,1.058,-.934))
    shell(room)
    torus((1.80,.951,-.934),Y,.053,.008,"Carbon_Ceramic",28,7)
    active(room,"grab_handle",(-1.30,1.31,.97),(-1.242,1.33,.99))
    handle((-1.293,1.31,1.241),X,.390,.080,True,P("grab_handle"),.019)
    shell(room)
    label((2.164,1.255,-1.146),-X,.372,.077,"water")


aerospace_fitout()
berth_props()


def service_props():
    room="service";shell(room)
    # Anti-crush jamb seal, carriage runner and keeper are fixed to the bulkhead.
    for z in (1.807,1.990):
        cube((.26,2.194,z),(2.05,.052,.048),"Titanium",.011)
    for s in (-1,1):
        for ht in (.25,.84,1.74):
            cube((s*.714,ht,1.900),(.053,.098,.152),"Graphite_Alloy",.010)
    active(room,"pressure_hatch",(0,1.09,1.90),(0,1.32,1.827),add_anim("translate","x",1.51))
    cube((0,1.109,1.90),(1.397,2.176,.117),"Carbon_Ceramic",.045)
    for s in (-1,1):
        n=Z*s;z=1.900+s*.060
        plate((0,1.102,z),n,1.327,2.079,.038,P("pressure_hatch"),.033)
        for xxv in (-.595,.595):
            plate((xxv,1.08,z+s*.024),n,.033,1.737,.018,"Titanium",.008)
        pp=v((0,1.641,z+s*.027))
        rim(pp,n,.463,.174,.052,.396,.116,.041,.007,"Graphite_Alloy")
        flat_round(pp+n*.002,n,.4,.12,.042,"Smoked_Display")
        label((0,1.353,z+s*.021),n,.497,.104,"airlock")
        for k in range(6):
            d=(k-2.5)*.158
            plate((d,.315,z+s*.022),n,.105,.031,.003,"Signal_Orange",.001)
        handle((-.418,1.06,z+s*.024),n,.24,.045,True,"Black_Rubber",.016)
        for xxv in (-.534,.534):
            for ht in (.23,1.89):screw((xxv,ht,z+s*.024),n,.015,False)
    active(room,"card_reader",(1.02,1.32,1.783),(1.02,1.34,1.777))
    cube((1.02,1.355,1.789),(.239,.335,.074),P("card_reader"),.023)
    plate((1.02,1.390,1.747),-Z,.191,.173,.012,"Smoked_Display",.005)
    live_panel("Access",(1.02,1.422,1.739),-Z,.166,.075)
    pp=v((1.02,1.329,1.739));torus(pp,-Z,.028,.0025,"Mint_Emitter",24,6)
    cube((1.02,1.254,1.746),(.161,.019,.026),"Titanium",.007)
    cube((1.02,1.255,1.731),(.132,.008,.005),"Black_Rubber",.002)
    for sx in (-1,1):screw((1.02+sx*.091,1.489,1.747),-Z,.008)
    shell(room)
    # The wiring stays bolted to its backplane while the cabinet door opens inboard.
    base=v((2.120,1.492,3.54));right,up,normal=basis(-X)
    plate(base,-X,1.40,1.14,.075,"Carbon_Ceramic",.037)
    plate(base-X*.042,-X,1.325,1.065,.022,"Composite_Slate",.019)
    for height in (.952,2.035):cube((1.931,height,3.54),(.411,.043,1.40),"Titanium",.009)
    for zz in (2.852,4.227):cube((1.930,1.491,zz),(.411,1.125,.044),"Titanium",.01)
    for j in range(5):
        zz=3.029+j*.25
        cube((1.991,1.872,zz),(.083,.126,.187),"Graphite_Alloy",.009)
        label((1.946,1.893,zz),-X,.155,.035,("cablea","cableb","cablec","cabled","cableb")[j])
        for off in (-.064,.064):screw((1.946,1.844,zz+off),-X,.008)
        for off in (-.052,.0,.052):
            rod((1.992,1.811,zz+off),(1.992,1.776,zz+off),.019,"Titanium",10)
    cable_mats=["Cable_Orange","Carbon_Ceramic","Cable_Orange","Cable_Blue","Cable_Cyan",
                "Black_Rubber","Cable_Orange","Black_Rubber","Cable_Cyan","Cable_Blue","Technical_Twill",
                "Cable_Cyan","Cable_Blue","Black_Rubber","Cable_Cyan"]
    for j in range(15):
        zz=3.029+(j//3)*.25+(j%3-1)*.052
        rr=.011 if j%3!=1 else .008
        # Distinct grommet branches respect bend radii, then run in segregated channels.
        x1=1.986-(j%3)*.014;endz=2.958+(j%5)*.063+(j//5-1)*.015
        yy=1.448+(j//3)*.054+(j%3)*.014
        dst=1.081+(j%5)*.039+(j//5-1)*.012
        path=[(1.992,1.785,zz),(x1,1.718,zz),(x1,yy+.043,zz),
              (x1-.015,yy+.014,zz-.014),(x1-.020,yy,zz-.046),
              (x1-.020,yy,endz+.045),(x1-.016,yy-.013,endz+.015),
              (x1-.011,yy-.047,endz),(x1-.011,dst+.045,endz),(x1-.001,dst+.019,endz),(2.014,dst,endz)]
        # Some branches near their destination can fold back without introducing duplicate points.
        if j in (6,11):
            # Replace exactly one original fixed span with a real service loop.
            # Its two short approach collars remain rigid on the harness rack.
            a=v(path[4])+v((-.042,0,0));b=v(path[5])+v((-.042,0,0))
            tube(path[:5]+[a],rr,cable_mats[j],9);tube([b]+path[5:],rr,cable_mats[j],9)
            key="loom_service_power" if j==6 else "loom_service_fiber"
            service_junctions[key]={"a":a,"b":b,"radius":rr if j==6 else .007,
                "material":"Cable_Orange" if j==6 else "Cable_Cyan","sag":.128 if j==6 else .142,
                "out":.063 if j==6 else .048,"max":.040 if j==6 else .062}
        else:tube(path,rr,cable_mats[j],8)
        rod((x1,1.762,zz),(x1,1.738,zz),rr*1.45,"Black_Rubber",8)
        rod((x1,1.738,zz),(x1,1.729,zz),rr*1.35,"Ceramic_Pearl" if j%2 else "Safety_Amber",8)
        rod((x1-.010,dst+.071,endz),(x1-.010,dst+.051,endz),rr*1.34,"Titanium",8)
        rod((2.043,dst,endz),(2.003,dst,endz),rr*1.72,"Titanium",8)
        rod((2.004,dst,endz),(1.988,dst+.008,endz),rr*1.42,"Black_Rubber",9)
    plate((2.069,1.168,3.086),-X,.398,.287,.060,"Graphite_Alloy",.015)
    label((2.037,1.065,3.199),-X,.113,.027,"cablea")
    for k,zz in enumerate((3.367,3.70,3.958)):
        cube((2.012,1.567,zz),(.061,.31,.043),"Graphite_Alloy",.007)
        for yy in (1.477,1.55,1.627,1.702):
            cube((1.934,yy,zz),(.015,.043,.027),"Technical_Twill",.004)
        cube((1.935,1.381,zz),(.019,.039,.096),"Cable_Orange" if k==0 else "Cable_Cyan",.004)
    for k in range(4):
        zz=3.355+k*.23
        cube((2.014,1.186,zz),(.067,.221,.194),"Black_Rubber",.009)
        for e in range(5):
            cube((1.974,1.21,zz+(e-2)*.027),(.012,.10,.009),"Aluminum",.002)
        probe_control(k,zz)
    panel=v((1.930,1.936,3.67))
    plate(panel,-X,.570,.087,.026,"Graphite_Alloy",.007)
    live_panel("Service",panel-X*.014,-X,.542,.067)
    for zz in (2.91,4.164):
        for ht in (1.020,1.965):screw((1.889,ht,zz),-X,.018,False)
    active(room,"service_cabinet",(1.755,1.487,2.877),(1.733,1.53,3.52),add_anim("rotate","y",-84.0))
    cube((1.758,1.49,3.552),(.054,1.076,1.350),P("service_cabinet"),.027)
    plate((1.725,1.503,3.555),-X,1.229,.941,.018,"Composite_Slate",.026)
    plate((1.711,1.513,3.557),-X,.995,.715,.011,"Carbon_Ceramic",.023)
    for j in range(9):
        zz=3.304+j*.059
        plate((1.701,1.514,zz),-X,.013,.402,.009,"Graphite_Alloy",.003)
    label((1.700,1.815,3.474),-X,.526,.109,"utility")
    label((1.70,1.241,3.727),-X,.251,.051,"cablea")
    handle((1.718,1.495,4.084),-X,.234,.061,True)
    for ht in (1.145,1.822):
        rod((1.755,ht-.075,2.877),(1.755,ht+.075,2.877),.030,"Titanium",14)
        for ds in (-.052,.052):rod((1.755,ht+ds-.010,2.877),(1.755,ht+ds+.010,2.877),.033,"Graphite_Alloy",14)
    shell(room)
    plate((2.142,1.39,4.74),-X,.338,.435,.073,"Graphite_Alloy",.02)
    plate((2.097,1.403,4.74),-X,.275,.352,.025,"Ceramic_Pearl",.015)
    board_legend((2.082,1.522,4.74),-X,.179,.035,"BAY LIGHT")
    plate((2.069,1.393,4.74),-X,.09,.14,.052,"Black_Rubber",.016)
    for zz in (4.680,4.800):
        tube([(2.079,1.34,zz),(2.025,1.35,zz),(2.012,1.365,zz),(2.012,1.423,zz),(2.029,1.439,zz),(2.079,1.450,zz)],.006,"Titanium",8)
    telltale((2.08,1.265,4.738),-X,"breaker",(246,176,93),.044,.013)
    moving_control(room,"breaker",(2.048,1.393,4.739),(2.002,1.397,4.739),"rotate",Z,26)
    cube((2.018,1.397,4.741),(.071,.070,.065),P("breaker"),.012,rot(Z,.23))
    for ht in (1.384,1.396,1.408):
        rod((1.983,ht,4.717),(1.983,ht,4.763),.0022,"Grip_Elastomer",8)
    active(room,"pressure_gauge",(-2.098,1.44,4.79),(-2.043,1.46,4.79))
    # A calibrated digital differential transducer is serviceable behind a captive ring.
    plate((-2.145,1.46,4.79),X,.331,.350,.054,"Graphite_Alloy",.018)
    rod((-2.13,1.461,4.79),(-2.058,1.461,4.79),.126,P("pressure_gauge"),32)
    rod((-2.059,1.461,4.79),(-2.043,1.461,4.79),.108,"Smoked_Display",32)
    live_panel("Pressure",(-2.041,1.46,4.79),X,.149,.109)
    torus((-2.046,1.461,4.79),X,.112,.006,"Titanium",32,7)
    shell(room)
    plate((-2.146,1.594,2.535),X,.244,.346,.080,P("intercom"),.023)
    plate((-2.103,1.604,2.535),X,.209,.281,.021,"Carbon_Ceramic",.012)
    for j in range(7):
        for k in range(4):
            q=v((-2.091,1.613+k*.015,2.535+(j-3)*.022));rod(q,q+X*.002,.0057,"Black_Rubber",6)
    live_panel("Intercom",(-2.089,1.699,2.535),X,.160,.046)
    pp=v((-2.083,1.536,2.535));torus(pp,X,.035,.004,"Titanium",24,6)
    telltale(pp+Z*.062,X,"intercom",(138,231,204),.025,.006)
    moving_control(room,"intercom",pp,pp+X*.009,"press",-X,.008)
    rod(pp-X*.005,pp+X*.011,.028,"Grip_Elastomer",28,r2=.025)
    for dz in (-.009,0,.009):
        rod(pp+X*.011+Z*dz-Y*.013,pp+X*.011+Z*dz+Y*.013,.0014,"Graphite_Alloy",6)
    shell(room)
    cube((-1.892,.817,3.70),(.50,.063,1.21),"Composite_Slate",.019)
    rim((-1.879,.852,3.70),Y,.45,1.155,.036,.415,1.118,.026,.016,"Titanium")
    active(room,"tool_roll",(-1.87,.893,3.70),(-1.87,.907,3.70))
    active(room,"docking_wheel",(0,1.27,5.43),(0,1.27,5.426),add_anim("rotate","z",88.0))
    cc=v((0,1.27,5.43));n=-Z
    rod(cc+Z*.157,cc+Z*.023,.076,"Graphite_Alloy",24)
    torus(cc,n,.275,.029,P("docking_wheel"),48,11)
    for k in range(3):
        t=math.pi/2+T*k/3;direction=X*math.cos(t)+Y*math.sin(t)
        rod(cc+direction*.051+Z*.049,cc+direction*.247,.024,"Titanium",12,r2=.017)
    rod(cc+Z*.055,cc-Z*.014,.065,"Carbon_Ceramic",20)
    rod(cc-Z*.014,cc-Z*.023,.047,"Signal_Orange",20)
    for k in range(6):
        a=T*k/6; pnt=cc+X*math.cos(a)*.275+Y*math.sin(a)*.275-Z*.023
        rod(pnt,pnt-Z*.004,.008,"Ceramic_Pearl",8)


service_props()


def inset(c,n,w,h,outer="Graphite_Alloy",inside="Ceramic_Pearl",rr=.047,fas=.012):
    c=v(c);r,u,n=basis(n)
    rim(c,n,w,h,rr,w-2*fas,h-2*fas,max(.012,rr-fas),.012,outer)
    flat_round(c-n*.003,n,w-fas*2+.002,h-fas*2+.002,max(.01,rr-fas),inside)
    for a in (-1,1):
        for b in (-1,1):
            screw(c+r*a*(w*.5-.048)+u*b*(h*.5-.038),n,.008)
def aero_detail():
    global current
    for room in rooms:
        shell(room);cz=midpoints[room]
        for s in (-1,1):
            for j in (-1,0,1):
                z=cz+j*1.21
                plate((s*2.044,.148,z),X*-s,.99,.052,.019,"Black_Rubber",.005)
                plate((s*2.031,.148,z),X*-s,.83,.014,.004,"Opal_Emitter",.001)
            # Ceiling connection points have articulated clevises rather than flat panel-to-panel junctions.
            for z in (cz-1.37,cz+.47):
                pp=v((s*1.67,2.48,z))
                cube(pp,(.142,.091,.115),"Graphite_Alloy",.014,rot(Z,s*.22))
                rod(pp-Z*.067,pp+Z*.074,.036,"Titanium",12)
                screw(pp+Z*.077,Z,.018,False)
        for j in (-1,0,1):
            z=cz+j*1.239
            for x in (-.69,.69):
                inset((x,.0197,z),Y,.178,.108,"Carbon_Ceramic","Graphite_Alloy",.018,.008)
                cube((x,.022,z),(.094,.005,.009),"Black_Rubber",.002)
        for s in (-1,1):
            for j in range(3):
                pos=(s*1.161,2.571,cz+(j-1)*1.21)
                inset(pos,-Y,.96,.533,"Graphite_Alloy","Ceramic_Pearl",.052,.007)
    shell("observation")
    # A load-bearing inclined mullion separates the outboard fixed laminate from the forward view.
    # The metal edge and dark recessed web catch different lengths of specular glint.
    for off,rr,m,zt in ((0,.031,"Graphite_Alloy",-5.55),(-.033,.012,"Titanium",-5.554),(.031,.011,"Carbon_Ceramic",-5.55)):
        tube([(-1.112+off,.79,zt),(-1.095+off,.952,zt),(-.767+off,2.171,zt),(-.700+off,2.392,zt)],rr,m,8)
    for yv in (.912,1.323,1.919,2.261):
        xxv=-1.112+(yv-.79)*.254
        screw((xxv,yv,-5.515),Z,.010,False)
    for ss in (-1,1):
        # Pressure liner across the transom and sill ends in gasketed shear panels.
        inset((ss*1.44,.42,-5.556),Z,.79,.43,"Graphite_Alloy","Composite_Slate",.049,.010)
        plate((ss*1.489,.705,-5.443),Z,.48,.063,.012,"Carbon_Ceramic",.005)
        plate((ss*1.489,.703,-5.433),Z,.34,.011,.005,"Blue_Emitter",.001)
        for ht in (.989,2.189):
            plate((ss*1.941,ht,-5.552),Z,.096,.179,.035,"Titanium",.012)
            for h in (-.053,.053):screw((ss*1.941,ht+h,-5.529),Z,.014,False)
    shell("berth")
    for s in (-1,1):
        for z,n in ((1.820,-Z),(-1.822,Z)):
            inset((s*1.52,1.59,z),n,.93,1.16,"Graphite_Alloy","Ceramic_Pearl",.095,.008)
            inset((s*1.53,.495,z),n,.92,.51,"Graphite_Alloy","Composite_Slate",.058,.008)
    # Diamond-seamed, lightly creased restraint quilt, conforming to the existing padded sleep cell.
    current=groups[("berth","bunk")]
    quilt=quilt_height
    for zz in (-.461,.533):
        path=[(-2.104,.841,zz),(-2.105,.888,zz),(-2.099,.925,zz),(-2.091,.944,zz)]
        for k in range(29):
            x=QUILT_X[0]+(QUILT_X[1]-QUILT_X[0])*k/28
            path.append((x,quilt(x,zz)+.0055,zz))
        path.extend([(-1.274,.946,zz),(-1.266,.929,zz),(-1.258,.888,zz),(-1.259,.841,zz)])
        belt(list(reversed(path)),.053,"Aramid_Webbing",widthdir=Z)
        cube((-1.473,quilt(-1.473,zz)+.025,zz),(.075,.02,.069),"Titanium",.005)
        cube((-1.468,quilt(-1.473,zz)+.039,zz),(.018,.006,.054),"Signal_Orange",.002)
    shell("berth")
    # Quilted acoustic / thermal head wall with positive restraint eyelets.
    for i in range(5):
        for j in range(2):
            zz=-.965+i*.48
            upholstered((-2.134,1.275+j*.374,zz),(.118,.353,.465),"Pressure_Fabric",ex=.37)
    for zz in (-1.015,1.015):
        inset((-1.581,2.103,zz),-Y,.43,.19,"Graphite_Alloy","Ceramic_Pearl",.036,.012)
    shell("service")
    # Circular docking collar, sixteen captive locks, indexing marks and three clamp actuators.
    cc=v((0,1.269,5.592));nn=-Z
    for radius,rad,mat,depth in ((.816,.066,"Graphite_Alloy",0),(.786,.032,"Titanium",.018),
                                 (.746,.027,"Black_Rubber",.026),(.712,.015,"Aluminum",.028)):
        torus(cc+nn*depth,nn,radius,rad,mat,80,9)
    for j in range(16):
        t=T*j/16;d=X*math.cos(t)+Y*math.sin(t)
        pnt=cc+d*.817+nn*.063
        rod(pnt,pnt+nn*.009,.025,"Titanium",9)
        screw(pnt+nn*.010,nn,.013,False)
        if j%2==0:
            to=cc+d*.58+nn*.022;end=cc+d*.728+nn*.022
            tube([to,end],.008,"Graphite_Alloy",6)
    for j in range(3):
        t=T*j/3+math.pi/2;d=X*math.cos(t)+Y*math.sin(t);tan=X*-math.sin(t)+Y*math.cos(t)
        p=cc+d*.87+nn*.04
        rod(p-tan*.108,p+tan*.108,.038,"Composite_Slate",12)
        for side in (-1,1):
            rod(p+tan*side*.107,p+tan*side*.138,.025,"Titanium",10)
        plate(p+nn*.049,nn,.081,.021,.005,"Amber_Emitter",.002)
    for s in (-1,1):
        inset((s*1.992,1.57,5.647),-Z,.277,1.43,"Graphite_Alloy","Composite_Slate",.053,.009)
    # High-contrast inner service jamb and pressure/service sample points.
    for zz in (2.245,5.210):
        for ss in (-1,1):
            tube([(ss*2.087,.119,zz),(ss*2.096,1.47,zz),(ss*2.016,2.17,zz),(ss*1.715,2.48,zz)],.037,"Graphite_Alloy",8)


aero_detail()


def edit_prop(room,id):
    global current
    current=groups[(room,id)]


def loft(sections,mat):
    # Each section is (x coordinate, ordered [(height, longitudinal position)...]).
    rings=[]
    for x,pts in sections:
        points=[v((x,y,z)) for y,z in pts];ring=[]
        for i,p in enumerate(points):
            prior=points[i-1]-p;nxt=points[(i+1)%len(points)]-p
            radius=min(.026,prior.length*.24,nxt.length*.24)
            a=p+prior.normalized()*radius;b=p+nxt.normalized()*radius
            for t in (0,.33,.67,1.):
                ring.append(a*(1-t)**2+p*(2*t*(1-t))+b*t*t)
        rings.append(ring)
    ctr=sum([p for row in rings for p in row],v((0,0,0)))/sum(map(len,rings))
    face(rings[0],mat,-X);face(rings[-1],mat,X)
    for k,(aa,bb) in enumerate(zip(rings[:-1],rings[1:])):
        for i in range(len(aa)):
            j=(i+1)%len(aa);vv=[aa[i],aa[j],bb[j],bb[i]]
            ns=[]
            for u,w in ((k,i),(k,j),(k+1,j),(k+1,i)):
                along=rings[min(len(rings)-1,u+1)][w]-rings[max(0,u-1)][w]
                pprev=rings[u][w-1];pnext=rings[u][(w+1)%len(aa)];p=rings[u][w]
                rr=(p-pprev).normalized()+(pnext-p).normalized()
                no=rr.cross(along).normalized()
                if no.dot(p-ctr)<0:no.negate()
                ns.append(no)
            face(vv,mat,sum(ns,v((0,0,0))),normals=ns)
def shaped_station():
    room="observation";edit_prop(room,"pilot_console")
    main=[(.127,-5.557),(.127,-5.320),(.262,-5.204),(.487,-5.198),(.728,-4.971),
          (.786,-4.841),(.841,-4.793),(.914,-4.796),(1.026,-4.926),(1.075,-5.029),
          (1.306,-5.190),(1.360,-5.295),(1.369,-5.451),(1.302,-5.532),(.512,-5.562)]
    def section(x,dy=0,dz=0):
        return (x,[(y+dy*max(0,min(1,(y-.52)/.54)),z+dz*(.35+.65*max(0,min(1,(y-.5)/.4)))) for y,z in main])
    loft([section(-.476,-.10,-.17),section(-.414,-.033,-.103),section(-.27,0,-.012),
          section(.18),section(.92),section(1.179,-.014,0),section(1.240,-.116,-.042),
          section(1.37,-.215,-.057),section(1.86,-.202,-.106),section(2.026,-.242,-.213)],"Composite_Slate")
    # The lower centre is a cantilevered electronics bay bolted into the pressure wall.
    for xxv in (-.32,.13,.96,1.63):
        casing_x(xxv,.061,[(.17,-5.494),(.18,-5.30),(.36,-5.15),(.49,-5.13),
                            (.733,-4.96),(.733,-5.06),(.477,-5.33),(.42,-5.45)],"Graphite_Alloy")
    lowern=v((0,-.42,.91)).normalized();p=v((.43,.60,-5.065))
    plate(p,lowern,1.14,.16,.023,"Carbon_Ceramic",.009)
    for i in range(26):
        pp=p+X*((i-12.5)*.038)+lowern*.015
        plate(pp,lowern,.023,.097,.006,"Black_Rubber",.003)
    label((1.47,.384,-5.17),Z,.305,.062,"civil")
    # Tilted black-glass instrument band. Structural cheeks and thin top hood stay integral with the hull.
    n=v((0,.58,.815)).normalized();r,u,_=basis(n);c=v((.475,1.193,-5.102))
    plate(c,n,1.46,.305,.042,"Carbon_Ceramic",.021)
    for s in (-1,1):
        pp=c+r*s*.724
        plate(pp+n*.022,n,.026,.294,.019,"Titanium",.005)
        for d in (-.108,.108):screw(pp+u*d+n*.034,n,.008,False)
    plate(c+u*.164+n*.022,n,1.482,.045,.080,"Graphite_Alloy",.017)
    plate(c-u*.157+n*.026,n,1.454,.025,.031,"Titanium",.009)
    secondaries(c,n)
    dnorm=v((0,.83,.557)).normalized();dr,du,_=basis(dnorm);deck=v((.429,.966,-4.857))
    plate(deck,dnorm,1.458,.197,.022,P("pilot_console"),.012)
    flight_controls(deck,dnorm)
    palm=[(-.45,.808,-4.927),(-.29,.855,-4.83),(-.158,.867,-4.803),(.98,.867,-4.803),
          (1.173,.862,-4.810),(1.336,.774,-4.884),(1.724,.753,-4.93),(1.924,.726,-5.036)]
    tube(palm,.032,"Harness_Grip",16)
    tube([(x,y-.033,z-.004) for x,y,z in palm],.012,"Titanium",8)
    # Stamped three-detent exterior camera quadrant; gate is captive in the low starboard cheek.
    p=v((1.471,.962,-5.066));plate(p,Y,.297,.338,.037,"Carbon_Ceramic",.017)
    for j in range(3):
        pp=p+Z*(j-1)*.061-X*.097+Y*.023
        cube(pp,(.032,.003,.009),"Ceramic_Pearl" if j!=1 else "Amber_Emitter")
    label(p+X*.117+Y*.022,Y,.047,.186,"manual",right=Z)
    edit_prop(room,"nav_screen")
    p=v((.716,1.198,-5.104))+n*.040
    plate(p,n,.758,.283,.036,P("nav_screen"),.018)
    rim(p+n*.019,n,.748,.277,.026,.677,.212,.021,.008,"Graphite_Alloy")
    surface=p+n*.0206;w=.675;h=.211
    face([surface+r*w*a/2+u*h*b/2 for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))],
         "Nav_Active_Pixels",n,[(0,0),(1,0),(1,1),(0,1)])
    for sx in (-1,1):
        for sy in (-1,1):screw(p+r*(sx*.353)+u*(sy*.111)+n*.021,n,.006)
    for j in range(4):
        pp=p+r*((j-1.5)*.043)-u*.127+n*.0215
        plate(pp,n,.018,.004,.002,"Blue_Emitter",.0008)
    shell(room)
    # A continuous raked internal reveal, distinct from the flush glass-to-pressure-frame bond.
    cross=[(3.94,1.87,.313,.147),(3.89,1.823,.297,.190),(3.735,1.67,.236,.104),(3.60,1.534,.194,.082)]
    c=v((0,1.59,-5.706))
    borders=[]
    for sw,sh,sr,depth in cross:
        borders.append([c+X*x+Y*y+Z*depth for x,y in arc_rect(sw,sh,sr,6)])
    for i,(aa,bb) in enumerate(zip(borders[:-1],borders[1:])):
        for j in range(len(aa)):
            k=(j+1)%len(aa);face([aa[j],aa[k],bb[k],bb[j]],("Graphite_Alloy","Ceramic_Pearl","Titanium")[i],Z)
    for sx in (-1,1):
        shoulder=[(sx*1.954,.88,-5.526),(sx*1.989,1.011,-5.515),(sx*2.016,2.078,-5.503),(sx*1.787,2.422,-5.532)]
        tube(shoulder,.046,"Graphite_Alloy",10)
        for yyv in (1.11,1.71,2.015):
            pp=v((sx*1.866,yyv,-5.549));rod(pp,pp+Z*.012,.023,"Black_Rubber",10);screw(pp+Z*.013,Z,.014,False)


def shaped_seats():
    edit_prop("observation","lounge_seat")
    control=[(-1.261,.585,.335),(-1.302,.649,.390),(-1.438,.674,.413),(-1.654,.651,.413),
             (-1.802,.611,.386),(-1.870,.641,.374),(-1.891,.754,.377),(-1.885,.901,.389),
             (-1.918,1.064,.409),(-1.965,1.222,.406),(-2.014,1.343,.339),(-2.025,1.452,.253),(-2.023,1.527,.219)]
    def spline(t):
        seg=min(len(control)-2,max(0,math.floor(t)));f=t-seg
        aa=control[max(0,seg-1)];b=control[seg];c=control[seg+1];dd=control[min(len(control)-1,seg+2)]
        return [(.5*((2*b[k])+(-aa[k]+c[k])*f+(2*aa[k]-5*b[k]+4*c[k]-dd[k])*f*f+(-aa[k]+3*b[k]-3*c[k]+dd[k])*f*f*f)) for k in range(3)]
    def sample(t,q,zz,offset=0,edge=0):
        x,y,w=spline(t);p=spline(max(0,t-.01));nxt=spline(min(12,t+.01))
        normal=v((nxt[1]-p[1],-(nxt[0]-p[0]),0)).normalized()
        wing=.078*abs(q)**2.9 * (.73+.27*math.sin(t*.31))
        tuck=-.014*math.exp(-((q/.29)**2))*math.sin(math.pi*t/12)**2
        pads=.003*math.cos(q*15+t*.43)
        return v((x,y,zz+q*(w+edge)))+normal*(offset+wing+tuck+pads),normal
    for zz in (-4.17,-3.225):
        # Fibre-reinforced pan can be unbolted individually from the load-sharing spar.
        for shift in (-.231,.231):
            z=zz+shift
            tube([(-1.995,.19,z),(-1.972,.326,z),(-1.833,.467,z),(-1.575,.48,z),(-1.4,.528,z)],.036,"Graphite_Alloy",9)
            for x,y in ((-1.966,.322),(-1.445,.515)):
                pp=v((x,y,z));rod(pp-Z*.027,pp+Z*.027,.044,"Titanium",10)
        def skin(offset,edge,mat):
            grid=[]
            for j in range(37):
                t=j/3
                grid.append([sample(t,k/8-1,zz,offset,edge)[0] for k in range(17)])
            for j in range(36):
                for k in range(16):
                    ix=((j,k),(j+1,k),(j+1,k+1),(j,k+1));pts=[grid[a][b] for a,b in ix]
                    ns=[]
                    for a,b in ix:
                        dt=grid[min(36,a+1)][b]-grid[max(0,a-1)][b]
                        dq=grid[a][min(16,b+1)]-grid[a][max(0,b-1)]
                        ns.append(dt.cross(dq).normalized())
                    face(pts,mat,sum(ns,v((0,0,0))),normals=ns)
            return grid
        under=skin(-.045,.022,"Carbon_Ceramic");top=skin(.007,0,P("lounge_seat"))
        for edge in (0,16):
            pts=[row[edge] for row in top]
            for j in range(36):
                face([top[j][edge],top[j+1][edge],under[j+1][edge],under[j][edge]],"Graphite_Alloy",Z*(-1 if edge==0 else 1))
            tube(pts,.005,"Harness_Grip",7)
        for j in (0,36):
            for k in range(16):
                face([top[j][k],top[j][k+1],under[j][k+1],under[j][k]],"Carbon_Ceramic",Y if j else X)
        for k in (-.52,.52):
            tube([sample(j/3,k,zz,.010)[0] for j in range(37)],.0021,"Pressure_Fabric",6)
        upholstered((-1.986,1.431,zz),(.088,.168,.399),"Pressure_Fabric",rot(Z,.08),.50)
        # Shoulder webbing follows the actual surface down the lumbar curve, introducing its own small shadow.
        for side in (-1,1):
            chain=[]
            for i in range(17):
                t=10.90-i*.395; q=side*(.67-.44*i/16)
                chain.append(sample(t,q,zz,.031)[0])
            chain.append(v((-1.647,.687,zz+side*.052)))
            belt(chain,.047,"Restraint_Webbing",widthdir=Z)
            p=chain[7];cube(p+X*.008,(.023,.054,.061),"Titanium",.004,rot(Z,.14))
            cube(p+X*.023,(.006,.022,.037),"Black_Rubber",.002)
            if side==(1 if zz< -4 else -1):
                tail=p+v((.024,-.009,side*.003))
                remember_flex("observation","flex_seat_forward_tail" if zz< -4 else "flex_seat_aft_tail","lounge_seat",
                    [tail,tail+v((.009,-.023,side*.004)),tail+v((.024,-.058,side*.007)),tail+v((.030,-.100,side*.010)),
                     tail+v((.024,-.146,side*.016)),tail+v((.015,-.183,side*.021))],[0,1],.033,.0026,
                     "Restraint_Webbing","ribbon",.047,guide=(0,0,1))
        cube((-1.625,.69,zz),(.076,.029,.129),"Graphite_Alloy",.009)
        cube((-1.616,.710,zz),(.042,.011,.062),"Signal_Orange",.004)
    for z in (-4.65,-2.747):
        tube([(-1.975,.469,z),(-1.942,.795,z),(-1.845,.835,z),(-1.491,.830,z),(-1.416,.772,z)],.022,"Titanium",14)
        upholstered((-1.682,.848,z),(.45,.065,.068),"Harness_Grip",ex=.50)
    for x in (-1.91,-1.55):
        cube((x,.447,-3.701),(.075,.084,1.927),"Graphite_Alloy",.014)
    for z in (-4.332,-3.057):
        tube([(-1.985,.082,z),(-1.974,.279,z),(-1.795,.414,z),(-1.527,.441,z)],.048,"Composite_Slate",9)
        cube((-1.978,.071,z),(.225,.10,.199),"Carbon_Ceramic",.023)
        for x in (-2.046,-1.912):screw((x,.123,z),Y,.016,False)


shaped_station()
shaped_seats()


def final_fit():
    global current
    shell("observation")
    # A large registration is directly printed on the liner, with the glass serial by the release fitting.
    mark((1.44,.643,-5.529),Z,.57,.120,"carid")
    mark((2.139,1.071,-3.21),-X,.61,.135,"glazing")
    mark((-2.14,1.125,-4.71),X,.30,.072,"serial")
    for sx in (-1,1):
        for zz in (-4.97,-2.63):
            inset((sx*2.153,.909,zz),X*-sx,.44,.125,"Graphite_Alloy","Ceramic_Pearl",.024,.007)
    current=groups[("observation","pilot_console")]
    mark((-.477,1.118,-5.366),-X,.172,.053,"carid")
    for xxv in (-.092,1.038):
        mark((xxv,.825,-4.777),Z,.166,.036,"identity")
    current=groups[("observation","lounge_seat")]
    profile=[(-1.35,.481),(-1.251,.513),(-1.223,.586),(-1.239,.694),(-1.327,.734),(-1.479,.708),(-1.596,.686),
             (-1.691,.733),(-1.762,.869),(-1.823,1.050),(-1.865,1.237),(-1.931,1.376),(-2.025,1.484),
             (-2.085,1.483),(-2.123,1.403),(-2.128,1.089),(-2.073,.791),(-1.954,.585),(-1.677,.472)]
    for zz in (-4.17,-3.225):
        for side in (-1,1):
            z=zz+side*.409
            aa=[v((x,y,z)) for x,y in profile];bb=[p+Z*(side*.024) for p in aa]
            face(aa,"Carbon_Ceramic",-Z*side);face(bb,"Ceramic_Pearl",Z*side)
            for i in range(len(aa)):
                j=(i+1)%len(aa);face([aa[i],aa[j],bb[j],bb[i]],"Composite_Slate")
            tube(bb,.007,"Ceramic_Pearl",8,True)
            for x,y in ((-1.359,.587),(-1.901,.841),(-2.053,1.312)):
                screw((x,y,z+side*.029),Z*side,.010,False)
            mark((-1.969,1.157,z+side*.0246),Z*side,.135,.045,"identity")
        for z in (zz-.274,zz+.274):
            belt([(-1.538,.493,z),(-1.552,.561,z),(-1.601,.642,z),(-1.621,.674,zz+math.copysign(.058,z-zz))],.042,"Restraint_Webbing",widthdir=Z)
    shell("berth")
    # A single co-cured aramid/titanium shell defines the pod mouth, with accessible panel seams.
    c=v((-1.286,1.437,0))
    rim(c,X,2.53,1.602,.314,2.348,1.379,.293,.065,"Ceramic_Pearl","Graphite_Alloy")
    rim(c+X*.002,X,2.369,1.397,.298,2.342,1.369,.283,.013,"Black_Rubber")
    for s in (-1,1):
        for z in (-.98,-.44,.34,.99):screw(c+X*.004+Z*z+Y*s*.743,X,.009,False)
    mark((-1.278,.716,.519),X,.35,.063,"bunkmark")
    pr=[(-2.13,2.18),(-1.88,2.241),(-1.57,2.239),(-1.438,2.184),(-1.343,2.069),(-1.32,2.002)]
    for j in range(len(pr)-1):
        a,b=pr[j],pr[j+1]
        face([(a[0],a[1],-1.18),(b[0],b[1],-1.18),(b[0],b[1],1.18),(a[0],a[1],1.18)],"Ceramic_Pearl")
        face([(a[0],a[1]-.033,-1.18),(a[0],a[1]-.033,1.18),(b[0],b[1]-.033,1.18),(b[0],b[1]-.033,-1.18)],"Graphite_Alloy")
    for zz in (-.58,.58):
        plate((-1.788,2.164,zz),-Y,.30,.841,.022,"Carbon_Ceramic",.009)
        plate((-1.788,2.150,zz),-Y,.045,.640,.008,"Opal_Emitter",.003)
    current=groups[("service","pressure_hatch")]
    for s in (-1,1):
        n=Z*s;c=v((0,1.128,1.9+s*.087));r,u,_=basis(n)
        rim(c,n,1.276,2.042,.168,1.22,1.977,.139,.016,"Graphite_Alloy")
        for sign in (-1,1):
            # Shallow formed panel stiffeners form opposing diagonal shoulders in the laminate.
            a=c+r*(sign*.51)+u*.62+n*.010;b=c+r*(sign*.39)+u*.80+n*.010
            d=c+r*(sign*.268)+u*.85+n*.010
            tube([a,b,d],.011,"Composite_Slate",8)
            a=c+r*(sign*.499)-u*.63+n*.011;b=c+r*(sign*.40)-u*.78+n*.011;d=c+r*(sign*.33)-u*.82+n*.011
            tube([a,b,d],.011,"Composite_Slate",8)
        mark(c-u*.484+r*.209+n*.004,n,.452,.104,"emergency")
        mark(c+u*.795+r*.058+n*.004,n,.403,.091,"identity")
        c2=c+u*.507
        rim(c2+n*.012,n,.272,.407,.118,.194,.337,.093,.014,"Titanium")
        flat_round(c2+n*.014,n,.199,.345,.095,"Smoked_Display")
        live_panel("Seal",c2+n*.016,n,.148,.206)
    shell("service")
    cc=v((0,1.269,5.592));n=-Z
    for j in range(64):
        t=T*j/64;u=T*(j+1)/64;da=X*math.cos(t)+Y*math.sin(t);db=X*math.cos(u)+Y*math.sin(u)
        face([cc+da*.707+n*.015,cc+db*.707+n*.015,cc+db*.395+n*.031,cc+da*.395+n*.031],
             "Ceramic_Pearl",n)
        if j%8==0:
            rod(cc+da*.407+n*.035,cc+da*.685+n*.019,.005,"Titanium",8)
    mark(cc+X*.025+Y*.511+n*.032,n,.426,.106,"collar")
    for s in (-1,1):
        for xoff,radius in ((1.34,.051),(1.51,.074),(1.72,.036)):
            for ht in (.30,2.22):
                tube([(s*xoff,ht,5.51),(s*xoff,ht+(1 if ht>1 else -1)*.078,5.51),
                      (s*xoff,ht+(1 if ht>1 else -1)*.131,5.544),(s*xoff,ht+(1 if ht>1 else -1)*.144,5.649)],radius,"Titanium",12)
            plate((s*xoff,1.57,5.43),-Z,.083,.184,.014,"Ceramic_Pearl",.007)
            mark((s*xoff,1.57,5.422),-Z,.071,.146,"serial",right=Y)
    current=groups[("service","docking_wheel")]
    cc=v((0,1.27,5.43));n=-Z
    pp=cc+X*.141-Y*.029+n*.036
    tube([cc+n*.028,cc+X*.085+n*.037,pp,cc+X*.219-Y*.040+n*.036],.015,"Signal_Orange",10)
    rod(pp+n*.003,pp+n*.026,.022,"Graphite_Alloy",12)
    current=groups[("service","service_cabinet")]
    mark((1.697,1.645,3.950),-X,.246,.054,"servicebay")
    # Inside of the maintenance cover carries a routing chart, grounding braid and retaining jaws.
    plate((1.789,1.588,3.558),X,.884,.581,.014,"Graphite_Alloy",.015)
    label((1.798,1.588,3.558),X,.853,.554,"cablemap")
    for z in (3.094,3.981):
        for h in (1.192,1.893):screw((1.789,h,z),X,.010,False)
    tube([(1.798,1.086,2.979),(1.827,1.099,3.009),(1.835,1.144,3.041),
          (1.824,1.183,3.053),(1.795,1.227,3.049)],.007,"Titanium",7)
    shell("service")
    # Lower module looms terminate at each actual connector. Corrugated shield and heatshrink
    # rings distinguish optical pairs from high-current feeder runs at inspection distance.
    for j in range(12):
        zz=3.348+(j//3)*.23+(j%3-1)*.042
        outer=4.095+(j%3)*.027;basey=1.047+(j//3)*.032
        upper=1.57+(j//3)*.057;end=3.29+(j//3)*.23
        xf=1.931-(j%3)*.012
        rr=.008 if j%3 else .012
        route=[(1.991,1.114,zz),(1.966,1.104,zz),(xf,1.077,zz),(xf,basey+.010,zz+.012),(xf,basey,zz+.030),
               (xf,basey,outer-.052),(xf,basey+.017,outer-.019),(xf,basey+.041,outer),
               (xf,upper-.040,outer),(xf,upper-.014,outer-.015),(xf,upper,outer-.040),
               (xf,upper,end+.051),(xf+.010,upper+.019,end+.026),(1.969,upper+.050,end),
               (1.992,1.775,end)]
        mt=("Cable_Orange","Cable_Blue","Technical_Twill")[j%3]
        tube(route,rr,mt,8)
        if j%3==0:probe_trace(j//3,route)
        for a in range(5):
            yy=basey+.09+a*.077
            rod((xf,yy,outer),(xf,yy+.012,outer),rr*1.26,"Black_Rubber",8)
        rod((1.98,1.100,zz),(2.006,1.118,zz),rr*1.39,"Titanium",10)
    for j in range(8):
        for k in range(6):
            zz=3.086+j*.135;h=1.284+k*.074
            pp=v((2.062,h,zz));rod(pp,pp-X*.004,.004,"Black_Rubber",6)
    plate((1.943,2.003,3.55),-Y,.218,1.00,.030,"Carbon_Ceramic",.006)
    plate((1.942,1.984,3.55),-Y,.062,.918,.008,"Opal_Emitter",.003)


final_fit()
exec(compile((ROOT/"source"/"handhelds.py").read_text(),str(ROOT/"source"/"handhelds.py"),"exec"))
exec(compile((ROOT/"source"/"gravity_authoring.py").read_text(),str(ROOT/"source"/"gravity_authoring.py"),"exec"))
exec(compile((ROOT/"source"/"furnishings_authoring.py").read_text(),str(ROOT/"source"/"furnishings_authoring.py"),"exec"))
switchboard_package=finish_switchboard()
for folder in (WEB,FBX):(folder/"switchboard.json").write_text(json.dumps(switchboard_package,indent=2))


def blender(p):
    return (p[0],-p[2],p[1])
def trim(p):
    return [round(x,5) for x in p]
def select_only(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[-1]
def printable_objects():
    return {room:bpy.data.collections.new(room.capitalize()) for room in rooms}
colls=printable_objects()
for col in colls.values():scene.collection.children.link(col)
start_time=time.monotonic()
def log(msg):
    print(f"[UPWELL +{time.monotonic()-start_time:.1f}s] {msg}",flush=True)


def room_occluders(room):
    verts=[];faces=[]
    skip={"window","roller_shade","privacy_curtain","access_card","field_glasses","logbook","mug","tool_roll","service_cabinet","pressure_hatch"}
    for g in groups.values():
        if g.room!=room or g.id in skip:continue
        offset=len(verts);verts.extend(g.verts)
        faces.extend([tuple(idx+offset for idx in f) for f in g.faces])
    return BVHTree.FromPolygons(verts,faces,all_triangles=False,epsilon=0.0)
def ao_for_group(g,tree):
    """Short-range ambient contact, only against fixed fittings. No baked directional light."""
    result=[];cache={}
    weights=(.26,.23,.23,.15,.13)
    for p,n in zip(g.verts,g.normals):
        key=(round(p.x*85),round(p.y*85),round(p.z*85),round(n.x*5),round(n.y*5),round(n.z*5))
        color=cache.get(key)
        if color is None:
            n=v(n).normalized();r,u,n=basis(n);o=p+n*.0026
            occ=0
            for direction,weight in zip((n,(n*.54+r*.85).normalized(),(n*.54-r*.85).normalized(),
                                         (n*.54+u*.85).normalized(),(n*.54-u*.85).normalized()),weights):
                loc,_,_,dist=tree.ray_cast(o,direction,.38)
                if loc is not None:occ+=(1-dist/.38)**1.6*weight
            color=.99-.53*occ;cache[key]=color
        result.extend((color,color,min(1.,color+(1-color)*.036),1.))
    return result


def make_mesh(g,tree):
    name=("shell_"+g.room if g.id=="shell" else "geo_"+g.id)
    mesh=bpy.data.meshes.new(name)
    mapped=getattr(g,"bind_uv",None)
    if mapped:
        # Weld the physical front, back and edge vertices. UVs / split normals
        # remain per-corner so a hem can carry its own material without tears.
        lookup={};unique=[];remap=[];g.vertex_bindings=[]
        for p in g.verts:
            key=tuple(round(float(q),7) for q in p)
            if key not in lookup:
                lookup[key]=len(unique);unique.append(blender(p-g.pivot));g.vertex_bindings.append(mapped(p))
            remap.append(lookup[key])
        mesh.from_pydata(unique,[],[tuple(remap[i] for i in f) for f in g.faces],shade_flat=False)
    else:
        mesh.from_pydata([blender(p-g.pivot) for p in g.verts],[],g.faces,shade_flat=False)
    for mat in g.matlist:mesh.materials.append(M[mat])
    mesh.polygons.foreach_set('material_index',g.ids)
    uv=mesh.uv_layers.new(name="Physical UV")
    uv.uv.foreach_set('vector',[k for uvp in g.uv for k in uvp])
    if mapped:
        uv2=mesh.uv_layers.new(name="Deform UV");auxuv=[mapped(p) for p in g.verts]
        uv2.uv.foreach_set("vector",[val for u0,v0 in auxuv for val in (u0,1-v0)])
        mesh.uv_layers.active=uv;uv.active_render=True
    mesh.normals_split_custom_set([blender(p) for p in g.normals])
    if tree:
        ao=mesh.color_attributes.new(name="Contact_Occlusion",type="BYTE_COLOR",domain="CORNER" if mapped else "POINT")
        ao.data.foreach_set("color",ao_for_group(g,tree))
        mesh.color_attributes.active_color=ao
    mesh.update()
    o=bpy.data.objects.new(name,mesh);colls[g.room].objects.link(o);g.mesh=o
    if g.room=="exterior":
        o.location=blender(g.pivot);o.name=g.id;g.object=o
        return o
    if g.id in flex_parts or g.id in mechanisms or g.id in auxiliary_parts:
        par=groups[(g.room,g.parent)];o.name=g.id;o.parent=par.object;o.location=blender(g.pivot-par.pivot)
        g.object=o;o["component_parent"]=g.parent
        if g.id in mechanisms:
            mech=mechanisms[g.id];prop="travel_"+g.id.removeprefix("mech_");par.object[prop]=0.
            par.object.id_properties_ui(prop).update(min=0.,max=1.,description=mech["label"])
            axis_index,sign={"x":(0,1),"y":(2,1),"z":(1,-1)}[mech["axis"]]
            curve=o.driver_add("rotation_euler",axis_index);driver=curve.driver;driver.type="SCRIPTED"
            variable=driver.variables.new();variable.name="travel";variable.targets[0].id=par.object
            variable.targets[0].data_path='["'+prop+'"]';driver.expression="travel*"+str(sign*math.radians(mech["travel"]))
        return o
    if g.id=="shell":
        g.object=o;return
    root=bpy.data.objects.new("prop_"+g.id,None);colls[g.room].objects.link(root)
    if g.parent:
        par=groups[(g.room,g.parent)];root.parent=par.object
        root.location=blender(g.pivot-par.pivot)
    else:
        root.location=blender(g.pivot)
    root.empty_display_type="PLAIN_AXES";root.empty_display_size=.08
    root["id"]=g.id;root["action"]=propinfo[g.id]["action"];root["room"]=g.room
    if g.animation:root["motion"]=json.dumps(g.animation)
    o.parent=root;g.object=root


for room in rooms:
    log(f"meshing {room}")
    tree=room_occluders(room)
    for g in [g for g in groups.values() if g.room==room]:
        make_mesh(g,tree)
    log(f"{room} geometry ready")
    del tree

scene.render.engine="CYCLES"
scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX"
scene.world=bpy.data.worlds.new("Pressure-window daylight")
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get("Background");bg.inputs["Color"].default_value=(.18,.27,.35,1);bg.inputs["Strength"].default_value=.58
rig=bpy.data.collections.new("Photography");scene.collection.children.link(rig)
def aim(o,target,track="-Z"):
    o.rotation_euler=(v(blender(target))-o.location).to_track_quat(track,"Y").to_euler()
def area(name,pos,target,power,color,size,size_y=None):
    light=bpy.data.lights.new(name,"AREA");light.energy=power;light.color=color;light.shape="RECTANGLE";light.size=size;light.size_y=size_y or size
    obj=bpy.data.objects.new(name,light);rig.objects.link(obj);obj.location=blender(pos);aim(obj,target);return obj
def camera(name,pos,target,lens):
    cam=bpy.data.cameras.new(name);cam.lens=lens;cam.clip_start=.03;cam.clip_end=30000
    ob=bpy.data.objects.new(name,cam);rig.objects.link(ob);ob.location=blender(pos);aim(ob,target);return ob
area("Front laminate",(-.6,2.6,-7.6),(0,.8,-3.7),660,(.72,.85,1),3.6,2.3)
area("Warm solar reflection",(-4.8,3.0,-4.7),(.6,.35,-3.15),590,(1,.74,.52),3.2,1.25)
area("Cloud bounce",(4.4,1.8,-3.4),(-1.7,.8,-3.6),240,(.68,.83,1),2.1,1.25)
for room in rooms:
    cz=midpoints[room]
    for s in (-1,1):
        area(room.title()+" indirect "+str(s),(s*1.79,2.32,cz),(s*.50,.8,cz),41 if room!="service" else 50,(1,.9,.76) if s<0 else (.79,.90,.98),.23,2.04)
area("Sleeper exterior",(4.4,2.3,.17),(-1.77,.7,.14),194,(.68,.87,1),2.4,1.4)
area("Service exterior",(-4.1,2.3,3.71),(1.43,.98,3.68),125,(.64,.82,1),1.4,.9)
cameras=[
    camera("Observation / forward",(1.48,1.43,-2.12),(-.52,1.26,-4.49),17),
    camera("Sleeper / aft",(.66,1.50,-1.46),(-.70,1.19,.37),16.5),
    camera("Service / aft",(-.60,1.50,2.19),(.45,1.37,4.89),17),
]
scene.camera=cameras[0]
cameras[0].rotation_euler.rotate_axis("Z",-.023)
camera("Service / loom",(-.18,1.39,4.66),(1.96,1.47,3.64),21)
area("Harness inspection channel",(1.91,1.952,3.55),(1.968,1.20,3.55),8.5,(.79,.94,1),.104,.90)
exec(compile((ROOT/"source"/"native_exterior.py").read_text(),str(ROOT/"source"/"native_exterior.py"),"exec"))
for area_ui in bpy.context.screen.areas:
    if area_ui.type=="VIEW_3D":
        area_ui.spaces.active.region_3d.view_perspective="CAMERA"
        area_ui.spaces.active.shading.color_type='MATERIAL'
        area_ui.spaces.active.overlay.show_overlays=False
camera("Instrument / nadir",(.11,-.28,-5.83),(.11,-180,-5.83),72)
camera("Instrument / guide",(-2.10,1.72,4.04),(-3.46,1.26,3.06),20)
bpy.context.view_layer.update()
layout=[]; props={}; rooms_json={}
for room in rooms:
    lo=midpoints[room]-1.9;hi=midpoints[room]+1.9
    rooms_json[room]={"file":room+".glb","center":[0,1.32,midpoints[room]],"bounds":[[-2.2,0,lo],[2.2,2.64,hi]]}
    for g in [a for a in groups.values() if a.room==room]:
        if g.id in flex_parts or g.id in mechanisms or g.id in auxiliary_parts:continue
        bounds=current_bounds(g);name="shell" if g.id=="shell" else "prop_"+g.id
        entry={"id":g.id,"room":g.room,"file":room+"/"+name+".fbx","node":g.object.name,"webPivot":trim(g.pivot),
               "webCenter":trim(g.center),"webBounds":bounds,"dimensions":[round(b-a,5) for a,b in zip(*bounds)]}
        if g.animation:entry["animation"]=g.animation
        if g.parent:entry["parent"]=g.parent
        layout.append(entry)
        if g.id!="shell":props[g.id]={**entry,"pivot":entry["webPivot"],"center":entry["webCenter"],"bounds":bounds}
data={"units":"m","basis":"glTF +X starboard, +Y up, +Z aft","rooms":rooms_json,"props":props,"switchboard":switchboard_package}
(WEB/"scene.json").write_text(json.dumps(data,indent=2))
(FBX/"layout.json").write_text(json.dumps({"basis":data["basis"],"units":"m","parts":layout},indent=2))
flex_manifest={"basis":data["basis"],"units":"m","coordinateSpace":"parent-local glTF","parts":[]}
for id,d in flex_parts.items():
    g=groups[(d["room"],id)];par=groups[(d["room"],d["parent"])]
    local=[p-par.pivot for p in d["points"]]
    entry={"id":id,"node":id,"room":g.room,"parentId":g.parent,"parentNode":"prop_"+g.parent,
           "file":g.room+"/"+id+".fbx","webPivot":trim(par.pivot),"webBounds":current_bounds(g),
           "localBounds":[trim(v(g.lo)-par.pivot),trim(v(g.hi)-par.pivot)],"localReferenceVertex":trim(g.verts[0]-par.pivot),
           "restPoints":[trim(q) for q in local],"worldRestPoints":[trim(q) for q in d["points"]],
           "pinIndices":d["pins"],"pinnedEnds":[0 in d["pins"],len(local)-1 in d["pins"]],"kind":d["kind"],
           "width":d["width"],"thickness":d["thickness"],"material":d["material"],"maxOffset":d["limit"],
           "widthGuide":trim(d["guide"]),"supportY":None if d["support"] is None else round(d["support"]-par.pivot.y,6),
           "supportWorldY":d["support"]}
    flex_manifest["parts"].append(entry)
for folder in (WEB,FBX):(folder/"flex.json").write_text(json.dumps(flex_manifest,indent=2))
mech_manifest={"basis":data["basis"],"units":"m","parts":[]}
for id,m in mechanisms.items():
    g=groups[(m["room"],id)];par=groups[(g.room,m["parent"])]
    mech_manifest["parts"].append(dict(id=id,node=id,room=g.room,parentId=g.parent,parentNode="prop_"+g.parent,
        file=g.room+"/"+id+".fbx",webPivot=trim(g.pivot),parentLocalPivot=trim(g.pivot-par.pivot),kind="rotate",axis=m["axis"],
        amount=m["travel"],detents=m["detents"],label=m["label"],webBounds=current_bounds(g),
        localBounds=[trim(v(g.lo)-g.pivot),trim(v(g.hi)-g.pivot)],localReferenceVertex=trim(g.verts[0]-g.pivot)))
for folder in (WEB,FBX):(folder/"mechanisms.json").write_text(json.dumps(mech_manifest,indent=2))
gravity_data={"basis":data["basis"],"units":"m","accelerometer":accel_spec,"capillary":cell_spec,"parts":[]}
soft_data={"basis":data["basis"],"units":"m","coordinateSpace":"node-local glTF metres","parts":[]}
for name,info in auxiliary_parts.items():
    room=info["room"];g=groups[(room,name)];par=groups[(room,g.parent)]
    key=par.object.name
    part=dict(id=name,node=name,room=room,parentId=g.parent,parentNode=key,file=room+"/"+name+".fbx",
              webPivot=trim(g.pivot),parentLocalPivot=trim(g.pivot-par.pivot),webBounds=current_bounds(g),
              localBounds=[trim(v(g.lo)-g.pivot),trim(v(g.hi)-g.pivot)],localReferenceVertex=trim(g.verts[0]-g.pivot))
    if info["domain"]=="gravity":gravity_data["parts"].append(part)
    else:
        part.update(furnishing_specs[name])
        if getattr(g,"bind_uv",None):part.update(deformAttribute="TEXCOORD_1",deformUV="u,v; v towards foot for quilt, downward for curtain",fbxVIsOneMinusV=True)
        soft_data["parts"].append(part)
for folder in (WEB,FBX):
    (folder/"gravity-instruments.json").write_text(json.dumps(gravity_data,indent=2))
    (folder/"furnishings.json").write_text(json.dumps(soft_data,indent=2))

# Each terminal is authored against the current native master; room exports remain local to their own collections.
if (ROOT/"source"/"build_terminals.py").exists() and (ROOT/"unity"/"Assets"/"Upwell"/"Terminals"/"Textures"/"materials.json").exists():
    import runpy
    runpy.run_path(str(ROOT/"source"/"build_terminals.py"),init_globals={"TERMINAL_EMBED_ONLY":True})
    capture_cam=camera("Instrument / capture",(.30,2.82,-4.13),(.0,20,0),21)
    target=bpy.data.objects.new("Aster Reach · receiving axis",None);rig.objects.link(target)
    target.parent=bpy.data.objects["aster"];target.location=blender((0,3.41,0));target.empty_display_size=.15
    track=capture_cam.constraints.new("TRACK_TO");track.target=target;track.track_axis="TRACK_NEGATIVE_Z";track.up_axis="UP_Y"
blendfile=BLEND/"Upwell.blend"
for image in imgcache.values():
    if not image.packed_file:image.pack()
select_only([cameras[0]])
bpy.ops.wm.save_as_mainfile(filepath=str(blendfile),compress=True)
log("Blender scene saved")
export_args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
only_room=next((a.partition("=")[2] for a in export_args if a.startswith("--room=")),None)
only_part=next((a.partition("=")[2] for a in export_args if a.startswith("--part=")),None)
for room in rooms:
    if only_room and room!=only_room:continue
    select_only(list(colls[room].objects))
    bpy.ops.export_scene.gltf(filepath=str(WEB/(room+".glb")),export_format="GLB",use_selection=True,
        export_extras=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False,
        export_vertex_color="ACTIVE",export_image_format="AUTO",export_image_quality=85,
        export_materials="EXPORT",export_normals=True,export_texcoords=True,export_tangents=False)
    log("exported "+room+".glb")
    (FBX/room).mkdir(exist_ok=True)
    for g in [a for a in groups.values() if a.room==room]:
        if only_part and g.id not in only_part.split(","):continue
        name="shell" if g.id=="shell" else g.id if g.id in flex_parts or g.id in mechanisms or g.id in auxiliary_parts else "prop_"+g.id
        temp=bpy.data.objects.new("SM_"+name,g.mesh.data)
        rig.objects.link(temp)
        select_only([temp])
        bpy.ops.export_scene.fbx(filepath=str(FBX/room/(name+".fbx")),use_selection=True,
            axis_forward="-Z",axis_up="Y",object_types={"MESH"},bake_space_transform=True,
            bake_anim=False,apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
            path_mode="RELATIVE",colors_type="LINEAR",use_triangles=True)
        bpy.data.objects.remove(temp,do_unlink=True)
    log("exported "+room+" FBX kit")
exec(compile((ROOT/"source"/"native_suspension.py").read_text(),str(ROOT/"source"/"native_suspension.py"),"exec"))
if "--preview" in sys.argv:
    for room,cam in zip(rooms,cameras):
        scene.camera=cam;scene.render.filepath=str(BLEND/(room+".jpg"))
        scene.render.image_settings.file_format="JPEG";scene.render.image_settings.quality=91
        bpy.ops.render.render(write_still=True)
log("finished")
