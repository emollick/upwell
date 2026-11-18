"""Editable native response of the gauge, wetting cell and three classes of soft furnishing."""
import math
import runpy
from mathutils import Vector

flight=runpy.run_path(str(ROOT/"source"/"ascent_geometry.py"))
loads=runpy.run_path(str(ROOT/"source"/"native_ride_loads.py"))
def effective_g(sec):
    return loads["signed_load"](flight["height"](sec))
native_g=groups[("observation","accelerometer")].object
native_c=groups[("berth","capillary_cell")].object
native_g["signed_load_g"]=1.;native_g.id_properties_ui("signed_load_g").update(min=-.18,max=1.18,description="Signed apparent acceleration, positive floorward")
native_g["test_stroke"]=0.;native_g.id_properties_ui("test_stroke").update(min=0.,max=1.,description="Spring calibration plunger, +0.10 g at full stroke")
native_c["primer_stroke"]=0.;native_c.id_properties_ui("primer_stroke").update(min=0.,max=1.,description="Displace the capillary primer")
def driven(obj,path,idx,expr,variables):
    curve=obj.driver_add(path,idx) if idx is not None else obj.driver_add(path)
    driver=curve.driver;driver.type="SCRIPTED"
    for name,target,key in variables:
        var=driver.variables.new();var.name=name;var.targets[0].id=target;var.targets[0].data_path='["'+key+'"]'
    driver.expression=expr
vargs=(("load",native_g,"signed_load_g"),("test",native_g,"test_stroke"))
applied="min(1.18,max(-.18,load+.10*test))"
mass=groups[("observation",accel_spec["massNode"])].object
driven(mass,"location",2,f"{mass.location.z:.9f}+(.162*(1-({applied})))",vargs)
for part in accel_spec["springs"]:
    ob=groups[("observation",part["node"])].object
    ob.shape_key_add(name="Rest pitch",from_mix=False)
    pitch=ob.shape_key_add(name="Wire pitch • zero g",from_mix=False);pitch.slider_min=-.18;pitch.slider_max=1.18
    fractions=np.asarray(spring_fractions[part["node"]]);assert len(fractions)==len(ob.data.vertices)
    xyz=np.empty((len(fractions),3),dtype=np.float32);ob.data.vertices.foreach_get("co",xyz.ravel());xyz[:,2]+=.162*fractions
    pitch.data.foreach_set("co",xyz.ravel());driven(pitch,"value",None,"1-("+applied+")",vargs)
plunger=groups[("observation","accel_test")].object;primer=groups[("berth","capillary_primer")].object
driven(plunger,"location",1,f"{plunger.location.y:.9f}+.009*test",(("test",native_g,"test_stroke"),))
driven(primer,"location",0,f"{primer.location.x:.9f}+.009*press",(("press",native_c,"primer_stroke"),))
for name,mapping in fluid_maps.items():
    g=groups[("berth",name)];ob=g.mesh
    if len(mapping)!=len(ob.data.vertices):raise ValueError("Fluid surface binding count differs for "+name)
    ob.shape_key_add(name="Stratified · one g",from_mix=False);levels=fluid_model["LEVELS"];keys=[]
    for reach in levels[:-1]:
        key=ob.shape_key_add(name="Sealed cell • buoyancy %+.2f"%reach,from_mix=False);keys.append(key)
        p=fluid_model["points"](reach,mapping)
        # Local (right,up,toward lens) -> Blender (-toward lens,-right,up).
        xyz=np.column_stack((-p[:,2],-p[:,0],p[:,1])).astype(np.float32);key.data.foreach_set("co",xyz.ravel())
    for sec in range(361):
        reach=fluid_model["signed_reach"](effective_g(sec));j=min(len(levels)-2,max(0,int(np.searchsorted(levels,reach))-1))
        f=norm01((reach-levels[j])/(levels[j+1]-levels[j]));frame=flight["frame_at"](sec)
        for i,key in enumerate(keys):
            key.value=(1-f if i==j else f if i==j+1 else 0.)
            key.keyframe_insert("value",frame=frame)
for sec in range(361):
    native_g["signed_load_g"]=effective_g(sec);native_g.keyframe_insert(data_path='["signed_load_g"]',frame=flight["frame_at"](sec))
