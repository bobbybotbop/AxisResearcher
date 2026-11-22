# Sweep bump Distance on the REAL production node graph (Generated + Wave Z,
# Scale=300 for 0.2mm) to find the smallest Distance that puts visible ridges
# on the cabin walls. Renders 4 values, crops the wall region for inspection.
import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
IN, OUTDIR = argv[0], argv[1]
ASSUMED = 60.0; STANDARD_SIZE = 2.0; LAYER_MM = 0.2
SCALE = ASSUMED / LAYER_MM  # 300, matches production

for dist in [0.0033, 0.01, 0.02, 0.04]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_mesh.stl(filepath=IN)
    obj=[o for o in bpy.data.objects if o.type=="MESH"][0]
    bpy.context.view_layer.objects.active=obj; obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    corners=[obj.matrix_world@Vector(c) for c in obj.bound_box]
    mins=Vector((min(c[i] for c in corners) for i in range(3)))
    maxs=Vector((max(c[i] for c in corners) for i in range(3)))
    size=max(maxs[i]-mins[i] for i in range(3)); scale=STANDARD_SIZE/size; center=(mins+maxs)/2
    obj.scale=(scale,)*3; obj.location=Vector((-center.x*scale,-center.y*scale,-mins.z*scale))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mat=bpy.data.materials.new("M"); mat.use_nodes=True
    bsdf=mat.node_tree.nodes["Principled BSDF"]
    def lin(c): return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
    bsdf.inputs["Base Color"].default_value=(lin(0.102),)*3+(1.0,)
    bsdf.inputs["Roughness"].default_value=0.3
    nt=mat.node_tree
    tc=nt.nodes.new("ShaderNodeTexCoord")
    wave=nt.nodes.new("ShaderNodeTexWave"); wave.wave_type='BANDS'; wave.bands_direction='Z'; wave.wave_profile='SIN'
    wave.inputs["Scale"].default_value=SCALE
    bump=nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value=0.4
    bump.inputs["Distance"].default_value=dist
    nt.links.new(tc.outputs["Generated"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    obj.data.materials.append(mat)
    for p in obj.data.polygons: p.use_smooth=True
    mesh=bpy.data.meshes.new("G"); half=50.0
    mesh.from_pydata([(-half,-half,0),(half,-half,0),(half,half,0),(-half,half,0)],[],[(0,1,2,3)])
    g=bpy.data.objects.new("G",mesh); bpy.context.collection.objects.link(g)
    if hasattr(g,"is_shadow_catcher"): g.is_shadow_catcher=True
    def light(name,loc,energy,size,shadow=True):
        d=bpy.data.lights.new(name,"AREA"); d.energy=energy; d.shape="DISK"; d.size=size; d.use_shadow=shadow
        o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o); o.location=loc
        o.rotation_euler=((Vector((0,0,1))-o.location).to_track_quat("-Z","Y").to_euler())
    light("Key",(4,-3,6),150,1.5); light("Fill",(-4,-2,3),60,4.0,False); light("Rim",(1,5,7),250,3.0,False)
    bbox=[Vector(c) for c in obj.bound_box]; cen=sum(bbox,Vector())/8
    radius=max((c-cen).length for c in bbox)
    cd=bpy.data.cameras.new("C"); cd.angle=math.radians(40)
    cam=bpy.data.objects.new("C",cd); bpy.context.collection.objects.link(cam)
    d=radius/math.tan(math.radians(40)/2)*1.15
    az,el=math.radians(45),math.radians(28)
    dv=Vector((math.cos(el)*math.cos(az),math.cos(el)*math.sin(az),math.sin(el)))
    cam.location=cen+dv*d; cam.rotation_euler=(cen-cam.location).to_track_quat("-Z","Y").to_euler()
    bpy.context.scene.camera=cam
    w=bpy.data.worlds.new("W"); w.use_nodes=True
    w.node_tree.nodes["Background"].inputs[0].default_value=(1,1,1,1)
    w.node_tree.nodes["Background"].inputs[1].default_value=0.35
    bpy.context.scene.world=w
    sc=bpy.context.scene; sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=48
    sc.cycles.use_adaptive_sampling=True; sc.cycles.adaptive_threshold=0.02; sc.cycles.max_bounces=4
    sc.cycles.use_denoising=True
    try: sc.view_layers[0].cycles.denoiser="OPENIMAGEDENOISE"
    except TypeError: pass
    sc.render.resolution_x=512; sc.render.resolution_y=512; sc.render.resolution_percentage=100
    sc.view_settings.view_transform="Standard"; sc.render.image_settings.file_format="PNG"
    sc.render.film_transparent=True
    sc.render.filepath=f"{OUTDIR}/dist_{dist}.png"
    bpy.ops.render.render(write_still=True)
    print("wrote", dist)
