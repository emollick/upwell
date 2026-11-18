"""Flight-deck controls. Build in the shared glTF-coordinate authoring context."""
deck_atlas = json.loads((LIB/"deck_legends.json").read_text())
switch_specs = []
pixel_specs = []
trace_specs = []
board_materials = {}
probe_ids = ("test_power","test_fiber","test_seal","test_return")
trace_names = ("Power","Fiber","Seal","Return")
fan_pivot = (0,2.545,-4.2715)


def board_mat(name, **settings):
    if name not in M:
        settings = {"rgb":[255,255,255],"roughness":.42,"metallic":.06,"alpha":1,**settings}
        material(name,settings)
        board_materials[name] = settings
    return name


board_mat("Deck_Legends",baseColor="Deck_Legends.png",roughness=.56)
board_mat("Berth_Diffuser",rgb=[250,220,168],emission=1.6)
for panel_name in ("Diagnostic","Drive","Access","Pressure","Berth","Seal","Intercom","Service","Folio","Optic","Vessel"):
    board_mat("Pixels_"+panel_name,baseColor="Standby_"+panel_name+".png",roughness=.23,emission=.55)


def board_legend(center,normal,width,height,word):
    r,u,n = basis(normal)
    x,y,w,h = deck_atlas["rects"][word]
    aw,ah = deck_atlas["size"]
    # Preserve the glyph proportions inside the stamped legend's envelope.
    h0 = min(height,width*h/w)
    w0 = h0*w/h
    uv = [(x/aw,1-(y+h)/ah),((x+w)/aw,1-(y+h)/ah),((x+w)/aw,1-y/ah),(x/aw,1-y/ah)]
    p = v(center)
    face([p+r*(a*w0/2)+u*(b*h0/2) for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))],"Deck_Legends",n,uv)


def live_panel(id, p, n, w, h):
    r,u,n = basis(n)
    p = v(p)
    key = "Pixels_"+id
    face([p+r*(a*w/2)+u*(b*h/2) for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))],key,n,[(0,0),(1,0),(1,1),(0,1)])
    pixel_specs.append(dict(id=id,room=current.room,part=current.id,material=key,center=list(p),normal=list(n),size=[w,h]))


def new_part(room,key,p,focus=None,title=None):
    if key not in propinfo:
        propinfo[key] = dict(name=title or key.replace("_"," ").title(),action="Operate")
    return active(room,key,p,focus if focus is not None else p)


def moving_control(room,key,p,focus,kind,axis,amount,stops=2):
    switch_specs.append(dict(id=key,room=room,kind=kind,axis=list(v(axis).normalized()),amount=amount,stops=stops))
    return new_part(room,key,p,focus)


def telltale(p,n,key,colour=(128,224,213),width=.019,height=.005):
    name = board_mat("Ann_"+key,rgb=list(colour),roughness=.26,emission=1.15)
    plate(p,n,width+.005,height+.004,.003,"Black_Rubber",.001)
    plate(v(p)+v(n)*.002,n,width,height,.002,name,.0008)


def secondaries(c,n):
    r,u,n = basis(n)
    for x,w,kind,key in ((-.128,.268,"Diagnostic","diagnostic_screen"),(.156,.258,"Drive","drive_screen")):
        p = v((x,1.195,-5.103))+n*.026
        new_part("observation",key,p,p+n*.018)
        plate(p,n,w,.235,.022,"Graphite_Alloy",.015)
        rim(p+n*.012,n,w-.008,.226,.014,w-.032,.194,.009,.004,"Black_Rubber")
        live_panel(kind,p+n*.0126,n,w-.031,.194)
    edit_prop("observation","pilot_console")


