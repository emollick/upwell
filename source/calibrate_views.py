"""Calibrate the three material-reference cameras from the saved Blender project.

The ray buffer contains camera-axis depth at pixel centers, in integer centimetres.
The external environment and see-through pressure glazing never write depth.
"""
from pathlib import Path
import json
import math
import struct
import zlib

import bpy
import numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree


root=Path(bpy.data.filepath).resolve().parents[1]
target=root/"art"/"matched";target.mkdir(parents=True,exist_ok=True)
W,H=1600,900
scene=bpy.context.scene;scene.frame_set(88)
deps=bpy.context.evaluated_depsgraph_get()
basis=Matrix(((1.,0.,0.,0.),(0.,0.,-1.,0.),(0.,1.,0.,0.),(0.,0.,0.,1.)))
verts=[];faces=[]
for obj in bpy.data.objects:
    if obj.type!="MESH" or not obj.name.startswith(("shell_","geo_")):continue
    mesh=obj.data;offset=len(verts);world=obj.matrix_world
    verts.extend(world@p.co for p in mesh.vertices)
    for poly in mesh.polygons:
        m=mesh.materials[poly.material_index]
        if m.name in ("Clear_Glass","Surface_window","Hull_Stencils"):continue
        faces.append(tuple(offset+j for j in poly.vertices))
tree=BVHTree.FromPolygons(verts,faces,all_triangles=False)
def encode_png(path,arr):
    height,width=arr.shape
    def chunk(kind,body):
        return struct.pack(">I",len(body))+kind+body+struct.pack(">I",zlib.crc32(kind+body)&0xffffffff)
    raw=b"".join(b"\0"+row.tobytes() for row in arr.astype(">u2"))
    header=struct.pack(">IIBBBBB",width,height,16,0,0,0,0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",header)+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))
def rows(matrix):
    return [[float(z) for z in row] for row in matrix]
def column_major(matrix):
    return [float(matrix[r][c]) for c in range(4) for r in range(4)]
out={"coordinateSystem":"glTF / Three world coordinates in metres, +Y up, +Z aft",
     "width":W,"height":H,"frame":88,"depthEncoding":"unsigned 16-bit grayscale PNG, linear positive axial camera distance in centimetres = round(-viewZ * 100). Zero means no opaque interior intersection.",
     "projection":"OpenGL NDC with near=-1 far=+1; ndc=(VP*vec4(world,1)).xyz/clip.w; u=ndc.x*.5+.5, topDownV=.5-ndc.y*.5. PNG row 0 is top. Pixel-center samples. Column-major arrays suit Three.Matrix4.fromArray.",
     "occluders":"All three as-built room shells and props at their closed/resting poses. Clear glazing, exterior and alpha-cutout stencil labels do not write depth. Moving objects should stop sampling when displaced. Printed surfaces on opaque equipment remain occluders.",
     "rooms":{}}
for rid,name in (("observation","Observation / forward"),("berth","Sleeper / aft"),("service","Service / aft")):
    cam=bpy.data.objects[name].evaluated_get(deps)
    vw=cam.matrix_world.inverted()@basis;proj=cam.calc_matrix_camera(deps,x=W,y=H,scale_x=1,scale_y=1);vp=proj@vw
    world=cam.matrix_world;eye=world.translation.copy();r=world.to_3x3()@Vector((1,0,0));u=world.to_3x3()@Vector((0,1,0));back=world.to_3x3()@Vector((0,0,1))
    out["rooms"][rid]={"camera":name,"depthFile":rid+"-depth.png","near":cam.data.clip_start,"far":cam.data.clip_end,
        "eyeWeb":list((basis.inverted()@eye.to_4d()).xyz),"forwardWeb":list((basis.inverted().to_3x3()@(-back))),
        "viewProjectionColumnMajor":column_major(vp),"viewColumnMajor":column_major(vw),
        "projectionColumnMajor":column_major(proj),"viewProjectionRows":rows(vp),"viewRows":rows(vw)}
    # Publish camera geometry before the long ray pass so runtime work can start.
    (target/"cameras.json").write_text(json.dumps(out,indent=2))
    xs=(2*(np.arange(W)+.5)/W-1+proj[0][2])/proj[0][0]
    ys=(1-2*(np.arange(H)+.5)/H+proj[1][2])/proj[1][1]
    dx=[r*float(x) for x in xs];buf=np.zeros((H,W),dtype=np.uint16)
    for y,dy in enumerate(ys):
        axis=u*float(dy)-back
        norm=np.sqrt(1+xs*xs+dy*dy)
        for x,direction_x in enumerate(dx):
            direction=axis+direction_x;direction.normalize()
            loc,_,_,distance=tree.ray_cast(eye,direction,40)
            if loc is not None:
                buf[y,x]=min(65535,max(1,round(distance/norm[x]*100)))
    encode_png(target/(rid+"-depth.png"),buf)
    print(rid, int((buf>0).sum()),"opaque pixels; maximum",buf.max(),"cm",flush=True)
print("Camera calibration complete.",flush=True)
