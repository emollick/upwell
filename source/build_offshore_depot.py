"""Build Pelagic Anchor's fixed offshore cable depot. Survey basis is glTF, in metres."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web/assets/harbor'
UNITY=ROOT/'unity/Assets/Upwell/Resources/Harbor'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
v=Vector
X,Y,Z=(v(p) for p in ((1,0,0),(0,1,0),(0,0,1)))
T=math.tau
metadata={}
exec(compile((ROOT/'source/mesh_primitives.py').read_text(),'mesh_primitives.py','exec'))
for spec in json.loads((WEB/'berth-finishes.json').read_text())['materials']:
    metadata[spec['name']]=spec
    m=bpy.data.materials.new(spec['name']);m.use_nodes=True
    channels=[int(spec['color'][i:i+2],16)/255 for i in (1,3,5)]
    color=[c/12.92 if c<.04045 else ((c+.055)/1.055)**2.4 for c in channels]+[1]
    bs=m.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=color
    bs.inputs['Metallic'].default_value=spec['metal'];bs.inputs['Roughness'].default_value=spec['rough'];m.diffuse_color=color
blue,water,steel,pale,gold,oxide,rubber,wire,glass=['Harbor_Berth_'+n for n in ('BlueSteel','Waterline','Deck','Coaming','Gantry','Inspections','Fender','WoundWire','Glazing')]
active('harbor','offshore_depot')

def girder(a,b,w,h,mat):
    a,b=v(a),v(b);r,u,axis=basis(b-a)
    cube((a+b)/2,(w,h,(a-b).length),mat,0,Matrix((r,u,axis)).transposed())

def rail(a,b):
    a,b=v(a),v(b);n=max(1,math.ceil((a-b).length/3.4))
    for j in range(n+1):
        p=a.lerp(b,j/n);rod(p,p+Y*1.18,.054,pale,6)
    for h in (.57,1.17):rod(a+Y*h,b+Y*h,.049,pale,7)

def platform(x0,x1,z0,z1,h,sidewalk=True):
    cube(((x0+x1)/2,h-.19,(z0+z1)/2),(x1-x0,.38,z1-z0),steel,.12)
    for x in (x0+.32,x1-.32):
        girder((x,h-1.28,z0),(x,h-1.28,z1),.36,.46,blue)
        n=math.ceil((z1-z0)/3.2)
        for j in range(n):
            a=z0+(z1-z0)*j/n;b=z0+(z1-z0)*(j+1)/n
            rod((x,h-.25,a),(x,h-1.28,b),.105,blue,7)
        if sidewalk:rail((x,h,z0),(x,h,z1))
    for z in (z0,z1):
        girder((x0,h-.98,z),(x1,h-.98,z),.4,.5,blue)
        if sidewalk:rail((x0,h,z),(x1,h,z))

# Six splayed piles and real cross-bracing, visible through the open underdeck.
for x in (-21,20):
    for z in (-15,0,15):
        bottom=v((x*1.19,-13,z*1.18));top=v((x*.94,17.2,z*.96))
        rod(bottom,top,1.31,oxide,22,r2=1.02);rod(bottom.lerp(top,.45),top,1.16,gold,20,r2=1.03)
        for y in (2,8.5,14):
            p=bottom.lerp(top,(y+13)/30.2);rod(p-Y*.16,p+Y*.16,1.29,pale,18)
    for z0,z1 in ((-15,0),(0,15)):
        for a,b in ((z0,z1),(z1,z0)):
            rod((x*1.10,1.8,a),(x*.95,13.4,b),.34,gold,10)
for z in (-15,15):
    rod((-21,4.2,z),(20,14.6,z),.43,gold,12);rod((20,4.2,z),(-21,14.6,z),.43,gold,12)
platform(-25,25,-18,18,16.6)
platform(-24,5,-16,15,22.5)
for x in (-22,3):
    for z in (-14,12,0):rod((x,16.7,z),(x,22.5,z),.39,blue,10)

# Cable store and glazed operations gallery, with roof vents, aerials and service walkways.
for j,(y,sx,sz) in enumerate(((24.55,21,19),(28.2,19,16.3))):
    cube((-11,y,-1),(sx,3.54,sz),pale,.39)
    cube((-11,y+1.85,-1),(sx+.8,.36,sz+.8),blue,.18)
    for side in (-1,1):
        for k in range(7):
            x=-11+(k-3)*2.25
            cube((x,y+.22,-1+side*sz/2),(1.85,.94,.18),glass,.09)
        for z in (-6,-3,0,3,6):cube((-11+side*sx/2,y+.21,z),(.18,.90,2.02),glass,.08)
for x in (-17,-11,-5):
    rod((x,29.9,-3),(x,32.4,-3),.78,steel,18)
    rod((x,32.4,-3),(x,32.62,-3),.96,blue,18)
for x,z,h in ((-19,4,14),(-7,-5,10)):
    rod((x,30,z),(x,30+h,z),.17,pale,12,r2=.048)
    for dx,dz in ((-2.7,-2.3),(2.3,-2),(.8,2.4)):
        rod((x+dx,30,z+dz),(x,30+h*.7,z),.038,wire,6)

# Cantilevered octagonal rescue helideck; actual truss and open mesh rim below the landing surface.
pad=v((-26.5,31.4,5.6));rad=10.4
corners=[pad+v((math.cos((i+.5)*T/8)*rad,0,math.sin((i+.5)*T/8)*rad)) for i in range(8)]
face(corners,steel,Y)
for i,p in enumerate(corners):
    q=corners[(i+1)%8];girder(p,q,.40,.43,pale);rod(p-Y*1.48,q-Y*1.48,.16,blue,9)
    rod(p,q-Y*1.48,.15,blue,9);rod(pad-Y*3,p-Y*.12,.24,blue,10)
    rod((-20,22.5,6),p-Y*1.4,.24,blue,10)
torus(pad+Y*.06,Y,6.3,.13,gold,64,7)
for x in (-1.8,1.8):cube(pad+v((x,.11,0)),(.65,.13,6.0),pale,.03)
cube(pad+Y*.11,(3.7,.13,.62),pale,.03)

# Pedestal crane: triangular boom, luffing backstays, discrete sheaves and twin hoist falls.
pivot=v((13,25.25,4));tip=v((34,48.8,-7));axis=(tip-pivot).normalized()
side,up,unused=basis(axis)
rod((13,16.6,4),(13,24.9,4),2.06,gold,26,r2=1.60)
rod((13,23.3,4),(13,23.78,4),2.30,blue,28)
cube((12.2,25.37,4.0),(6.8,2.24,4.28),gold,.25)
cube((10.8,26.85,5.9),(3.2,2.4,2.2),pale,.16)
cube((10.9,27.04,7.04),(2.75,1.14,.09),glass,.08)
sections=[]
for j in range(10):
    f=j/9;w=1.52*(1-f)+.34*f;p=pivot.lerp(tip,f)
    sections.append([p+side*w,p-side*w,p+up*1.35*w]);
for a,b in zip(sections,sections[1:]):
    for i in range(3):
        rod(a[i],b[i],.159,gold,8);rod(a[i],b[(i+1)%3],.087,gold,7);rod(a[i],a[(i+1)%3],.105,gold,8)
mast=v((10.5,35.7,5.4))
for dx in (-1.6,1.6):
    rod((12.3+dx,25.6,6.1),mast+X*dx*.58,.23,blue,10)
    rod(mast+X*dx*.58,tip+side*dx*.18,.075,wire,8)
    rod(tip+X*dx*.13,(tip.x+dx*.13,31.7,tip.z),.052,wire,7)
rod((33.5,31.7,-7),(34.5,31.7,-7),.56,oxide,12)
torus((34,30.83,-7),Z,.46,.104,gold,24,8,(.1,5.35))

for z in (-11,6):
    c=v((12.7,20.0,z));rod(c-X*3,c+X*3,2.58,wire,32)
    for s in (-1,1):
        p=c+X*3.15*s;torus(p,X,3.05,.18,oxide,32,8)
        for i in range(8):rod(p,p+v((0,math.cos(i*T/8)*3.02,math.sin(i*T/8)*3.02)),.115,oxide,7)
        for d in (-1.6,1.6):rod((p.x,16.68,z+d),p,.21,blue,10)
for z in range(-14,15,3):
    rod((25,10.1,z),(27.6,10.1,z),.18,blue,10)
cube((26.8,10.38,0),(3.35,.42,30),steel,.15);rail((28.3,10.55,-15),(28.3,10.55,15))

def bl(p):return (p[0],-p[2],p[1])
g=current;mesh=bpy.data.meshes.new('Pelagic cable depot')
mesh.from_pydata([bl(p) for p in g.verts],[],g.faces,shade_flat=False)
for mat in g.matlist:mesh.materials.append(bpy.data.materials[mat])
mesh.polygons.foreach_set('material_index',g.ids);mesh.normals_split_custom_set([bl(n) for n in g.normals]);mesh.update()
obj=bpy.data.objects.new('offshore_depot',mesh);bpy.context.collection.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/harbor/OffshoreCableDepot.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(WEB/'offshore_depot.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_texcoords=False)
bpy.ops.export_scene.fbx(filepath=str(UNITY/'offshore_depot.fbx'),use_selection=True,axis_forward='-Z',axis_up='Y',bake_space_transform=True,bake_anim=False,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',path_mode='STRIP',add_leaf_bones=False)
print('Offshore cable depot waterline bounds',current_bounds(g))
