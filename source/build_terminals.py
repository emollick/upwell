"""Construct the ocean-anchor launch shaft and orbital receiving vault.

Run in Blender against Upwell.blend. Geometry lives in local glTF metres with
+Y vertical and -Z forward. Room meshes and their exports are left alone.
"""
import bpy
import json
import math
import random
import sys
import tempfile
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"web"/"assets"/"terminals"
UNITY=ROOT/"unity"/"Assets"/"Upwell"/"Terminals"
TEX=UNITY/"Textures"
BASE=ROOT/"unity"/"Assets"/"Upwell"/"SourceModels"/"Textures"
for path in (WEB,UNITY,ROOT/"source"/".export-cache"):path.mkdir(parents=True,exist_ok=True)
tempfile.tempdir=str(ROOT/"source"/".export-cache")
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
if not bpy.data.materials.get("Ceramic_Pearl"):
    raise RuntimeError("Open the packed Upwell.blend before building its terminal exteriors.")
v=Vector;X=v((1,0,0));Y=v((0,1,0));Z=v((0,0,1));T=math.tau
atlas=json.loads((TEX/"atlas.json").read_text());meta=json.loads((TEX/"materials.json").read_text())
metadata={**json.loads((BASE/"materials.json").read_text()),**meta}
exec(compile((ROOT/"source"/"mesh_primitives.py").read_text(),str(ROOT/"source"/"mesh_primitives.py"),"exec"))
def bl(p):return (p[0],-p[2],p[1])
def trim(p):return [round(float(a),5) for a in p]
def select(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:ob.select_set(True)
    bpy.context.view_layer.objects.active=objs[-1]
def material(name,spec):
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials.new(name);m.use_nodes=True
    nd=m.node_tree.nodes;lk=m.node_tree.links;b=nd.get("Principled BSDF")
    rgb=tuple((i/255/12.92 if i/255<.04045 else ((i/255+.055)/1.055)**2.4) for i in spec["rgb"]);m.diffuse_color=(*rgb,spec.get("alpha",1))
    b.inputs["Base Color"].default_value=(*rgb,1);b.inputs["Metallic"].default_value=spec["metallic"];b.inputs["Roughness"].default_value=spec["roughness"]
    if spec.get("emission"):
        b.inputs["Emission Color"].default_value=(*rgb,1);b.inputs["Emission Strength"].default_value=spec["emission"]
    for key,socket in (("baseColor","Base Color"),("normal","Normal"),("roughnessMap","Roughness")):
        if key not in spec:continue
        f=TEX/spec[key]
        if not f.exists():f=BASE/spec[key]
        im=bpy.data.images.load(str(f),check_existing=True)
        if key!="baseColor":im.colorspace_settings.name="Non-Color"
        if not im.packed_file:im.pack()
        node=nd.new("ShaderNodeTexImage");node.image=im
        if key=="normal":
            nm=nd.new("ShaderNodeNormalMap");nm.inputs["Strength"].default_value=.57
            lk.new(node.outputs["Color"],nm.inputs["Color"]);lk.new(nm.outputs["Normal"],b.inputs[socket])
        else:lk.new(node.outputs["Color"],b.inputs[socket])
        if key=="baseColor" and spec.get("emission"):
            lk.new(node.outputs["Color"],b.inputs["Emission Color"]);b.inputs["Emission Strength"].default_value=spec["emission"]
    return m
for name,spec in meta.items():material(name,spec)

def print_face(c,n,w,h,key,screen=False):
    c=v(c);r,u,n=basis(n);sx,sy,sw,sh=atlas["rects"][key];aw,ah=atlas["size"]
    uv=[(sx/aw,1-(sy+sh)/ah),((sx+sw)/aw,1-(sy+sh)/ah),((sx+sw)/aw,1-sy/ah),(sx/aw,1-sy/ah)]
    pp=[c+r*w*a/2+u*h*b/2 for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))]
    face(pp,"Terminal_Display" if screen else "Terminal_Print",n,uv)
def sign(c,n,w,h,key,screen=False,plate_mat="Graphite_Alloy"):
    c=v(c);n=v(n)
    plate(c,n,w+.045,h+.039,.033,plate_mat,.008)
    print_face(c+n*.018,n,w,h,key,screen)
def strut(a,b,w,h,mat,edge=0):
    a=v(a);b=v(b);e=(b-a).normalized()
    side=e.cross(Y)
    if side.length<.01:side=X.copy()
    side.normalize();up=side.cross(e).normalized()
    cube((a+b)/2,(w,h,(b-a).length),mat,edge,Matrix((side,up,e)).transposed())
def channel(a,b,width,depth,mat):
    a=v(a);b=v(b);e=(b-a).normalized();r,u,n=basis(e)
    strut(a,b,width*.24,depth,mat)
    for s in (-1,1):strut(a+u*s*depth*.45,b+u*s*depth*.45,width,depth*.13,mat)
def lightbar(c,n,width,light="Opal_Emitter",mat="Graphite_Alloy"):
    c=v(c);r,u,n=basis(n);plate(c,n,width+.13,.124,.075,mat,.012)
    plate(c+n*.040,n,width,.072,.010,light,.004)
    for q in (-1,1):rod(c+r*q*(width*.5+.038)-n*.015,c+r*q*(width*.5+.038)+n*.04,.028,"Titanium",8)
def rails(a,b,height=1.03,mat="Structural_Galvanized",cap=None):
    a=v(a);b=v(b);dv=b-a;length=dv.length
    for y,r in ((height,.030),(height*.52,.018)):
        rod(a+Y*y,b+Y*y,r,cap or mat,8)
    for i in range(max(1,math.ceil(length/1.5))+1):
        t=i/max(1,math.ceil(length/1.5));p=a+dv*t
        rod(p,p+Y*height,.031,mat,8);cube(p+Y*.025,(.115,.047,.115),mat,.006)
def grating(cx,y,cz,w,d,edge="Graphite_Alloy",density=.145):
    # Open metal construction with true slots and through-light.
    for sx in (-1,1):cube((cx+sx*(w/2-.035),y-.062,cz),(.07,.155,d),edge)
    for sz in (-1,1):cube((cx,y-.062,cz+sz*(d/2-.035)),(w,.155,.07),edge)
    count=max(2,int(w/density))
    for k in range(count):
        x=cx-w*.5+(k+.5)*w/count;cube((x,y-.045,cz),(.029,.084,d-.072),"Structural_Galvanized")
    for j in range(max(2,int(d/.32))):
        z=cz-d*.5+(j+.5)*d/max(2,int(d/.32));cube((cx,y-.081,z),(w-.06,.035,.026),edge)
def deck(cx,y,cz,w,d,mat,edge="Graphite_Alloy"):
    cube((cx,y-.12,cz),(w,.23,d),edge,.020)
    nx=max(1,round(w/1.7));nz=max(1,round(d/1.7))
    for i in range(nx):
        for j in range(nz):
            x=cx-w/2+(i+.5)*w/nx;z=cz-d/2+(j+.5)*d/nz
            cube((x,y-.013,z),(w/nx-.025,.034,d/nz-.025),mat,.004)
def rack(c,n,width=.70,height=1.70,tone="Carbon_Ceramic",screen="scada"):
    c=v(c);r,u,n=basis(n)
    plate(c,n,width,height,.35,tone,.03)
    for x in (-.45,.45):plate(c+n*.182+r*x*width,n,.024,height-.075,.025,"Titanium",.006)
    for j in range(8):
        p=c+n*.185+u*((j-3.5)*(height-.16)/8)
        plate(p,n,width-.084,(height-.16)/8-.022,.046,"Graphite_Alloy",.006)
        if j in (4,6):
            print_face(p+n*.025,n,width*.63,(height-.16)*.085,screen,True)
        else:
            for k in range(10):plate(p+n*.024+r*((k-4.5)*width*.047),n,.010,.066,.006,"Black_Rubber")
            for k in (-1,1):plate(p+n*.025+r*(k*width*.37),n,.020,.014,.003,"Mint_Emitter" if j%3 else "Amber_Emitter")
