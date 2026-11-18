"""Fabrication geometry for the five inspectable, hand-scale carriage items."""
handatlas=json.loads((LIB/"handheld_atlas.json").read_text())
def print_uv(key,ux,uy):
    x,y,w,h=handatlas["rects"][key];aw,ah=handatlas["size"]
    return ((x+ux*w)/aw,1-(y+(1-uy)*h)/ah)
def dataface(c,n,w,h,key,em=False,right=None):
    c=v(c);r,u,n=basis(n)
    if right is not None:r=v(right).normalized();u=n.cross(r)
    xy=((-1,-1),(1,-1),(1,1),(-1,1))
    ink=key in ("vessel","optics","focus","driver","log_shell","valve","log_paper")
    face([c+r*w*a/2+u*h*b/2 for a,b in xy],"Handheld_Display" if em else "Handheld_Markings" if ink else "Service_Print",n,
         [print_uv(key,(a+1)/2,(b+1)/2) for a,b in xy])
def turned(c,n,profile,seg=40):
    """Rotationally machined solid or open bore. Each contour carries its surface finish."""
    c=v(c);r,u,n=basis(n);ds=[r*math.cos(T*j/seg)+u*math.sin(T*j/seg) for j in range(seg)]
    for (ta,ra,mat),(tb,rb,_) in zip(profile[:-1],profile[1:]):
        if abs(tb-ta)+abs(rb-ra)<1e-8:continue
        for j in range(seg):
            k=(j+1)%seg;aa=ds[j];bb=ds[k]
            na=(aa*(tb-ta)-n*(rb-ra)).normalized();nb=(bb*(tb-ta)-n*(rb-ra)).normalized()
            pp=[c+n*ta+aa*ra,c+n*ta+bb*ra,c+n*tb+bb*rb,c+n*tb+aa*rb]
            nn=[na,nb,nb,na]
            uv=None
            if mat=="Vessel_Enamel":
                uv=[(j/seg,ta/.125),((j+1)/seg,ta/.125),((j+1)/seg,tb/.125),(j/seg,tb/.125)]
            elif mat=="Vessel_Keeper":
                uv=[(.5+(p.x-c.x)/.068,.5+(p.z-c.z)/.068) for p in pp]
            elif mat in ("Titanium","Graphite_Alloy","Grip_Elastomer") and abs(tb-ta)>.0005:
                repeat=T*(ra+rb)*.5*8
                uv=[(j/seg*repeat,ta*8),((j+1)/seg*repeat,ta*8),((j+1)/seg*repeat,tb*8),(j/seg*repeat,tb*8)]
            if ra<.00001:
                pp.pop(1);nn.pop(1)
                if uv:uv.pop(1)
            elif rb<.00001:
                pp.pop(2);nn.pop(2)
                if uv:uv.pop(2)
            face(pp,mat,na+nb,uv=uv,normals=nn)
def knurl(c,n,radius,length,mat,count=36,wire=.00048,twist=.10,both=False):
    c=v(c);r,u,n=basis(n)
    for i in range(count):
        for s in ((-1,1) if both else (1,)):
            a=T*i/count;path=[]
            for k in range(3):
                t=k/2;ang=a+s*(t-.5)*twist
                path.append(c+n*((t-.5)*length)+(r*math.cos(ang)+u*math.sin(ang))*radius)
            tube(path,wire,mat,5)
def polyprism(points,n,depth,mat):
    n=v(n).normalized();a=[v(p)-n*depth/2 for p in points];b=[v(p)+n*depth/2 for p in points]
    face(a,mat,-n);face(b,mat,n)
    for i in range(len(a)):
        j=(i+1)%len(a);face([a[i],a[j],b[j],b[i]],mat)
def optic(c,n,r,depth,mat):
    c=v(c);a,b,n=basis(n);steps=40;rings=8
    shape=[]
    for i in range(rings+1):
        q=i/rings;row=[]
        for j in range(steps):
            rn=a*math.cos(T*j/steps)+b*math.sin(T*j/steps)
            row.append((c+rn*r*q+n*depth*(1-q*q),(n+rn*(2*depth*q/r)).normalized()))
        shape.append(row)
    for i in range(rings):
        for j in range(steps):
            k=(j+1)%steps;ids=[(i,j),(i,k),(i+1,k),(i+1,j)]
            if i==0:ids.pop(1)
            pp=[shape[h][z][0] for h,z in ids];ns=[shape[h][z][1] for h,z in ids]
            uv=[(.5+.5*(h/rings)*math.cos(T*j0/steps),.5+.5*(h/rings)*math.sin(T*j0/steps)) for h,j0 in ids]
            face(pp,mat,n,uv,normals=ns)
