"""Build the floating cable workshop in metres, with its origin on the load waterline."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web/assets/harbor"
UNITY = ROOT / "unity/Assets/Upwell/Resources/Harbor"
SOURCE = ROOT / "blender/harbor"
for folder in (WEB, UNITY, SOURCE):
    folder.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
v = Vector
X, Y, Z = (v(p) for p in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
T = math.tau
metadata = {}
exec(compile((ROOT / "source/mesh_primitives.py").read_text(), "mesh_primitives.py", "exec"))


def finish(name, color, metal, rough):
    label = "Harbor_Berth_" + name
    m = bpy.data.materials.new(label)
    m.use_nodes = True
    rgb = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    linear = tuple(x / 12.92 if x < .04045 else ((x + .055) / 1.055) ** 2.4 for x in rgb)
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*linear, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*linear, 1)
    metadata[label] = dict(name=label, color="#" + color, metal=metal, rough=rough,
                           alpha=1, gain=0, emit="#000000")
    return label


hull = finish("BlueSteel", "334a52", .37, .53)
keel = finish("Waterline", "463d36", .21, .62)
deck = finish("Deck", "65716d", .32, .65)
buff = finish("Coaming", "c4bb9d", .22, .48)
yellow = finish("Gantry", "c99d52", .30, .49)
oxide = finish("Inspections", "965a3b", .21, .69)
rubber = finish("Fender", "303634", .04, .82)
cable = finish("WoundWire", "747c77", .73, .49)
glass = finish("Glazing", "385c66", .38, .18)
active("harbor", "line_berth")


def beam(a, b, width, depth, mat):
    a, b = v(a), v(b)
    r, u, axis = basis(b-a)
    cube((a+b)/2, (width, depth, (a-b).length), mat, 0, Matrix((r, u, axis)).transposed())


def pontoon(cx):
    rings = []
    # Raked ends and rounded bilges leave daylight through the middle of the hull.
    for z, half, bottom, top in ((-16,.62,-.42,1.27),(-14,1.55,-1.22,1.42),
                                 (-10,1.85,-1.60,1.42),(10,1.85,-1.60,1.42),
                                 (14.2,1.49,-1.03,1.42),(16,.68,-.38,1.26)):
        rings.append([v((cx+u*half, h, z)) for u,h in
                     ((-.76,bottom),(.76,bottom),(.98,bottom*.58),(1,.22),(.94,top),
                      (-.94,top),(-1,.22),(-.98,bottom*.58))])
    for a,b in zip(rings,rings[1:]):
        for i in range(8):
            j=(i+1)%8
            mid=(a[i]+a[j]+b[j]+b[i])/4
            face((a[i],a[j],b[j],b[i]), keel if i in (0,1,7) else hull,
                 (mid.x-cx,mid.y+.04,0))
    face(rings[0],hull,-Z)
    face(rings[-1],hull,Z)


for x in (-4.05, 4.05):
    pontoon(x)
for z in (-12,-7,-2,3,8,12):
    cube((0,1.26,z),(9.4,.46,.35),hull,.06)
for x in (-3.6,0,3.6):
    cube((x,1.58,0),(3.50,.25,26.3),deck,.05)
for side in (-1,1):
    x=side*5.84
    cube((x,1.12,0),(.18,.31,24.4),hull,.06)
    for z in (-11,-7,-3,1,5,9,12):
        # Rubber extrusion with its curved face and both hanging straps.
        rod((x,1.12,z-.55),(x,1.12,z+.55),.28,rubber,10)
        for dz in (-.35,.35):
            rod((x,1.14,z+dz),(x-side*.33,1.72,z+dz),.045,cable,6)
    for z in (-12.2,-9.2,-6.2,6.2,9.2,12.2):
        rod((side*5.17,1.69,z),(side*5.17,2.75,z),.042,buff,8)
    for z0,z1 in ((-12.2,-6.2),(6.2,12.2)):
        for h in (2.2,2.74):
            rod((side*5.17,h,z0),(side*5.17,h,z1),.042,buff,8)
    for z in (-10.8,10.8):
        for dz in (-.24,.24):
            rod((side*4.5,1.70,z+dz),(side*4.5,2.21,z+dz),.125,hull,12)
            rod((side*4.5,2.21,z+dz),(side*4.5,2.26,z+dz),.16,cable,12)

# The two A-frames are open in both directions, with a sheave hanging below the bridge.
for side in (-1,1):
    x=side*4.35
    for z in (-5.1,3.2):
        cube((x,1.83,z),(.86,.24,.9),oxide,.04)
        beam((x,1.90,z),(side*3.83,10.60,-1.35),.39,.47,yellow)
    beam((x,4.58,-3.99),(x,4.58,1.80),.22,.26,yellow)
    beam((side*4.11,7.54,-2.75),(side*4.11,7.54,.11),.19,.24,yellow)
for z in (-1.65,-1.06):
    beam((-4.12,10.55,z),(4.12,10.55,z),.38,.36,yellow)
for x in (-3.25,-1.6,0,1.6,3.25):
    beam((x,10.56,-1.66),(x,10.56,-1.05),.13,.12,hull)
rod((.9,9.94,-1.36),(1.47,9.94,-1.36),.42,hull,18)
for x in (1.02,1.34):
    rod((x,9.86,-1.37),(x,6.44,-1.37),.032,cable,7)
rod((.97,6.4,-1.37),(1.4,6.4,-1.37),.23,oxide,14)
torus((1.19,6.05,-1.37),X,.21,.057,cable,18,7,(-.2,5.08))

# Full and spare drums; real spokes read through the flanges against the water.
def reel(cx, z, radius, span, wound):
    y=1.77+radius+.32
    for side in (-1,1):
        x=cx+side*span/2
        beam((x,1.71,z-.78),(x,y,z),.22,.24,hull)
        beam((x,1.71,z+.78),(x,y,z),.22,.24,hull)
        torus((x,y,z),X,radius,.106,yellow,36,7)
        for j in range(8):
            a=j*T/8
            rod((x,y,z),(x,y+radius*math.sin(a),z+radius*math.cos(a)),.089,yellow,7)
    core=radius*(.74 if wound else .33)
    rod((cx-span/2-.12,y,z),(cx+span/2+.12,y,z),core,cable,32)
    for j in range(14 if wound else 4):
        x=cx-span*.46+j*span*.92/(13 if wound else 3)
        torus((x,y,z),X,core,.037,hull,28,6)


reel(-.3,-2.1,2.34,3.55,True)
reel(1.96,4.25,1.39,2.12,False)

# Short outboard wheelhouse, recessed sills and divided anti-glare glazing.
cx,cz=-1.85,8.23
cube((cx,3.04,cz),(3.95,2.70,4.24),buff,.22)
cube((cx,4.49,cz),(4.34,.23,4.64),hull,.08)
for side in (-1,1):
    for dz in (-1.08,0,1.08):
        cube((cx+side*1.975,3.66,cz+dz),(.07,.94,.98),hull,.035)
        cube((cx+side*2.019,3.70,cz+dz),(.035,.75,.84),glass,.02)
    for dx in (-.84,.84):
        cube((cx+dx,3.66,cz+side*2.12),(1.5,.91,.065),hull,.025)
        cube((cx+dx,3.70,cz+side*2.16),(1.32,.74,.032),glass,.012)
rod((cx-.9,4.54,cz+1.01),(cx-.9,8.16,cz+1.01),.078,buff,9,r2=.029)
rod((cx-.9,6.15,cz+.52),(cx-.9,6.15,cz+1.50),.049,hull,8)
for i in range(6):
    cube((3.18,1.78+i*.19,9.9+i*.24),(1.21,.095,.36),cable,.02)
for side in (-1,1):
    x=3.18+side*.61
    beam((x,2.46,9.81),(x,3.51,11.39),.058,.06,buff)
    for z,h in ((9.9,2.52),(11.34,3.49)):
        rod((x,h-.80,z),(x,h,z),.034,buff,7)

def bl(point):
    return (point[0],-point[2],point[1])


g=current
mesh=bpy.data.meshes.new("Cable workshop · painted steel and rigging")
mesh.from_pydata([bl(p) for p in g.verts], [], g.faces, shade_flat=False)
for name in g.matlist:
    mesh.materials.append(bpy.data.materials[name])
mesh.polygons.foreach_set("material_index", g.ids)
mesh.normals_split_custom_set([bl(n) for n in g.normals])
mesh.update()
obj=bpy.data.objects.new("line_berth",mesh)
bpy.context.collection.objects.link(obj)
obj.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/"LineServiceBerth.blend"),compress=True)
bpy.ops.export_scene.gltf(filepath=str(WEB/"line_berth.glb"),export_format="GLB",use_selection=True,
                          export_animations=False,export_yup=True,export_texcoords=False)
bpy.ops.export_scene.fbx(filepath=str(UNITY/"line_berth.fbx"),use_selection=True,axis_forward="-Z",axis_up="Y",
                         object_types={"MESH"},bake_space_transform=True,bake_anim=False,apply_unit_scale=True,
                         apply_scale_options="FBX_SCALE_UNITS",path_mode="STRIP",add_leaf_bones=False)
palette=json.dumps({"materials":list(metadata.values()),"units":"m"},indent=2)+"\n"
for directory in (WEB,UNITY):
    (directory/"berth-finishes.json").write_text(palette,encoding="utf-8")
print("Berth bounds in metres at the waterline",current_bounds(g))
