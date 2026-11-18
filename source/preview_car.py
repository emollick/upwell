"""Render the selected carriage cameras to the Blender workspace for visual review."""
from pathlib import Path
import sys
import bpy

root=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
scene.render.engine="CYCLES"
cp=bpy.context.preferences.addons["cycles"].preferences
try:
    cp.compute_device_type="OPTIX";cp.refresh_devices()
    gpus=[d for d in cp.devices if d.type=="OPTIX"]
    if gpus:
        for d in cp.devices:d.use=d in gpus
        scene.cycles.device="GPU"
except (RuntimeError,TypeError):
    pass
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.cycles.samples=32;scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.058
scene.render.image_settings.file_format="JPEG";scene.render.image_settings.quality=92
shots=(("observation","Observation / forward",88),("berth","Sleeper / aft",88),
       ("service","Service / aft",88),("cable-bay","Service / loom",88),
       ("departure","Observation / forward",1),("arrival","Observation / forward",270),
       ("approach","Observation / forward",242),("earth","Instrument / nadir",228),("guideway","Instrument / guide",88),
       ("capture-throat","Instrument / capture",254))
requested=set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
for rid,title,frame in shots:
    if requested and rid not in requested:continue
    scene.frame_set(frame)
    scene.camera=bpy.data.objects[title]
    if rid=="cable-bay":
        import math
        bpy.data.objects["prop_service_cabinet"].rotation_euler.z=math.radians(-84)
    scene.render.filepath=str(root/"blender"/(rid+".jpg"))
    bpy.ops.render.render(write_still=True)