def crate(c,w,h,d,base_mat="Marine_Primer"):
    c=v(c);cube(c,(w,h,d),base_mat,.039)
    for j in (-1,1):
        cube(c+Y*(j*(h/2-.04)),(w+.025,.074,d+.025),"Graphite_Alloy",.009)
        for k in (-1,1):cube(c+X*j*(w/2-.036)+Z*k*(d/2-.036),(.086,h,.084),"Structural_Galvanized",.012)
    sign(c+Z*(d/2+.014),Z,min(.41,w*.50),.123,"cargo")
def pipe(path,r,mat,clamps=True):
    tube(path,r,mat,12)
    if clamps:
        for j in range(1,len(path)-1):
            a=v(path[j]);direction=(v(path[j+1])-a).normalized()
            rod(a+direction*r*.3,a+direction*r*.75,r*1.18,"Graphite_Alloy",10)
def hatch(c,n,w,h,tone):
    c=v(c);r,u,n=basis(n)
    rim(c,n,w,h,.25,w-.17,h-.17,.20,.13,"Graphite_Alloy")
    flat_round(c-n*.04,n,w-.15,h-.15,.19,tone)
    rim(c+n*.012,n,w-.11,h-.11,.23,w-.16,h-.16,.20,.032,"Structural_Galvanized")
    sign(c+u*h*.18,n,w*.53,.13,"service")
    rod(c-r*w*.31+u*.13,c-r*w*.31-u*.13,.019,"Titanium",10)
def drum(c,axis,span,r,paint):
    c=v(c);n=v(axis).normalized();rgt,up,n=basis(n)
    rod(c-n*span*.53,c+n*span*.53,r*.76,"Graphite_Alloy",24)
    for s in (-1,1):
        t=c+n*s*span*.52;rod(t-n*.068,t+n*.068,r,paint,32)
        torus(t+n*s*.072,n,r*.89,.027,"Structural_Galvanized",32,6)
        rod(t+n*s*.072,t+n*s*.19,r*.30,"Titanium",16)
        for j in range(6):
            d=rgt*math.cos(T*j/6)+up*math.sin(T*j/6)
            rod(t+n*s*.078+d*r*.61,t+n*s*.105+d*r*.61,.043,"Graphite_Alloy",8)
    for j in range(23):
        t=c+n*((j-11)*span*.041)
        torus(t,n,r*.78,.019,"Structural_Galvanized" if j%5 else "Graphite_Alloy",26,6)
def tank(c,r,h,mat):
    c=v(c);rod(c-Y*h/2,c+Y*h/2,r,mat,24)
    rod(c+Y*h/2,c+Y*(h/2+.18),r,"Structural_Galvanized",24,r2=r*.52)
    rod(c-Y*(h/2+.13),c-Y*h/2,r*.64,"Graphite_Alloy",20,r2=r)
    for y in (-.38,.0,.38):
        torus(c+Y*(y*h),Y,r+.015,.020,"Graphite_Alloy",28,6)
    rod(c+Y*(h/2+.16),c+Y*(h/2+.29),r*.20,"Titanium",12)
def stair(a,b,width,tone):
    a=v(a);b=v(b);horizontal=v((b.x-a.x,0,b.z-a.z));n=horizontal.normalized();right=Y.cross(n).normalized()
    count=max(3,round((b.y-a.y)/.205))
    for j in range(count):
        p=a+(b-a)*(j/count);strut(p-right*width/2,p+right*width/2,.101,horizontal.length/count*1.19,tone)
        # Steps use physical horizontal tread lips with a nonslip contrast edge.
        cube(p,(width,.072,horizontal.length/count*.91),"Tidal_Deck",.006) if abs(n.z)>.8 else cube(p,(horizontal.length/count*.91,.072,width),"Tidal_Deck",.006)
    for s in (-1,1):
        d=right*s*width/2;strut(a+d-Y*.18,b+d-Y*.18,.091,.18,"Graphite_Alloy")
        rails(a+d,b+d,.96,"Structural_Galvanized",tone)

collections={};roots={};actions={};lights={};display_positions={}
def group(bay,key,pivot=(0,0,0),anim=None):
    g=active(bay,bay+"_"+key,pivot)
    if anim:actions[g.id]=anim
    return g
def static(bay):
    global current
    current=groups[(bay,bay+"_static")]
def motion(kind,axis,amount,delay=0):
    return dict(kind=kind,axis=axis,amount=amount,clearAmount=amount,dockedAmount=0,phaseDelay=delay)
def light(bay,key,pos,target,color,power,size,exposure=1):
    entries=lights.setdefault(bay,[]);base=bay+"_"+key
    keyname=base if not any(q["id"]==base for q in entries) else base+"_"+str(len(entries))
    entries.append(dict(id=keyname,position=pos,target=target,color=color,
                                         power=power,size=size,exposure=exposure))
def gallery_booth(bay,c,n,w=4.6,h=2.65,d=2.45):
    c=v(c);r,u,n=basis(n);ground=bay=="anchor"
    wall="Marine_Primer" if ground else "Orbital_Porcelain";dark="Capture_Blue" if not ground else "Graphite_Alloy"
    # Front glazing remains open to light; the rails, slab, rake, inner screens and seats are separate solids.
    plate(c-u*h*.44,n,w+.28,h*.17,d,"Graphite_Alloy",.065)
    plate(c+u*h*.46,n,w+.37,h*.12,d+.27,wall,.055)
    plate(c-n*d*.45,n,w-.04,h-.26,.15,wall,.045)
    plate(c+n*d*.46-u*h*.276,n,w,.57,.13,wall,.029)
    for side in (-1,1):
        # Side returns are glazed above low console level, giving a genuine angled side view.
        pp=c+r*side*(w*.5-.04)
        endn=r*side
        rim(pp-endn*.011,endn,d+.025,h-.13,.085,d-.211,h*.58,.063,.115,wall,"Graphite_Alloy",center_offset=(0,.128))
        flat_round(pp-endn*.068+Y*.128,endn,d-.211,h*.58,.063,"Clear_Glass")
        sign(pp+endn*.008-Y*h*.33,endn,d*.48,.145,"hyd" if ground else "sensor")
        for ss in (-1,1):
            p=pp+n*ss*(d*.39);rod(p-u*h*.36,p+u*h*.40,.071,"Graphite_Alloy",10)
    for j in range(4):
        pp=c+r*((j-1.5)*w/4)+n*(d*.47)+u*.15
        rim(pp,n,w/4+.013,h*.57,.070,w/4-.083,h*.57-.097,.038,.047,dark)
        flat_round(pp-n*.017,n,w/4-.077,h*.57-.09,.040,"Clear_Glass")
    board=c+n*(d*.475)+u*(h*.446)
    sign(board,n,w*.83,.37,"dispatch" if ground else "arrival")
    lightbar(c+n*d*.38+u*h*.36,-Y,w*.76)
    # Raked MFD desk, lit status bank and dedicated comms post inside the booth.
    p=c+n*(d*.11)-u*.34
    plate(p,n,w*.86,.11,.82,"Carbon_Ceramic",.022)
    for j in (-1,0,1):
        pp=p+r*(j*w*.25)+u*.30+n*.03
        plate(pp,n,w*.215,.366,.066,"Graphite_Alloy",.014)
        print_face(pp+n*.035,n,w*.195,.292,("scada","anchor_screen" if ground else "aster_screen","oscilloscope")[j+1],True)
        rod(pp-u*.196,pp-u*.324,.019,"Titanium",8)
    for side in (-1,1):
        pp=c+r*side*w*.40-n*d*.29
        rack(pp,n,.45,1.46,"Carbon_Ceramic")
        s=c+r*side*w*.19-n*d*.21-Y*.54
        rod(s-Y*.55,s+Y*.063,.031,"Titanium",10);cube(s,(.36,.096,.35),"Graphite_Alloy",.035)
        plate(s+Y*.217-n*.17,n,.36,.43,.071,"Pressure_Fabric",.031)
    light(bay,"booth",trim(c+u*.96+n*.32),trim(c-u*.32),[1,.76,.50] if ground else [.52,.84,1],225,1.45)