def flight_controls(deck,n):
    r,u,n = basis(n)
    room = "observation"
    toggles = ("guide_flood","cabin_lights","solar_film","vent_fan")
    for j,key in enumerate(toggles):
        edit_prop(room,"pilot_console")
        p = deck+r*(-.615+j*.112)+n*.020-u*.004
        plate(p-n*.004,n,.099,.131,.009,"Graphite_Alloy",.007)
        pp = p+n*.004
        if j in (0,3):
            rod(pp,pp+n*.008,.025,"Titanium",12)
            torus(pp+n*.008,n,.019,.0034,"Black_Rubber",20,6)
            if j==0:
                for s in (-1,1):
                    q=pp+r*s*.041
                    tube([q-u*.036,q-u*.032+n*.027,q-u*.017+n*.047,q+u*.025+n*.047,q+u*.037+n*.018,q+u*.041],.0042,"Titanium",8)
        else:
            rim(pp+n*.004,n,.080,.085,.009,.061,.065,.006,.010,"Black_Rubber")
        board_legend(p+u*.071+n*.005,n,.080,.016,("GUIDE","CABIN","FILM","VENT")[j])
        telltale(p-u*.054+n*.004,n,key,(255,174,88) if j in (0,2) else (140,222,213),.024)
        pivot=pp+n*.012
        moving_control(room,key,pivot,pivot+n*(.025 if j in (0,3) else .007), "rotate",r,(-45,-24,-30,-42)[j])
        if j in (0,3):
            end=pivot+n*.043-u*.018
            rod(pivot-n*.005,end,.0063,"Titanium",12,r2=.0073)
            if j==0:
                rod(end-n*.009+u*.004,end+n*.014-u*.006,.010,"Signal_Orange",16,r2=.0085)
                rod(end+n*.010-u*.004,end+n*.013-u*.006,.010,"Ceramic_Pearl",14)
            else:
                plate(end+n*.001,n,.031,.021,.016,"Grip_Elastomer",.005)
                for k in (-1,0,1):
                    plate(end+n*.010+r*.009*k,n,.002,.014,.0012,"Titanium",.0004)
        else:
            levernormal=(n-u*.23).normalized()
            plate(pivot+n*.003,levernormal,.057,.067,.016,"Carbon_Ceramic" if j==1 else "Titanium",.005)
            if j==1:
                for k in range(4):
                    q=pivot+n*.012+u*(.002+k*.0051)
                    rod(q-r*.021,q+r*.021,.00125,"Grip_Elastomer",6)
                plate(pivot+n*.015-u*.021,n,.026,.003,.0015,"Ceramic_Pearl",.0005)
            else:
                rod(pivot-r*.031,pivot+r*.031,.006,"Graphite_Alloy",12)
                plate(pivot-u*.016+n*.013,n,.045,.022,.0045,"Safety_Amber",.002)
    keys=("key_route","key_optics","key_seals","key_load","key_traffic","key_comms","key_lamp_test")
    for j,key in enumerate(keys):
        edit_prop(room,"pilot_console")
        p=deck+r*(-.177+j*.078)+n*.020-u*.008
        plate(p,n,.072,.090,.010,"Graphite_Alloy",.006)
        rim(p+n*.008,n,.064,.083,.006,.056,.073,.005,.008,"Black_Rubber")
        telltale(p+u*.056+n*.001,n,key,(244,175,99) if j in (5,6) else (117,223,211),.027)
        pivot=p+n*.013
        moving_control(room,key,pivot,pivot+n*.009,"press",-n,.0075)
        plate(pivot,n,.054,.070,.015,"Titanium" if j in (0,3) else "Graphite_Alloy",.004)
        plate(pivot+n*.008,n,.0502,.065,.006,"Carbon_Ceramic",.003)
        board_legend(pivot+n*.0113+u*.003,n,.045,.018,("RTE","CAM","SEAL","LOAD","TRAF","CREW","TEST")[j])
        # Distinct tactile indexes let the watch find the optical and audio keys in darkness.
        if j in (1,5):
            for k in range(1 if j==1 else 2):
                q=pivot+n*.011-u*(.018+.0045*k)
                rod(q-r*.012,q+r*.012,.0013,"Safety_Amber" if j==5 else "Aluminum",8)
    for j,key in enumerate(("panel_gain","camera_focus")):
        edit_prop(room,"pilot_console")
        p=deck+r*(.477+j*.16)+n*.022-u*.005
        rod(p-n*.003,p+n*.001,.057,"Graphite_Alloy",32)
        torus(p+n*.0014,n,.049,.0015,"Titanium",36,5,span=(math.radians(11),math.radians(170)))
        for tick in range(13):
            angle=math.radians(-130+tick*260/12)
            d=u*math.cos(angle)+r*math.sin(angle)
            rod(p+d*.045+n*.002,p+d*(.054 if tick%3==0 else .05)+n*.002,.0011,"Ceramic_Pearl" if tick%3==0 else "Aluminum",5)
        board_legend(p+u*.076+n*.001,n,.085,.016,("GAIN","LENS")[j])
        pivot=p+n*.004
        moving_control(room,key,pivot,pivot+n*.022,"rotate",n,-260,5)
        rod(pivot,pivot+n*.005,.039,"Titanium",32)
        rod(pivot+n*.004,pivot+n*.033,.035 if j else .037,"Grip_Elastomer" if j else "Graphite_Alloy",48,r2=.033 if j else .036)
        for k in range(26 if j else 34):
            angle=T*k/(26 if j else 34)
            d=r*math.cos(angle)+u*math.sin(angle);side=-r*math.sin(angle)+u*math.cos(angle)
            radius=.035 if j else .037
            rod(pivot+d*radius+n*.006,pivot+d*(radius-.001)+side*(.003 if j else -.003)+n*.030,.00145,"Titanium" if not j else "Carbon_Ceramic",6)
        cap=pivot+n*.035
        rod(cap-n*.003,cap,.032 if j else .034,"Titanium" if j else "Carbon_Ceramic",32)
        d=u*math.cos(math.radians(-130))+r*math.sin(math.radians(-130))
        rod(cap+d*.011+n*.0005,cap+d*.032+n*.0005,.002,"Signal_Orange" if j else "Ceramic_Pearl",8)
    edit_prop(room,"pilot_console")


