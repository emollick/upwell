"""Machine the galley flask's keeper plate and three spring clips at actual scale."""
import math
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
web = ROOT/"web/assets/docking"
unity = ROOT/"unity/Assets/Upwell/Resources/Docking"
master = ROOT/"blender/equipment/docking"
bpy.ops.wm.read_factory_settings(use_empty=True)

def metal(name, rgb, metallic, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = rough
    mat.diffuse_color = (*rgb, 1)
    return mat

alloy = metal("Cradle ferritic steel", (.23,.25,.26), .88, .35)
ceramic = metal("Cradle carbon composite", (.031,.035,.035), .22, .48)
spring = metal("Cradle phosphor bronze", (.42,.25,.12), .82, .34)
pin = metal("Cradle burnished pin", (.36,.39,.40), .96, .23)
paint = metal("Cradle ivory witness", (.58,.59,.52), .13, .46)

def sector(name, start, end, section, mat, center=(0,0), steps=70):
    full = abs(end-start-360)<.001
    verts=[]
    for i in range(steps if full else steps+1):
        a=math.radians(start+(end-start)*i/steps)
        for r,z in section:
            verts.append((center[0]+r*math.cos(a),center[1]+r*math.sin(a),z))
    faces=[]
    n=len(section)
    for i in range(steps):
        j=(i+1)%steps if full else i+1
        for t in range(n):
            k=(t+1)%n
            faces.append((i*n+t,j*n+t,j*n+k,i*n+k))
    if not full:
        faces.extend((tuple(reversed(range(n))),tuple(steps*n+j for j in range(n))))
    geo=bpy.data.meshes.new(name);geo.from_pydata(verts,[],faces);geo.materials.append(mat);geo.update()
    obj=bpy.data.objects.new(name,geo);bpy.context.collection.objects.link(obj)
    for p in geo.polygons: p.use_smooth=p.index<steps*n and p.index%n in (1,2)
    return obj

sector("Recessed keeper plate",0,360,[(.001,-.003),(.055,-.003),(.056,-.0022),(.056,.0012),(.055,.0021),(.042,.0021),(.040,.0007),(.001,.0007)],alloy)
sector("Elastomer heel seat",0,360,[(.029,.00065),(.039,.00065),(.039,.0026),(.0375,.003),(.029,.0024)],ceramic)
for a in (30,150,270):
    sector("Raised rail",a-31,a+31,[(.043,.001),(.054,.001),(.054,.0043),(.052,.005),(.044,.005),(.043,.0035)],ceramic,steps=24)
    sector("Spring finger",a-14,a+14,[(.044,.003),(.0476,.003),(.0481,.0138),(.0478,.0163),(.047,.0164),(.0458,.0146)],spring,steps=18)
    angle=math.radians(a+46)
    xy=(.0495*math.cos(angle),.0495*math.sin(angle))
    sector("Countersunk fixing",0,360,[(.001,.0019),(.0034,.0019),(.0035,.0024),(.003,.0027),(.001,.0027)],pin,center=xy,steps=20)
    sector("Witness mark",a-2,a+2,[(.049,.005),(.053,.005),(.053,.00514),(.049,.00514)],paint,steps=4)
bpy.ops.object.select_all(action="SELECT")
bpy.context.view_layer.objects.active=next(iter(bpy.context.scene.objects))
bpy.ops.object.join()
body=bpy.context.object;body.name="Vessel keeper cradle"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.export_scene.gltf(filepath=str(web/"VesselCradle.glb"),export_format="GLB",export_animations=False)
bpy.ops.export_scene.fbx(filepath=str(unity/"VesselCradle.fbx"),axis_forward="-Z",axis_up="Y",
                         bake_space_transform=True,bake_anim=False,apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS")
bpy.ops.wm.save_as_mainfile(filepath=str(master/"VesselCradle.blend"),compress=True)