def berth_installation(bay):
    ground=bay=="anchor";paint="Marine_Vermilion" if ground else "Capture_Blue"
    body="Marine_Primer" if ground else "Orbital_Porcelain"
    zarm=-3.15 if ground else -2.91
    for side,nm in ((-1,"port"),(1,"starboard")):
        pivot=v((side*4.88,1.22,zarm));static(bay)
        cube(pivot-Y*.71,(.63,1.38,.72),"Graphite_Alloy",.065)
        cube(pivot-Y*1.34,(.92,.17,.97),body,.029)
        for xx in (-.33,.33):
            for zz in (-.37,.37):rod(pivot+v((xx,-1.247,zz)),pivot+v((xx,-1.184,zz)),.043,"Structural_Galvanized",8)
        rod(pivot-Y*.17,pivot+Y*.19,.294,"Titanium",24)
        group(bay,"arm_"+nm,pivot,motion("rotate","y",side*-74,.055 if side>0 else 0))
        end=v((side*2.392,1.25,zarm));axis=(end-pivot).normalized()
        for z in (-.17,.17):
            strut(pivot+Z*z+Y*.126,end-axis*.26+Z*z*.50+Y*.125,.105,.14,paint,.015)
            strut(pivot+Z*z-Y*.14,end-axis*.26+Z*z*.50-Y*.052,.087,.103,body,.011)
        for k in range(5):
            a=pivot+axis*(.26+k*.387);b=a+axis*.344
            for z in (-.17,.17):
                rod(a+Z*z-Y*.105,b+Z*z+Y*.105,.036,"Graphite_Alloy",8)
        rod(pivot-Y*.24,pivot+Y*.23,.257,paint,24)
        rod(pivot+Y*.229,pivot+Y*.270,.189,"Graphite_Alloy",20)
        for j in range(8):
            pp=pivot+X*math.cos(T*j/8)*.201+Z*math.sin(T*j/8)*.201+Y*.23;rod(pp,pp+Y*.029,.020,"Titanium",8)
        shaft=pivot+axis*.559+Z*.227
        rod(shaft,shaft+axis*.731,.066,"Carbon_Ceramic",14)
        rod(shaft+axis*.65,end-axis*.48+Z*.171,.034,"Titanium",14)
        cube(end-axis*.12,(.232,.37,.306),"Graphite_Alloy",.03)
        cube(end,(.070,.299,.252),"Black_Rubber",.02)
        p=pivot+axis*.93+Y*.157
        print_face(p,Y,.42,.070,"hazard")
        lightbar(pivot+axis*1.61+Y*.10,Z,.28,"Amber_Emitter")
    static(bay)
    # The bellows sleeve meets the actual aft docking face, leaving the forward and side views free.
    cube((0,1.26,9.81),(3.16,2.9,.54),body,.109)
    rim((0,1.28,9.491),-Z,2.93,2.72,.361,1.80,2.06,.268,.143,"Graphite_Alloy")
    group(bay,"bridge",(0,1.29,5.93),motion("translate","z",2.42,.09))
    for j in range(9):
        zz=6.08+j*.13
        rim((0,1.29,zz),-Z,2.52,2.52,.334,1.85,2.015,.269,.070,
            "Graphite_Alloy" if j%2 else "Black_Rubber")
    rim((0,1.29,5.96),-Z,2.55,2.53,.355,1.81,2.005,.255,.091,"Structural_Galvanized")
    for s in (-1,1):
        cube((s*1.154,1.28,6.49),(.114,2.12,1.10),body,.027)
        cube((s*.995,1.28,6.49),(.036,1.74,.64),"Amber_Emitter",.008)
    # Overhead half-baffles leave a clear vertical flight shaft once released.
    shutter_y=8.50 if ground else 10.16
    for side,nm in ((-1,"port"),(1,"starboard")):
        piv=v((side*1.93,shutter_y,.0))
        group(bay,"shutter_"+nm,piv,motion("translate","x",side*3.83,.00 if side<0 else .045))
        for j in range(5):
            zz=(j-2)*2.541
            cube((piv.x,shutter_y,zz),(3.74,.161,2.498),body,.031)
            for off in (-1.36,-.66,0,.66,1.36):
                cube((piv.x+off,shutter_y-.122,zz),(.074,.148,2.41),"Graphite_Alloy",.008)
            lightbar((piv.x+side*1.57,shutter_y-.124,zz),-Y,1.37,"Opal_Emitter")
        for xx in (piv.x-1.73,piv.x+1.73):
            cube((xx,shutter_y+.093,0),(.12,.14,12.65),"Structural_Galvanized",.010)
    static(bay)
    dc=v((-5.15,1.22,-.85) if ground else (5.42,1.38,-.63))
    for ss in (-1,1):
        pp=dc+Z*ss*.89
        strut(pp-X*.59-Y*1.12,pp+Y*.05,.14,.18,body,.01)
        strut(pp+X*.59-Y*1.12,pp+Y*.05,.14,.18,body,.01)
    group(bay,"drum",dc,motion("rotate","z",284 if ground else 193,.04))
    drum(dc,Z,1.53,.69,paint)
    static(bay)
    bc=v((-3.86,2.05,-7.47) if ground else (-4.28,1.99,-7.91))
    rod(bc-Y*.364,bc,.066,"Graphite_Alloy",12)
    group(bay,"beacon",bc,motion("spin","y",360,0))
    rod(bc,bc+Y*.164,.093,"Carbon_Ceramic",16)
    rod(bc+Y*.111,bc+Y*.267,.079,"Amber_Emitter" if ground else "Blue_Emitter",16)
    plate(bc+Z*.072+Y*.187,Z,.149,.113,.04,"Graphite_Alloy",.013)
    static(bay)
    dp=v((-3.29,2.72,-7.84) if ground else (-3.72,2.72,-8.07))
    plate(dp-Z*.064,Z,.97,.48,.146,"Graphite_Alloy",.034)
    group(bay,"display",dp)
    print_face(dp+Z*.015,Z,.853,.378,"anchor_screen" if ground else "aster_screen",True)
    display_positions[bay]=trim(dp)


