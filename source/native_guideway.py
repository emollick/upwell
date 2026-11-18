"""Build the localized, instanced cable / roller package and place it in Blender."""
guide_web=ROOT/"web"/"assets"/"guideway"
guide_unity=ROOT/"unity"/"Assets"/"Upwell"/"Guideway"
for directory in (guide_web,guide_unity):directory.mkdir(exist_ok=True,parents=True)
kit_parts={};wheel_info=[]
guide_fin=json.loads((guide_unity/"Textures"/"materials.json").read_text())
for name,spec in guide_fin.items():
    value=dict(spec)
    for key in ("baseColor","normal","roughnessMap"):
        if key in value:value[key]=str(guide_unity/"Textures"/value[key])
    material(name,value)
def kit(name,p=(0,0,0)):
    g=native(name,p);kit_parts[name]=g;return g
def lenticular(c,low,high,width,thick,finish,segments=32):
    # The belt has a structural lens section through its broad faces, with
    # independently reinforced edges and a nonzero radius at the tips.
    c=v(c);rings=[]
    for h in (low,high):
        rings.append([c+v((math.cos(T*j/segments)*thick*(.67+.33*abs(math.cos(T*j/segments))),h,
                            math.copysign(abs(math.sin(T*j/segments))**.77,math.sin(T*j/segments))*width)) for j in range(segments)])
    for i in range(segments):
        j=(i+1)%segments
        da=(rings[0][i]-c-Y*low);db=(rings[0][j]-c-Y*low)
        na=v((da.x/(thick*thick),0,da.z/(width*width))).normalized();nb=v((db.x/(thick*thick),0,db.z/(width*width))).normalized()
        face([rings[0][i],rings[0][j],rings[1][j],rings[1][i]],finish,na+nb,normals=[na,nb,nb,na])
def native_strut(a,b,width,height,mat):
    a=v(a);b=v(b);n=(b-a).normalized();r,u,n=basis(n)
    cube((a+b)/2,(width,height,(b-a).length),mat,min(width,height)*.095,Matrix((r,u,n)).transposed())
span=kit("load_span")
lenticular((0,0,0),-4,4,.376,.108,"Tow_Carbon",40)
# Sixteen continuous carbon bundles define the actual 3-D broad-face relief.
for s in (-1,1):
    for k in range(-4,5):
        z=k*.076;x=s*(.094*math.sqrt(max(.03,1-(z/.383)**2)))
        lenticular((x,0,z),-4,4,.044,.0185,"Tow_Carbon",12)
    rod((.059,-4,s*.485),(.059,4,s*.485),.063,"Precision_Titanium",22)
    rod((-.062,-4,s*.401),(-.062,4,s*.401),.028,"Graphite_Alloy",12)
# A six-around-one messenger cable is physically helical, rather than a line
# texture. Eight full lays per instance meet smoothly at both segment ends.
mc=v((-.121,0,.607));rod(mc-Y*4,mc+Y*4,.026,"Graphite_Alloy",10)
for strand in range(6):
    pp=[]
    for k in range(105):
        u=k/104;a=T*(8*u+strand/6)
        pp.append(mc+Y*(u*8-4)+X*math.cos(a)*.033+Z*math.sin(a)*.033)
    tube(pp,.0168,"Precision_Titanium" if strand%3 else "Anodized_Frame",6)
# Independently jacketed high-voltage, return, and optical lines ride in a restrained comb.
for x,z,r,mat in ((-.124,-.516,.033,"Cable_Orange"),(-.171,-.464,.037,"Black_Rubber"),(-.172,-.555,.024,"Cable_Cyan")):
    rod((x,-4,z),(x,4,z),r,mat,13)
for y in (-3,-1,1,3):
    cube((-.105,y,-.466),(.214,.060,.284),"Graphite_Alloy",.016)
    for z in (-.516,-.462,-.555):
        rod((-.182,y-.043,z),(-.182,y+.043,z),.039,"Grip_Elastomer",9)
    for s in (-1,1):
        cube((-.024,y,s*.437),(.144,.048,.15),"Graphite_Alloy",.009)
native_finish(span)
joint=kit("splice")
for s in (-1,1):
    left=s*.127
    cube((left,0,0),(.046,.263,.706),"Graphite_Alloy",.023)
    cube((s*.150,.018,0),(.019,.177,.612),"Titanium",.008)
    for zz in (-.248,0,.248):
        for yy in (-.063,.064):screw((s*.165,yy,zz),X*s,.017,False)
    cube((s*.161,.013,.135),(.005,.046,.098),"Signal_Orange",.002)
