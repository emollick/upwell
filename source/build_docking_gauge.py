"""Build the Blender master and both runtime meshes of the collar travel indicator."""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web/assets/docking"
UNITY = ROOT / "unity/Assets/Upwell/Resources/Docking"
MASTER = ROOT / "blender/equipment/docking"
RADIUS = .077
ARC = 118


def print_face():
    from PIL import Image, ImageDraw, ImageFont
    import random

    size = 768
    image = Image.new("RGB", (size, size))
    rng = random.Random(7207)
    image.putdata([(v, v - 5, v - 21) for v in
                   (max(226, min(240, round(rng.gauss(234, 1.65)))) for _ in range(size * size))])
    d = ImageDraw.Draw(image)
    ink, oxide = "#29302d", "#256056"
    fontfile = next((p for p in ("C:/Windows/Fonts/bahnschrift.ttf", "DejaVuSans.ttf")
                     if Path(p).is_file()), "DejaVuSans.ttf")
    def facefont(points):
        return ImageFont.truetype(str(fontfile), points)
    def polar(angle, radius):
        rad = math.radians(angle)
        return size / 2 + math.sin(rad) * radius, size / 2 - math.cos(rad) * radius
    def put(at, copy, font, fill=ink):
        d.text(at, copy, fill=fill, font=facefont(font), anchor="mm")

    for i in range(37):
        angle = -ARC + i / 36 * ARC * 2
        is_major = i % 6 == 0
        d.line([polar(angle, 321 if is_major else 338 if i % 2 == 0 else 347),
                polar(angle, 358)], fill=ink, width=6 if is_major else 3)
        if is_major:
            put(polar(angle, 279), str(i // 2), 47)
    for q in range(91):
        angle = 106 + q * .131
        d.line([polar(angle, 364), polar(angle, 372)], fill=oxide, width=3)
    put((384, 244), "CLAMP TRAVEL", 30)
    put((384, 472), "mm", 44)
    put((384, 541), "ASTER   /   03", 21)
    put((384, 602), "CONTACT", 25, oxide)
    d.line([(321, 576), (447, 576)], fill="#899087", width=2)
    UNITY.mkdir(parents=True, exist_ok=True)
    image.save(UNITY / "ClampEnamel.png", optimize=True)


def build():
    import bpy
    from mathutils import Matrix

    for folder in (WEB, UNITY, MASTER):
        folder.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def material(name, color, metallic, rough):
        m = bpy.data.materials.new(name)
        rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (0, 2, 4))
        linear = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)
        m.use_nodes = True
        shader = m.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = (*linear, 1)
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Roughness"].default_value = rough
        m.diffuse_color = (*linear, 1)
        return m

    body = material("ClampCasting", "536160", .61, .43)
    satin = material("ClampSteel", "9ca6a2", .83, .30)
    rubber = material("ClampPacking", "242a29", .04, .70)
    dark = material("ClampPointer", "303b39", .28, .38)
    red = material("ClampVermilion", "b74522", .12, .37)
    face = material("ClampEnamel", "ffffff", .03, .53)
    tex = face.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(UNITY / "ClampEnamel.png"))
    face.node_tree.links.new(tex.outputs["Color"], face.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    parts, needle = [], []
    def add(obj, mat, moving=False):
        obj.data.materials.append(mat)
        (needle if moving else parts).append(obj)
        return obj

    def turned(profile, mat, count=96, moving=False, center=(0, 0)):
        # Lathed profile, open inner surface behind the face. Each bend catches a different highlight.
        verts = [(center[0] + r * math.cos(i * 2 * math.pi / count),
                  center[1] + r * math.sin(i * 2 * math.pi / count), z)
                 for r, z in profile for i in range(count)]
        polys = [(j * count + i, j * count + (i + 1) % count,
                  (j + 1) * count + (i + 1) % count, (j + 1) * count + i)
                 for j in range(len(profile) - 1) for i in range(count)]
        mesh = bpy.data.meshes.new(mat.name)
        mesh.from_pydata(verts, [], polys)
        mesh.update()
        obj = bpy.data.objects.new(mat.name, mesh)
        bpy.context.collection.objects.link(obj)
        for p in mesh.polygons:
            p.use_smooth = True
        return add(obj, mat, moving)

    def prism(points, z, height, mat, moving=False):
        n = len(points)
        verts = [(x, y, z + h) for h in (0, height) for x, y in points]
        polys = [tuple(reversed(range(n))), tuple(range(n, n * 2))]
        polys.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
        mesh = bpy.data.meshes.new(mat.name)
        mesh.from_pydata(verts, [], polys)
        mesh.update()
        obj = bpy.data.objects.new(mat.name, mesh)
        bpy.context.collection.objects.link(obj)
        return add(obj, mat, moving)

    turned([(.048, -.062), (.060, -.060), (.063, -.036), (.081, -.029), (.086, -.022),
            (.086, -.010), (.084, -.008)], body)
    turned([(.084, -.009), (.087, -.0065), (.087, -.004), (.084, -.0025)], rubber)
    turned([(.081, -.005), (.086, -.003), (.087, 0), (.0858, .0045),
            (.083, .0068), (.078, .0068), (.0765, .004), (.0758, -.002)], satin)
    turned([(.077, -.004), (.0787, -.002), (.0777, .0018), (.0755, .0018)], rubber)
    # Recessed fastener heads with actual stamped drive slots.
    for angle in (32, 148, 212, 328):
        theta = math.radians(angle)
        x, y = .0811 * math.sin(theta), .0811 * math.cos(theta)
        turned([(.0035, .0057), (.0031, .0069), (.00001, .0069)], dark, 16, center=(x, y))
        prism([(x-.0017,y-.0004),(x+.0017,y-.0004),(x+.0017,y+.0004),(x-.0017,y+.0004)], .0069, .00012, rubber)
    pts = [(RADIUS * math.cos(i * math.tau / 96), RADIUS * math.sin(i * math.tau / 96)) for i in range(96)]
    dial = prism(pts, -.0042, .0009, face)
    uv = dial.data.uv_layers.new(name="Enamel print")
    for loop in dial.data.loops:
        x, y, _ = dial.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (.5 + x / (2 * RADIUS), .5 + y / (2 * RADIUS))
    prism([(-.0038,-.021),(.0038,-.021),(.003,.011),(.0009,.0675),(-.0009,.0675),(-.003,.011)], -.0014, .0018, dark, True)
    prism([(-.00155,.048),(.00155,.048),(.00065,.0685),(-.00065,.0685)], .00042, .0003, red, True)
    turned([(.0094, -.001), (.0105, .001), (.0082, .0033), (.00001, .0033)], satin, 48, True)
    turned([(.0042, .0025), (.0036, .0041), (.00001, .0041)], dark, 36, True)
    # The model axes are manufactured face-right, face-up and toward the viewer.
    # This rigid rotation installs the face looking aft from inside the service lock.
    install = Matrix(((-1,0,0,0),(0,0,1,0),(0,1,0,0),(0,0,0,1)))
    def bundle(meshes, name):
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        obj = bpy.context.object
        obj.name = name
        obj.data.transform(install)
        return obj
    fixed = bundle(parts, "clamp_gauge_body")
    pointer = bundle(needle, "clamp_gauge_needle")
    fixed.select_set(True)
    pointer.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(WEB / "ClampIndicator.glb"), export_format="GLB",
                              use_selection=True, export_animations=False, export_yup=True)
    bpy.ops.export_scene.fbx(filepath=str(UNITY / "ClampIndicator.fbx"), use_selection=True,
                             axis_forward="-Z", axis_up="Y", object_types={"MESH"},
                             bake_space_transform=True, bake_anim=False, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", path_mode="STRIP", add_leaf_bones=False)
    tex.image.pack()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(MASTER / "ClampIndicator.blend"), compress=True)


if __name__ == "__main__":
    try:
        import bpy
    except ImportError:
        print_face()
    else:
        build()
