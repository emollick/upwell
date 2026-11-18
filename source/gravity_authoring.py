"""Cabin-wide gravity instruments. All authoring positions are glTF metres."""
import runpy
_gc=runpy.run_path(str(ROOT/"source"/"gravity_contracts.py"))
accel_spec=_gc["accelerometer"];cell_spec=_gc["capillary"]
grav_atlas=json.loads((LIB/"gravity_atlas.json").read_text())
spring_fractions={}

def grav_uv(key,x,y):
    u0,v0,ww,hh=grav_atlas["rects"][key];aw,ah=grav_atlas["size"]
    return ((u0+x*ww)/aw,1-(v0+(1-y)*hh)/ah)
def grav_print(c,n,w,h,key,mat="Gravity_Print",right=None):
    c=v(c);r,u,n=basis(n)
    if right is not None:r=v(right).normalized();u=n.cross(r)
    if key not in ("load_scale","cell_screen"):
        _,_,sw,sh=grav_atlas["rects"][key];w=min(w,h*sw/sh);h=w*sh/sw
    xy=((-1,-1),(1,-1),(1,1),(-1,1))
    face([c+r*(w*a/2)+u*(h*b/2) for a,b in xy],mat,n,[grav_uv(key,(a+1)/2,(b+1)/2) for a,b in xy])
def gravity_root(room,key,p,center,title,action):
    propinfo[key]={"name":title,"action":action}
    return active(room,key,p,center)
def grip_ring(c,n,radius,length,finish,count=24):
    c=v(c);r,u,n=basis(n)
    for j in range(count):
        a=T*j/count;d=r*math.cos(a)+u*math.sin(a)
        rod(c+d*radius-n*length*.5,c+d*radius+n*length*.5,.00072,finish,5)
def spring_helix(c,axis,length,radius,wire,count,finish):
    c=v(c);r,u,n=basis(axis);rings=[];directions=[];weights=spring_fractions[current.id]
    for i in range(count*24+1):
        q=i/(count*24);a=T*count*q;radial=r*math.cos(a)+u*math.sin(a)
        tangent=(n*length+(u*math.cos(a)-r*math.sin(a))*(radius*T*count)).normalized()
        across=tangent.cross(radial).normalized();p=c+n*(length*q)+radial*radius
        ns=[radial*math.cos(T*j/8)+across*math.sin(T*j/8) for j in range(8)]
        directions.append(ns);rings.append([p+k*wire for k in ns])
    for i in range(len(rings)-1):
        for j in range(8):
            inds=((i,j),(i,(j+1)%8),(i+1,(j+1)%8),(i+1,j))
            pts=[rings[k][h] for k,h in inds];ns=[directions[k][h] for k,h in inds]
            fractions=[k/(len(rings)-1) for k,h in inds]
            if (pts[1]-pts[0]).cross(pts[2]-pts[0]).dot(ns[0])<0:fractions.reverse()
            face(pts,finish,ns[0],normals=ns);weights.extend(fractions)

