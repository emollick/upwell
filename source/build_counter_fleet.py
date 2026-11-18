"""Two purpose-built non-passenger vehicles on the measured CounterCar bogie.

Blender -b --python upwell/source/build_counter_fleet.py -- --preview
Geometry is built in glTF metres with +Y along the cable and the guide at -X.
The passenger shell, rolling contact mesh and existing runtime files stay independent.
"""
from pathlib import Path
import json
import math
import sys
import bpy
from mathutils import Vector,Matrix

ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'web/assets/orbital';NATIVE=ROOT/'unity/Assets/Upwell/Resources/OrbitalHardware';ART=ROOT/'blender/orbital'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
v=Vector;X=v((1,0,0));Y=v((0,1,0));Z=v((0,0,1));T=math.tau;metadata={}
exec(compile((ROOT/'source/mesh_primitives.py').read_text(),str(ROOT/'source/mesh_primitives.py'),'exec'))
specs=json.loads((NATIVE/'finishes.json').read_text())['materials'];mats={};images={}
used={'Frame','Gasket','Structure','Shell','Recoat','BlueGrey','Radiator','Foil','Orange','Navigation','Mirror','CarGlass','LitWindow'}
def lin(s):return tuple((int(s[i:i+2],16)/255/12.92 if int(s[i:i+2],16)/255<=.04045 else ((int(s[i:i+2],16)/255+.055)/1.055)**2.4) for i in (1,3,5))
for s in specs:
    short=s['name'].removeprefix('Aster_')
    if short not in used:continue
    m=bpy.data.materials.new(s['name']);mats[short]=m;m.use_nodes=True;node=m.node_tree.nodes['Principled BSDF'];rgb=lin(s['color']);m.diffuse_color=(*rgb,s['alpha'])
    node.inputs['Base Color'].default_value=(*rgb,1);node.inputs['Metallic'].default_value=s['metal'];node.inputs['Roughness'].default_value=s['rough'];node.inputs['Emission Color'].default_value=(*lin(s['emit']),1);node.inputs['Emission Strength'].default_value=s['gain'];node.inputs['Alpha'].default_value=s['alpha']
    if s['alpha']<1:m.surface_render_method='BLENDED'
    if s['image']:
        stem=s['image']
        if stem not in images:images[stem]=bpy.data.images.load(str(NATIVE/(stem+'.jpg')))
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=images[stem];m.node_tree.links.new(tex.outputs['Color'],node.inputs['Base Color'])

def bl(p):return (p[0],-p[2],p[1])
def trim(p):return [round(float(q),6) for q in p]
def bar(a,b,w,h,mat='Structure',bevel=.008):
    a=v(a);b=v(b);long=(b-a).normalized();right=Y.cross(long)
    if right.length<.02:right=X.copy()
    right.normalize();up=long.cross(right).normalized();cube((a+b)*.5,(w,h,(b-a).length),mat,bevel,Matrix((right,up,long)).transposed())
def pin(p,n,r,size,mat='Structure'):
    p=v(p);n=v(n);rod(p-n*size*.5,p+n*size*.5,r,mat,12)
def bolt(p,n,r=.032):
    p=v(p);n=v(n);rod(p-n*.004,p+n*.008,r*1.24,'Gasket',9);rod(p+n*.007,p+n*.018,r,'Structure',6)
def stripe(p,n,w,h,mat='Orange'):
    p=v(p);n=v(n);plate(p,n,w,h,.009,mat,min(.008,h*.1))
def cylinder(p,n,stages):
    p=v(p);n=v(n)
    for (s,r,m),(s1,r1,_) in zip(stages,stages[1:]):rod(p+n*s,p+n*s1,r,m,26,r2=r1,cap=False)
def angular_collar(p,n,rr,hook='Frame'):
    p=v(p);n=v(n);r,u,n=basis(n)
    for ang in range(8):
        d=r*math.cos(T*ang/8)+u*math.sin(T*ang/8);bolt(p+d*rr,n,.022)
    torus(p,n,rr*.94,.013,hook,32,6)
def chamfered(w,d,k):
    return [(-w+k,-d),(w-k,-d),(w,-d+k),(w,d-k),(w-k,d),(-w+k,d),(-w,d-k),(-w,-d+k)]