runpy.run_path(str(ROOT/"source"/"native_cell_primer.py"))["install"]()
for name,spec in furnishing_specs.items():
    if spec["kind"]=="curtainHardware":continue
    g=groups[(auxiliary_parts[name]["room"],name)];o=g.mesh;basis_key=o.shape_key_add(name="Secured • at rest",from_mix=False)
    reduced=o.shape_key_add(name="Low apparent gravity",from_mix=False)
    cross=o.shape_key_add(name="Guide sway",from_mix=False);cross.slider_min=-1;cross.slider_max=1
    if spec["kind"]=="quilt":
        occupied=o.shape_key_add(name="Occupied depression",from_mix=False)
        p=groups[("berth","bunk")].object;p["occupied"]=0.;p.id_properties_ui("occupied").update(min=0.,max=1.)
        driven(occupied,"value",None,"occupied",(("occupied",p,"occupied"),))
    elif spec["kind"]=="curtain":
        spread=o.shape_key_add(name="Curtain drawn",from_mix=False)
        p=groups[("berth","privacy_curtain")].object;p["drawn"]=0.;p.id_properties_ui("drawn").update(min=0.,max=1.)
        driven(spread,"value",None,"drawn",(("drawn",p,"drawn"),))
        frames={}
    for i,vert in enumerate(o.data.vertices):
        loc=v((vert.co.x,vert.co.z,-vert.co.y));w=g.pivot+loc
        if spec["kind"]=="quilt":
            u,v0=q_bind(w);z=w.z
            belt_mask=min(1.,min(abs(z-vq) for vq in QUILT_BELTS)/.115)
            head_mask=min(1.,v0/.12);edge=(.21+.79*math.sin(math.pi*min(.98,u))**.57)
            amt=belt_mask*head_mask*edge;loft=.095*amt*(.47+.53*v0)
            reduced.data[i].co=vert.co+v(blender((.008*amt,loft,.006*amt)))
            cross.data[i].co=vert.co+v(blender((.012*amt,.002*amt,.005*amt)))
            depth=.041*math.exp(-((u-.46)/.28)**2-((v0-.48)/.43)**2)*belt_mask
            occupied.data[i].co=vert.co+v(blender((0,-min(depth,max(0,w.y-.944)),0)))
        elif spec["kind"]=="curtain":
            u,v0=g.vertex_bindings[i];param=(u,v0)
            if param not in frames:
                def frame(opened):
                    at=sample_drape(u,v0,opened);nn=cloth_normal(u,v0,opened)
                    side=(sample_drape(min(1,u+.00034),v0,opened)-sample_drape(max(0,u-.00034),v0,opened)).normalized()
                    return at,side,nn.cross(side).normalized(),nn
                frames[param]=(frame(False),frame(True))
            old,new=frames[param];offset=w-old[0]
            dest=new[0]+sum((new[j]*offset.dot(old[j]) for j in (1,2,3)),v((0,0,0)))
            spread.data[i].co=v(blender(dest-g.pivot))
            amt=v0**1.6*math.sin(math.pi*u)**.66
            reduced.data[i].co=vert.co+v(blender((amt*.027,amt*.035,0)))
            cross.data[i].co=vert.co+v(blender((amt*.046,amt*.003,amt*.009)))
        else:
            pts=[v(q) for q in spec["restPoints"]];best=(float("inf"),0.)
            for j,(a,b) in enumerate(zip(pts[:-1],pts[1:])):
                seg=b-a;t0=norm01((loc-a).dot(seg)/max(1e-12,seg.length_squared));ds=(loc-a-seg*t0).length_squared
                if ds<best[0]:best=(ds,(j+t0)/(len(pts)-1))
            q=best[1];amt=math.sin(q*math.pi)**1.75
            reduced.data[i].co=vert.co+v(blender((-.010*amt,spec["maxOffset"]*.68*amt,.004*amt)))
            cross.data[i].co=vert.co+v(blender((-.018*amt,.004*amt,.006*amt)))
    for sec in range(0,361,2):
        grav=max(0,min(1,effective_g(sec)));reduced.value=(1-grav)*.89
        pulse=sum(math.sin((sec-t)*1.91)*math.exp(-(sec-t)*.51)*amp for t,amp in ((8,.8),(23,.39),(104,.22),(340,.47),(352,.76)) if sec>=t)
        cross.value=max(-1,min(1,pulse));f=flight["frame_at"](sec)
        reduced.keyframe_insert("value",frame=f);cross.keyframe_insert("value",frame=f)
curtain=groups[("berth","privacy_curtain")].object
for h in furnishing_specs["cloth_berth_curtain"]["hardware"]:
    ob=groups[("berth",h["node"])].object;delta=h["openTranslation"][2]
    driven(ob,"location",1,f"{ob.location.y:.9f}-drawn*{delta:.9f}",(("drawn",curtain,"drawn"),))
