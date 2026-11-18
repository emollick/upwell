"""Audit the packed Blender master's physical travel and editable cabin fixtures."""
from pathlib import Path
import json
import math
import runpy

import bpy
from mathutils import Vector

root=Path(bpy.data.filepath).resolve().parents[1];reports=root/'blender'/'apparent-weight';reports.mkdir(exist_ok=True)
scene=bpy.context.scene;objects=bpy.data.objects;tree=bpy.context.evaluated_depsgraph_get()
nodes={o.name for o in objects if o.name.startswith('prop_')};assert len(nodes)==48,len(nodes)
data=json.loads((root/'web/assets/rooms/gravity-instruments.json').read_text());a=data['accelerometer'];c=data['capillary']
survey=json.loads((root/'web/assets/rooms/furnishings.json').read_text())
assert len(survey['parts'])==13 and len(data['parts'])==5
def q(p):return Vector((p.x,p.z,-p.y))
def place(name):return q(objects[name].evaluated_get(tree).matrix_world.to_translation())
def state(frame):scene.frame_set(frame,subframe=.0001);bpy.context.view_layer.update()
def setp(obj,field,val):objects[obj][field]=val;objects[obj].update_tag()
def cloud(name):
    ob=objects[name].evaluated_get(tree);m=ob.to_mesh();verts=[q(ob.matrix_world@v.co) for v in m.vertices];ob.to_mesh_clear();return verts
def close(a,b,eps=1e-4):assert abs(a-b)<eps,(a,b)

current={};profile=runpy.run_path(str(root/'source/native_capillary_profile.py'))
for tag,frame in (('anchor',1),('braking',243),('docked',270)):
    state(frame);g=objects[a['node']]['signed_load_g'];pos=place(a['massNode']);expect=a['zeroCenter'][1]-a['metersPerG']*g
    close(pos.y,expect);families=[len(objects[n].data.shape_keys.key_blocks) for n in c['standInNodes']];assert families==[13,13]
    current[tag]=dict(signedG=g,massWorldY=pos.y,idealWorldY=expect,nativeGasFraction=profile['gas_fraction'](profile['signed_reach'](g)))
assert current['anchor']['signedG']>.99 and current['braking']['signedG']<-.01 and abs(current['docked']['signedG'])<.001
state(1);mass=place(a['massNode']);button=place(a['testNode']);setp(a['node'],'test_stroke',1.);state(1)
move=place(a['massNode'])-mass;press=place(a['testNode'])-button;close(move.y,-.0162);close(press.z,-.009)
setp(a['node'],'test_stroke',0.);state(1);button=place(c['primerNode']);setp(c['node'],'primer_stroke',1.);state(1)
prime=place(c['primerNode'])-button;close(prime.x,.009);tilt=objects[c['gasNode']].evaluated_get(tree).rotation_euler.x;close(tilt,.125)
setp(c['node'],'primer_stroke',0.);state(1)
for name in ('cloth_berth_quilt','cloth_berth_curtain'):
    assert [u.name for u in objects[name].data.uv_layers]==['Physical UV','Deform UV']
for name in ('loom_service_power','loom_service_fiber'):
    assert {'Secured • at rest','Low apparent gravity','Guide sway'}<=set(objects[name].data.shape_keys.key_blocks.keys())
tail='curtain_ring_07';fixed='curtain_ring_00';x0=place(tail);anchor=place(fixed)
setp('prop_privacy_curtain','drawn',1.);state(1);travel=place(tail)-x0;close(travel.z,1.86);close((place(fixed)-anchor).length,0.)
cloth=cloud('cloth_berth_curtain');width=max(p.z for p in cloth)-min(p.z for p in cloth);assert 2.229<width<2.25,width
setp('prop_privacy_curtain','drawn',0.);state(1);rest=cloud('cloth_berth_quilt')
index=min([i for i,p in enumerate(rest) if p.y>.966],key=lambda i:(rest[i].x+1.722)**2+(rest[i].z-.156)**2)
setp('prop_bunk','occupied',1.);state(1);depression=rest[index].y-cloud('cloth_berth_quilt')[index].y;assert .025<depression<.043,depression
images=[i for i in bpy.data.images if i.source=='FILE' and i.users];missing=[i.name for i in images if not i.packed_file];assert not missing,missing
receipt=dict(ordinaryInteractiveRoots=len(nodes),instrumentAccessories=5,furnishingSections=13,packedFileImages=len(images),
    states=current,testPointerDeltaM=move.y,testPlungerTravelM=press.z,primerTravelM=prime.x,primerSurfaceTiltDeg=math.degrees(tilt),
    drawnFabricSpanM=width,leadCarrierTravelM=travel.z,occupiedQuiltDepressionM=depression)
(reports/'native-check.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
