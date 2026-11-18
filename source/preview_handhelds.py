"""Render the actual interactive item meshes under a measured three-light inspection rig."""
import bpy
from mathutils import Vector
from pathlib import Path
import math
import sys

root=Path(bpy.data.filepath).resolve().parents[1]
dest=root/"blender"/"equipment";dest.mkdir(exist_ok=True)
def bl(p):return Vector((p[0],-p[2],p[1]))
views={"field_glasses":(.56,.54,1.12),"mug":(-1.13,.42,.64),"logbook":(.24,1.40,.570),
       "access_card":(.12,1.40,.39),"tool_roll":(.88,.84,.45)}
requested=set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
operated="--operated" in requested;requested.discard("--operated")
for id,direction in views.items():
    if requested and id not in requested:continue
    source=bpy.data.objects["geo_"+id];sc=bpy.data.scenes.new("Equipment · "+id)
    if operated:
        for k in source.parent.keys():
            if k.startswith("travel_"):source.parent[k]=1.
        source.parent.update_tag()
        active_scene=bpy.context.scene;active_scene.frame_set(active_scene.frame_current+1)
        bpy.context.view_layer.update()
    sc.render.engine="CYCLES";sc.cycles.samples=60;sc.cycles.use_denoising=True
    cp=bpy.context.preferences.addons["cycles"].preferences
    try:
        cp.compute_device_type="OPTIX";cp.refresh_devices()
        for d in cp.devices:d.use=d.type=="OPTIX"
        if any(d.use for d in cp.devices):sc.cycles.device="GPU"
    except (TypeError,RuntimeError):pass
    group=[source]+[p for p in source.parent.children if p.name.startswith(("flex_","mech_"))]
    allverts=[ob.matrix_local@v.co for ob in group for v in ob.data.vertices]
    lo=Vector([min(v[k] for v in allverts) for k in range(3)]);hi=Vector([max(v[k] for v in allverts) for k in range(3)])
    mid=(lo+hi)*.5;span=max(hi-lo)
    shift=Vector((-mid.x,-mid.y,-lo.z+span*.025))
    for m in group:
        ob=bpy.data.objects.new(id+" inspection",m.data);sc.collection.objects.link(ob);ob.matrix_world=m.matrix_local.copy();ob.location+=shift
    floor=bpy.data.meshes.new("Studio plane");S=span*75
    floor.from_pydata([(-S,-S,0),(S,-S,0),(S,S,0),(-S,S,0)],[],[(0,1,2,3)])
    ground=bpy.data.objects.new("Matte carbon sweep",floor);sc.collection.objects.link(ground)
    mat=bpy.data.materials.new("Neutral studio gray");mat.use_nodes=True;bs=mat.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(.030,.040,.046,1);bs.inputs["Roughness"].default_value=.49;floor.materials.append(mat)
    sub=Vector((0,0,(hi.z-lo.z)*.49+span*.025))
    sc.world=bpy.data.worlds.new(id+" ambient");sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes.get("Background");bg.inputs["Color"].default_value=(.29,.35,.41,1);bg.inputs["Strength"].default_value=.29
    def area(name,pos,power,color,size,size2):
        li=bpy.data.lights.new(name,'AREA');li.energy=power*span**2;li.shape="RECTANGLE";li.size=size*span;li.size_y=size2*span;li.color=color
        a=bpy.data.objects.new(name,li);sc.collection.objects.link(a);a.location=sub+bl(pos)*span
        a.rotation_euler=(sub-a.location).to_track_quat("-Z","Y").to_euler()
    area("Large soft key",(-1.1,2.2,-.55),165,(1,.91,.78),1.83,1.27)
    area("Cool edgebox",(1.20,1.30,.92),95,(.65,.83,1),.69,1.91)
    area("Lower bounce",(-.49,.47,1.73),52,(.89,.95,1),1.28,1.35)
    cam=bpy.data.cameras.new("Inspection");cam.type="ORTHO";cam.ortho_scale=span*1.32;cam.clip_start=.001
    co=bpy.data.objects.new("Inspection",cam);sc.collection.objects.link(co);co.location=sub+bl(direction).normalized()*span*2.52
    co.rotation_euler=(sub-co.location).to_track_quat("-Z","Y").to_euler();sc.camera=co
    basis=co.rotation_euler.to_matrix();right=basis@Vector((1,0,0));up=basis@Vector((0,1,0))
    horizontal=[(p+shift).dot(right) for p in allverts];vertical=[(p+shift).dot(up) for p in allverts]
    width=max(horizontal)-min(horizontal);height=max(vertical)-min(vertical)
    cam.ortho_scale=max(width,height*1220/952)*1.19
    co.location+=right*((max(horizontal)+min(horizontal))*.5-sub.dot(right))+up*((max(vertical)+min(vertical))*.5-sub.dot(up))
    sc.render.resolution_x=1220;sc.render.resolution_y=952;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="JPEG";sc.render.image_settings.quality=94;sc.render.filepath=str(dest/(id+("-operated" if operated else "")+".jpg"))
    bpy.ops.render.render(scene=sc.name,write_still=True)
