"""Native Blender exterior and time-compressed ascent; loaded by build_car.py."""
ext=bpy.data.collections.new("Tether & Aster Reach")
scene.collection.children.link(ext);colls["exterior"]=ext
scene.frame_start=1;scene.frame_end=270;scene.render.fps=24
for frame,stage in ((1,"Marine layer"),(86,"Blue limb"),(165,"High orbit"),(225,"Aster Reach approach"),(270,"Capture")):
    scene.timeline_markers.new(stage,frame=frame)

# Native Earth albedo, physical atmospheric scattering and wind-advected clouds.
import runpy
astro=runpy.run_path(str(ROOT/"source"/"ascent_geometry.py"))
weather_impl=runpy.run_path(str(ROOT/"source"/"native_weather.py"))
weather=weather_impl["build_native_weather"](collection=ext,altitude_km=.007,weather_seconds=0,sun_direction=astro["sun_at"](0))
for second in range(0,361,3):
    altitude=astro["height"](second)
    weather_impl["update_native_weather"](weather,altitude+.007,second,astro["sun_at"](altitude),frame=astro["frame_at"](second))
world_nodes=scene.world.node_tree.nodes;world_links=scene.world.node_tree.links
background=world_nodes.get("Background")
background.inputs["Color"].default_value=(.0014,.0021,.0037,1);background.inputs["Strength"].default_value=.32

def local_sea():
    # The anchor's waterline is seven metres below the carriage. Actual swells
    # in the near field join the curved geographic surface beyond the pier.
    sz=121;span=18000.;vv=[];ff=[]
    def spacing(i):
        q=(i-(sz-1)/2)/((sz-1)/2)
        return math.copysign((abs(q)**3.14)*span,q)
    for j in range(sz):
        for i in range(sz):
            x,z=spacing(i),spacing(j);r2=x*x+z*z
            swell=(.19*math.sin(.151*x+.078*z)+.115*math.cos(.084*x-.181*z)+.050*math.sin(.399*z+.080*x))*math.exp(-r2/1.8e6)
            vv.append(blender((x,-6.96+swell-r2/(2*6371000),z)))
    for j in range(sz-1):
        for i in range(sz-1):
            q=j*sz+i;ff.append((q,q+sz,q+sz+1,q+1))
    me=bpy.data.meshes.new("Nearshore wave field");me.from_pydata(vv,[],ff)
    for p in me.polygons:p.use_smooth=True
    mat=bpy.data.materials.new("Wind-driven equatorial seawater");mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(.012,.057,.076,1);bs.inputs["Roughness"].default_value=.158
    bs.inputs["Metallic"].default_value=.31;bs.inputs["IOR"].default_value=1.333;bs.inputs["Coat Weight"].default_value=.45
    tc=nodes.new("ShaderNodeTexCoord");field=nodes.new("ShaderNodeTexNoise");field.noise_dimensions="4D";field.inputs["Scale"].default_value=.446
    field.inputs["Detail"].default_value=5.1;field.inputs["Roughness"].default_value=.61;links.new(tc.outputs["Object"],field.inputs["Vector"])
    bump=nodes.new("ShaderNodeBump");bump.inputs["Strength"].default_value=.42;bump.inputs["Distance"].default_value=.105
    links.new(field.outputs["Fac"],bump.inputs["Height"]);links.new(bump.outputs["Normal"],bs.inputs["Normal"])
    me.materials.append(mat);o=bpy.data.objects.new("Pelagic Anchor · moving sea",me);ext.objects.link(o)
    for sec in range(0,361,3):
        altitude=astro["height"](sec);o.location.z=-altitude*1000;o.keyframe_insert("location",frame=astro["frame_at"](sec))
        field.inputs["W"].default_value=sec*.082;field.inputs["W"].keyframe_insert("default_value",frame=astro["frame_at"](sec))
    return o
local_sea()

def native(name,p=(0,0,0)):
    return active("exterior",name,p,p)
def native_finish(g):
    return make_mesh(g,None)
exec(compile((ROOT/"source"/"native_guideway.py").read_text(),str(ROOT/"source"/"native_guideway.py"),"exec"))
# A maintenance vehicle descends the counterline as it passes the observation glazing.
px,pz=-7.89,-24.8
cab=native("Counterline carriage",(px,0,pz))
cube((px+.84,0,pz),(1.73,3.36,1.63),"Ceramic_Pearl",.218)
cube((px+.86,.27,pz+.770),(1.39,1.64,.15),"Carbon_Ceramic",.11)
for xoff in (-.535,.535):
    cube((px+.84+xoff,.29,pz+.859),(.341,1.30,.035),"Smoked_Display",.014)
    cube((px+.84+xoff,1.27,pz+.817),(.121,.075,.076),"Amber_Emitter",.014)
cube((px+.84,-.88,pz+.785),(1.62,.14,.059),"Signal_Orange",.018)
car=native_finish(cab)
for fr,h in ((1,16),(80,4.9),(145,-8.4),(270,-30)):
    car.location=blender((px,h,pz));car.keyframe_insert("location",frame=fr)