def acceleration_gauge():
    room="observation";id="accelerometer";n=Z
    c=v((-.760,1.305,-5.257))
    gravity_root(room,id,c,(-.759,1.310,-5.186),"Axial accelerometer","Read axial load")
    # A folded two-foot bracket keys into the actual shelf and supports the independently isolated instrument.
    for sx in (-1,1):
        xp=c.x+sx*.093
        cube((xp,.980,-5.266),(.063,.023,.113),"Anodized_Frame",.006)
        for z in (-5.300,-5.237):hand_screw((xp,.993,z),Y,.0057)
        profile=[(xp-.010,.991,-5.291),(xp-.010,1.076,-5.278),(xp-.010,1.119,-5.253),
                 (xp-.010,1.101,-5.224),(xp-.010,1.052,-5.235),(xp-.010,.991,-5.253)]
        polyprism(profile,X,.018,"Precision_Titanium")
        for yy in (1.053,1.075):
            p=v((xp,yy,-5.248));rod(p-X*.013,p+X*.013,.007,"Anodized_Frame",10)
    # Extruded back spine, four independent flexure shoes, shadow gap, and two nested optical seals.
    plate(c-Z*.010,n,.280,.452,.063,"Anodized_Frame",.015)
    rim(c+Z*.035,n,.271,.444,.016,.211,.315,.018,.018,"Handheld_Shell","Anodized_Frame",center_offset=(-.012,-.018))
    pp=c+v((-.012,-.018,.036))
    rim(pp,n,.240,.343,.026,.203,.312,.017,.016,"Precision_Titanium","Black_Rubber")
    flat_round(pp-Z*.014,n,.205,.315,.017,"Carbon_Ceramic")
    rim(pp+Z*.0016,n,.209,.317,.019,.199,.307,.015,.008,"Black_Rubber")
    rim(pp+Z*.048,n,.224,.330,.022,.201,.308,.017,.047,"Anodized_Frame","Anodized_Frame")
    rim(pp+Z*.054,n,.221,.327,.021,.201,.309,.017,.008,"Precision_Titanium","Black_Rubber")
    for sx in (-1,1):
        for sy in (-1,1):hand_screw(c+v((sx*.118,sy*.199,.0356)),n,.0062)
    grav_print(c+v((-.008,.185,.0359)),n,.190,.037,"load_title")
    # The light ceramic rule is real imagery aligned one-to-one with the pointer travel.
    sc=v((-.704,(1.117+1.412)*.5,-5.1779))
    plate(sc-Z*.021,n,.077,.296,.041,"Anodized_Frame",.004)
    plate(sc-Z*.0014,n,.076,.295,.0024,"Ceramic_Pearl",.0009)
    grav_print(sc+Z*.0001,n,.075,.295,"load_scale")
    for x in (-.815,-.748):
        rod((x,1.103,-5.207),(x,1.445,-5.207),.0036,"Precision_Titanium",14)
        for yy in (1.105,1.439):
            pp0=v((x,yy,-5.207));rod(pp0-Y*.006,pp0+Y*.006,.0062,"Anodized_Frame",12)
    # Behind the carriage, a piston in a small silicone dashpot suppresses bounce.
    dash=v((-.828,1.160,-5.228))
    turned(dash,Y,[(-.053,.006,"Anodized_Frame"),(-.049,.009,"Precision_Titanium"),(.028,.009,"Anodized_Frame"),
                   (.031,.010,"Precision_Titanium"),(.036,.006,"Black_Rubber")],16)
    rod(dash+Y*.03,dash+Y*.192,.0023,"Precision_Titanium",12)
    for yv in (1.102,1.444):rod((-.792,yv,-5.219),(-.769,yv,-5.219),.0045,"Anodized_Frame",10)
    glass=pp+Z*.0521
    flat_round(glass,n,.199,.307,.015,"Cell_Optical_Glass")
    for s in (-1,1):
        for h in (1.167,1.389):
            p=v((-.772+s*.109,h,-5.162))
            plate(p,Z,.014,.043,.011,"Anodized_Frame",.003);hand_screw(p+Z*.006,Z,.0023)
    plate((-.783,1.098,-5.201),n,.127,.036,.026,"Handheld_Shell",.004)
    grav_print((-.783,1.098,-5.1875),n,.121,.025,"load_test")
    pp=v(accel_spec["testPivot"])
    rod(pp-Z*.040,pp-Z*.010,.022,"Anodized_Frame",28)
    torus(pp-Z*.013,Z,.0193,.0020,"Precision_Titanium",28,7)
    for k in range(3):rod(pp-X*.021+Y*(k-1)*.007-Z*.018,pp-X*.026+Y*(k-1)*.007-Z*.018,.0014,"Load_Index",6)
    # The lifted amber nose and tungsten block stay in one rigid moving carriage.
    mc=v(accel_spec["restCenter"]);aux("gravity",room,accel_spec["massNode"],id,mc)
    mass=mc-X*.020
    cube(mass,(.069,.049,.043),"Load_Mass",.009)
    for sx in (-1,1):
        xp=-.815 if sx<0 else -.748
        rod((xp,mc.y-.020,-5.207),(xp,mc.y+.020,-5.207),.0073,"Precision_Titanium",18)
        for yy in (-.017,.017):
            rod((xp,mc.y+yy-.0018,-5.207),(xp,mc.y+yy+.0018,-5.207),.0081,"Anodized_Frame",14)
    cube(mass+Z*.022,(.050,.023,.004),"Anodized_Frame",.0017)
    for dx in (-.018,.018):hand_screw(mass+v((dx,.002,.025)),Z,.0024)
    nose=[mc+v((-.003,-.005,.024)),mc+v((.031,-.004,.024)),mc+v((.043,0,.024)),
          mc+v((.031,.004,.024)),mc+v((-.003,.005,.024))]
    polyprism(nose,Z,.0030,"Load_Index")
    cube(mc+v((.018,0,.02575)),(.035,.00090,.00036),"Handheld_Shell",.00010)
    for spec in accel_spec["springs"]:
        p=v(spec["fixedEnd"]);t=v(spec["restMovingEnd"]);axis=(t-p).normalized()
        aux("gravity",room,spec["node"],id,p)
        spring_fractions[current.id]=[]
        spring_helix(p,axis,spec["restLength"],spec["radius"],spec["wireRadius"],spec["turns"],"Precision_Titanium")
        for phase,end in enumerate((p,t)):
            before=len(current.verts);torus(end,Y,.0090,.00148,"Anodized_Frame",24,6)
            spring_fractions[current.id].extend([float(phase)]*(len(current.verts)-before))
    p=v(accel_spec["testPivot"])
    gravity_root(room,accel_spec["testId"],p,p+Z*.004,"Accelerometer test","Apply a +0.10 g test load")
    turned(p,Z,[(-.036,.006,"Precision_Titanium"),(-.016,.006,"Anodized_Frame"),(-.014,.014,"Load_Index"),
               (-.011,.016,"Load_Index"),(.002,.016,"Load_Index"),(.005,.014,"Anodized_Frame"),(.005,0,"Anodized_Frame")],32)
    grip_ring(p-Z*.004,Z,.016,.009,"Load_Index",22)
    for j in (-1,0,1):plate(p+Z*.0055+X*j*.004,Z,.0012,.011,.0005,"Load_Index")