def probe_control(k,z):
    key=probe_ids[k]
    n=-X;r,u,_=basis(n);p=v((1.932,1.192,z))
    plate(p+X*.025,n,.163,.154,.050,"Graphite_Alloy",.011)
    rim(p,n,.157,.145,.012,.143,.130,.009,.008,"Titanium")
    board_legend(p+u*.048+n*.002,n,.113,.019,("28 V","FIBER","SEALS","RETURN")[k])
    q=p+u*.002+n*.004
    if k in (0,2):
        rod(q-n*.002,q+n*.003,.033,"Black_Rubber",20)
    else:
        plate(q,n,.080,.064,.008,"Black_Rubber",.006)
    telltale(p-u*.053+n*.002,n,key,(248,174,86) if k in (0,2) else (101,214,231),.046,.008)
    pivot=q+n*.010
    moving_control("service",key,pivot,pivot+n*.008,"press",-n,.008)
    if k in (0,2):
        rod(pivot-n*.005,pivot+n*.006,.026,"Safety_Amber" if k==0 else "Composite_Slate",24,r2=.023)
        torus(pivot+n*.006,n,.014,.0016,"Graphite_Alloy" if k==0 else "Aluminum",16,5)
    else:
        plate(pivot,n,.064,.046,.016,"Carbon_Ceramic",.005)
        for j in (-1,0,1):
            rod(pivot+n*.008+u*.006*j-r*.017,pivot+n*.008+u*.006*j+r*.017,.0012,"Titanium",6)
    shell("service")


