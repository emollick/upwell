"""Native Blender Earth + 3-D weather. No image sky/cloud backdrop.

Call build_native_weather(collection, altitude_km, weather_seconds, sun_direction).
Directions use web ENU (+X east,+Y up,+Z north); Blender basis is (x,-z,y).
Distances in scene are meters. Procedural volume nodes approximate the shared
web Perlin/Worley medium; native noise is not claimed bit-identical to the LUT.
"""
from pathlib import Path
import math
import bpy
from mathutils import Vector

EARTH_KM=6371.

def _math(nodes,links,op,a,b=None):
    n=nodes.new('ShaderNodeMath');n.operation=op
    for i,v in enumerate([a,b] if b is not None else [a]):
        if isinstance(v,(float,int)):n.inputs[i].default_value=v
        else:links.new(v,n.inputs[i])
    return n.outputs[0]

def _sphere(name,radius,collection,material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128,ring_count=64,radius=radius)
    ob=bpy.context.object;ob.name=name
    for c in tuple(ob.users_collection):c.objects.unlink(ob)
    collection.objects.link(ob);ob.data.materials.append(material)
    for p in ob.data.polygons:p.use_smooth=True
    return ob

def _band(nodes,links,height,lo,hi):
    d=_math(nodes,links,'DIVIDE',_math(nodes,links,'SUBTRACT',height,(lo+hi)/2),(hi-lo)/2)
    return _math(nodes,links,'MAXIMUM',_math(nodes,links,'SUBTRACT',1.,_math(nodes,links,'MULTIPLY',d,d)),0.)