exec(compile((ROOT/"source"/"instrument_fluid_mesh.py").read_text(),str(ROOT/"source"/"instrument_fluid_mesh.py"),"exec"))


def capillary_fitting():
    room="berth";id="capillary_cell";c=v(cell_spec["center"]);n=-X;r=Z;u=Y
    gravity_root(room,id,c,c+n*.016,"Capillary sight cell","Inspect liquid distribution")
    # Four isolated pads mount a circular instrument to the gusseted galley liner.
    for sy in (-1,1):
        for sz in (-1,1):
            p=c+u*(sy*.112)+r*(sz*.104)
            rod(p-n*.099,p-n*.046,.016,"Anodized_Frame",18)
            rod(p-n*.050,p-n*.032,.019,"Grip_Elastomer",18)
            cube(p-n*.024,(.024,.044,.039),"Handheld_Shell",.005)
            hand_screw(p-n*.009,n,.0060)
    turned(c,n,[(-.048,.093,"Anodized_Frame"),(-.046,.117,"Handheld_Shell"),(-.038,.127,"Handheld_Shell"),
                (-.027,.128,"Graphite_Alloy"),(-.024,.126,"Precision_Titanium"),(-.019,.128,"Handheld_Shell"),
                (.001,.126,"Precision_Titanium"),(.007,.121,"Precision_Titanium"),(.015,.118,"Anodized_Frame"),
                (.021,.111,"Precision_Titanium"),(.021,.106,"Black_Rubber"),(.017,.103,"Anodized_Frame"),
                (.013,.102,"Precision_Titanium"),(-.013,.102,"Anodized_Frame")],96)
    # The black precision groove makes the lens edge legible without darkening its optical aperture.
    torus(c+n*.019,n,.110,.0014,"Black_Rubber",80,7)
    torus(c+n*.0158,n,.1028,.00115,"Precision_Titanium",80,7)
    for j in range(12):
        a=T*j/12+.09;d=r*math.cos(a)+u*math.sin(a);pp=c+d*.117+n*.0196
        hand_screw(pp,n,.0039)
    for a in (-.58,.56,2.49,-2.48):
        p=c+(r*math.cos(a)+u*math.sin(a))*.123
        plate(p+n*.0005,n,.013,.008,.002,"Load_Index",.0007)
    # Shallow central backplate bulge in local (u,v) produces the surveyed low-g pocket.
    seg=96;radial=18
    for i in range(radial):
        for j in range(seg):
            ids=[(i,j),(i,j+1),(i+1,j+1),(i+1,j)]
            if i==0:ids.pop(1)
            pts=[];uv=[]
            for k,l in ids:
                a=T*l/seg;q=cell_spec["radius"]*k/radial;xx=math.cos(a)*q;yy=math.sin(a)*q
                off=((xx-.008)/.056)**2+((yy-.0036)/.056)**2
                h=-.0114-.0020*math.exp(-off)
                pts.append(c+n*h+r*xx+u*yy);uv.append(grav_uv("cell_screen",.5+xx/.204,.5+yy/.204))
            face(pts,"Cell_Diffuser",n,uv)
    for j in range(72):
        a=T*j/72;d=r*math.cos(a)+u*math.sin(a);outer=.0978;inset=.0085 if j%6==0 else .0037
        q0=c+d*(outer-inset)-n*.01112;q1=c+d*outer-n*.01112
        rod(q0,q1,.00039 if j%6==0 else .00021,"Cell_Etch",5)
    for h in (-.042,0,.042):
        a=c+r*.025+u*h-n*.01225
        rod(a,a+r*.016,.00042,"Cell_Etch",6)
    for j in range(3):
        port=c+r*(-.074+j*.0016)
        rod(port-u*.058-n*.003,port+u*.058-n*.003,.00047,"Wick_Mesh",7)
    for i in range(29):
        pp=c+r*-.073+u*((i-14)*.00392)-n*.0023
        rod(pp-r*.00238,pp+r*.00238,.00026,"Precision_Titanium",5)
    for yy in (-.059,.059):
        p=c+r*-.073+u*yy-n*.002
        rod(p-n*.011,p+n*.0015,.0039,"Precision_Titanium",12)
    optic(c+n*.0137,n,.104,.0019,"Cell_Optical_Glass")
    # Duplex capillary channels lead to the actual captive piston, with compression nuts and a service port.
    p=v(cell_spec["primerPivot"])
    for sy in (-1,1):
        a=c+r*.119+u*(sy*.016)-n*.027;b=p-r*.024+u*sy*.008-n*.018
        tube([a,a+r*.014,b-u*sy*.004,b],.0028,"Precision_Titanium",8)
        rod(a-r*.008,a+r*.005,.006,"Anodized_Frame",8)
    rod(p-n*.038,p-n*.009,.024,"Anodized_Frame",26)
    torus(p-n*.009,n,.0204,.0021,"Precision_Titanium",26,7)
    lp=c+r*.164+u*.008-n*.037
    plate(lp,n,.072,.027,.006,"Handheld_Shell",.002)
    grav_print(lp+n*.0035,n,.067,.025,"cell_prime")
    title=c-u*.148-n*.027;plate(title,n,.234,.043,.008,"Anodized_Frame",.003)
    grav_print(title+n*.0042,n,.222,.037,"cell_title")
    plate(c+r*.169+u*.060-n*.036,n,.072,.039,.006,"Handheld_Shell",.002)
    grav_print(c+r*.169+u*.060-n*.0324,n,.069,.034,"cell_volume")
    gravity_root(room,"capillary_primer",p,p+n*.003,"Capillary primer","Pulse the sealed fluid cell")
    turned(p,n,[(-.033,.007,"Titanium"),(-.018,.007,"Anodized_Frame"),(-.016,.015,"Precision_Titanium"),
                (-.013,.017,"Load_Index"),(.001,.017,"Load_Index"),(.004,.014,"Anodized_Frame"),
                (.004,0,"Anodized_Frame")],30)
    grip_ring(p-n*.005,n,.017,.011,"Load_Index",20)
    for j in (-1,0,1):plate(p+n*.0044+r*j*.004,n,.0012,.011,.0005,"Load_Index")
    fluid_volume()

acceleration_gauge();capillary_fitting()