def plateform(cx,y,cz,w,d,height,mat,cut=.20):
    poly=chamfered(w/2,d/2,cut);lower=[v((cx+x,y-height/2,cz+z)) for x,z in poly];upper=[p+Y*height for p in lower]
    face(upper,mat,Y);face(lower,mat,-Y)
    for i,p in enumerate(lower):
        j=(i+1)%len(lower);n=(p+lower[j])*.5-v((cx,y-height/2,cz));face([p,lower[j],upper[j],upper[i]],mat,n)
def optical_head(p,n,r):
    # Multistage lens, protective ribs, four light wells and a separate
    # entrance pupil behind thin clear glass. These are genuine optics.
    p=v(p);n=v(n).normalized();a,b,n=basis(n)
    cylinder(p,n,[(-.20,r*.58,'Frame'),(-.12,r*.83,'Recoat'),(-.07,r,'Shell'),(.055,r,'Frame'),(.075,r*.87,'Structure'),(.098,r*.79,'Gasket'),(.063,r*.72,'Mirror')])
    rod(p+n*.055,p+n*.062,r*.715,'CarGlass',26);torus(p+n*.062,n,r*.545,.012,'Structure',26,6)
    rod(p+n*.024,p+n*.032,r*.66,'Mirror',22);rod(p+n*.033,p+n*.039,r*.35,'BlueGrey',20)
    for k in range(4):
        d=a*math.cos(T*(k+.125)/4)+b*math.sin(T*(k+.125)/4);o=p+d*r*.80+n*.088
        rod(o,o+n*.01,r*.068,'Navigation',8);bar(p+d*r+n*.055,p+d*r-n*.08,r*.07,r*.10,'Frame')
def junction(p,n,w,h):
    p=v(p);n=v(n);r,u,n=basis(n);plate(p,n,w,h,.16,'Frame',.035);plate(p+n*.09,n,w*.88,h*.85,.026,'BlueGrey',.019)
    for k in range(5):stripe(p+r*w*.04+u*(k-2)*h*.101+n*.109,n,w*.64,h*.025,'Gasket')
    for s in (-1,1):
        for t in (-1,1):bolt(p+r*s*w*.423+u*t*h*.384+n*.111,n,.018)
def bracket():
    n=Z;p=v((0,1.70,1.326));plate(p,n,1.099,.322,.030,'Frame',.033)
    plate(p+n*.019,n,1.045,.264,.004,'Recoat',.014)
    for sx in (-1,1):
        for sy in (-1,1):bolt(p+X*sx*.511+Y*sy*.136+n*.022,n,.009)
def common_bogie():
    active('counter','counter_common_bogie')
    # Identical inboard saddle mounting and axle envelopes to the passenger
    # assembly, with open lightening holes, brakes and four shock-isolated feet.
    for s in (-1,1):
        z=s*.48;bar((-1.27,-2.815,z),(-1.27,2.835,z),.207,.146,'Frame',.026)
        bar((-1.16,-2.81,z),(-1.16,2.82,z),.068,.215,'Structure')
        for y in (-2.50,2.46):
            cube((-1.30,y,z),(.40,.66,.30),'Orange',.053)
            bar((-1.22,y-.50,s*.55),(-1.59,y+.16,s*.55),.113,.115,'Structure',.024)
            plate((-1.50,y+.13,s*.48),-X,.17,.26,.061,'Frame',.022)
            for end in (-1,1):bolt((-1.521,y+.13+end*.075,s*.48),-X,.027)
            p=v((-.97,y,z));rod(p-X*.25,p-X*.105,.14,'Structure',14);rod(p-X*.10,p+X*.015,.112,'Gasket',14)
            cube((-.87,y,z),(.20,.25,.245),'Recoat',.036)
        for y in (-1.68,-.57,.54,1.67):
            p=v((-1.205,y,z));junction(p,X,.173,.22)
    for y in (-2.47,-1.27,.03,1.26,2.45):
        bar((-1.13,y,-.50),(-1.13,y,.50),.10,.14,'Frame');bar((-.94,y-.15,-.43),(-.94,y+.15,.43),.080,.077,'Structure')