for z in (-.485,.485):
    for yy in (-.129,.129):
        rod((.059,yy-.024,z),(.059,yy+.024,z),.0743,"Titanium",18)
rod((-.121,-.141,.607),(-.121,.141,.607),.058,"Graphite_Alloy",16)
for z in (-.516,-.462,-.555):rod((-.159,-.058,z),(-.159,.058,z),.049,"Titanium",10)
native_finish(joint)
bogie=kit("bogie")
for side in (-1,1):
    zz=side*.485
    for yy in (-.343,.343):
        # Carriage-side axle carrier and the opposite pinching shoe form a closed load path.
        native_strut((.311,yy,zz-side*.13),(.692,yy*.64,zz-side*.137),.095,.110,"Graphite_Alloy")
        native_strut((.645,yy*.62,zz-side*.129),(1.027,yy*.94,zz-side*.044),.092,.106,"Ceramic_Pearl")
        native_strut((1.005,yy*.97,zz-side*.047),(.693,-yy*.48,zz-side*.157),.054,.068,"Titanium")
        pp=v((.334,yy,zz-side*.145))
        rod(pp-Z*.048,pp+Z*.048,.076,"Anodized_Frame",16)
        r0=v((.581,yy*.94,zz-side*.187));r1=v((.973,yy*.19,zz-side*.158))
        rod(r0,r0.lerp(r1,.61),.042,"Carbon_Ceramic",12);rod(r0.lerp(r1,.56),r1,.024,"Titanium",14)
    cube((1.039,0,zz),(.155,.946,.169),"Graphite_Alloy",.024)
    for yy in (-.333,.333):
        screw((1.119,yy,zz),X,.033,False)
        # Opposite load arm wraps around the outside of the rail without piercing the load belt.
        tube([(.68,yy*.76,zz+side*.076),(.49,yy*.74,zz+side*.21),(.23,yy*.80,zz+side*.261),
              (-.02,yy*.92,zz+side*.256),(-.221,yy,zz+side*.152)],.043,"Ceramic_Pearl",10)
    tube([(.97,-.24,zz),(.83,-.37,zz-side*.025),(.69,-.38,zz-side*.05),(.51,-.23,zz-side*.083)],.0144,"Cable_Orange",8)
for yy in (-.38,.38):
    native_strut((.92,yy,-.515),(.92,yy,.515),.105,.100,"Carbon_Ceramic")
for zz in (-.28,.28):
    cube((.892,.064,zz),(.149,.162,.185),"Graphite_Alloy",.022)
    for k in range(5):cube((.810,.063,zz+(k-2)*.023),(.024,.126,.012),"Titanium",.002)
label((.934,.438,-.102),Y,.31,.063,"tether")
native_finish(bogie)
for zsign,zn in ((-1,"front"),(1,"rear")):
    for ysign,yn in ((-1,"lower"),(1,"upper")):
        for xsign,xn in ((1,"drive"),(-1,"idler")):
            radius=.214 if xsign==1 else .162
            center=v((.059+xsign*(.063+radius),ysign*.343,zsign*.485));n=Z
            name="roller_"+zn+"_"+yn+"_"+xn;gg=kit(name,center)
            pos=center;w=.123 if xsign==1 else .100
            turned(pos,n,[(-w*.56,radius*.39,"Carbon_Ceramic"),(-w*.53,radius*.57,"Anodized_Frame"),
                (-w*.52,radius*.87,"Titanium"),(-w*.48,radius*1.07,"Titanium"),(-w*.38,radius*1.072,"Graphite_Alloy"),
                (-w*.31,radius,"Grip_Elastomer"),(w*.29,radius,"Grip_Elastomer"),(w*.37,radius*1.065,"Anodized_Frame"),
                (w*.47,radius*1.061,"Titanium"),(w*.53,radius*.85,"Titanium"),(w*.54,radius*.60,"Graphite_Alloy")],32)
            rod(pos-n*.104,pos+n*.104,radius*.26,"Graphite_Alloy",22)
            for j in range(6):
                a=T*j/6;d=X*math.cos(a)+Y*math.sin(a);t=-X*math.sin(a)+Y*math.cos(a)
                native_strut(pos+d*radius*.21+t*.010,pos+d*radius*.76-t*.010,.020,.029,"Titanium")
                if j%2==0:
                    pp=pos+d*radius*.71+n*w*.56
                    cube(pp,(.023,.017,.005),"Signal_Orange",.002)
            native_finish(gg);gg.object.parent=bogie.object;gg.object.location=blender(center)
            wheel_info.append(dict(node=name,pivot=trim(center),axis="z",radius=radius,sign=xsign))
