"""Separable blanket, moving privacy drape and two terminated service loops.

The visible fabric, underside, edge binding and stitching share one deformable
component, an indexed surface, and a common normalised material-coordinate map.
"""
from bisect import bisect_left
from mathutils.kdtree import KDTree

furnishing_specs={}
def norm01(q):return max(0,min(1,q))
def q_point(u,vv):
    x=QUILT_X[0]+(QUILT_X[1]-QUILT_X[0])*u;z=QUILT_Z[0]+(QUILT_Z[1]-QUILT_Z[0])*vv
    return v((x,quilt_height(x,z),z))
def q_normal(p):
    x,y,z=p;dx=(quilt_height(x+.006,z)-quilt_height(x-.006,z))/.012;dz=(quilt_height(x,z+.006)-quilt_height(x,z-.006))/.012
    return v((-dx,1,-dz)).normalized()
def q_bind(p):
    return (norm01((p.x-QUILT_X[0])/(QUILT_X[1]-QUILT_X[0])),norm01((p.z-QUILT_Z[0])/(QUILT_Z[1]-QUILT_Z[0])))
def rounded(vs):return [round(float(x),6) for x in vs]
def handles(values):return sorted(set(round(norm01(float(x)),8) for x in values))
def as_grid(xdir,ydir,fn,pivot):
    return [rounded(fn(u,vv)-pivot) for vv in ydir for u in xdir]

def berth_quilt():
    room="berth";par=groups[(room,"bunk")];g=aux("furnishings",room,"cloth_berth_quilt","bunk",par.pivot)
    g.bind_uv=q_bind
    uvals=[i/48 for i in range(49)];vvals=[i/116 for i in range(117)]
    top=[[q_point(u,vv) for u in uvals] for vv in vvals]
    normals=[[q_normal(p) for p in row] for row in top]
    def under(p):
        yy=.9355+.0022*math.sin(19*p.x+8*p.z)+.0019*math.cos(12*p.x-13*p.z)
        return v((p.x,min(p.y-.0086,max(.9334,yy)),p.z))
    for j in range(len(vvals)-1):
        for i in range(len(uvals)-1):
            ix=((j,i),(j,i+1),(j+1,i+1),(j+1,i))
            pts=[top[a][b] for a,b in ix];ns=[normals[a][b] for a,b in ix]
            uv=[((p.x-QUILT_X[0])/.302,(p.z-QUILT_Z[0])/.302) for p in pts]
            face(pts,"Quilt_Ripstop",Y,uv,normals=ns)
            face([under(p) for p in pts],"Quilt_Lining",-Y,uv,normals=[-Y]*4)
    edges=[top[0],top[-1],[row[0] for row in top],[row[-1] for row in top]]
    for edge,direction in zip(edges,(-Z,Z,-X,X)):
        for a,b in zip(edge,edge[1:]):
            aa=under(a);bb=under(b)
            face([a,b,bb,aa],"Berth_Bias_Tape",direction)
            ia=a-direction*.012;ib=b-direction*.012
            ia.y=quilt_height(ia.x,ia.z)+.00125;ib.y=quilt_height(ib.x,ib.z)+.00125
            lip=[a+Y*.00065,b+Y*.00065,ib,ia]
            face(lip,"Berth_Bias_Tape",Y,[(p.x/.24,p.z/.24) for p in lip])
        tube([p-Y*.0044 for p in edge],.0026,"Berth_Bias_Tape",7)
    # Unequal, swept transverse baffles. Symmetric twin rows carry load into
    # the liner; short individual needle lengths show the human sewing scale.
    for seam in range(1,8):
        for row in (-.0028,.0028):
            for k in range(72):
                x=QUILT_X[0]+.018+(QUILT_X[1]-QUILT_X[0]-.041)*k/71
                z=quilt_seam(x,seam)+row;xn=x+.0047;zn=quilt_seam(xn,seam)+row
                if QUILT_Z[0]+.015 < min(z,zn) and max(z,zn)<QUILT_Z[1]-.015:
                    p=v((x,quilt_height(x,z)+.00095,z));q=v((xn,quilt_height(xn,zn)+.00095,zn))
                    rod(p,q,.00044,"Quilt_Lining",5)
    # Retaining badge follows the actual surface rather than floating above the folds.
    x,z=-1.462,.910;cp=v((x,quilt_height(x,z)+.0013,z));normal=q_normal(cp)
    for k in range(12):
        ua,ub=k/12,(k+1)/12
        pts=[];tex=[]
        for uu,vv in ((ua,0),(ub,0),(ub,1),(ua,1)):
            xx=x+(uu-.5)*.073;zz=z-(vv-.5)*.022
            pts.append(v((xx,quilt_height(xx,zz)+.00155,zz)))
            tex.append(grav_uv("quilt_tag",uu,vv))
        face(pts,"Gravity_Print",normal,tex)
    xx=[i/10 for i in range(11)]
    vbelts=[(z-QUILT_Z[0])/(QUILT_Z[1]-QUILT_Z[0]) for z in QUILT_BELTS]
    zz=handles([i/18 for i in range(19)]+vbelts)
    bidx=[min(range(len(zz)),key=lambda j:abs(zz[j]-q)) for q in vbelts]
    pins=[0,len(xx)-1]+[r*len(xx)+c for r in bidx for c in (0,len(xx)-1)]
    furnishing_specs[g.id]={"kind":"quilt","uvFrame":{"uAxis":[1,0,0],"vAxis":[0,0,1],"uWorld":list(QUILT_X),"vWorld":list(QUILT_Z)},
        "grid":{"u":xx,"v":zz,"restPoints":as_grid(xx,zz,q_point,par.pivot)},"pinIndices":sorted(set(pins)),"beltRows":bidx,
        "undersideThickness":.015,"underside":"quilted loft varies; lining rests within 0.5–5 mm of the mattress in 1g",
        "maxLift":.117,"maxCompression":.040,"mattressTopWorldY":.933,"mattressTopLocalY":.933-par.pivot.y,
        "clearance":{"worldBounds":[[-2.122,.934,-.635],[-1.233,1.185,1.043]]},"material":"Quilt_Ripstop"}


