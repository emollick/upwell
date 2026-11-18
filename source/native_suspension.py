"""Editable, lightly damped trim response to guide engagement and effective gravity.

Run after the unposed GLBs and FBXs are emitted, so the runtime solvers receive
the same rest geometry, anchor positions and clearance limits as the Blender rig.
"""
import runpy
ride=runpy.run_path(str(ROOT/"source"/"ascent_geometry.py"))
for index,(name,d) in enumerate(flex_parts.items()):
    g=groups[(d["room"],name)];ob=g.mesh
    ob.shape_key_add(name="Under one g",from_mix=False)
    sway=ob.shape_key_add(name="Lateral deflection",from_mix=False)
    lift=ob.shape_key_add(name="Reduced apparent gravity",from_mix=False)
    p=d["points"];lengths=[0.]
    for a,b in zip(p[:-1],p[1:]):lengths.append(lengths[-1]+(b-a).length)
    pins=[lengths[k] for k in d["pins"]]
    def anchor_weight(vertex):
        best=(float("inf"),0.)
        for j,(a,b) in enumerate(zip(p[:-1],p[1:])):
            seg=b-a;u=max(0,min(1,(vertex-a).dot(seg)/max(.0000001,seg.length_squared)))
            dv=(vertex-a-seg*u).length_squared
            if dv<best[0]:best=(dv,lengths[j]+u*seg.length)
        w=min(abs(best[1]-q) for q in pins)/max(.001,lengths[-1]*(.45 if len(pins)>1 and d["pins"][-1]==len(p)-1 else .90))
        return min(1,w)**.77
    for j,vertex in enumerate(g.verts):
        w=anchor_weight(vertex);base=ob.data.vertices[j].co
        sway.data[j].co=base+v(blender((d["limit"]*.80*w,0,d["limit"]*.39*w)))
        lift.data[j].co=base+v(blender((0,d["limit"]*.70*w,0)))
    sway.slider_min=-1.;sway.slider_max=1.;lift.slider_min=0.;lift.slider_max=1.
    for sec in range(361):
        km=ride["height"](sec);gravity=max(0,(6371/(6371+km))**2-(6371+km)/42157*(6371/42157)**2)
        pulse=sum(math.sin((sec-t)*2.51)*math.exp(-(sec-t)*.74)*amp for t,amp in ((8,1),(22,.42),(134,.32),(192,.35),(339,.38),(353,.82)) if sec>=t)
        sway.value=max(-1,min(1,pulse*(.89+.08*math.sin(index))+math.sin(sec*.91+index)*.041))
        lift.value=max(0,min(1,(1-gravity)*.76))
        frame=ride["frame_at"](sec)
        sway.keyframe_insert("value",frame=frame);lift.keyframe_insert("value",frame=frame)
exec(compile((ROOT/"source"/"native_gravity.py").read_text(),str(ROOT/"source"/"native_gravity.py"),"exec"))
scene.frame_set(88)
bpy.ops.wm.save_as_mainfile(filepath=str(blendfile),compress=True)