def anchor():
    bay="anchor";group(bay,"static")
    # Four wet maintenance galleries wrap the rectangular lift well. The front terrace opens onto the sea.
    deck(-8.57,0,.10,9.45,13.26,"Tidal_Deck");deck(8.43,0,.10,9.18,13.26,"Tidal_Deck")
    deck(0,0,-10.85,26.5,7.32,"Tidal_Deck");deck(0,0,9.88,26.5,5.12,"Tidal_Deck")
    for sx in (-1,1):
        grating(sx*3.528,-.015,.0,.756,13.25);rails((sx*3.17,-.01,-6.63),(sx*3.17,-.01,-4.72))
        rails((sx*3.17,-.01,-1.84),(sx*3.17,-.01,5.85),1.025)
        for z in (-6.22,-3.84,.1,4.18,6.40):
            strut((sx*3.22,-.207,z),(sx*4.32,-1.41,z),.115,.135,"Marine_Primer")
    grating(0,-.016,-6.928,25.9,.542,density=.17)
    for lo,hi in ((-12.4,-4.5),(-3.58,.72),(1.52,12.4)):
        rails((lo,-.01,-6.70),(hi,-.01,-6.70),.981,cap="Safety_Amber")
    for x in (-9.6,-4.0,4.0,9.6):
        for z in (-14.9,-6.83,6.85,12.45):
            cube((x,-3.16,z),(.76,6.14,.78),"Marine_Primer",.025)
            cube((x,-.47,z),(1.03,.39,1.07),"Graphite_Alloy",.028)
            if z<-4:
                strut((x,-.4,z),(x+1.31,-2.22,z),.165,.194,"Marine_Vermilion")
    # Tall skeletal marine portal cranes with inspectable gusset plates and transverse top rails.
    for sx in (-1,1):
        for z in (-13.1,-6.82,4.07,10.81):
            x=sx*(5.75 if z==-6.82 else 8.70)
            channel((x,-.16,z),(x,10.72,z),.49,.46,"Marine_Primer")
            for y in (1.31,3.52,6.61,9.36):
                cube((x,y,z),(.562,.153,.545),"Structural_Galvanized",.014)
            for h in (.26,3.52):
                plate((x,h,z+.252),Z,.67,.39,.037,"Marine_Vermilion",.015)
                for dx in (-.205,.205):
                    for dd in (-.102,.102):screw((x+dx,h+dd,z+.274),Z,.028,False)
            channel((x,9.64,z),(x-sx*1.48,10.53,z),.35,.40,"Marine_Primer")
            lightbar((x-sx*.12,3.16,z+.31),Z,.37)
        channel((sx*5.52,6.27,-14.05),(sx*5.52,6.27,11.20),.368,.477,"Graphite_Alloy")
        channel((sx*8.71,10.31,-17.31),(sx*8.71,10.31,12.9),.44,.51,"Marine_Primer")
        for j in range(6):
            z=-12.7+j*3.86
            strut((sx*8.70,6.60,z),(sx*8.70,9.96,z+3.72),.140,.17,"Structural_Galvanized")
        # Overhead maintenance pipe tray retains an open center above the lifting carriage.
        for k in range(3):
            xp=sx*(5.65+k*.29)
            pipe([(xp,5.66,-15.9),(xp,5.66,-7.23),(xp,5.72,-6.81),(xp,5.90,-6.37),(xp,5.90,9.10)],.077+k*.031,
                 ("Structural_Galvanized","Marine_Vermilion","Graphite_Alloy")[k])
    for z in (-14.45,-6.92,6.95,12.42):
        channel((-8.99,10.40,z),(8.99,10.40,z),.49,.52,"Marine_Primer")
        if z in (-14.45,12.42):
            channel((-8.80,8.98,z),(8.80,8.98,z),.27,.29,"Marine_Primer")
            for j in range(9):
                x=-8.65+j*1.92
                strut((x,9.08,z),(x+1.88,10.19,z),.103,.133,"Marine_Vermilion")
    # A suspended 16-ton bridge crane crosses the front yard; drums, sheaves and hook hang outside the climb envelope.
    for z in (-12.66,-11.81):
        channel((-9.12,6.19,z),(9.12,6.19,z),.29,.49,"Marine_Vermilion")
        for j in range(10):
            x=-8.74+j*1.88
            cube((x,6.19,z),(.077,.425,.31),"Graphite_Alloy")
    win=v((1.89,5.77,-12.20))
    cube(win,(1.78,.64,1.31),"Marine_Vermilion",.043)
    for off in (-.62,.62):
        for zo in (-.512,.512):rod(win+X*(off-.068)+Z*zo+Y*.327,win+X*(off+.068)+Z*zo+Y*.327,.20,"Graphite_Alloy",14)
    for dx in (-.22,.22):rod(win+X*dx-Y*.30,win+X*dx-Y*2.18,.017,"Structural_Galvanized",8)
    rod(win-X*.35-Y*2.2,win+X*.35-Y*2.2,.144,"Graphite_Alloy",16)
    tube([win-Y*2.24,win-Y*2.63,win+X*.19-Y*2.77,win+X*.36-Y*2.69,win+X*.39-Y*2.56],.048,"Safety_Amber",10)
    sign(win+Z*.672,Z,1.17,.275,"load")
    gallery_booth(bay,(-4.77,1.65,-10.33),Z,4.93,2.69,2.62)
    deck(-5.11,3.98,-9.99,6.51,4.49,"Tidal_Deck");rails((-8.12,3.98,-7.82),(-2.11,3.98,-7.82))
    stair((-8.24,.03,-5.35),(-8.24,3.98,-11.26),1.02,"Marine_Primer")
    for j in range(3):
        x=-11.48+j*1.17
        tank((x,1.78,-4.25),.433,2.93,"Structural_Galvanized" if j<2 else "Marine_Primer")
        pipe([(x,3.38,-4.25),(x,3.72,-4.25),(x,3.86,-4.47),(x,3.86,-6.51)],.065,"Marine_Vermilion")
    for j in range(4):
        rack((-6.204,1.14,1.69+j*.682),X,.63,1.74,"Marine_Primer")
    for j in range(3):
        off=(j-1)*.79;pp=(4.79+off,.53,-9.32)
        crate(pp,.74,1.02,.91);crate((pp[0],.46,-10.37),.74,.85,.88,"Marine_Vermilion")
    for j in range(3):
        tank((7.17+j*1.18,1.32,-11.03),.47,2.17,"Marine_Primer")
    # Far yard uses separate portal frames, real walkways and crane silhouettes in front of the open horizon.
    deck(-.14,-.32,-18.73,24.1,6.64,"Tidal_Deck")
    for x in (-10.21,-6.93,6.25,10.24):
        channel((x,-2.35,-21.06),(x,7.11,-21.06),.51,.53,"Marine_Primer")
        strut((x,4.68,-21.06),(x+(1.31 if x<0 else -1.31),6.96,-21.06),.26,.29,"Marine_Primer")
    channel((-10.56,7.10,-21.06),(10.56,7.10,-21.06),.61,.78,"Marine_Primer")
    sign((-1.09,6.92,-20.64),Z,6.72,1.30,"anchor")
    for z in (-17.84,-21.39):
        rails((-9.45,-.31,z),(9.45,-.31,z),.99,cap="Structural_Galvanized")
    for j in range(4):
        crate((-8.40+j*.975,.223,-18.42),.91,1.03,.93,"Marine_Primer")
    for sx in (-1,1):
        x=sx*13.2
        channel((x,0,-25.1),(x,15.81,-25.1),.69,.71,"Marine_Primer")
        for h in (3.5,7.1,10.8):
            strut((x,h,-25.1),(x+sx*1.75,h+3.41,-26.14),.20,.25,"Structural_Galvanized")
        rod((x,13.9,-25.1),(x-sx*7.6,17.84,-27.5),.207,"Marine_Vermilion",9)
        rod((x-sx*7.6,17.84,-27.5),(x-sx*7.6,13.14,-27.5),.029,"Graphite_Alloy",8)
    sign((-4.94,.74,-7.30),Z,1.08,.27,"launch");sign((-5.47,3.74,-6.56),Z,1.34,.52,"number")
    sign((6.75,2.77,-8.02),Z,1.30,.317,"pump")
    for j in (-1,1):
        light(bay,"front_key"+str(j),[j*4.83,4.78,-7.1],[j*1.20,.82,-3.93],[1.0,.70,.46],620,2.1)
    light(bay,"sea_portal",[-5.88,4.80,-16.0],[1.4,.92,-3.5],[1,.76,.55],1300,4.9)
    berth_installation(bay)