CURTAIN_X=-1.229;CURTAIN_Z=-1.201;C_TOP=2.108;C_BOTTOM=.873
CLOSE_W=.370;OPEN_W=2.230;WAVES=7;STOW_A=.0835
def drape_table(width,amplitude):
    segments=2048
    pp=[(math.sin(T*WAVES*i/segments)*amplitude,width*i/segments) for i in range(segments+1)]
    lengths=[0.]
    for a,b in zip(pp,pp[1:]):lengths.append(lengths[-1]+math.hypot(a[0]-b[0],a[1]-b[1]))
    return pp,[q/lengths[-1] for q in lengths],lengths[-1]
_rest=drape_table(CLOSE_W,STOW_A);lo=0;hi=STOW_A
for _ in range(30):
    mid=(lo+hi)*.5
    if drape_table(OPEN_W,mid)[2]<_rest[2]:lo=mid
    else:hi=mid
OPEN_A=(lo+hi)*.5;_spread=drape_table(OPEN_W,OPEN_A)
def sample_drape(u,vv,opened=False):
    pts,cum,_=_spread if opened else _rest
    u=norm01(u);vv=norm01(vv);j=max(1,min(len(cum)-1,bisect_left(cum,u)))
    f=(u-cum[j-1])/max(1e-12,cum[j]-cum[j-1])
    x=pts[j-1][0]*(1-f)+pts[j][0]*f;z=pts[j-1][1]*(1-f)+pts[j][1]*f
    width=OPEN_W if opened else CLOSE_W;t=z/width
    # Top seam follows the rail. Lower folds carry subtle bias and a weighted hem.
    x+=vv*.0088*math.sin(T*t*2.6+.7)*math.sin(math.pi*u)
    x+=vv*(1-vv)*.021*math.sin(T*t*(WAVES+.32))*math.sin(math.pi*u)
    x+=vv**1.20*(.018*math.sin(T*t*2.1+vv*2.4)+.010*math.sin(T*t*4.5-vv*3.7))*math.sin(math.pi*u)
    x+=.0044*math.sin(T*u*4.65+vv*9.4)*math.sin(math.pi*vv)*math.sin(math.pi*u)
    y=C_TOP-(C_TOP-C_BOTTOM)*vv + vv*vv*.007*math.sin(T*t*WAVES+.4)*math.sin(math.pi*u)
    return v((CURTAIN_X+x,y,CURTAIN_Z+z))
def drape_uv(p):
    z=norm01((p.z-CURTAIN_Z)/CLOSE_W);pts,cum,_=_rest
    i=z*(len(cum)-1);k=min(len(cum)-2,int(i));u=cum[k]+(cum[k+1]-cum[k])*(i-k)
    t=(C_TOP-p.y)/max(.001,C_TOP-C_BOTTOM)
    end_raise=.007*math.sin(T*z*WAVES+.4)*math.sin(math.pi*u)
    t+=t*t*end_raise/(C_TOP-C_BOTTOM)
    return (norm01(u),norm01(t))
def cloth_normal(u,vv,opened=False):
    du=sample_drape(min(1,u+.00034),vv,opened)-sample_drape(max(0,u-.00034),vv,opened)
    dv=sample_drape(u,min(1,vv+.001),opened)-sample_drape(u,max(0,vv-.001),opened)
    return du.cross(dv).normalized()