def curved_print(c,angle,radius,width,height,key,material="Service_Print"):
    c=v(c);count=20
    if key=="vessel":material="Handheld_Markings"
    for j in range(count):
        r0=j/count;r1=(j+1)/count
        a=angle+(r0-.5)*width/radius;b=angle+(r1-.5)*width/radius
        da=X*math.cos(a)+Z*math.sin(a);db=X*math.cos(b)+Z*math.sin(b)
        # Increasing angle moves left when seen from the outside.
        pts=[c+da*radius-Y*height/2,c+db*radius-Y*height/2,c+db*radius+Y*height/2,c+da*radius+Y*height/2]
        face(pts,material,da+db,[print_uv(key,1-r0,0),print_uv(key,1-r1,0),print_uv(key,1-r1,1),print_uv(key,1-r0,1)],
             [da,db,db,da])
def stitch(path,widthdir,width=.0069,thread="Technical_Twill",step=.006):
    ww=v(widthdir).normalized()
    for a,b in zip(path[:-1],path[1:]):
        a=v(a);b=v(b);d=b-a;count=max(1,int(d.length/step));unit=d/count
        for i in range(count):
            for s in (-1,1):
                pp=a+unit*i+ww*s*width*.366
                rod(pp,pp+unit*.63,.00038,thread,4)
def hardware_strap(points,w,guide,mat="Grip_Elastomer",sewn=True):
    line=[v(p) for p in points];d=v(guide).normalized()
    for a,b in zip(line[:-1],line[1:]):
        t=(b-a).normalized();r=(d-t*t.dot(d)).normalized()*w/2
        norm=t.cross(r).normalized();th=norm*.00074
        face([a-r+th,a+r+th,b+r+th,b-r+th],mat,norm)
        face([a-r-th,b-r-th,b+r-th,a+r-th],mat,-norm)
        for s in (-1,1):face([a+s*r-th,a+s*r+th,b+s*r+th,b+s*r-th],mat,r*s)
    if sewn:stitch(line,d,w)
def hand_screw(p,n,rad=.0024):
    p=v(p);r,u,n=basis(n)
    rod(p-n*rad*.28,p+n*rad*.18,rad*1.14,"Black_Rubber",12)
    rod(p+n*rad*.12,p+n*rad*.27,rad,"Titanium",12)
    for a in (0,math.pi/2):
        aa=(r*math.cos(a)+u*math.sin(a))*rad*.63
        bb=(-r*math.sin(a)+u*math.cos(a))*rad*.12;c=p+n*rad*.30
        face([c-aa-bb,c+aa-bb,c+aa+bb,c-aa+bb],"Graphite_Alloy",n)