def winding(c,n,width,r):
    c=v(c);a,b,n=basis(n);rod(c-n*width/2,c+n*width/2,r*.72,'Frame',24)
    steps=17;pts=[]
    for k in range(steps*28+1):
        t=k/(steps*28);ang=T*t*steps;pts.append(c+n*width*(t-.5)+(a*math.cos(ang)+b*math.sin(ang))*r*.755)
    tube(pts,.026,'Foil',6)
    for s in (-1,1):
        d=c+n*s*(width*.5+.03);torus(d,n,r,.041,'Structure',32,7);torus(d,n,r*.77,.029,'BlueGrey',28,6)
        for k in range(6):
            ray=a*math.cos(T*(k+.1)/6)+b*math.sin(T*(k+.1)/6);bar(d+ray*r*.14,d+ray*r*.97,.059,.049,'BlueGrey')
        pin(d+n*s*.059,n,r*.22,.12,'Orange');bolt(d+n*s*.128,n,r*.10)
def folded_outrigger(sign):
    z=sign*.89
    p=v((.95,-2.38,z));elbow=v((1.32,.85,z+sign*.07));tip=v((1.52,-.85,z+sign*.11))
    # Both forks remain positively latched alongside the frame during transit.
    # The open hinge centres, rod ends and glass inspection heads are visible.
    for s in (-1,1):
        off=Z*s*.065;bar(p+off,elbow+off,.10,.105,'Orange',.023)
        bar(elbow+off,tip+off,.085,.085,'Recoat',.018)
    for point,r in ((p,.15),(elbow,.14),(tip,.101)):
        pin(point,Z,r,.23,'Frame');pin(point+Z*sign*.123,Z,r*.65,.039,'Structure')
    for k in (0,1):
        a=p+v((.126,.45+k*.26,.0));b=elbow+v((-.072,-.78+k*.24,.0));rod(a,a.lerp(b,.61),.072,'Frame',10);rod(a.lerp(b,.56),b,.034,'Mirror',10)
    rail=[p-X*.10,p+Y*.32-X*.12,elbow+Y*.12-X*.109,elbow+Y*.20,elbow+Y*.07+X*.12,tip+X*.08]
    tube(rail,.028,'Gasket',7);head=tip+v((.042,-.16,sign*.04));optical_head(head,v((.22,-.12,sign*.94)),.143)
    cube((1.38,-.36,z+sign*.02),(.31,.10,.29),'Frame',.025);stripe((1.54,-.36,z),X,.21,.06)

