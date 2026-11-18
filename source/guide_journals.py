"""Blender fabrication of the fixed retaining hardware for both guide bogies."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
web = root / "web/assets/guideway"
native = root / "unity/Assets/Upwell/Resources/GuidewayFinish"
layout = json.loads((web / "layout.json").read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)

# The seated washer is nitrided, the outer face a dull nickel surface, the
# narrow edge left by the turning operation still catches the inspection light.
finishes = [
    ("Journal_Black", 0x30383D, .77, .43),
    ("Journal_Nickel", 0x849196, .81, .36),
    ("Journal_Edge", 0x9DA3A0, .84, .32),
    ("Journal_Recess", 0x272E30, .57, .58),
    ("Journal_Seal", 0xB7763D, .13, .63),
]
materials = []
for name, rgb, metal, rough in finishes:
    def linear(value):
        v = value / 255
        return v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4
    color = [linear((rgb >> bit) & 255) for bit in (16, 8, 0)] + [1]
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    material.diffuse_color = color
    materials.append(material)

verts, faces, face_materials, normals = [], [], [], []


def blender(v):
    return Vector((v[0], -v[2], v[1]))


def face(points, slot, ns=None):
    index = len(verts)
    verts.extend(map(blender, points))
    faces.append(tuple(range(index, index + len(points))))
    face_materials.append(slot)
    if ns is None:
        n = (verts[index + 1] - verts[index]).cross(verts[index + 2] - verts[index]).normalized()
        normals.extend([n] * len(points))
    else:
        normals.extend([blender(n).normalized() for n in ns])


full = math.tau
for w, wheel in enumerate(layout["rollers"]):
    cx, cy, cz = wheel["pivot"]
    radius = wheel["radius"]
    for side in (-1, 1):
        # Each static axle has its own installed orientation. The paint bridges
        # nut and washer across an actual break so slip would be visible.
        rotation = .15 + 1.237 * w + side * .38
        def radial(a, r, hexagonal):
            offset = (a - rotation + math.pi / 6) % (math.pi / 3) - math.pi / 6
            return r * (math.cos(math.pi / 6) / math.cos(offset) if hexagonal else 1)
        def point(a, r, depth, hexagonal=False):
            rr = radial(a, r, hexagonal)
            return (cx + rr * math.cos(a), cy + rr * math.sin(a), cz + side * (.104 + depth))
        # r in units of bearing OD, depth above axle face, hexagonal section,
        # material on the strip from the previous station to this one.
        rings = [
            (.274, -.0040, False, 0), (.294, -.0010, False, 2),
            (.294, .0027, False, 0), (.279, .0052, False, 1),
            (.237, .0052, False, 0), (.232, .0044, True, 3),
            (.233, .0118, True, 0), (.219, .0152, True, 2),
            (.100, .0152, True, 1), (.087, .0131, True, 2),
            (.087, .0057, True, 3), (.062, .0054, False, 3),
            (.000, .0054, False, 3),
        ]
        count = 36
        for idx, (outer, dep, hexagonal, slot) in enumerate(rings[1:], 1):
            prev, prev_dep, prev_hex, _ = rings[idx - 1]
            for i in range(count):
                a = rotation + i * full / count
                b = rotation + (i + 1) * full / count
                coords = [point(a, prev * radius, prev_dep, prev_hex),
                          point(b, prev * radius, prev_dep, prev_hex),
                          point(b, outer * radius, dep, hexagonal)]
                if outer:
                    coords.append(point(a, outer * radius, dep, hexagonal))
                if side < 0:
                    coords.reverse()
                ns = None
                if not prev_hex and not hexagonal and outer and idx < 4:
                    # Smooth only around round turned features, keep the
                    # locknut's broached planes and hard corner transitions.
                    dr = (outer - prev) * radius
                    dd = dep - prev_dep
                    ns = [(dd * math.cos(q), dd * math.sin(q), -side * dr) for q in (a, b, b, a)]
                    if side < 0:
                        ns.reverse()
                face(coords, slot, ns)
        for low, high, height in ((.127, .191, .0154), (.247, .273, .0055)):
            a = rotation + .173
            coords = [point(a - .047, low * radius, height), point(a - .032, high * radius, height),
                      point(a + .033, high * radius, height), point(a + .048, low * radius, height)]
            if side < 0:
                coords.reverse()
            face(coords, 4)

mesh = bpy.data.meshes.new("Stepped washers, broached sockets and seal lacquer")
mesh.from_pydata(verts, [], faces)
mesh.update()
for material in materials:
    mesh.materials.append(material)
for poly, slot in zip(mesh.polygons, face_materials):
    poly.material_index = slot
    poly.use_smooth = True
mesh.normals_split_custom_set(normals)
retainers = bpy.data.objects.new("Stationary bearing retainers", mesh)
bpy.context.collection.objects.link(retainers)
retainers.select_set(True)
bpy.context.view_layer.objects.active = retainers
bpy.ops.export_scene.gltf(filepath=str(web / "journal-caps.glb"), export_format="GLB",
                          use_selection=True, export_yup=True, export_animations=False)
bpy.ops.export_scene.fbx(filepath=str(native / "journal-caps.fbx"), use_selection=True,
                         axis_forward="-Z", axis_up="Y", object_types={"MESH"}, bake_space_transform=True,
                         bake_anim=False, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                         use_triangles=True)