def field_optics():
    edit_prop("observation","field_glasses")
    center=v((-1.17,1.008,-5.139))
    for s in (-1,1):
        c=center+X*s*.041
        prof=[(-.089,.018,"Grip_Elastomer"),(-.086,.025,"Grip_Elastomer"),(-.082,.026,"Grip_Elastomer"),
              (-.077,.026,"Grip_Elastomer"),(-.075,.024,"Carbon_Ceramic"),(-.073,.024,"Grip_Elastomer"),
              (-.071,.026,"Grip_Elastomer"),(-.063,.025,"Grip_Elastomer"),(-.061,.023,"Graphite_Alloy"),
              (-.054,.023,"Titanium"),(-.052,.025,P("field_glasses")),(-.041,.028,"Ceramic_Pearl"),
              (.004,.031,"Ceramic_Pearl"),(.043,.035,"Ceramic_Pearl"),(.047,.035,"Graphite_Alloy"),
              (.051,.034,"Titanium"),(.053,.0348,"Carbon_Ceramic"),(.065,.0348,"Graphite_Alloy"),
              (.071,.034,"Titanium"),(.072,.0325,"Carbon_Ceramic"),(.072,.0290,"Black_Rubber"),
              (.063,.0282,"Carbon_Ceramic"),(.060,.0271,"Graphite_Alloy"),(.055,.0261,"Carbon_Ceramic"),
              (.047,.0245,"Black_Rubber"),(.043,.0245,"Black_Rubber")]
        turned(c,Z,prof,48)
        optic(c+Z*.045,Z,.0246,.0038,"Optical_Coating")
        optic(c+Z*.052,Z,.0260,.0030,"Optical_Laminate")
        optic(c+Z*.059,Z,.0270,.0022,"Optical_Laminate")
        # Blackened aperture blades are visible between the objectives and the
        # smaller inner group at oblique inspection angles.
        for j in range(12):
            a=T*j/12;t=a+.32;u0=X*math.cos(a)+Y*math.sin(a);u1=X*math.cos(t)+Y*math.sin(t)
            vv=[c+Z*.058+u0*.0280,c+Z*.058+u1*.0280,
                c+Z*.055+u1*.0251,c+Z*.054+u0*.0247]
            face(vv,"Carbon_Ceramic" if j%2 else "Graphite_Alloy",Z)
        for z,rad in ((.045,.0252),(.052,.0262),(.060,.0271),(.065,.0287)):
            torus(c+Z*z,Z,rad,.00059,"Titanium" if z==.060 else "Graphite_Alloy",40,5)
        knurl(c+Z*.058,Z,.0349,.008,"Graphite_Alloy",36,.00038,.05)
        # Rear diopter has a recessed eyepiece, captive retaining ring and tactile alignment index.
        optic(c-Z*.081,-Z,.0177,.0018,"Optical_Coating")
        torus(c-Z*.087,-Z,.0189,.0010,"Black_Rubber",36,5)
        for j in range(7):
            a=.7+j*.25;p=c+v((math.cos(a)*.0257,math.sin(a)*.0257,-.060))
            rod(p-Z*.0014,p+Z*.0014,.00056,"Ceramic_Pearl" if j!=3 else "Signal_Orange",5)
        pp=c+Y*.029+Z*.011;cube(pp,(.043,.014,.075),"Ceramic_Pearl",.006)
        dataface(pp+Y*.0073,Y,.035,.023,"optics" if s<0 else "focus")
        for zz in (-.014,.037):hand_screw(pp+Y*.0073+X*s*.012+Z*zz,Y,.00165)
        outer=c+X*s*.032-Y*.003-Z*.018
        rim(outer+X*s*.004,X*s,.028,.018,.004,.017,.008,.003,.006,"Titanium")
    c=center+Y*.029
    for z in (-.047,.031):
        rod(c-X*.040+Z*z,c+X*.040+Z*z,.0079,"Graphite_Alloy",14)
        rod(c-X*.015+Z*z,c+X*.015+Z*z,.0101,"Titanium",18)
    fc=center+Y*.043-Z*.028
    articulate("observation","mech_optics_focus","field_glasses",fc,"z",72,6,"Turn focus drum")
    turned(fc,Z,[(-.018,.012,"Titanium"),(-.014,.0162,"Graphite_Alloy"),(-.010,.0178,"Titanium"),
                 (.010,.0178,"Graphite_Alloy"),(.014,.0162,"Titanium"),(.017,.012,"Graphite_Alloy")],36)
    knurl(fc,Z,.0178,.0194,"Graphite_Alloy",48,.0005,.12,True)
    for da in (0,.19):
        dd=X*math.sin(da)+Y*math.cos(da)
        rod(fc+dd*.01815-Z*.0076,fc+dd*.01815+Z*.0076,.00055,"Signal_Orange" if da==0 else "Handheld_Shell",5)
    edit_prop("observation","field_glasses")
    rod(fc-Z*.022,fc+Z*.023,.0103,"Carbon_Ceramic",24)
    rod(fc+Z*.020,fc+Z*.024,.0062,"Titanium",20)
    for s in (-1,1):
        tube([fc+X*s*.009-Z*.007,fc+v((s*.017,-.006,-.011)),center+v((s*.032,.021,-.037))],.0054,"Carbon_Ceramic",12)
    fc=center+v((0,.006,.057))
    cube(fc,(.039,.029,.023),"Carbon_Ceramic",.0041)
    dataface(fc+Z*.012,Y*.09+Z,.029,.017,"optic_lcd",True)
    strap=[center+v((-.077,-.001,-.021)),center+v((-.090,-.022,-.004)),center+v((-.099,-.034,.029)),
           center+v((-.079,-.035,.062)),center+v((-.031,-.035,.078)),center+v((.054,-.035,.080)),
           center+v((.092,-.034,.058)),center+v((.100,-.026,.018)),center+v((.075,-.001,-.022))]
    remember_flex("observation","flex_optic_lanyard","field_glasses",strap,[0,len(strap)-1],.008,.0016,
                  "Aramid_Webbing","ribbon",.061,.968,guide=(0,1,0))