def berth_curtain():
    room="berth";par=groups[(room,"privacy_curtain")]
    g=aux("furnishings",room,"cloth_berth_curtain","privacy_curtain",par.pivot)
    hints={};index_key=lambda p:tuple(round(float(x),7) for x in p)
    def binding(p):
        hit=hints.get(index_key(p));return hit if hit is not None else drape_uv(p)
    g.bind_uv=binding
    xs=[i/126 for i in range(127)];ys=handles([i/21 for i in range(22)]+[.012,.014,.038,.948,.973,.975,.992])
    pts=[[sample_drape(u,vv) for u in xs] for vv in ys]
    norms=[[cloth_normal(u,vv) for u in xs] for vv in ys]
    for j in range(len(ys)-1):
        for i in range(len(xs)-1):
            inds=((j,i),(j,i+1),(j+1,i+1),(j+1,i))
            p=[pts[a][b] for a,b in inds];nm=[norms[a][b] for a,b in inds]
            uv=[(xs[b]*_rest[2]/.31,(1-ys[a])*(C_TOP-C_BOTTOM)/.31) for a,b in inds]
            face(p,"Curtain_Acoustic",sum(nm,v((0,0,0))),uv,normals=nm)
            back=[p[k]-nm[k]*.0016 for k in range(4)]
            face(back,"Quilt_Lining",-sum(nm,v((0,0,0))),uv,normals=[-k for k in nm])
            for k,(a,b) in enumerate(inds):
                hints[index_key(p[k])]=(xs[b],ys[a]);hints[index_key(back[k])]=(xs[b],ys[a])
    for edge,nedge in ((pts[0],norms[0]),(pts[-1],norms[-1]),
                      ([a[0] for a in pts],[a[0] for a in norms]),([a[-1] for a in pts],[a[-1] for a in norms])):
        for j in range(len(edge)-1):
            a,b=edge[j],edge[j+1];face([a,b,b-nedge[j+1]*.0016,a-nedge[j]*.0016],"Quilt_Lining")
    # Woven hems and hardpoints are part of the cloth. Track rings and leading stile are separate rigid pieces.
    for vv in (.014,.973,.992):
        line=[sample_drape(u,vv)+cloth_normal(u,vv)*.0017 for u in xs]
        tree=KDTree(len(line))
        for k,p in enumerate(line):tree.insert(p,k)
        tree.balance();before=len(g.verts)
        tube(line,.0018 if vv==.992 else .0011,"Berth_Bias_Tape" if vv!=.014 else "Quilt_Lining",6)
        for p in g.verts[before:]:hints[index_key(p)]=(xs[tree.find(p)[1]],vv)
    # A flat-felled vertical join and a weighted woven hem are sewn into the
    # same textile, adding human-scale detail and cues to its change of shape.
    for band in ((.012,.038),(.948,.975)):
        for j in range(len(xs)-1):
            uvp=((xs[j],band[0]),(xs[j+1],band[0]),(xs[j+1],band[1]),(xs[j],band[1]))
            points=[sample_drape(u0,v0)+cloth_normal(u0,v0)*.00175 for u0,v0 in uvp]
            ns=[cloth_normal(u0,v0) for u0,v0 in uvp]
            face(points,"Berth_Bias_Tape",sum(ns,v((0,0,0))),[(a*_rest[2]/.24,(1-b)*(C_TOP-C_BOTTOM)/.24) for a,b in uvp],normals=ns)
            for p,q in zip(points,uvp):hints[index_key(p)]=q
    for uu in (.335,.672):
        for j in range(62):
            va=j/62;vb=(j+.58)/62
            p=sample_drape(uu,va)+cloth_normal(uu,va)*.0024;q=sample_drape(uu,vb)+cloth_normal(uu,vb)*.0024
            before=len(g.verts);rod(p,q,.00055,"Quilt_Lining",5)
            for point in g.verts[before:]:hints[index_key(point)]=(uu,va if (point-p).length_squared<(point-q).length_squared else vb)
    # Use a UV registry for every triangle loop, including side binding and tick stitches.
    hardware=[];ring_params=[i/7 for i in range(8)]
    for j,u0 in enumerate(ring_params):
        p0=sample_drape(u0,0);p1=sample_drape(u0,0,True)
        pivot=v((CURTAIN_X,2.145,p0.z))
        hf=aux("furnishings",room,"curtain_ring_"+str(j).zfill(2),"privacy_curtain",pivot)
        torus(pivot,Z,.0292,.0032,"Precision_Titanium",19,7)
        cube(pivot-Y*.027,(.011,.016,.009),"Anodized_Frame",.002)
        rod(pivot-Y*.034,p0+Y*.001,.0026,"Precision_Titanium",8)
        for delta in (-.003,.003):
            p=p0+Z*delta-X*.0006;rod(p-X*.003,p+X*.003,.0035,"Titanium",9)
        hardware.append({"node":hf.id,"u":u0,"restPivot":rounded(pivot-par.pivot),"openPivot":rounded(pivot-par.pivot+p1-p0),
                         "openTranslation":rounded(p1-p0)})
    p0=sample_drape(1,.5);p1=sample_drape(1,.5,True)
    pivot=v((CURTAIN_X,(C_TOP+C_BOTTOM)*.5,CURTAIN_Z+CLOSE_W))
    hf=aux("furnishings",room,"curtain_stile","privacy_curtain",pivot)
    cube(pivot+Z*.004,(.030,1.198,.014),"Anodized_Frame",.004)
    cube(pivot+X*.0148+Z*.004,(.0038,1.162,.011),"Titanium",.0017)
    handle(pivot+X*.018+Y*.022,X,.177,.033,True,"Grip_Elastomer",.009)
    hardware.append({"node":hf.id,"u":1.,"restPivot":rounded(pivot-par.pivot),"openPivot":rounded(pivot-par.pivot+p1-p0),"openTranslation":rounded(p1-p0)})
    # Samples follow material arclength, not projected Z, so opening the track changes its folds rather than stretching the fabric.
    xu=handles([i/56 for i in range(57)]+ring_params);yv=[i/9 for i in range(10)]
    pins=[min(range(len(xu)),key=lambda k:abs(xu[k]-q)) for q in ring_params]
    pins+= [j*len(xu)+len(xu)-1 for j in range(len(yv))]
    furnishing_specs[g.id]={"kind":"curtain","grid":{"u":xu,"v":yv,"restPoints":as_grid(xu,yv,sample_drape,par.pivot),
            "openPoints":as_grid(xu,yv,lambda a,b:sample_drape(a,b,True),par.pivot)},
            "pinIndices":sorted(set(pins)),"hardware":hardware,"trackAxis":[0,0,1],"stowedWidth":CLOSE_W,"openWidth":OPEN_W,
            "restAmplitude":STOW_A,"openAmplitude":OPEN_A,"materialArcLength":_rest[2],"pleatIntervals":WAVES,
            "uvFrame":{"u":"normalised pleat material arclength from fixed carrier","v":"top to bottom","stowedWorldZ":[CURTAIN_Z,CURTAIN_Z+CLOSE_W],"worldY":[C_TOP,C_BOTTOM]},
            "maxSway":.069,"material":"Curtain_Acoustic","clearance":{"worldBounds":[[-1.362,.848,-1.225],[-1.104,2.122,1.105]]}}
    for h in hardware:
        furnishing_specs[h["node"]]={"kind":"curtainHardware","clothNode":g.id,**h}