def inspection_tender():
    active('counter','counter_inspection_tender')
    # Three sparse longitudinal chords preserve a clear sightline through the
    # work platform, especially from the passing carriage's +Z-facing side.
    coords=[(-.79,-.74),(-.79,.74),(.79,-.68),(.79,.68)];heights=(-2.76,-.96,.80,2.59)
    for x,z in coords:bar((x,-2.86,z),(x,2.75,z),.103,.107,'Structure',.023)
    for y in heights:
        for i,j in ((0,1),(0,2),(1,3),(2,3)):bar((coords[i][0],y,coords[i][1]),(coords[j][0],y,coords[j][1]),.094,.104,'Frame')
        for x,z in coords:cube((x,y,z),(.175,.16,.17),'BlueGrey',.024)
    for idx,(ya,yb) in enumerate(zip(heights,heights[1:])):
        for s in (-1,1):
            if idx!=1 or s<0:bar((-.78,ya,s*.73),(.79,yb,s*.68),.058,.068,'Structure')
        bar((-.79,ya,-.73),(-.79,yb,.73),.069,.062,'BlueGrey')
    for y in (-2.50,2.46):
        for sign in (-1,1):bar((-.94,y,sign*.48),(-.66,y,sign*.73),.18,.18,'Frame',.026)
    for y in (-2.75,2.60):plateform(0,y,0,1.82,1.69,.18,'BlueGrey',.24)
    # High-offset sensing gantry, twin optical heads looking in different
    # directions, and an open rectangular fork balanced by lower ballast.
    for s in (-1,1):
        bar((-.70,2.65,s*.58),(-.35,3.64,s*.43),.106,.122,'Recoat',.019)
        bar((.75,2.65,s*.58),(.55,3.61,s*.43),.093,.098,'Structure',.018)
        bar((-.37,3.62,s*.43),(.56,3.62,s*.43),.132,.119,'Orange',.017)
    bar((.27,3.63,-.54),(.27,3.63,.54),.12,.13,'Frame',.012)
    for s in (-1,1):
        mount=v((.22,3.68,s*.51));pin(mount,Z,.214,.36,'BlueGrey');optical_head(mount+Z*s*.126+Y*.15,v((.31,.19,s)),.283)
        mast=mount+v((-.53,-.04,s*.03));pin(mast,Z,.127,.16,'Frame');optical_head(mast+Z*s*.08,v((-.62,.31,s)),.137)
    for sign in (-1,1):folded_outrigger(sign)
    win=v((.19,-.01,.016));winding(win,Z,.99,.669)
    for sz in (-1,1):
        p=win+Z*sz*.58;bar((-.43,-.90,sz*.693),p,.128,.147,'Recoat',.022);bar((.61,-.90,sz*.68),p,.12,.124,'Frame',.019)
    for sign in (-1,1):
        p=v((-.47,1.56,.36*sign));cube(p,(.35,1.10,.39),'Recoat',.064)
        for k in range(8):cube(p+X*.192+Y*(k-3.5)*.101,(.062,.023,.36),'Radiator',.01)
    # Calibration plates and twin extra beaded service harnesses in the bay.
    junction((.43,1.81,.17),X,.54,.72);junction((.05,-1.49,.36),Z,.52,.64)
    for d,mat in ((-.041,'Orange'),(.041,'Gasket')):
        tube([(-.61,1.91,.51+d),(-.53,1.62,.58+d),(-.33,.84,.60+d),(-.39,-.57,.65+d),(-.66,-.79,.62+d),(-.68,-.53,.52+d)],.028,mat,8)
    for s in (-1,1):
        p=v((.03,-2.03,s*.37));cylinder(p,Y,[(-.45,.14,'Frame'),(-.35,.205,'Foil'),(.21,.205,'Foil'),(.31,.144,'Structure'),(.35,.065,'Frame')]);pin(p+Y*.38,Y,.05,.092)
    for s in (-1,1):
        bar((-.62,-2.79,s*.54),(-.27,-3.65,s*.32),.11,.14,'BlueGrey');bar((.64,-2.79,s*.55),(.23,-3.65,s*.32),.11,.14,'Recoat')
    plateform(-.02,-3.67,0,.82,.88,.17,'Orange',.17);optical_head((.04,-3.82,.05),v((.11,-.98,.09)),.207)
    # External four-corner hardpoints support the same dynamic registration
    # placard as the passenger vehicle; there is no deck of passenger seats.
    for s in (-1,1):bar((-.55,1.57,s*.62),(-.34,1.70,s*1.17),.068,.071,'Frame')
    for s in (-1,1):bar((s*.44,1.73,.68),(s*.44,1.72,1.31),.064,.062,'Frame')
    bracket();return current