def drink_vessel():
    edit_prop("berth","mug");c=v((1.80,.950,-.934))
    # Formed underside, magnetic stainless keeper and recessed annular seal.
    # The elastomer heel supports the cup while the laser-marked keeper clears the table.
    turned(c,Y,[(.0026,0,"Vessel_Keeper"),(.0024,.019,"Vessel_Keeper"),(.0019,.025,"Vessel_Keeper"),
        (.0015,.0288,"Vessel_Keeper"),(.0015,.0296,"Black_Rubber"),(.0019,.0305,"Precision_Titanium"),
        (.0010,.0319,"Precision_Titanium"),(.0003,.0332,"Grip_Elastomer"),(0,.0340,"Grip_Elastomer"),(.001,.039,"Grip_Elastomer"),(.003,.0412,"Graphite_Alloy"),
        (.006,.0415,"Titanium"),(.009,.0405,P("mug")),(.015,.0440,"Vessel_Enamel"),
        (.020,.0455,"Vessel_Enamel"),(.022,.0461,"Vessel_Enamel"),(.0233,.0464,"Vessel_Enamel"),
        (.0245,.0461,"Vessel_Enamel"),(.029,.0464,"Vessel_Enamel"),(.085,.0464,"Vessel_Enamel"),
        (.098,.0454,"Vessel_Enamel"),(.100,.0455,"Vessel_Enamel"),(.1011,.04515,"Vessel_Enamel"),(.105,.0442,"Titanium"),(.107,.0441,"Black_Rubber"),
        (.109,.0425,"Titanium"),(.111,.0432,"Carbon_Ceramic"),(.118,.0444,"Graphite_Alloy"),
        (.123,.0435,"Carbon_Ceramic"),(.125,.0408,"Carbon_Ceramic"),(.125,.0360,"Black_Rubber"),
        (.122,.034,"Carbon_Ceramic"),(.122,0,"Carbon_Ceramic")],96)
    for h in (.0042,.0053,.1054):
        torus(c+Y*h,Y,.04155 if h<.01 else .04423,.00024,"Precision_Titanium",80,6)
    for i in range(3):
        a=T*(i+.21)/3;stake=c+(X*math.cos(a)+Z*math.sin(a))*.0247+Y*.0016
        rod(stake-Y*.0001,stake+Y*.0002,.0015,"Anodized_Frame",16)
        torus(stake,-Y,.00165,.00026,"Titanium",18,6)
    # Three short purchase pads around the locking collar leave the seal line exposed.
    for sector in range(3):
        for tooth in range(8):
            a=T*sector/3+(tooth-3.5)*.057;rad=X*math.cos(a)+Z*math.sin(a)
            rod(c+rad*.04405+Y*.1128,c+rad*.04418+Y*.1184,.00058,"Grip_Elastomer",6)
    for h in (.0108,.1035,.1087):torus(c+Y*h,Y,.0415 if h<.02 else .0442,.00085,"Black_Rubber",48,6)
    curved_print(c+Y*.066,math.pi,.0467,.071,.032,"vessel")
    curved_print(c+Y*.025,math.pi,.0466,.060,.0145,"cup_lcd","Handheld_Display")
    curved_print(c+Y*.068,.0,.0467,.048,.013,"valve")
    # D-shaped overmoulded handle, a visible through-hole, and four serviceable attachments.
    hc=c+Z*.070+Y*.066;n=-X
    contour=[(.044,.029),(.060,.025),(.078,.025),(.088,.029),(.095,.038),(.100,.055),
             (.100,.083),(.097,.095),(.091,.104),(.078,.110),(.060,.111),(.044,.103)]
    # Compact moulded handle follows a continuous spline. Its aperture suits
    # two fingers, with an overmoulded inner rim distinct from the cup shell.
    contour=[c+Z*(.044+(zz-.044)*.72)+Y*yy for zz,yy in contour]
    spline=[]
    for j in range(len(contour)-1):
        a,b,d,e=contour[max(0,j-1)],contour[j],contour[j+1],contour[min(len(contour)-1,j+2)]
        for k in range(4):
            t=k/4;spline.append((2*b+(-a+d)*t+(2*a-5*b+4*d-e)*t*t+(-a+3*b-3*d+e)*t*t*t)*.5)
    spline.append(contour[-1])
    tube(spline[:14],.0074,"Ceramic_Pearl",22)
    tube(spline[13:35],.00766,"Grip_Elastomer",24)
    tube(spline[34:],.0074,"Ceramic_Pearl",22)
    for k in (16,19,22,25,28,31):
        along=(spline[k+1]-spline[k-1]).normalized()
        torus(spline[k],along,.00735,.00045,"Grip_Elastomer",22,6)
    for h in (.027,.105):
        pp=c+Z*.044+Y*h
        cube(pp,(.020,.019,.026),"Carbon_Ceramic",.0052)
        hand_screw(pp-X*.0105,-X,.0020)
    # Captive lid rotates against annular gasket; two bosses support the hinged vent latch.
    for side in (-1,1):
        pp=c+X*(side*.013)+Z*.009+Y*.126
        cube(pp,(.008,.012,.022),"Graphite_Alloy",.0028)
    pin=c+Z*.011+Y*.132;rod(pin-X*.0182,pin+X*.0182,.0033,"Titanium",14)
    # A bored-in drink port and a concentric silicone seat become visible as the paddle lifts.
    hole=c+Y*.1235-Z*.011
    flat_round(hole,Y,.0194,.0127,.005,"Black_Rubber")
    rim(hole+Y*.0003,Y,.021,.015,.0058,.0163,.0103,.0047,.0008,"Titanium")
    articulate("berth","mech_mug_valve","mug",pin,"x",38,2,"Lift drink valve")
    plate(c+Y*.132-Z*.003,Y,.031,.039,.006,"Grip_Elastomer",.0023)
    cube(c+Y*.136-Z*.011,(.016,.0038,.011),"Signal_Orange",.0011)
    for zz in (-.027,-.020,-.014):
        cube(c+Y*.135+Z*zz,(.016,.0015,.0016),"Grip_Elastomer",.00035)
    edit_prop("berth","mug")
    flat_round(c+v((.013,.123,-.018)),Y,.0096,.0045,.0018,"Black_Rubber")
    for j in range(4):
        pp=c+v((-.018+j*.011,.1248,-.024))
        rod(pp-Y*.001,pp+Y*.0004,.0016,"Black_Rubber",10)
    st=c+v((-.013,.108,.045));torus(st+Y*.005,X,.009,.0016,"Titanium",22,6)
    remember_flex("berth","flex_vessel_keeper","mug",
        [st+Y*.006,st-X*.007-Y*.006+Z*.004,st-X*.011-Y*.031+Z*.010,st-X*.009-Y*.046+Z*.026,
         st-X*.003-Y*.044+Z*.027,st+X*.004-Y*.028+Z*.033,st+X*.006-Y*.016+Z*.035],[0,6],.0034,.0034,
         "Grip_Elastomer","cord",.017,.948)
    for j in range(30):
        a=T*j/30;p=c+v((.042*math.cos(a),.0047,.042*math.sin(a)))
        rod(p-Y*.00155,p+Y*.00155,.00067,"Grip_Elastomer",5)


