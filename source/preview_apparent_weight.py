"""Render the physical load, liquid, bedding and service-loop states from inside Car 07."""
from pathlib import Path
import math
import sys
import bpy
from mathutils import Vector

ROOT=Path(bpy.data.filepath).resolve().parents[1]
target=ROOT/"blender"/"apparent-weight";target.mkdir(exist_ok=True)
scene=bpy.context.scene;scene.render.engine="CYCLES";scene.cycles.use_denoising=True
options=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
quick="--quick" in options
selected={k for k in options if not k.startswith("--")}
scene.cycles.samples=8 if quick else 36;scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.057
scene.render.resolution_x=920 if quick else 1500;scene.render.resolution_y=580 if quick else 944;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="JPEG";scene.render.image_settings.quality=93
prefs=bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type="OPTIX";prefs.refresh_devices()
    for d in prefs.devices:d.use=d.type=="OPTIX"
    if any(d.use for d in prefs.devices):scene.cycles.device="GPU"
except (TypeError,RuntimeError):pass
def bl(w):return Vector((w[0],-w[2],w[1]))
def camera(eye,focus,focal):
    d=bpy.data.cameras.new("Inspection optics");d.lens=focal;d.clip_start=.012;d.clip_end=1e9
    c=bpy.data.objects.new("Onboard inspection",d);scene.collection.objects.link(c)
    c.location=bl(eye);c.rotation_euler=(bl(focus)-c.location).to_track_quat("-Z","Y").to_euler()
    return c
frames=[
    ("load-anchor",1,(-.598,1.355,-4.31),(-.759,1.287,-5.231),35),
    ("load-orbit",270,(-.598,1.355,-4.31),(-.759,1.287,-5.231),35),
    ("load-test",1,(-.598,1.355,-4.31),(-.759,1.287,-5.231),35),
    ("cell-anchor",1,(1.389,1.374,-.505),(2.061,1.310,-.633),42),
    ("cell-orbit",270,(1.389,1.374,-.505),(2.061,1.310,-.633),42),
    ("cell-braking",243,(1.389,1.374,-.505),(2.061,1.310,-.633),42),
    ("cell-prime",1,(1.389,1.374,-.505),(2.061,1.310,-.633),42),
    ("quilt-anchor",1,(-.028,1.722,.971),(-1.595,1.02,.121),31),
    ("quilt-orbit",243,(-.028,1.722,.971),(-1.595,1.02,.121),31),
    ("quilt-occupied",1,(-.028,1.722,.971),(-1.595,1.02,.121),31),
    ("weave-quilt",1,(-.810,1.322,.947),(-1.564,.965,.594),43),
    ("weave-curtain",1,(-.126,1.140,.924),(-1.237,1.12,.113),43),
    ("curtain-drawn",243,(-.011,1.557,.789),(-1.316,1.43,-.011),27),
    ("service-loops",243,(-.20,1.45,4.02),(1.966,1.49,3.51),39)]
for key,frame,eye,focus,lens in frames:
    if selected and key not in selected:continue
    scene.frame_set(frame);scene.camera=camera(eye,focus,lens)
    settings=[("prop_accelerometer","test_stroke",1. if key=="load-test" else 0.),
              ("prop_capillary_cell","primer_stroke",1. if key=="cell-prime" else 0.),
              ("prop_bunk","occupied",1. if key=="quilt-occupied" else 0.),
              ("prop_privacy_curtain","drawn",1. if key in ("curtain-drawn","weave-curtain") else 0.)]
    for parent,prop,value in settings:
        ob=bpy.data.objects[parent];ob[prop]=value;ob.update_tag()
    if key=="service-loops":bpy.data.objects["prop_service_cabinet"].rotation_euler.z=math.radians(-84)
    scene.frame_set(frame,subframe=.0001);bpy.context.view_layer.update()
    folder=ROOT/"source"/".export-cache" if quick else target
    scene.render.filepath=str(folder/(key+".jpg"));bpy.ops.render.render(write_still=True)