def build_native_weather(collection=None,altitude_km=12,weather_seconds=0,sun_direction=(-.6,.72,.35),coverage=.58):
    if collection is None:
        collection=bpy.data.collections.new('Physical Earth and weather');bpy.context.scene.collection.children.link(collection)
    center=bpy.data.objects.new('Earth-fixed weather coordinates',None);collection.objects.link(center);center.scale=(1000.,)*3
    day_path=Path(__file__).resolve().parents[1]/'web/assets/planet/earth-day.webp'
    earthmat=bpy.data.materials.new('NASA geographic surface · physically solar lit');earthmat.use_nodes=True
    n=earthmat.node_tree.nodes;l=earthmat.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Roughness'].default_value=.64
    if day_path.exists():
        image=bpy.data.images.load(str(day_path),check_existing=True);image.pack()
        t=n.new('ShaderNodeTexImage');t.image=image;t.label='NASA BMNG geographic albedo ONLY';l.new(t.outputs['Color'],p.inputs['Base Color'])
    earth=_sphere('Earth · real 6371 km sphere',EARTH_KM*1000,collection,earthmat)
    earth.rotation_euler=(math.pi/2,0,math.radians(-126))

    cloudmat=bpy.data.materials.new('Advected multi-band cloud volume');cloudmat.use_nodes=True
    n=cloudmat.node_tree.nodes;l=cloudmat.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial');volume=n.new('ShaderNodeVolumePrincipled')
    volume.inputs['Color'].default_value=(.96,.98,1.,1.);volume.inputs['Anisotropy'].default_value=.58
    l.new(volume.outputs['Volume'],out.inputs['Volume'])
    coords=n.new('ShaderNodeTexCoord');coords.object=center
    length=n.new('ShaderNodeVectorMath');length.operation='LENGTH';l.new(coords.outputs['Object'],length.inputs[0])
    height=_math(n,l,'SUBTRACT',length.outputs['Value'],EARTH_KM)
    drift=n.new('ShaderNodeVectorMath');drift.operation='ADD';drift.name='Wind advection km';l.new(coords.outputs['Object'],drift.inputs[0])
    sep=n.new('ShaderNodeSeparateXYZ');l.new(drift.outputs['Vector'],sep.inputs[0])
    broad=n.new('ShaderNodeTexNoise');broad.inputs['Scale'].default_value=.07;l.new(drift.outputs['Vector'],broad.inputs['Vector'])
    streetphase=_math(n,l,'DIVIDE',_math(n,l,'ADD',_math(n,l,'MULTIPLY',sep.outputs['X'],.35),sep.outputs['Y']),2.8)
    streets=_math(n,l,'MAXIMUM',_math(n,l,'ADD',.15,_math(n,l,'SINE',streetphase)),0.)
    towers=_math(n,l,'MINIMUM',_math(n,l,'MAXIMUM',_math(n,l,'MULTIPLY',_math(n,l,'SUBTRACT',broad.outputs['Fac'],.54),7.),0.),1.)
    total=None;noise_nodes=[]
    # Shape noise and Voronoi erosion are evaluated in 3-D world coordinates.
    for label,lo,hi,scale,threshold,sigma in [('Marine cumulus',.7,3.5,.53,.45,.0032),('Anvil/altostratus',4.6,12.1,.18,.50,.0015),('Cirrus',10.8,13.6,.055,.64,.00007)]:
        shape=n.new('ShaderNodeTexNoise');shape.noise_dimensions='4D';shape.name=label+' evolving shape'
        shape.inputs['Scale'].default_value=scale;shape.inputs['Detail'].default_value=4.;shape.inputs['Roughness'].default_value=.62
        l.new(drift.outputs['Vector'],shape.inputs['Vector']);noise_nodes.append(shape)
        vor=n.new('ShaderNodeTexVoronoi');vor.distance='EUCLIDEAN';vor.feature='F1';vor.inputs['Scale'].default_value=scale*3.5;l.new(drift.outputs['Vector'],vor.inputs['Vector'])
        eroded=_math(n,l,'SUBTRACT',shape.outputs['Fac'],_math(n,l,'MULTIPLY',vor.outputs['Distance'],.11))
        cut=_math(n,l,'SUBTRACT',eroded,threshold-(coverage-.58)*.22)
        den=_math(n,l,'MINIMUM',_math(n,l,'MAXIMUM',_math(n,l,'MULTIPLY',cut,5.),0.),1.)
        if label.startswith('Marine'):den=_math(n,l,'MULTIPLY',den,streets)
        if label.startswith('Anvil'):den=_math(n,l,'MULTIPLY',den,towers)
        den=_math(n,l,'MULTIPLY',den,_band(n,l,height,lo,hi));den=_math(n,l,'MULTIPLY',den,sigma)
        total=den if total is None else _math(n,l,'ADD',total,den)
    l.new(total,volume.inputs['Density'])
    clouds=_sphere('Earth weather · actual scattering medium', (EARTH_KM+13.6)*1000,collection,cloudmat)

    atmomat=bpy.data.materials.new('Exponential blue atmospheric scattering');atmomat.use_nodes=True
    n=atmomat.node_tree.nodes;l=atmomat.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial')
    scatter=n.new('ShaderNodeVolumeScatter');scatter.inputs['Color'].default_value=(.32,.56,1.,1.);scatter.inputs['Anisotropy'].default_value=.15
    tc=n.new('ShaderNodeTexCoord');tc.object=center;length=n.new('ShaderNodeVectorMath');length.operation='LENGTH';l.new(tc.outputs['Object'],length.inputs[0])
    h=_math(n,l,'MAXIMUM',_math(n,l,'SUBTRACT',length.outputs['Value'],EARTH_KM),0.)
    exponent=_math(n,l,'MULTIPLY',h,-1/8);density=_math(n,l,'MULTIPLY',_math(n,l,'POWER',math.e,exponent),.000018)
    l.new(density,scatter.inputs['Density'])
    ozone=n.new('ShaderNodeVolumeAbsorption');ozone.inputs['Color'].default_value=(.35,1.,.045,1.)
    ozone_profile=_math(n,l,'MAXIMUM',_math(n,l,'SUBTRACT',1.,_math(n,l,'DIVIDE',_math(n,l,'ABSOLUTE',_math(n,l,'SUBTRACT',h,25.)),15.)),0.)
    l.new(_math(n,l,'MULTIPLY',ozone_profile,.000001881),ozone.inputs['Density'])
    add=n.new('ShaderNodeAddShader');l.new(scatter.outputs[0],add.inputs[0]);l.new(ozone.outputs[0],add.inputs[1]);l.new(add.outputs[0],out.inputs['Volume'])
    atmosphere=_sphere('Atmosphere · 120 km exponential medium',(EARTH_KM+120)*1000,collection,atmomat)
    light=bpy.data.lights.new('Shared physical Sun','SUN');light.energy=3.5;light.angle=.0093
    sun=bpy.data.objects.new('Shared physical Sun',light);collection.objects.link(sun)
    state=dict(earth=earth,clouds=clouds,atmosphere=atmosphere,center=center,sun=sun,drift=drift,noise_nodes=noise_nodes,collection=collection)
    update_native_weather(state,altitude_km,weather_seconds,sun_direction)
    for camera in bpy.data.cameras:camera.clip_end=max(camera.clip_end,1e9)
    return state

def update_native_weather(state,altitude_km,weather_seconds,sun_direction,frame=None):
    center=(0.,0.,-(EARTH_KM+max(0.,altitude_km))*1000.)
    for key in ['earth','clouds','atmosphere','center']:
        state[key].location=center
        if frame is not None:state[key].keyframe_insert('location',frame=frame)
    drift=state['drift'].inputs[1];drift.default_value=(-.018*weather_seconds,.007*weather_seconds,0.)
    if frame is not None:drift.keyframe_insert('default_value',frame=frame)
    for node in state['noise_nodes']:
        node.inputs['W'].default_value=weather_seconds*.0015
        if frame is not None:node.inputs['W'].keyframe_insert('default_value',frame=frame)
    direction=Vector((sun_direction[0],-sun_direction[2],sun_direction[1])).normalized()
    state['sun'].rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
    dip=math.acos(EARTH_KM/(EARTH_KM+max(0,altitude_km)))
    visibility=max(0.,min(1.,(math.asin(max(-1.,min(1.,sun_direction[1])))+dip+.00465)/.0093))
    state['sun'].data.energy=3.5*visibility
    if frame is not None:
        state['sun'].keyframe_insert('rotation_euler',frame=frame);state['sun'].data.keyframe_insert('energy',frame=frame)
    state['collection']['altitude_km']=altitude_km;state['collection']['weather_seconds']=weather_seconds
    state['collection']['provenance']='Procedural 3-D noise/Voronoi cloud volume; NASA geographic surface only; no photo backdrop.'
    return state