# The inhabited valleys run along the axle. Real truss hoops, mirror outriggers
# and endcaps remain independent solids outside the photographed pressure skin.
material("Habitat photovoltaic",dict(rgb=(34,58,98),metallic=.62,roughness=.22,alpha=1))
world_art=ROOT/"web"/"assets"/"world"
for skin_name,metal,coat,glow in (("Aster Reach · pressure armor",.49,.12,0),
                                 ("Aster Reach · glazed valleys",.16,.41,.38)):
    skin=material(skin_name,dict(rgb=(255,255,255),metallic=metal,roughness=.38,alpha=1,
        baseColor=str(world_art/"habitat-hull.webp"),roughnessMap=str(world_art/"habitat-rough.webp"),
        emission=glow))
    shader=skin.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Coat Weight"].default_value=coat
    shader.inputs["Coat Roughness"].default_value=.21
settle=v((-530,250,-1980));hab=native("Aster Reach · rotating habitat",settle)
axis=v((.72,.13,.68)).normalized();e1=axis.cross(Y).normalized();e2=axis.cross(e1).normalized()
length=1310;radius=158
def hp(along,angle,rd):
    return settle+axis*along+rd*(e1*math.cos(angle)+e2*math.sin(angle))
segments=96
for j in range(segments):
    a=T*j/segments;b=T*(j+1)/segments
    # Orient the arrival meridian so a valley, its glazing and an armored flank share the cabin sightline.
    u0=j/segments+.13;u1=(j+1)/segments+.13
    band_fraction=((u0+u1)*1.5)%1
    laminate="Aster Reach · glazed valleys" if band_fraction<.565 else "Aster Reach · pressure armor"
    na=e1*math.cos(a)+e2*math.sin(a);nb=e1*math.cos(b)+e2*math.sin(b)
    for zone in range(12):
        v0=zone/12;v1=(zone+1)/12;aa=length*(v0-.5);bb=length*(v1-.5)
        face([hp(aa,a,radius),hp(bb,a,radius),hp(bb,b,radius),hp(aa,b,radius)],
             laminate,na+nb,[(u0,v0),(u0,v1),(u1,v1),(u1,v0)],[na,na,nb,nb])
        if j%8==0:
            rod(hp(aa,a,radius+1),hp(bb,a,radius+1),1.5,"Ceramic_Pearl",7)
        if j%32 in (17,30):
            a2=aa+5;b2=aa+11;mark_width=(b-a)*.20
            face([hp(a2,a,radius+.5),hp(b2,a,radius+.5),hp(b2,a+mark_width,radius+.5),hp(a2,a+mark_width,radius+.5)],
                 "Amber_Emitter" if zone%3==0 else "Blue_Emitter",na)
for along in [-length/2+i*length/12 for i in range(13)]:
    tube([hp(along,T*j/56,radius+1.4) for j in range(56)],3.0,"Titanium",6,True)
for s in (-1,1):
    end=settle+axis*s*length/2
    rod(end,end+axis*s*32,radius*.97,"Composite_Slate",48,r2=radius*.78)
    rod(end+axis*s*33,end+axis*s*68,radius*.77,"Aluminum",48,r2=radius*.405)
    rod(end+axis*s*68,end+axis*s*158,radius*.21,"Graphite_Alloy",32,r2=radius*.12)
    rod(end+axis*s*155,end+axis*s*165,radius*.29,"Safety_Amber",32)
    for j in range(8):
        a=T*j/8;rod(hp(s*length/2,a,radius*.94),end+axis*s*110,3.0,"Ceramic_Pearl",7)
for j in range(3):
    angle=T*j/3+.36;rad=e1*math.cos(angle)+e2*math.sin(angle);tan=axis.cross(rad)
    outer=settle+rad*(radius+133)
    for loc in (-.42,.42):
        aa=settle+axis*(length*loc)+rad*radius;bb=outer+axis*(length*loc)
        rod(aa,bb,3.5,"Aluminum",8)
    for k in range(10):
        aa=outer+axis*((k-5)*length*.085);bb=aa+axis*(length*.079)
        pp=[aa-tan*58,bb-tan*58,bb+tan*58,aa+tan*58]
        face(pp,"Habitat photovoltaic",rad)
        for a,b in zip(pp,pp[1:]+pp[:1]):rod(a,b,1.2,"Titanium",6)
        for d in (-29,0,29):rod(aa+tan*d,bb+tan*d,.49,"Aluminum",5)
colony=native_finish(hab)
for second in range(0,361,3):
    offset=1000*(35786-astro["height"](second))
    colony.location=blender((settle.x,settle.y+offset,settle.z))
    colony.keyframe_insert("location",frame=astro["frame_at"](second))
colony.rotation_mode="AXIS_ANGLE"
for fr,angle in ((1,0),(270,.81)):
    colony.rotation_axis_angle=(angle,*blender(axis));colony.keyframe_insert("rotation_axis_angle",frame=fr)
for name in ("Front laminate","Warm solar reflection","Cloud bounce","Sleeper exterior","Service exterior"):
    lamp=bpy.data.lights[name];base=lamp.energy;side=name=="Warm solar reflection"
    for fr,power,tint in ((1,1.50 if side else .72,(1.0,.64,.38) if side else (1.0,.82,.64)),
                          (86,.82 if side else 1.0,(1.0,.82,.67) if side else (.66,.84,1.0)),
                          (165,.21 if side else .26,(.52,.71,1.0)),(258,.28 if side else .56,(.71,.85,1.0))):
        lamp.energy=base*power;lamp.color=tint
        lamp.keyframe_insert("energy",frame=fr);lamp.keyframe_insert("color",frame=fr)
scene.frame_set(88)