def outer_anchor():
    bay="anchor";group(bay,"apron")
    cement="Pier_Concrete" if "Pier_Concrete" in meta else "Tidal_Deck"
    for side in (-1,1):
        cube((side*10.42,-4.45,-11.0),(13.75,5.12,40.2),cement,.52)
    cube((0,-4.45,-19.03),(7.45,5.12,24.12),cement,.42)
    cube((0,-4.45,9.80),(7.45,5.12,5.21),cement,.40)
    # A real central well remains open in the visible build above the caisson.
    for s in (-1,1):
        deck(s*15.04,-.655,-10.2,6.94,37.9,"Tidal_Deck")
        rails((s*18.37,-.65,-27.99),(s*18.37,-.65,8.1),1.01,cap="Safety_Amber")
        for z in (-25,-13,-2,6.5):
            cube((s*17.58,-3.39,z),(1.56,5.62,1.00),"Marine_Primer",.16)
            for h in (-5.47,-4.43):rod((s*18.40,h,z-.39),(s*18.40,h,z+.39),.45,"Black_Rubber",16)
    deck(0,-.655,-28.52,36.4,7.05,"Tidal_Deck")
    for sx in (-1,1):
        x=sx*9.42;z=-27.22
        cube((x,.786,z),(4.29,2.79,3.08),"Marine_Primer",.084)
        cube((x,2.20,z),(4.58,.142,3.30),"Structural_Galvanized",.025)
        for j in range(14):
            xx=x+(j-6.5)*.282
            cube((xx,.76,z+1.571),(.057,2.38,.052),"Graphite_Alloy",.007)
        sign((x,.985,z+1.61),Z,1.55,.384,"tower" if sx<0 else "service")
        for xx in (-.96,.96):
            rod((x+xx,2.29,z),(x+xx,2.66,z),.265,"Titanium",18)
    # Moored work tender at the sea datum (-7 m). Hull sections taper to a true bow.
    boat=v((-22.4,-6.58,-18.8));rows=[]
    for zz,ww,hh in ((-3.1,.07,.56),(-2.63,.84,.57),(-1.79,1.14,.58),(.8,1.22,.56),(2.67,1.03,.49),(2.95,.91,.46)):
        rows.append([boat+v((xx,yy,zz)) for xx,yy in ((-ww,hh),(-ww*.8,-.13),(0,-.59),(ww*.8,-.13),(ww,hh))])
    for aa,bb in zip(rows,rows[1:]):
        for k in range(4):face([aa[k],aa[k+1],bb[k+1],bb[k]],"Marine_Vermilion")
        face([aa[0],bb[0],bb[-1],aa[-1]],"Tidal_Deck",Y)
    for ss in (-1,1):
        tube([row[0 if ss<0 else -1] for row in rows],.070,"Black_Rubber",10)
    cube(boat+v((0,1.04,.248)),(1.51,1.05,1.50),"Orbital_Porcelain",.093)
    plate(boat+v((0,1.19,-.535)),-Z,1.28,.444,.055,"Smoked_Display",.022)
    for s in (-1,1):
        plate(boat+v((s*.78,1.18,.252)),X*s,1.17,.423,.045,"Smoked_Display",.016)
    rod(boat+Y*1.57,boat+Y*2.45,.037,"Titanium",8)
    rod(boat+Y*2.35-X*.55,boat+Y*2.35+X*.55,.039,"Ceramic_Pearl",8)
    for z in (-2.11,2.18):
        tube([boat+v((1.045,.58,z)),(-20.2,-6.10,boat.z+z),(-18.20,-2.52,boat.z+z*.88)],.029,"Aramid_Webbing",8)


def aster():
    bay="aster";group(bay,"static")
    for side in (-1,1):
        deck(side*7.72,.03,.14,8.83,13.35,"Composite_Slate","Carbon_Ceramic")
        deck(side*9.48,4.44,-2.08,4.51,14.09,"Orbital_Porcelain","Graphite_Alloy")
        rails((side*7.29,4.44,-9.09),(side*7.29,4.44,4.89),1.00,"Titanium","Capture_Blue")
        grating(side*3.27,.029,.01,.54,13.32,"Graphite_Alloy",.125)
        for z in (-6.63,-1.94,3.46):
            rails((side*3.01,.028,z),(side*3.01,.028,z+1.70),.972,"Titanium","Capture_Blue")
    deck(0,.03,-11.11,24.28,7.61,"Orbital_Porcelain");deck(0,.03,10.86,24.28,7.32,"Composite_Slate")
    grating(0,.028,-6.94,23.93,.707,"Graphite_Alloy",.168)
    for lo,hi in ((-11.8,-5.10),(-4.18,-.53),(.73,5.33),(6.28,11.82)):
        rails((lo,.03,-6.63),(hi,.03,-6.63),.986,"Titanium","Capture_Blue")
    # Structural compression hoops: three clear apertures with different spans and offsets.
    for ix,(zz,w,h,y,x) in enumerate(((-9.03,12.75,8.17,3.50,0),(-16.28,11.26,7.20,3.33,.62),(-24.70,10.18,6.21,3.04,1.06))):
        c=v((x,y,zz))
        rim(c,Z,w,h,1.60,w-1.16,h-.94,1.22,.57,"Orbital_Porcelain","Capture_Blue")
        rim(c+Z*.061,Z,w-.39,h-.35,1.40,w-.56,h-.54,1.32,.132,"Titanium")
        rim(c+Z*.015,Z,w-1.05,h-.832,1.255,w-1.19,h-.977,1.20,.224,"Graphite_Alloy")
        for s in (-1,1):
            xline=x+s*(w*.5-.35)
            for ht in (1.07,2.39,3.71,5.00):
                pp=v((xline,ht,zz+.097))
                plate(pp,Z,.245,.44,.069,"Graphite_Alloy",.023)
                screw(pp+Z*.041,Z,.039,False)
            for vy in (1.15,3.35):
                lightbar((xline-s*.31,vy,zz+.019),X*-s,.70,"Blue_Emitter")
        plate((x,y+h*.5-.31,zz+.112),Z,3.73,.514,.069,"Graphite_Alloy",.022)
        print_face((x,y+h*.5-.31,zz+.152),Z,3.54,.437,"aster" if ix==0 else "transfer" if ix==1 else "orbit")
        # Longitudinal physical stringers and polished clips carry the eyes to the distant habitat.
        if ix<2:
            for s in (-1,1):
                channel((x+s*(w*.5-.57),.34,zz-.55),(x+s*(w*.5-.94),.34,zz-6.90),.38,.31,"Capture_Blue")
    # Piers under the capture room: arriving passenger sees layers at +180m and through the underside.
    for sx in (-1,1):
        for zz in (-12.20,-6.63,.74,7.52,12.88):
            xp=sx*(5.68 if zz==-6.63 else 8.03)
            cube((xp,4.51,zz),(.47,11.52,.70),"Orbital_Porcelain",.067)
            cube((xp,-2.74,zz),(.71,3.14,.83),"Capture_Blue",.071)
            for ht in (-3.38,-1.36,2.61,6.55,9.43):
                cube((xp,ht,zz),(.576,.166,.798),"Titanium",.016)
            strut((xp,-4.14,zz),(xp-sx*1.35,-.14,zz-.20),.27,.39,"Graphite_Alloy",.031)
            strut((xp,7.43,zz),(xp-sx*1.57,9.47,zz),.27,.41,"Orbital_Porcelain",.038)
        # Inboard thermal risers with insulation sleeves, crossover elbows and cast brackets.
        for j in range(4):
            xp=sx*(5.53+j*.19)
            pipe([(xp,4.14,-14.73),(xp,4.14,-7.21),(xp,4.07,-6.76),(xp,3.82,-6.26),
                  (xp,3.82,7.21),(xp,4.06,7.72),(xp,4.06,10.93)],.057+j*.011,
                 ("Titanium","Capture_Blue","Structural_Galvanized","Graphite_Alloy")[j])
        for z in (-12,-7.3,-1.7,4.67,9.90):
            lightbar((sx*5.15,5.65,z),X*-sx,1.18,"Opal_Emitter")
    gallery_booth(bay,(-7.20,1.91,-2.99),X,5.39,2.87,2.21)
    gallery_booth(bay,(-4.68,4.73,-13.60),Z,3.39,2.13,1.97)
    for j in range(4):
        rack((5.63+.03*j,1.19,-2.57+j*.701),-X,.64,1.91,"Orbital_Porcelain","aster_screen")
    stair((9.63,.05,-5.19),(9.63,4.43,1.64),1.17,"Capture_Blue")
    for j in range(3):
        tank((6.81+j*1.10,1.54,-11.18),.438,2.66,"Orbital_Porcelain")
        pipe([(6.81+j*1.10,2.88,-11.18),(6.81+j*1.10,3.14,-11.18),
              (6.81+j*1.10,3.25,-11.46),(6.81+j*1.10,3.25,-14.47)],.063,"Titanium")
    # Suspended pressure galleries join the far portal. Their interiors contain desks, access panels and lit cassettes.
    for side in (-1,1):
        xp=side*6.00
        deck(xp,-.08,-20.55,4.30,13.66,"Composite_Slate")
        deck(xp,3.86,-20.55,3.32,12.94,"Orbital_Porcelain")
        rails((xp-side*1.58,3.87,-26.43),(xp-side*1.58,3.87,-14.29),.99,"Titanium","Capture_Blue")
        for zz in (-17.74,-20.49,-23.29,-26.21):
            cube((xp+side*.99,1.93,zz),(.214,3.91,.256),"Orbital_Porcelain",.022)
            rack((xp+side*.98,1.15,zz-.50),X*-side,.53,1.71,"Capture_Blue")
    hatch((-4.36,1.37,-16.95),Z,1.60,2.49,"Orbital_Porcelain")
    hatch((5.02,1.35,-17.06),Z,1.62,2.51,"Orbital_Porcelain")
    deck(1.02,-.08,-26.28,8.17,4.01,"Orbital_Porcelain")
    sign((-3.88,.77,-7.24),Z,1.04,.30,"dock")
    sign((5.20,3.04,-7.01),Z,1.95,.54,"vac")
    for j in (-1,1):
        light(bay,"capture_key"+str(j),[j*4.93,3.91,-7.84],[j*.75,.89,-3.64],[.62,.83,1],510,2.11)
    light(bay,"gallery",[-4.8,4.74,-10.9],[.65,1.17,-3.98],[1,.78,.55],670,2.43)
    berth_installation(bay)


