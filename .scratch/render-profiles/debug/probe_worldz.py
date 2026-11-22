# Probe: render benchy with layer-lines driven by WORLD-space Z (Option B)
# instead of Generated coords (Option A). If walls show ridges, the Generated
# axis mapping is the bug.
import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
IN, OUT = argv[0], argv[1]
LAYER_SPACING = float(argv[2]) if len(argv) > 2 else 0.0067  # scene units
STRENGTH = float(argv[3]) if len(argv) > 3 else 0.4

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_mesh.stl(filepath=IN)
obj = [o for o in bpy.data.objects if o.type=="MESH"][0]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
mins = Vector((min(c[i] for c in corners) for i in range(3)))
maxs = Vector((max(c[i] for c in corners) for i in range(3)))
size = max(maxs[i]-mins[i] for i in range(3))
scale = 2.0/size
center = (mins+maxs)/2
obj.scale = (scale,scale,scale)
obj.location = Vector((-center.x*scale, -center.y*scale, -mins.z*scale))
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

mat = bpy.data.materials.new("M"); mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
def lin(c): return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
bsdf.inputs["Base Color"].default_value = (lin(0.102),)*3 + (1.0,)
bsdf.inputs["Roughness"].default_value = 0.3
nt = mat.node_tree
geom = nt.nodes.new("ShaderNodeNewGeometry")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
mult = nt.nodes.new("ShaderNodeMath"); mult.operation='MULTIPLY'
mult.inputs[1].default_value = 2.0*math.pi/LAYER_SPACING
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = STRENGTH
bump.inputs["Distance"].default_value = 0.5*LAYER_SPACING
nt.links.new(geom.outputs["Position"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], mult.inputs[0])
nt.links.new(mult.outputs[0], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
obj.data.materials.append(mat)
for p in obj.data.polygons: p.use_smooth = True

# ground
mesh = bpy.data.meshes.new("G"); half=50.0
mesh.from_pydata([(-half,-half,0),(half,-half,0),(half,half,0),(-half,half,0)],[],[(0,1,2,3)])
g = bpy.data.objects.new("G", mesh); bpy.context.collection.objects.link(g)
if hasattr(g,"is_shadow_catcher"): g.is_shadow_catcher=True

def light(name, loc, energy, size, shadow=True):
    d = bpy.data.lights.new(name,"AREA"); d.energy=energy; d.shape="DISK"; d.size=size; d.use_shadow=shadow
    o = bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o); o.location=loc
    o.rotation_euler=((Vector((0,0,1))-o.location).to_track_quat("-Z","Y").to_euler())
light("Key",(4,-3,6),150,1.5); light("Fill",(-4,-2,3),60,4.0,False); light("Rim",(1,5,7),250,3.0,False)

bbox=[Vector(c) for c in obj.bound_box]; cen=sum(bbox,Vector())/8
radius=max((c-cen).length for c in bbox)
cam_d = bpy.data.cameras.new("C"); cam_d.angle=math.radians(40)
cam = bpy.data.objects.new("C",cam_d); bpy.context.collection.objects.link(cam)
dist = radius/math.tan(math.radians(40)/2)*1.15
az,el = math.radians(45), math.radians(28)
dirv = Vector((math.cos(el)*math.cos(az), math.cos(el)*math.sin(az), math.sin(el)))
cam.location = cen + dirv*dist
cam.rotation_euler = (cen-cam.location).to_track_quat("-Z","Y").to_euler()
bpy.context.scene.camera = cam

w = bpy.data.worlds.new("W"); w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(1,1,1,1)
w.node_tree.nodes["Background"].inputs[1].default_value=0.35
bpy.context.scene.world=w
sc = bpy.context.scene
sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=48
sc.cycles.use_adaptive_sampling=True; sc.cycles.adaptive_threshold=0.02
sc.cycles.max_bounces=4; sc.cycles.use_denoising=True
try: sc.view_layers[0].cycles.denoiser="OPENIMAGEDENOISE"
except TypeError: pass
sc.render.resolution_x=512; sc.render.resolution_y=512; sc.render.resolution_percentage=100
sc.view_settings.view_transform="Standard"
sc.render.image_settings.file_format="PNG"; sc.render.film_transparent=True
sc.render.filepath=OUT
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