def probe_trace(k, route):
    key=trace_names[k]
    names=("Trace_Power","Trace_Fiber","Trace_Seal","Trace_Return")
    mat=board_mat(names[k],rgb=[73,86,86],roughness=.38)
    # A laminated witness fibre runs along the inboard face of the corresponding physical loom.
    pts=[v(p)-X*.0130 for p in route]
    dist=[0.]
    for a,b in zip(pts,pts[1:]):dist.append(dist[-1]+(b-a).length)
    ds=[]
    for i,p in enumerate(pts):
        tangent=pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]
        side=tangent.cross(-X)
        if side.length<.000001:side=Y.copy()
        ds.append(side.normalized()*.0039)
    for i,(a,b) in enumerate(zip(pts,pts[1:])):
        t=dist[i]/dist[-1];q=dist[i+1]/dist[-1]
        face([a-ds[i],a+ds[i],b+ds[i+1],b-ds[i+1]],mat,-X,[(t,0),(t,1),(q,1),(q,0)])
    trace_specs.append(dict(id=probe_ids[k],material=names[k],points=[list(p) for p in pts]))


def fan_assembly():
    room="observation";shell(room)
    n=-Y;r,u,_=basis(n);p=v(fan_pivot)
    plate(p-n*.008,n,.315,.333,.031,"Graphite_Alloy",.015)
    rod(p+n*.002,p+n*.009,.139,"Black_Rubber",48)
    torus(p+n*.015,n,.137,.008,"Titanium",48,8)
    for rr in (.055,.091,.119):torus(p+n*.033,n,rr,.0022,"Graphite_Alloy",36,6)
    for k in range(6):
        angle=T*k/6;d=r*math.cos(angle)+u*math.sin(angle)
        rod(p+d*.025+n*.035,p+d*.135+n*.030,.0028,"Titanium",7)
    new_part(room,"blower_rotor",p,p,title="Circulation impeller")
    rod(p+n*.009,p+n*.026,.033,"Titanium",20,r2=.027)
    for k in range(7):
        a=T*k/7
        ring=[]
        for rad,da,h in ((.022,0,.018),(.077,.15,.020),(.123,.39,.019),(.124,.68,.013),(.102,.74,.012),(.065,.45,.014),(.025,.40,.018)):
            ring.append(p+(r*math.cos(a+da)+u*math.sin(a+da))*rad+n*h)
        face(ring,"Anodized_Frame",n)
    shell(room)


def remap_hand_panel(room,prop,panel,src):
    # The mug's LCD follows a curved steel wall; retain every authored vertex and unwrap just its display.
    group=groups[(room,"mech_log_leaf" if prop=="logbook" else prop)]
    old=group.matindex["Handheld_Display"]
    slot=group.matindex.setdefault("Pixels_"+panel,len(group.matlist))
    if slot==len(group.matlist):group.matlist.append("Pixels_"+panel)
    x,y,w,h=handatlas["rects"][src];aw,ah=handatlas["size"]
    for i,polygon in enumerate(group.faces):
        if group.ids[i]!=old:continue
        group.ids[i]=slot
        for vertex in polygon:
            a,b=group.uv[vertex]
            group.uv[vertex]=((a*aw-x)/w,(b*ah-(ah-y-h))/h)
    pixel_specs.append(dict(id=panel,room=room,part=prop,pixelNode=group.id,material="Pixels_"+panel))


def finish_switchboard():
    for room,prop,name,tile in (("berth","logbook","Folio","log_display"),("berth","mug","Vessel","cup_lcd"),("observation","field_glasses","Optic","optic_lcd")):
        remap_hand_panel(room,prop,name,tile)
    fan_assembly()
    pixel_specs.append(dict(id="Passage",room="observation",part="nav_screen",material="Nav_Active_Pixels"))
    return {"basis":"glTF +X starboard, +Y up, +Z aft", "units":"m", "controls":switch_specs,"displays":pixel_specs,
            "traces":trace_specs,"fan":{"node":"prop_blower_rotor","part":"blower_rotor","pivot":list(fan_pivot),"axis":[0,-1,0]},
            "materials":[dict(name=k,**val) for k,val in board_materials.items()]}