def inboard_galleries():
    # The carriage windows see this lower working layer at human eye level. The
    # upper cranes and deep portals remain visible while the car leaves its cradle.
    static("anchor")
    deck(1.90,2.94,-13.58,8.47,2.02,"Tidal_Deck")
    for x in (-2.1,.03,2.27,4.47,5.92):
        channel((x,.035,-13.73),(x,2.81,-13.73),.17,.22,"Marine_Primer")
        strut((x,1.99,-13.72),(x,2.82,-12.75),.095,.112,"Marine_Vermilion")
    rails((-2.13,2.94,-12.62),(5.92,2.94,-12.62),.97,cap="Safety_Amber")
    for xx in (-1.42,.52,2.46,4.40):
        cube((xx,2.703,-12.604),(1.87,.363,.114),"Marine_Primer",.013)
        lightbar((xx,2.488,-12.629),Z,.97)
    sign((1.01,3.040,-12.49),Z,4.24,.71,"anchor")
    for j in range(4):rack((2.60+j*.72,1.24,-13.87),Z,.65,1.75,"Marine_Primer")
    for j in range(2):
        tank((-.92+j*.87,1.22,-13.98),.291,1.89,"Structural_Galvanized")
    for j in range(3):
        zz=-4.87+j*.86;rack((-7.96,1.67,zz),X,.76,1.82,"Marine_Primer")
    cube((-8.26,2.85,-3.98),(.89,.21,3.63),"Marine_Vermilion",.026)
    sign((-7.753,2.534,-3.71),X,1.65,.348,"pump")
    for j in range(3):
        zz=-3.0+j*.22
        pipe([(-7.02,.23,zz),(-7.02,1.86,zz),(-7.05,2.13,zz),(-7.19,2.29,zz),
              (-7.72,2.29,zz)],.073,"Structural_Galvanized" if j<2 else "Marine_Vermilion")
    # Both keys have modeled flood housings at the exact points the runtimes use.
    for bay in ("anchor","aster"):
        static(bay)
        for point in lights[bay]:
            if not ("key" in point["id"] or "portal" in point["id"] or "gallery" in point["id"]):continue
            c=v(point["position"]);n=(v(point["target"])-c).normalized()
            plate(c-n*.125,n,.72,.436,.25,"Graphite_Alloy",.037)
            plate(c+n*.010,n,.606,.32,.015,"Opal_Emitter" if bay=="anchor" else "Blue_Emitter",.008)
            r,u,n=basis(n)
            for i in range(6):
                plate(c+n*.030+r*((i-2.5)*.091),n,.012,.31,.012,"Titanium")
    static("aster")
    # A suspended arrivals gallery bridges only the left portion of the portal.
    # Human-scale windows and an access door distinguish it from the heavy structural annulus.
    deck(-3.13,3.56,-13.80,3.18,1.91,"Composite_Slate")
    for xx in (-4.61,-3.55,-2.55,-1.64):
        cube((xx,1.769,-13.92),(.21,3.48,.28),"Capture_Blue",.015)
        rod((xx,3.58,-13.45),(xx,5.98,-13.45),.067,"Titanium",12)
    rails((-4.61,3.56,-12.90),(-1.64,3.56,-12.90),.96,"Titanium","Capture_Blue")
    sign((-3.12,3.74,-12.80),Z,2.93,.61,"aster",True)
    for j in range(3):
        xx=-4.18+j*.88;p=v((xx,1.50,-14.11))
        rim(p,Z,.882,1.84,.120,.771,1.692,.090,.095,"Orbital_Porcelain","Graphite_Alloy")
        flat_round(p-Z*.030,Z,.775,1.699,.090,"Clear_Glass")
        rack(p-Z*.57-Y*.08,Z,.608,1.27,"Orbital_Porcelain","aster_screen" if j==0 else "scada")
        for jy in (-.36,.37):
            plate(p-Z*.41+X*.256+Y*jy,Z,.119,.305,.052,"Capture_Blue",.013)
            for ix in (-1,1):plate(p-Z*.376+X*(.256+ix*.025)+Y*jy,Z,.015,.141,.009,"Amber_Emitter" if jy>0 else "Opal_Emitter")
    for side in (-1,1):
        for z in (-11.3,-7.85):
            xp=side*4.95;dc=v((xp,2.513,z))
            plate(dc,Z,.418,1.06,.23,"Orbital_Porcelain",.046)
            for j in range(3):pushpos=dc+Y*((j-1)*.245)+Z*.126;plate(pushpos,Z,.232,.121,.027,"Blue_Emitter" if j==1 else "Capture_Blue",.008)


def formed_bays():
    # A curved compression member is built from two continuous flanges and a
    # web with real clearance down the middle. Bolt groups sit at the splices.
    def crescent(center,n,r0,start,end,width,depth,body,edge):
        center=v(center);r,u,n=basis(n)
        for offset,th,mat in ((-width*.35,width*.30,edge),(0,width*.47,body),(width*.35,width*.30,edge)):
            rad=r0+offset;count=40
            for j in range(count):
                a=start+(end-start)*j/count;b=start+(end-start)*(j+1)/count
                d0=r*math.cos(a)+u*math.sin(a);d1=r*math.cos(b)+u*math.sin(b)
                z0=0 if offset else -depth*.23;z1=depth if offset else depth*.76
                corners=[center+d0*(rad-th*.5)+n*z1,center+d1*(rad-th*.5)+n*z1,
                         center+d1*(rad+th*.5)+n*z1,center+d0*(rad+th*.5)+n*z1]
                face(corners,mat,n)
                for side,nb in ((th*.5,d0+d1),(-th*.5,-d0-d1)):
                    face([center+d0*(rad+side)+n*z0,center+d1*(rad+side)+n*z0,
                          center+d1*(rad+side)+n*z1,center+d0*(rad+side)+n*z1],mat,nb)
                if j%5==0 and offset:
                    c=center+d0*rad+n*z1;rod(c,c+n*.023,.037,"Titanium",8)
    static("anchor")
    # Curved loading rail and hydraulic lifting shoe framing the wet forecourt.
    c=v((3.54,1.62,-12.04));crescent(c,Z,1.21,-.54,2.75,.252,.303,"Marine_Vermilion","Marine_Primer")
    for t in (.02,.64,1.31,2.09):
        d=X*math.cos(t)+Y*math.sin(t);pp=c+d*1.09
        rod(pp-Z*.07,pp+Z*.27,.131,"Graphite_Alloy",16)
        rod(pp+Z*.26,pp+Z*.30,.070,"Titanium",12)
        for k in range(4):
            e=X*math.cos(T*k/4)+Y*math.sin(T*k/4)
            screw(pp+Z*.31+e*.047,Z,.010,False)
    for j in range(4):
        cp=v((3.32+j*.34,.61,-11.879))
        tank(cp,.142,.69,"Marine_Vermilion" if j%2 else "Structural_Galvanized")
        pipe([cp+Y*.46,cp+Y*.69,cp+v((-.06,.79,0)),cp+v((-.16,.83,-.03))],.032,"Titanium")
    # An exposed inspection station behind the west glazing creates proper side depth.
    for z in (-4.29,-3.55):
        cb=v((-7.03,1.52,z))
        rod(cb-X*.095,cb+X*.21,.232,"Marine_Primer",24)
        torus(cb+X*.223,X,.156,.022,"Marine_Vermilion",26,7)
        for k in range(3):
            d=Y*math.cos(T*k/3)+Z*math.sin(T*k/3)
            rod(cb+X*.227,cb+X*.227+d*.14,.015,"Structural_Galvanized",8)
    static("aster")
    # A tilted, calibrated capture yoke is visible at eye level through the forward laminate.
    # The crescent's empty center reveals the illuminated instruments one gallery beyond.
    c=v((2.30,1.74,-11.99));n=v((-.19,.075,1)).normalized();r,u,n=basis(n)
    crescent(c,n,1.25,-.76,3.90,.264,.258,"Capture_Blue","Orbital_Porcelain")
    crescent(c+n*.297,n,1.179,-.75,3.91,.066,.057,"Titanium","Graphite_Alloy")
    for k in range(7):
        a=-.65+k*.718;d=r*math.cos(a)+u*math.sin(a);ta=-r*math.sin(a)+u*math.cos(a)
        pp=c+d*1.16+n*.228;rod(pp-ta*.103,pp+ta*.103,.068,"Graphite_Alloy",14)
        rod(pp-d*.054,pp-d*.188,.042,"Titanium",12);plate(pp+n*.067,n,.088,.026,.012,"Blue_Emitter" if k%3 else "Amber_Emitter",.003)
    for s in (-1,1):
        base=c+r*s*.79-Y*1.47;strut(base,c+r*s*1.07-Y*.73,.16,.235,"Capture_Blue",.023)
        cube(base,(.36,.16,.40),"Titanium",.024)
    for j in range(3):
        x=4.04+j*.62;rack((x,1.46,-14.37),Z,.55,1.51,"Orbital_Porcelain","scada")
    lx=(2.96,2.72,-12.79);lightbar(lx,-Y,1.39,"Blue_Emitter")
    light("aster","optics_bench",lx,[2.46,1.20,-13.65],[.43,.73,1],168,1.23)