def flight_log():
    edit_prop("berth","logbook");c=v((1.711,.953,.183))
    # Low-profile chart binder: glass flight log front, leafed hardcopy checklist and sewn hinge at its back.
    for y,ww,dd,th,mat in ((.001,.216,.157,.006,"Grip_Elastomer"),(.006,.211,.152,.007,P("logbook")),
        (.012,.202,.147,.005,"Technical_Twill"),(.017,.202,.147,.007,"Paper")):
        cube(c+Y*y,(ww,th,dd),mat,.0029)
    for j in range(7):
        pp=c+Y*(.0145+j*.00072)
        cube(pp+X*.101,(.00061,.00025,.139),"Paper" if j%2 else "Data_Jacket")
        cube(pp+Z*.073,(.194,.00025,.00057),"Paper" if j%3 else "Composite_Slate")
    dataface(c+Y*.0207,Y,.188,.129,"log_checklist")
    for z in (-.047,.047):
        pp=c+v((-.104,.023,z));rod(pp-Z*.016,pp+Z*.016,.0052,"Titanium",14)
    articulate("berth","mech_log_leaf","logbook",c+v((-.104,.023,0)),"z",72,2,"Open flight log")
    for y,ww,dd,th,mat in ((.022,.214,.154,.004,"Carbon_Ceramic"),(.026,.214,.154,.006,"Ceramic_Pearl")):
        cube(c+Y*y,(ww,th,dd),mat,.0029)
    rim(c+Y*.030,Y,.213,.153,.010,.188,.117,.004,.005,"Graphite_Alloy")
    plate(c+Y*.0298,Y,.189,.118,.003,"Smoked_Display",.0014)
    dataface(c+Y*.0315,Y,.183,.113,"log_display",True)
    dataface(c+v((-.049,.0304,-.067)),Y,.069,.010,"log_shell")
    for sx in (-1,1):
        for sz in (-1,1):
            pp=c+X*sx*.099+Z*sz*.069+Y*.029
            cube(pp,(.015,.006,.014),"Titanium",.0024)
            hand_screw(pp+Y*.0032,Y,.0022)
    for j in range(3):
        p=c+X*.107+Y*.022+Z*((j-1)*.021)
        cube(p,(.0045,.0048,.011),"Graphite_Alloy",.0013)
    dataface(c+Y*.01985,-Y,.134,.064,"log_paper",right=X)
    edit_prop("berth","logbook")
    strap=c-X*.102+Y*.012
    turned(strap,Z,[(-.074,.005,"Grip_Elastomer"),(-.068,.0080,"Wallet_Canvas"),(.064,.0080,"Wallet_Canvas"),(.074,.005,"Graphite_Alloy")],18)
    stitch([strap-X*.007-Z*.067,strap-X*.007+Z*.065],Y,.004,step=.0048)
    # Stainless spring fence clamps down on the manual watch card on the underside.
    h=c+v((.014,-.0027,.045))
    dataface(c-Y*.0025,-Y,.142,.090,"log_paper",right=X)
    tube([h-X*.030,h-X*.030-Z*.025,h-X*.025-Z*.03,h+X*.027-Z*.03,h+X*.031-Z*.026,h+X*.031],.0014,"Titanium",8)
    rod(h-X*.036,h+X*.037,.0022,"Graphite_Alloy",10)
    left=c+v((-.110,.017,-.049));rim(left,X,.019,.012,.003,.012,.006,.002,.003,"Titanium")
    line=[left,left-X*.012+Z*.004,left-X*.019+Z*.024-Y*.005,left-X*.014+Z*.042-Y*.011,left-X*.006+Z*.052-Y*.013]
    hardware_strap(line,.006,Y,"Aramid_Webbing")