def freight_carrier():
    active('counter','counter_freight_carrier')
    # Three independently secured unpressurised pallets, with a visible gap
    # between their twistlocks. Different payloads can be released separately.
    modules=[(-2.40,1.87,.01,1.97,1.59,'BlueGrey'),(.04,2.41,.00,2.09,1.63,'Recoat'),(2.39,1.73,-.10,1.78,1.51,'BlueGrey')]
    for i,(yc,h,cx,w,dep,mat) in enumerate(modules):
        plateform(cx,yc,0,w,dep,h,mat,min(w,dep)*.095)
        for sy in (-1,1):
            g=yc+sy*(h*.5-.05);plateform(cx,g,0,w+.075,dep+.09,.11,'Frame',.17)
            for sx in (-1,1):
                for sz in (-1,1):
                    lock=v((cx+sx*(w*.5-.089),g,sz*(dep*.5-.087)));cube(lock,(.211,.15,.217),'Orange',.021)
                    pin(lock+Y*sy*.09,Y,.062,.042,'Structure')
        for sz in (-1,1):
            z=sz*(dep*.5+.018)
            for j in range(6):
                xx=cx+(j-2.5)*w*.135
                if i!=0:cube((xx,yc,z),(.040,h-.30,.038),'BlueGrey',.012)
            for sx in (-1,1):
                # Lever-lock inspection door with die-formed edge seal and
                # actual captive pin handles; hatches remain cargo hardware.
                if i==0:
                    facecen=v((cx+sx*w*.235,yc,z));n=Z*sz
                    rim(facecen,n,w*.42,h*.69,.085,w*.38,h*.66,.060,.031,'Structure','Gasket')
                    plate(facecen-n*.012,n,w*.38,h*.66,.030,'BlueGrey',.055)
                    pp=facecen+X*sx*w*.095;rod(pp-Y*.38,pp+Y*.38,.028,'Structure',8)
                    tube([pp+Y*.03,pp+n*.085+Y*.034,pp+X*.12+n*.085+Y*.034],.022,'Frame',6)
            stripe((cx,yc-h*.28,sz*(dep*.5+.050)),Z*sz,w*.63,.105,'Orange' if i!=1 else 'BlueGrey')
        for sx in (-1,1):
            x=cx+sx*(w*.5+.017)
            for j in range(max(3,int(h/.275))):
                y=yc-h*.38+j*(h*.76/max(1,int(h/.275)-1));bar((x,y,-dep*.37),(x,y,dep*.37),.050,.047,'Structure',.008)
            p=v((x+sx*.012,yc-h*.23,0));junction(p,X*sx,.52,.23)
    # External longeron and positive capture frame. Two vertically tensioned
    # canisters sit outside the stack, giving the carrier a broad load face.
    for sy in (-1,1):
        y=sy*3.67;plateform(.10,y,0,2.69,2.19,.19,'Frame',.34)
        for z in (-.89,.89):
            bar((-.96,y,z),(-.86,sy*3.09,z*.81),.127,.135,'Structure');bar((1.21,y,z),(1.14,sy*3.23,z*.91),.126,.145,'BlueGrey')
        for sx in (-1,1):bar((sx*.69,y,-.84),(sx*.69,y,.84),.081,.081,'Recoat')
    for z in (-.78,.78):
        bar((-.96,-3.61,z),(-.96,3.61,z),.119,.14,'Frame',.018)
        bar((1.15,-3.64,z),(1.15,3.64,z),.13,.13,'Structure',.018)
        for y in (-2.50,2.46):bar((-.94,y,math.copysign(.48,z)),(-.76,y,z),.18,.17,'Recoat',.028)
    for sz in (-1,1):
        c=v((1.31,-.34,sz*.44));cylinder(c,Y,[(-2.36,.079,'Frame'),(-2.22,.22,'Structure'),(-2.11,.283,'Foil'),(1.91,.283,'Foil'),(2.02,.218,'Structure'),(2.15,.092,'Frame')])
        for y in (-2.12,-1.24,-.12,1.01,1.90):
            pin(c+Y*y,Y,.295,.068,'Structure');bar((.94,c.y+y,sz*.78),(1.32,c.y+y,sz*.70),.08,.088,'Orange')
        mastop=c+Y*2.20;pin(mastop,Y,.062,.149,'Frame')
        tube([mastop+Y*.05,mastop+Y*.17,mastop-X*.36+Y*.17,mastop-X*.46],.031,'Foil',8)
    for sy in (-1,1):
        z=sy*.55;p=v((.11,3.85,z));bar((-.65,3.70,z),(-.57,3.93,z),.084,.084,'Structure');bar((.78,3.70,z),(.68,3.93,z),.084,.084,'Structure');bar((-.57,3.93,z),(.68,3.93,z),.106,.083,'Recoat')
    for sx in (-1,1):bar((sx*.45,1.69,.76),(sx*.45,1.69,1.32),.066,.068,'Frame')
    bracket();return current