def approach_throat():
    static("aster")
    # The transit axis is vertical. No floor or end plate spans the capsule
    # envelope. Four flared capture guides silhouette the interior of the vault.
    courses=((-10.8,10.52,19.38,2.31),(-6.64,9.12,17.72,1.96),(-3.14,8.05,16.23,1.62),(-.52,7.19,14.75,1.31))
    for ix,(y,w,d,rr) in enumerate(courses):
        c=v((0,y,0));n=-Y
        rim(c,n,w,d,rr,w-.43,d-.43,rr-.16,.34,"Orbital_Porcelain","Capture_Blue")
        rim(c-Y*.055,n,w-.092,d-.092,rr-.046,w-.163,d-.163,rr-.07,.065,"Titanium")
        rim(c-Y*.041,n,w-.345,d-.345,rr-.130,w-.425,d-.425,rr-.16,.057,"Graphite_Alloy")
        # Bay-index lights are geometrically interrupted by clamps, not one uniform neon tube.
        for side in (-1,1):
            xx=side*(w*.5-.114)
            for z in (-d*.28,-d*.12,d*.12,d*.28):
                pp=v((xx,y-.071,z));plate(pp,-Y,.130,1.24,.038,"Graphite_Alloy",.012)
                plate(pp-Y*.022,-Y,.079,1.03,.010,"Blue_Emitter" if side>0 else "Amber_Emitter",.004)
            for x in (-w*.19,w*.19):
                pos=v((x,y-.075,side*(d*.5-.118)))
                plate(pos,-Y,1.056,.157,.061,"Capture_Blue",.013)
                plate(pos-Y*.034,-Y,.80,.076,.014,"Opal_Emitter",.003)
        # Actual tapering meridians and diagonal cross-braces carry shear between the hoops.
        if ix<len(courses)-1:
            upper,w1,d1,r1=courses[ix+1]
            for side in (-1,1):
                for zfrac in (-.351,-.148,.148,.351):
                    a=v((side*(w*.5-.13),y+.21,d*zfrac));b=v((side*(w1*.5-.13),upper+.13,d1*zfrac))
                    strut(a,b,.182,.151,"Titanium",.014)
                    strut(a+X*side*.12,b+X*side*.12+Z*(.78 if zfrac<0 else -.78),.079,.115,"Capture_Blue",.008)
                    for p in (a,b):
                        rod(p-Z*.147,p+Z*.147,.089,"Graphite_Alloy",10)
                for xfrac in (-.30,.30):
                    a=v((w*xfrac,y+.16,side*(d*.5-.13)));b=v((w1*xfrac,upper+.11,side*(d1*.5-.13)))
                    strut(a,b,.161,.193,"Orbital_Porcelain",.019)
            if ix==0:
                for sx in (-1,1):
                    p=v((sx*3.45,y-.13,-8.71))
                    plate(p,-Y,1.45,.65,.086,"Capture_Blue",.034)
                    print_face(p-Y*.046,-Y,1.32,.50,"dock")
    # Removable underside fairings, castellated ties and service points keep the
    # underside legible on final approach. All panels lie outside the open bore.
    for sx in (-1,1):
        for j in range(7):
            z=-5.85+j*1.93;xp=sx*4.82
            plate((xp,-.235,z),-Y,2.30,1.69,.083,"Graphite_Alloy",.028)
            plate((xp,-.283,z),-Y,2.12,1.48,.025,"Orbital_Porcelain",.012)
            for ox in (-.76,.76):
                for oz in (-.51,.51):screw((xp+ox,-.303,z+oz),-Y,.031,False)
            cube((xp,-.418,z+.16),(1.22,.25,.102),"Capture_Blue",.021)
            for k in range(4):
                cube((xp+(k-1.5)*.225,-.356,z-.209),(.067,.105,.332),"Titanium",.009)
        for zz in (-7.99,8.11):
            for j in range(3):
                x=1.36+j*1.58;cp=v((sx*x,-.313,zz))
                plate(cp,-Y,1.374,1.03,.127,"Graphite_Alloy",.028)
                plate(cp-Y*.077,-Y,1.246,.934,.044,"Orbital_Porcelain",.017)
                print_face(cp-Y*.101,-Y,.65,.177,"sensor" if j%2 else "dock")
    for k,(x,z) in enumerate(((-3.88,-6.44),(3.88,-6.44),(-3.88,6.44),(3.88,6.44),(0,-7.88),(0,7.88))):
        c=v((x,-1.27,z));target=v((x*.53,-8.0,z*.48));n=(target-c).normalized()
        plate(c-n*.12,n,.69,.47,.249,"Graphite_Alloy",.035)
        plate(c+n*.011,n,.566,.341,.015,"Blue_Emitter" if k in (0,2) else "Opal_Emitter",.006)
        light("aster","underdeck_"+str(k),trim(c),trim(target),[.54,.77,1] if k%2==0 else [1,.76,.55],610,1.36)
    # Lower entry target uses a physically luminous real-space ring and remains out of the pass-through.
    for sx in (-1,1):
        c=v((sx*4.99,-10.98,-2.48));torus(c,-Y,.263,.034,"Opal_Emitter",28,8)
        for j in range(4):
            d=X*math.cos(T*j/4)+Z*math.sin(T*j/4);rod(c+d*.25,c+d*.36,.017,"Titanium",8)


anchor();outer_anchor();aster();inboard_galleries();formed_bays();approach_throat()
exec(compile((ROOT/"source"/"waterfront.py").read_text(),str(ROOT/"source"/"waterfront.py"),"exec"))


def room_tree(bay):
    vv=[];ff=[]
    for g in groups.values():
        if g.room!=bay or g.id not in (bay+"_static",bay+"_apron"):continue
        offset=len(vv);vv.extend(g.verts)
        for ix,q in enumerate(g.faces):
            if g.matlist[g.ids[ix]]=="Clear_Glass":continue
            ff.append(tuple(i+offset for i in q))
    return BVHTree.FromPolygons(vv,ff,all_triangles=False)
