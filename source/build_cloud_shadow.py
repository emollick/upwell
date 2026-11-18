"""Project Car 07's opaque Blender mesh in the morning solar direction."""
import json
import struct
import zlib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(bpy.data.filepath).resolve().parents[1]
vertices, faces = [], []

def add_mesh(obj, translation=Vector((0, 0, 0))):
    if obj.type != 'MESH':
        return
    mesh = obj.data
    mesh.calc_loop_triangles()
    offset = len(vertices)
    for vertex in mesh.vertices:
        p = obj.matrix_world @ vertex.co
        vertices.append(Vector((p.x, p.z, -p.y)) + translation)
    clear = {i for i, m in enumerate(mesh.materials) if m and any(
        name in m.name.lower() for name in ('glass', 'surface_window', 'trace_', 'stencil'))}
    faces.extend(tuple(offset+i for i in tri.vertices) for tri in mesh.loop_triangles if tri.material_index not in clear)

for compartment in ('Observation', 'Berth', 'Service'):
    for obj in bpy.data.collections[compartment].all_objects:
        add_mesh(obj)

layout = json.loads((root/'web/assets/guideway/layout.json').read_text())
for obj in bpy.data.collections['Guideway · local source parts'].all_objects:
    if obj.type == 'MESH' and ('bogie' in obj.name.lower() or 'roller' in obj.name.lower()):
        for track in layout['placements']:
            if track['id'] != 'counterline':
                add_mesh(obj, Vector(track['position']))

tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
solar = Vector((.9652923, .1580617, -.2079117)).normalized()
across = Vector((-solar.z, 0, solar.x)).normalized()
up = across.cross(solar)
origin = Vector((0, 1.54, 0))
width, height, pitch = 256, 128, .09375
mask = np.zeros((height,width), dtype=bool)
for r,c in np.ndindex(mask.shape):
    p = origin + across*((c+.5-width/2)*pitch) + up*((r+.5-height/2)*pitch)
    mask[r,c] = tree.ray_cast(p-solar*26,solar,52)[0] is not None
edge = np.zeros_like(mask)
edge[1:-1,1:-1] = ((mask[1:-1,1:-1] != mask[:-2,1:-1]) | (mask[1:-1,1:-1] != mask[2:,1:-1]) |
                    (mask[1:-1,1:-1] != mask[1:-1,:-2]) | (mask[1:-1,1:-1] != mask[1:-1,2:]))
boundary = np.argwhere(edge).astype(np.float32)
distance = np.empty(mask.shape,dtype=np.float32)
assert 200 < len(boundary) < 4000 and not mask[0,:].any() and not mask[-1,:].any()
for r in range(height):
    dy2 = (boundary[:,0]-r)**2
    dx2 = (boundary[None,:,1]-np.arange(width)[:,None])**2
    distance[r] = np.sqrt((dx2+dy2).min(axis=1))*pitch
distance[mask] *= -1
alpha = np.round(np.clip(.5+distance/12,0,1)*255).astype(np.uint8)
pixels = np.full((height,width,4),255,dtype=np.uint8)
pixels[:,:,3] = alpha[::-1]
def chunk(tag, data):
    return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
raw = b''.join(b'\0'+row.tobytes() for row in pixels)
png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
for name in ('web/assets/planet/car-sun-mask.png','unity/Assets/Upwell/Resources/CarSunMask.png'):
    (root/name).write_bytes(png)
print('Projected',len(faces),'triangles, opaque area',round(float(mask.sum())*pitch**2,2),'square metres.')