def credential():
    edit_prop("berth","access_card");c=v((1.67,.702,-.31));w=.0866;h=.0550
    # The suspension slot penetrates every ply and both printed faces. Copper zones are physical inlays.
    p=v((-.0356,0,.001));wc=.0035;hc=.0148
    for yy,th,mat in ((.00052,.00105,"Graphite_Alloy"),(-.00045,.0003,"Ceramic_Pearl"),(-.00073,.0003,"Carbon_Ceramic")):
        rim(c+Y*yy,Y,w,h,.0039,wc,hc,.00165,th,mat,"Titanium",center_offset=(p.x,-p.z))
    def print_ply(side,key):
        n=Y*side;r,u,n=basis(n)
        # Mirrored lower print still reads left-to-right when the card is turned over.
        a=[(x,y) for x,y in arc_rect(w,h,.0039,7)]
        b=[(x+p.x,y+(c+p-c).dot(u)) for x,y in arc_rect(wc,hc,.00165,7)]
        pos=c+n*.00095
        for j in range(len(a)):
            k=(j+1)%len(a);q=(a[j],a[k],b[k],b[j])
            face([pos+r*x+u*y for x,y in q],"Service_Print",n,
                 [print_uv(key,x/w+.5,y/h+.5) for x,y in q])
    print_ply(1,"card_face");print_ply(-1,"card_reverse")
    chip=c+X*(-.027)+Z*.004+Y*.00108
    flat_round(chip,Y,.0124,.0094,.00165,"Black_Rubber")
    for j in range(2):
        for k in range(3):
            pp=chip+Y*.000095+X*((k-1)*.00378)+Z*((j-.5)*.00403)
            flat_round(pp,Y,.00358,.00384,.00062,"Credential_Contacts")
    for j in range(4):
        t=j/3
        tube([chip+v((-.0048,.0002,-.0034+t*.002)),chip+v((-.0034,.0002,-.0016+t*.002)),chip+v((-.0004,.0002,-.0016+t*.002))],
             .000070,"Graphite_Alloy",5)
    # Optical witness slivers in the die-cut laminated edge.
    for z in (-.013,.013):
        cube(c+v((.0429,.00002,z)),(.00073,.00040,.0060),"Signal_Orange")