def bake_contact(g,tree):
    values=[];cache={}
    for p,n in zip(g.verts,g.normals):
        k=(round(p.x*21),round(p.y*21),round(p.z*21),round(n.x*3),round(n.y*3),round(n.z*3))
        occ=cache.get(k)
        if occ is None:
            r,u,n=basis(n);origin=p+n*.006;dark=0
            for direction,weight in ((n,.24),((n*.61+r*.80).normalized(),.19),((n*.61-r*.80).normalized(),.19),
                                     ((n*.61+u*.80).normalized(),.19),((n*.61-u*.80).normalized(),.19)):
                hit,_,_,dist=tree.ray_cast(origin,direction,1.36)
                if hit is not None:dark+=weight*(1-dist/1.36)**1.64
            occ=.985-.58*dark;cache[k]=occ
        values.extend((occ,occ,min(1,occ+(1-occ)*.036),1))
    return values
def reusable_mesh(bay,g,tree):
    mesh=bpy.data.meshes.new(g.id+" geometry")
    mesh.from_pydata([bl(q-g.pivot) for q in g.verts],[],g.faces,shade_flat=False)
    for m in g.matlist:
        mat=bpy.data.materials.get(m)
        if mat is None and m in metadata:mat=material(m,metadata[m])
        if mat is None:raise ValueError("Missing finish "+m+" on "+g.id)
        mesh.materials.append(mat)
    mesh.polygons.foreach_set('material_index',g.ids)
    uv=mesh.uv_layers.new(name="Physical UV");uv.uv.foreach_set("vector",[i for p in g.uv for i in p])
    mesh.normals_split_custom_set([bl(q) for q in g.normals])
    col=mesh.color_attributes.new(name="Contact_Occlusion",type="BYTE_COLOR",domain="POINT")
    col.data.foreach_set("color",bake_contact(g,tree));mesh.color_attributes.active_color=col
    mesh.update()
    ob=bpy.data.objects.new(g.id,mesh);collections[bay].objects.link(ob);ob.parent=roots[bay];ob.location=bl(g.pivot)
    g.object=ob;return ob
def clean_station(bay):
    name="Terminal · "+bay.capitalize();old=bpy.data.collections.get(name)
    if old:
        for o in list(old.objects):
            data=o.data;bpy.data.objects.remove(o,do_unlink=True)
            if data and data.users==0:
                if isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)
                elif isinstance(data,bpy.types.Light):bpy.data.lights.remove(data)
        bpy.data.collections.remove(old)
    co=bpy.data.collections.new(name);scene.collection.children.link(co);collections[bay]=co
    root=bpy.data.objects.new(bay,None);co.objects.link(root);root.empty_display_size=.30;roots[bay]=root
def interpolate_linear(obj):
    ac=obj.animation_data.action if obj.animation_data else None
    if not ac:return
    for layer in ac.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for kp in curve.keyframe_points:kp.interpolation="LINEAR"


manifest={"basis":"glTF metres: +X starboard, +Y up, +Z aft","stations":{},"parts":[]}
for bay in ("anchor","aster"):
    clean_station(bay);tree=room_tree(bay);station_groups=[g for g in groups.values() if g.room==bay]
    desc={"file":bay+".glb","waterline":-7 if bay=="anchor" else None,
          "bounds":[[round(min(g.lo[k] for g in station_groups),4) for k in range(3)],[round(max(g.hi[k] for g in station_groups),4) for k in range(3)]],
          "motions":[],"lights":lights[bay],"display":bay+"_display","displayCenter":display_positions[bay],
          "parts":[]}
    manifest["stations"][bay]=desc
    for g in station_groups:
        ob=reusable_mesh(bay,g,tree);key=g.id[len(bay)+1:]
        file=bay+"/"+key+".fbx"
        entry={"id":g.id,"room":bay,"station":bay,"node":g.id,"file":file,"webPivot":trim(g.pivot),"webBounds":current_bounds(g),
               "localBounds":[trim(v(g.lo)-g.pivot),trim(v(g.hi)-g.pivot)],"webCenter":trim((v(g.lo)+v(g.hi))*.5),
               "localReferenceVertex":trim(g.verts[0]-g.pivot)}
        a=actions.get(g.id)
        if a:
            channel=key.partition("_")[0];desc["motions"].append(dict(node=g.id,channel=channel,**a))
            entry["animation"]=a
        desc["parts"].append(entry);manifest["parts"].append(entry)
    del tree
    if globals().get("TERMINAL_EMBED_ONLY"):continue
    dest=UNITY/bay;dest.mkdir(exist_ok=True)
    for g in station_groups:
        key=g.id[len(bay)+1:];temp=bpy.data.objects.new("SM_"+g.id,g.object.data);collections[bay].objects.link(temp)
        select([temp])
        bpy.ops.export_scene.fbx(filepath=str(dest/(key+".fbx")),use_selection=True,axis_forward="-Z",axis_up="Y",object_types={"MESH"},
            bake_space_transform=True,bake_anim=False,apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
            colors_type="LINEAR",path_mode="RELATIVE",use_triangles=True)
        bpy.data.objects.remove(temp,do_unlink=True)
    select([roots[bay]]+[g.object for g in station_groups])
    bpy.ops.export_scene.gltf(filepath=str(WEB/(bay+".glb")),export_format="GLB",use_selection=True,
        export_extras=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False,
        export_vertex_color="ACTIVE",export_image_format="AUTO",export_image_quality=84,export_materials="EXPORT",
        export_normals=True,export_texcoords=True,export_tangents=False)
    print("STATION EXPORT",bay,desc["bounds"],len(station_groups),flush=True)
if not globals().get("TERMINAL_EMBED_ONLY"):
    for folder in (WEB,UNITY):(folder/"layout.json").write_text(json.dumps(manifest,indent=2))
for bay in ("anchor","aster"):
    for item in lights[bay]:
        ld=bpy.data.lights.new(item["id"],"AREA");ld.shape="RECTANGLE";ld.size=item["size"];ld.size_y=item["size"]*.55
        ld.energy=item["power"];ld.color=item["color"]
        ob=bpy.data.objects.new(item["id"],ld);collections[bay].objects.link(ob);ob.parent=roots[bay];ob.location=bl(item["position"])
        ob.rotation_euler=(v(bl(item["target"]))-ob.location).to_track_quat("-Z","Y").to_euler()
    root=roots[bay]
    # Native animation is the same six-minute journey, played in 270 preview frames.
    import runpy
    flight=runpy.run_path(str(ROOT/"source"/"ascent_geometry.py"));frame=flight["frame_at"]
    for t in range(361):
        altitude=flight["height"](t);dy=(-altitude if bay=="anchor" else 35786-altitude)*1000
        root.location=bl((0,dy,0));root.keyframe_insert("location",frame=frame(t))
    interpolate_linear(root)
    for g in [g for g in groups.values() if g.room==bay and g.id in actions]:
        a=actions[g.id];obj=g.object;ax=a["axis"];delay=a["phaseDelay"]
        keys=((0,0),(3+delay*8,0),(9+delay*8,1),(360,1)) if bay=="anchor" else ((0,1),(350+delay*12,1),(359.5,0),(360,0))
        for sec,state in keys:
            if a["kind"]=="translate":
                dir={"x":X,"y":Y,"z":Z}[ax];obj.location=bl(g.pivot+dir*a["amount"]*state);prop="location"
            else:
                idx,sign=(0,1) if ax=="x" else (2,1) if ax=="y" else (1,-1)
                obj.rotation_euler[idx]=math.radians(a["amount"]*(state if a["kind"]!="spin" else sec/3)*sign);prop="rotation_euler"
            obj.keyframe_insert(prop,frame=frame(sec))
        interpolate_linear(obj)
for t,key in ((0,"Pelagic Anchor · departure bay"),(9,"Shaft release"),(339,"Capture approach"),(360,"Aster Reach · hard dock")):
    marker=scene.timeline_markers.get(key) or scene.timeline_markers.new(key);marker.frame=round(frame(t))
axis_target=bpy.data.objects.get("Aster Reach · receiving axis")
if axis_target:
    axis_target.parent=roots["aster"];axis_target.location=bl((0,3.41,0))
scene.frame_set(88)
select([scene.camera])
if not globals().get("TERMINAL_EMBED_ONLY"):
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"blender"/"Upwell.blend"),compress=True)
