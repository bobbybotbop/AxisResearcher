import bpy, sys
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_mesh.stl(filepath=argv[0])
obj = [o for o in bpy.data.objects if o.type=="MESH"][0]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# world bbox
corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
mins = Vector((min(c[i] for c in corners) for i in range(3)))
maxs = Vector((max(c[i] for c in corners) for i in range(3)))
print("WORLD bbox min", tuple(round(v,3) for v in mins), "max", tuple(round(v,3) for v in maxs))
dims = tuple(round(maxs[i]-mins[i],3) for i in range(3))
print("WORLD dims (x,y,z):", dims)
# A benchy is taller (z) than wide? Actually benchy: ~60mm tall, ~62mm long, ~31mm wide
