"""Blender 3.6 headless studio render, run as:

    blender --background --python blender_studio.py -- \
        --input model.stl --output render.png \
        --color 0.10 0.10 0.10 --roughness 0.3 --resolution 1024

Scene per .scratch/studio-render/spec.md: white sweep + shadow-catcher ground,
3-point area-light rig, single Principled BSDF, Cycles CPU + OIDN denoise.
Camera params (--azimuth/--elevation/--fov/--target) are fixed defaults in
ticket 02; ticket 03 (Camera Intent) passes real values from the preview.
"""

import argparse
import math
import sys

import bpy
from mathutils import Vector

# Model is normalized so its largest dimension equals this (scene units)
STANDARD_SIZE = 2.0
FRAME_MARGIN = 1.15  # breathing room around the model in frame


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--color", type=float, nargs=3, default=[0.102, 0.102, 0.102])
    parser.add_argument("--roughness", type=float, default=0.3)
    parser.add_argument("--resolution", type=int, default=1024)
    # Camera Intent (ticket 03): direction + target + FOV
    parser.add_argument("--azimuth", type=float, default=45.0)
    parser.add_argument("--elevation", type=float, default=28.0)
    parser.add_argument("--fov", type=float, default=40.0)
    parser.add_argument("--target", type=float, nargs=3, default=None)
    return parser.parse_args(argv)


def import_mesh(filepath):
    before = set(bpy.data.objects)
    lower = filepath.lower()
    if lower.endswith(".stl"):
        bpy.ops.import_mesh.stl(filepath=filepath)
    elif lower.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=filepath)
    elif lower.endswith(".ply"):
        bpy.ops.wm.ply_import(filepath=filepath)
    else:
        raise ValueError(f"Unsupported mesh format: {filepath}")
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not imported:
        raise ValueError(f"No mesh found in {filepath}")
    return imported


def join_objects(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def normalize(model):
    """Center on origin, base on z=0, largest dimension = STANDARD_SIZE."""
    bpy.context.view_layer.objects.active = model
    bpy.ops.object.select_all(action="DESELECT")
    model.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    corners = [model.matrix_world @ Vector(c) for c in model.bound_box]
    mins = Vector((min(c[i] for c in corners) for i in range(3)))
    maxs = Vector((max(c[i] for c in corners) for i in range(3)))
    size = max(maxs[i] - mins[i] for i in range(3))
    if size <= 0:
        raise ValueError("Model has zero size")

    scale = STANDARD_SIZE / size
    center = (mins + maxs) / 2
    model.scale = (scale, scale, scale)
    model.location = Vector((-center.x * scale, -center.y * scale, -mins.z * scale))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bbox = [Vector(c) for c in model.bound_box]
    center = sum(bbox, Vector()) / 8
    radius = max((c - center).length for c in bbox)
    return center, radius


def apply_material(model, color, roughness):
    def srgb_to_linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    material = bpy.data.materials.new("StudioMaterial")
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (
        srgb_to_linear(color[0]), srgb_to_linear(color[1]), srgb_to_linear(color[2]), 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if model.data.materials:
        model.data.materials[0] = material
    else:
        model.data.materials.append(material)

    for polygon in model.data.polygons:
        polygon.use_smooth = True
    if hasattr(model.data, "use_auto_smooth"):
        model.data.use_auto_smooth = True


def add_area_light(name, location, energy, size, color=(1.0, 1.0, 1.0), target=Vector((0, 0, 1)), shadow=True):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    data.use_shadow = shadow
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def add_ground():
    mesh = bpy.data.meshes.new("Ground")
    half = 50.0
    mesh.from_pydata(
        [(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)],
        [],
        [(0, 1, 2, 3)],
    )
    ground = bpy.data.objects.new("Ground", mesh)
    bpy.context.collection.objects.link(ground)
    if hasattr(ground, "is_shadow_catcher"):
        ground.is_shadow_catcher = True
    else:  # fallback: plain white floor if shadow catchers are unavailable
        material = bpy.data.materials.new("GroundMaterial")
        material.use_nodes = True
        material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 1, 1, 1)
        material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
        ground.data.materials.append(material)
    return hasattr(ground, "is_shadow_catcher") and ground.is_shadow_catcher


def add_camera(target, radius, azimuth, elevation, fov):
    data = bpy.data.cameras.new("Camera")
    data.angle = math.radians(fov)
    camera = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(camera)

    distance = radius / math.tan(math.radians(fov) / 2) * FRAME_MARGIN
    direction = Vector((
        math.cos(math.radians(elevation)) * math.cos(math.radians(azimuth)),
        math.cos(math.radians(elevation)) * math.sin(math.radians(azimuth)),
        math.sin(math.radians(elevation)),
    ))
    camera.location = Vector(target) + direction * distance
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera
    return camera


def setup_white_compositor(scene):
    """Composite the transparent render over pure white (255) background.

    A highlight clip pushes near-whites (soft floor gradient) to pure 255 white
    while leaving the model and its contact shadow untouched. The ramp drives a
    mix factor toward white so the model's color survives (feeding the image
    through the ramp directly would map everything to grayscale).
    """
    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links
    nodes.clear()
    render_layers = nodes.new("CompositorNodeRLayers")
    alpha_over = nodes.new("CompositorNodeAlphaOver")
    alpha_over.inputs[1].default_value = (1.0, 1.0, 1.0, 1.0)
    clip = nodes.new("CompositorNodeValToRGB")
    clip.color_ramp.elements[0].position = 0.0
    clip.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    clip.color_ramp.elements[1].position = 0.85
    clip.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    # compositor values are linear: 0.83 linear ~= sRGB 230
    hold = clip.color_ramp.elements.new(0.83)
    hold.color = (0.83, 0.83, 0.83, 1.0)
    whiten = nodes.new("CompositorNodeMixRGB")
    whiten.blend_type = "MIX"
    whiten.inputs[2].default_value = (1.0, 1.0, 1.0, 1.0)
    composite = nodes.new("CompositorNodeComposite")
    links.new(render_layers.outputs["Image"], alpha_over.inputs[2])
    links.new(alpha_over.outputs["Image"], clip.inputs["Fac"])
    links.new(alpha_over.outputs["Image"], whiten.inputs[1])
    links.new(clip.outputs["Image"], whiten.inputs[0])
    links.new(whiten.outputs["Image"], composite.inputs["Image"])


def main():
    args = parse_args()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    model = join_objects(import_mesh(args.input))
    center, radius = normalize(model)
    apply_material(model, args.color, args.roughness)

    has_shadow_catcher = add_ground()
    target = args.target if args.target else (0.0, 0.0, center.z)

    # 3-point area-light rig (key / fill / rim); only the key casts a shadow so
    # the floor gets one clean soft contact shadow
    add_area_light("Key", (4, -3, 6), energy=150, size=1.5)
    add_area_light("Fill", (-4, -2, 3), energy=60, size=4.0, shadow=False)
    add_area_light("Rim", (1, 5, 7), energy=250, size=3.0, shadow=False)

    add_camera(target, radius, args.azimuth, args.elevation, args.fov)

    # World lights the scene; transparent film keeps it out of the background
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    scene.world = world
    scene.render.film_transparent = has_shadow_catcher

    if has_shadow_catcher:
        setup_white_compositor(scene)

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    try:
        scene.view_layers[0].cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass  # older Blender: default denoiser is fine
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = args.output

    bpy.ops.render.render(write_still=True)
    print(f"[blender_studio] wrote {args.output}")


if __name__ == "__main__":
    main()