def wallet():
    edit_prop("service","tool_roll");c=v((-1.868,.862,3.70))
    # Open shock-mounted service folio with a raised, angled lid at the wall side.
    base=c+Z*.004
    cube(base,(.305,.026,.488),"Carbon_Ceramic",.011)
    rim(base+Y*.015,Y,.305,.487,.021,.279,.457,.017,.007,"Titanium","Grip_Elastomer")
    cube(base+Y*.014,(.282,.013,.459),P("tool_roll"),.005)
    for sx in (-1,1):
        for sz in (-1,1):
            pp=base+X*sx*.133+Z*sz*.223+Y*.016
            cube(pp,(.030,.013,.026),"Grip_Elastomer",.0043);hand_screw(pp+Y*.008,Y,.003)
    hinge=base-X*.145+Y*.020
    for sz in (-1,1):
        pp=hinge+Z*sz*.143
        rod(pp-Z*.053,pp+Z*.053,.0094,"Titanium",18)
        for off in (-.039,.0,.039):rod(pp+Z*(off-.008),pp+Z*(off+.008),.0115,"Graphite_Alloy",14)
    n=v((.93,.367,0)).normalized();r,u,n=basis(n)
    lc=hinge+u*.095
    plate(lc,n,.465,.187,.016,"Wallet_Canvas",.006)
    rim(lc+n*.009,n,.465,.187,.017,.429,.151,.012,.006,"Graphite_Alloy","Titanium")
    dataface(lc+n*.0094,n,.331,.094,"case_lid")
    for ss in (-1,1):
        line=[lc+r*(q*.182)+u*ss*.079+n*.013 for q in (-1,-.55,0,.55,1)]
        stitch(line,u,.0038,step=.0072)
    for j in range(6):
        a=hinge+Z*((j-2.5)*.068)
        tube([a+X*.017,a+Y*.017-X*.001,a+Y*.030-X*.014],.00325,"Grip_Elastomer",7)
    front=c+X*.149+Y*.009
    for z in (-.137,.137):
        l=front+Z*z;cube(l,(.015,.019,.043),"Graphite_Alloy",.004)
        cube(l+X*.007+Y*.001,(.009,.010,.030),"Signal_Orange",.002)
    # Maker's torque driver: turned endcap, metered rotation scale, undercut knurls, keyed chuck and actual bit.
    tc=c+v((-.085,.047,.003));axis=Z
    turned(tc,axis,[(-.193,.005,"Titanium"),(-.182,.010,"Titanium"),(-.165,.010,"Graphite_Alloy"),
      (-.159,.014,"Titanium"),(-.149,.016,"Titanium"),(-.143,.018,"Graphite_Alloy"),
      (-.121,.018,"Titanium"),(-.116,.019,"Signal_Orange"),(-.107,.019,"Grip_Elastomer"),
      (-.099,.021,"Grip_Elastomer"),(-.073,.022,"Grip_Elastomer"),(-.051,.017,"Ceramic_Pearl"),
      (.067,.017,"Ceramic_Pearl"),(.081,.021,"Grip_Elastomer"),(.109,.021,"Grip_Elastomer"),
      (.124,.019,"Graphite_Alloy"),(.132,.018,"Titanium"),(.150,.0165,"Graphite_Alloy"),(.162,.014,"Titanium"),
      (.170,.009,"Titanium"),(.179,.0067,"Carbon_Ceramic")],40)
    rod(tc-Z*.190,tc-Z*.213,.005,"Graphite_Alloy",6)
    rod(tc+Z*.168,tc+Z*.204,.0062,"Titanium",6)
    knurl(tc-Z*.135,Z,.0181,.020,"Titanium",40,.00068,.21,True);knurl(tc+Z*.143,Z,.0167,.014,"Graphite_Alloy",34,.00054,.10)
    for j in range(14):
        a=T*j/14
        for z0,z1 in ((-.100,-.070),(.085,.116)):
            d=X*math.cos(a)+Y*math.sin(a)
            tube([tc+Z*z0+d*.021,tc+Z*((z0+z1)*.5)+d*.0218,tc+Z*z1+d*.0205],.00082,"Grip_Elastomer",5)
    dataface(tc+Y*.01734,Y,.093,.0156,"driver",right=Z)
    # Steel ratchet and open combination spanner each have real tool ends, pivots and bore.
    rat=c+v((-.015,.035,-.014))
    turned(rat,Z,[(-.174,.0078,"Titanium"),(-.162,.0094,"Graphite_Alloy"),(-.150,.011,"Grip_Elastomer"),
                  (-.065,.011,"Grip_Elastomer"),(-.056,.007,"Titanium"),(.088,.0065,"Titanium"),(.130,.011,"Titanium")],20)
    rc=rat+Z*.141;rod(rc-Y*.009,rc+Y*.009,.025,"Titanium",28)
    torus(rc+Y*.010,Y,.017,.0020,"Graphite_Alloy",24,7);rod(rc+Y*.008,rc+Y*.014,.012,"Carbon_Ceramic",18)
    cube(rc+Y*.015-Z*.006,(.009,.006,.017),"Signal_Orange",.002)
    wr=c+v((.044,.031,.005));rod(wr-Z*.126,wr+Z*.107,.0054,"Titanium",12)
    head=wr+Z*.119
    outline=[(-.007,-.017),(-.016,-.005),(-.019,.014),(-.013,.024),(-.007,.011),(.004,.008),
             (.011,.017),(.015,.027),(.021,.015),(.019,-.001),(.010,-.016)]
    polyprism([head+X*x+Z*z for x,z in outline],Y,.0082,"Titanium")
    torus(wr-Z*.137,Y,.013,.004,"Titanium",12,8)
    # Hex sockets are hollow, supported on a captive pin rail. Multiple ends remain visually distinct when inspected.
    bc=c+v((.100,.027,.017));cube(bc,(.041,.010,.306),"Graphite_Alloy",.004)
    for i in range(6):
        pp=bc+Z*((i-2.5)*.0455)+Y*.006;rr=.0095+i*.0008
        turned(pp,Y,[(0,rr*.67,"Black_Rubber"),(.005,rr,"Titanium"),(.019,rr,"Titanium"),(.022,rr*.87,"Titanium"),
                     (.022,rr*.52,"Graphite_Alloy"),(.012,rr*.46,"Black_Rubber")],12 if i>2 else 18)
        rod(pp+Y*.008,pp+Y*.012,rr*.43,"Carbon_Ceramic",6)
    kp=c+v((.100,.057,.167))
    for sx in (-1,1):
        cube(kp+X*sx*.020-Y*.008,(.007,.022,.019),"Graphite_Alloy",.002)
    rod(kp-X*.023,kp+X*.023,.0033,"Titanium",14)
    articulate("service","mech_tool_keeper","tool_roll",kp,"x",62,2,"Release socket keeper")
    for sx in (-1,1):
        path=[kp+X*sx*.015,kp+X*sx*.016-Z*.012+Y*.003,kp+X*sx*.016-Z*.105+Y*.003,
              kp+X*sx*.013-Z*.116]
        tube(path,.0027,"Titanium",8)
    for zz in (.029,.069,.109):
        cube(kp-Z*zz+Y*.003,(.034,.0048,.009),"Restraint_Webbing" if zz<.1 else "Signal_Orange",.0013)
    edit_prop("service","tool_roll")
    for zz in (-.123,.103):
        line=[c+v((-.113,.017,zz)),c+v((-.110,.055,zz)),c+v((-.091,.071,zz)),c+v((-.072,.073,zz)),
              c+v((-.061,.059,zz)),c+v((-.058,.022,zz))]
        hardware_strap(line,.014,Z,"Restraint_Webbing")
    dataface(c+v((.085,.0215,-.191)),Y,.098,.027,"bit_tag")
    # Doubled-back aramid pockets trap the ratchet and spanner without covering their heads.
    for xp,ww in ((-.015,.046),(.044,.042)):
        row=[]
        for j in range(11):
            q=j/10;xx=xp+(q-.5)*ww
            crown=.023*(math.sin(math.pi*q)**.70)
            row.append([c+v((xx,.021+crown*.51,-.150)),c+v((xx,.025+crown,-.129)),
                        c+v((xx,.023+crown,-.092+.004*math.sin(q*7)))])
        for a,b in zip(row[:-1],row[1:]):
            for i in (0,1):face([a[i],b[i],b[i+1],a[i+1]],"Wallet_Canvas",Y)
        tube([a[-1] for a in row],.0015,"Aramid_Webbing",6)
        for k in (-1,1):
            line=[c+v((xp+k*(ww/2-.003),.024,-.149)),c+v((xp+k*(ww/2-.003),.025,-.095))]
            stitch(line,X,.0025,step=.0052)
    remember_flex("service","flex_tool_tether","tool_roll",
        [tc+Z*.171+X*.003,tc+Z*.187-X*.009+Y*.006,tc+Z*.201-X*.029+Y*.001,tc+Z*.204-X*.047-Y*.014,
         tc+Z*.191-X*.057-Y*.027,tc+Z*.166-X*.059-Y*.027,tc+Z*.147-X*.053-Y*.017],
         [0,6],.004,.004,"Grip_Elastomer","cord",.022,.877)