def to_object(g):
    vertices=[];table={};remap=[]
    for p in g.verts:
        key=tuple(round(e,7) for e in p)
        if key not in table:table[key]=len(vertices);vertices.append(bl(p))
        remap.append(table[key])
    m=bpy.data.meshes.new(g.id);m.from_pydata(vertices,[],[tuple(remap[i] for i in f) for f in g.faces],shade_flat=False)
    for mat in g.matlist:m.materials.append(mats[mat])
    m.polygons.foreach_set('material_index',g.ids);layer=m.uv_layers.new(name='Physical UV');layer.uv.foreach_set('vector',[q for uv in g.uv for q in uv]);m.normals_split_custom_set([bl(n) for n in g.normals]);m.update()
    ob=bpy.data.objects.new(g.id,m);bpy.context.collection.objects.link(ob);return ob
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def export():
    common_bogie();inspection_tender();freight_carrier();nodes={g.id:to_object(g) for g in groups.values()}
    select(list(nodes.values()))
    bpy.ops.export_scene.gltf(filepath=str(WEB/'CounterFleet.glb'),export_format='GLB',use_selection=True,export_yup=True,export_animations=False,
        export_cameras=False,export_lights=False,export_normals=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO',export_image_quality=85)
    bpy.ops.export_scene.fbx(filepath=str(NATIVE/'CounterFleet.fbx'),use_selection=True,axis_forward='-Z',axis_up='Y',object_types={'MESH'},bake_space_transform=True,
        bake_anim=False,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_triangles=True,path_mode='STRIP',colors_type='LINEAR')
    survey=dict(units='m',basis='glTF +Y along the cable; guide lies at -X. Unity Local Z is negative glTF Z after the existing CounterCar import rotation.',
        filename='CounterFleet',bogie='counter_common_bogie',passenger='counter_body',inspection='counter_inspection_tender',freight='counter_freight_carrier',
        registration={'web':[0,1.70,1.359],'normal':[0,0,1],'size':[1.04,.262]},wheelAssembly='counter_wheels',
        wheelCentres=[[-1.28,y,z] for y in (-2.50,2.46) for z in (-.50,.47)],parts={})
    for name,ob in nodes.items():
        g=groups[('counter',name)];survey['parts'][name]={'node':name,'localPosition':[0,0,0],'webBounds':[trim(g.lo),trim(g.hi)],'slots':[mats[k].name for k in g.matlist],'triangles':sum(len(f)-2 for f in g.faces)}
    for folder in (WEB,NATIVE,ART):(folder/'counter-fleet-layout.json').write_text(json.dumps(survey,indent=2))
    for im in images.values():im.pack()
    return nodes

def photograph(nodes):
    scene=bpy.context.scene;scene.world=bpy.data.worlds.new('Orbital hardware studio');scene.world.use_nodes=True;bg=scene.world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.109,.142,.167,1);bg.inputs['Strength'].default_value=.46
    def light(name,point,energy,size,tint):
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=tint;ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=bl(point);ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
    light('Large earthward fill',(1.45,4.08,6.19),680,5.0,(.79,.89,1));light('Solar key',(-5,7,4.6),1100,4.50,(1,.88,.73));light('Narrow rim',(2.64,2.9,-5.5),1090,3.8,(.88,.93,1))
    camera=bpy.data.cameras.new('Survey camera');camera.lens=50;camera.type='ORTHO';camera.ortho_scale=10.1
    ob=bpy.data.objects.new('Survey camera',camera);scene.collection.objects.link(ob);scene.camera=ob
    ob.location=bl((6.8,2.5,11.1));ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
    group=bpy.data.collections.new('Inspection tender assembly');scene.collection.children.link(group)
    freight=bpy.data.collections.new('Freight carrier assembly');scene.collection.children.link(freight)
    bogie=nodes['counter_common_bogie'];fg=bogie.copy();fg.name='Freight bogie';freight.objects.link(fg)
    for part,collection in ((bogie,group),(nodes['counter_inspection_tender'],group),(nodes['counter_freight_carrier'],freight)):
        for old in tuple(part.users_collection):old.objects.unlink(part)
        collection.objects.link(part)
    # In this editable lineup the two vehicles are separated only via their
    # collection parent offsets, after each rigid mesh was exported at zero.
    for c,dx in ((group,-2.08),(freight,2.08)):
        par=bpy.data.objects.new(c.name+' datum',None);c.objects.link(par);par.empty_display_size=.26
        for model in c.objects:
            if model!=par:model.parent=par
        par.location=bl((dx,0,0))
    ob.location=bl((5.3,2.3,13.0));ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.ortho_scale=10.9
    scene.render.engine='CYCLES';scene.render.resolution_x=1100;scene.render.resolution_y=950;scene.render.resolution_percentage=100;scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=93
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.refresh_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
    except (TypeError,RuntimeError):pass
    select([nodes['counter_inspection_tender']]);bpy.ops.wm.save_as_mainfile(filepath=str(ART/'CounterFleet.blend'),compress=True)
    if '--preview' in sys.argv:
        scene.render.filepath=str(ART/'counter-fleet.jpg');bpy.ops.render.render(write_still=True)

if __name__=='__main__':photograph(export())