def service_loops():
    for key,spec in service_junctions.items():
        room="service";p0=v(spec["a"]);p1=v(spec["b"]);rr=spec["radius"];count=28
        def path_func(t):
            chord=p0.lerp(p1,t);s=math.sin(math.pi*t)
            return chord+v((-spec["out"]*s, -spec["sag"]*s*s, .012*math.sin(T*t)*s))
        path=[path_func(j/count) for j in range(count+1)];pivot=(p0+p1)*.5
        g=aux("furnishings",room,key,"shell",pivot)
        tube(path,rr,spec["material"],12)
        for t in (.19,.21,.73):
            k=int(t*count);direction=(path[k+1]-path[k-1]).normalized();q=path[k]
            rod(q-direction*.005,q+direction*.005,rr*1.080,"Technical_Twill" if t!=.73 else "Load_Index",12)
        # Both actual machined cable glands and clamps stay attached to the fixed chassis.
        shell(room)
        for p,d in ((p0,(path[1]-p0).normalized()),(p1,(path[-2]-p1).normalized())):
            rod(p-d*.022,p+d*.007,rr*1.93,"Anodized_Frame",10)
            rod(p-d*.009,p+d*.002,rr*2.05,"Precision_Titanium",8)
            rod(p+d*.003,p+d*.012,rr*1.37,"Grip_Elastomer",12)
        bounds=[[1.788,min(p0.y,p1.y)-spec["sag"]-.048,min(p0.z,p1.z)-.024],[2.032,max(p0.y,p1.y)+.071,max(p0.z,p1.z)+.024]]
        furnishing_specs[g.id]={"kind":"cable","restPoints":[rounded(q-pivot) for q in path],"worldRestPoints":[rounded(q) for q in path],
            "pinIndices":[0,1,count-1,count],"radius":rr,"material":spec["material"],"length":sum((a-b).length for a,b in zip(path[:-1],path[1:])),
            "maxOffset":spec["max"],"clearance":{"worldBounds":bounds,"localBounds":[rounded(v(q)-pivot) for q in bounds]}}
berth_quilt();berth_curtain();service_loops()