field_optics();drink_vessel();flight_log();credential();wallet()

remember_flex("observation","flex_seat_sling","lounge_seat",
      [(-1.33,.533,-4.434),(-1.322,.501,-4.389),(-1.317,.454,-4.311),(-1.318,.437,-4.192),
       (-1.321,.449,-4.065),(-1.328,.491,-3.984),(-1.339,.533,-3.925)],[0,6],.019,.0022,
       "Aramid_Webbing","ribbon",.057,guide=(1,0,0))
_buckle_height=quilt_height(-1.473,.533)+.027
remember_flex("berth","flex_berth_tail","bunk",
      [(-1.471,_buckle_height,.542),(-1.439,_buckle_height+.005,.540),(-1.391,quilt_height(-1.391,.54)+.017,.543),(-1.333,quilt_height(-1.333,.54)+.017,.545),
       (-1.290,.957,.549),(-1.267,.931,.556),(-1.252,.889,.560)],[0,1],.037,.0028,
       "Restraint_Webbing","ribbon",.036,None,guide=(0,0,1))
for flex_id,d in flex_parts.items():
    par=groups[(d["room"],d["parent"])]
    g=active(d["room"],flex_id,par.pivot,par.center,parent=par.id)
    if d["kind"]=="cord":
        tube(d["points"],d["width"]*.5,d["material"],9)
    else:
        hardware_strap(d["points"],d["width"],d["guide"],d["material"])