# Export linked geometry while all nodes are at their documented local rest positions.
kit_root=bpy.data.objects.new("guideway",None);ext.objects.link(kit_root)
for name in ("load_span","splice","bogie"):kit_parts[name].object.parent=kit_root
layout={"basis":"glTF metres, vertical +Y, car attachment on +X","file":"guideway.glb","spanNode":"load_span",
    "repeatHeight":8,"spanMinY":-4,"spanMaxY":4,"spliceNode":"splice","splicePeriod":16,"bogieNode":"bogie",
    "railCenters":[[.059,0,-.485],[.059,0,.485]],"railRadius":.063,"rollerAxis":"z","rollers":wheel_info,
    "placements":[{"id":"saloon","position":[-3.46,1.27,-4.87]},{"id":"service","position":[-3.46,1.37,3.06]},
                  {"id":"counterline","position":[-7.89,0,-24.8]}],"parts":[]}
for name,g in kit_parts.items():
    layout["parts"].append(dict(id=name,node=name,file=name+".fbx",webPivot=trim(g.pivot),webBounds=current_bounds(g),
        localBounds=[trim(v(g.lo)-g.pivot),trim(v(g.hi)-g.pivot)],localReferenceVertex=trim(g.verts[0]-g.pivot)))
if "--skip-guide-export" not in sys.argv:
    select_only([kit_root]+[g.object for g in kit_parts.values()])
    bpy.ops.export_scene.gltf(filepath=str(guide_web/"guideway.glb"),export_format="GLB",use_selection=True,
       export_yup=True,export_animations=False,export_lights=False,export_cameras=False,export_extras=True,
       export_vertex_color="ACTIVE",export_image_quality=86)
    for name,g in kit_parts.items():
        tmp=bpy.data.objects.new("SM_"+name,g.mesh.data);ext.objects.link(tmp);select_only([tmp])
        bpy.ops.export_scene.fbx(filepath=str(guide_unity/(name+".fbx")),use_selection=True,axis_forward="-Z",axis_up="Y",
            object_types={"MESH"},bake_space_transform=True,bake_anim=False,apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_UNITS",colors_type="LINEAR",path_mode="RELATIVE",use_triangles=True)
        bpy.data.objects.remove(tmp,do_unlink=True)
    for path in (guide_web,guide_unity):(path/"layout.json").write_text(json.dumps(layout,indent=2))
kit_collection=bpy.data.collections.new("Guideway · local source parts");kit_collection.use_fake_user=True
for ob in [kit_root]+[g.object for g in kit_parts.values()]:
    for co in list(ob.users_collection):co.objects.unlink(ob)
    kit_collection.objects.link(ob)
# Linked native copies provide real parallax in both windows without packing repeated geometry.
def instance(name,g,loc,parent=None):
    ob=bpy.data.objects.new(name,g.mesh.data);ext.objects.link(ob)
    ob.location=blender(loc);ob.parent=parent;return ob
for ii,p0 in enumerate(layout["placements"]):
    x,yp,z=p0["position"];center=v((x,yp,z))
    feed=bpy.data.objects.new(p0["id"]+" · traction feed",None);ext.objects.link(feed)
    for j in range(-5,6):
        instance(p0["id"]+" tow "+str(j),span,(x,j*8,z),feed)
        if j%2==0:instance(p0["id"]+" splice "+str(j),joint,(x,j*8,z),feed)
    for sec in range(361):
        travel=astro["height"](sec)*1000
        feed.location.z=-(travel%16.);feed.keyframe_insert("location",frame=astro["frame_at"](sec))
    if ii<2:
        root=bpy.data.objects.new(p0["id"]+" · load bogie",None);ext.objects.link(root);root.location=blender(center)
        instance(p0["id"]+" pressure frame",bogie,(0,0,0),root)
        for settings in wheel_info:
            g=kit_parts[settings["node"]];wheel=instance(p0["id"]+" "+g.id,g,g.pivot,root)
            for sec in range(0,361,6):
                travelled=astro["height"](sec)*1000;wheel.rotation_euler.y=-settings["sign"]*travelled/settings["radius"]
                wheel.keyframe_insert("rotation_euler",frame=astro["frame_at"](sec))
    far=native(p0["id"]+" · long tensile sightline")
    for low,high in ((-48000,-44),(44,48000)):
        lenticular((x,0,z),low,high,.374,.103,"Tow_Carbon",20)
        for zz in (-.485,.485):rod((x+.059,low,z+zz),(x+.059,high,z+zz),.063,"Precision_Titanium",10)
        rod((x-.121,low,z+.607),(x-.121,high,z+.607),.049,"Anodized_Frame",10)
    native_finish(far).parent=feed
