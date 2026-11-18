"""Manifold editable surfaces for the water charge and its nine-plane gas cap."""
import numpy as np

fluid_model=runpy.run_path(str(ROOT/"source"/"native_capillary_profile.py"))
fluid_maps={}

def fluid_volume():
    room="berth";parent=cell_spec["id"];c=v(cell_spec["center"]);r=Z;u=Y;n=-X
    radius=cell_spec["radius"];count=fluid_model["N"];layer_count=9;depth=cell_spec["depth"];half=depth/2
    core_half=fluid_model["HALF"];gas,outer,origin=fluid_model["boundary"](28.)
    cell_spec["nativeOneG"]={"sectionCount":layer_count,"profileSamples":count,"interfaceV":round(float(min(gas[4,:,1])),7),
        "gasFractionMesh":round(fluid_model["gas_fraction"](28.),6),"nativeZeroGGasFractionMesh":round(fluid_model["gas_fraction"](0.),6),
        "method":"Nine constant-charge sections clipped to the physical cavity and radial / pane wetting film."}

    def point(tag):
        kind,lev,ray,f,dh=tag;ray%=count;g=gas[lev,ray]
        xy=g+(outer[lev,ray]-g)*f if kind==0 else origin[lev]+(g-origin[lev])*f
        return c+r*float(xy[0])+u*float(xy[1])+n*(core_half*(lev/4-1)+dh)

    def bound_face(tags,material_name,direction):
        pts=[point(t) for t in tags]
        uv=[(.5+(p-c).dot(r)/(2*radius),.5+(p-c).dot(u)/(2*radius)) for p in pts]
        expected=(pts[1]-pts[0]).cross(pts[2]-pts[0]);stored=list(reversed(tags)) if expected.dot(direction)<0 else tags
        old=len(current.verts);face(pts,material_name,direction,uv)
        if len(current.verts)!=old:fluid_maps[current.id].extend(stored)

    aux("gravity",room,"capillary_liquid",parent,c);fluid_maps[current.id]=[]
    # Front and aft water surfaces, including the rolled inner meniscus. Each
    # ring reaches the wall along the same interior-origin ray as the gas.
    for side,lev in ((-1,0),(1,8)):
        for ring in range(5):
            for j in range(count):
                ix=((ring,j),(ring,j+1),(ring+1,j+1),(ring+1,j));tags=[]
                for k,a in ix:
                    f=k/5;dh=side*cell_spec["paneFilm"]*(1-math.exp(-f*20))
                    tags.append((0,lev,a,f,dh))
                bound_face(tags,"Cell_Liquid",n*side)
    for j in range(count):
        d=u*math.sin(j*T/count)+r*math.cos(j*T/count)
        for k in range(8):
            ix=((k,j),(k,j+1),(k+1,j+1),(k+1,j))
            bound_face([(0,lev,a,0.,0.) for lev,a in ix],"Cell_Meniscus",-d)
            bound_face([(0,lev,a,1.,cell_spec["paneFilm"]*(lev/4-1)) for lev,a in ix],"Cell_Liquid",d)

    aux("gravity",room,"capillary_gas",parent,c);fluid_maps[current.id]=[]
    # The transparent gas is a genuinely closed volume. Its side is just
    # inside the water-side interface to keep both optical surfaces distinct.
    for side,lev in ((-1,0),(1,8)):
        for j in range(count):
            for ring in range(3):
                ix=[(ring,j),(ring,j+1),(ring+1,j+1),(ring+1,j)]
                if not ring:ix.pop(1)
                bound_face([(1,lev,a,k/3*.9998,0.) for k,a in ix],"Cell_Gas",n*side)
    for j in range(count):
        d=u*math.sin(j*T/count)+r*math.cos(j*T/count)
        for k in range(8):
            ix=((k,j),(k,j+1),(k+1,j+1),(k+1,j))
            bound_face([(1,lev,a,.9998,0.) for lev,a in ix],"Cell_Gas",d)
        # A narrow optical highlight belongs to the bevel of the interface,
        # rather than spanning the gas as an opaque or coloured circular tile.
        ix=((j,.9997,0.),(j+1,.9997,0.),(j+1,.9870,-.00039),(j,.9870,-.00039))
        bound_face([(1,8,a,f,h) for a,f,h in ix],"Cell_Meniscus",n)
    for key in ("capillary_liquid","capillary_gas"):
        fluid_maps[key]=np.asarray(fluid_maps[key],dtype=np.float32)
