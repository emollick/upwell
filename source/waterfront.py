"""Sea-level logistics and wave protection around the pelagic launch pier."""
def harbor():
    global current
    current=groups[("anchor","anchor_apron")]
    cement="Pier_Concrete" if "Pier_Concrete" in meta else "Tidal_Deck"
    def pile(p,r=.53):
        p=v(p);rod(p-Y*7.6,p+Y*.28,r,cement,16)
        rod(p-Y*6.12,p-Y*5.06,r*1.018,"Marine_Primer",16)
        rod(p-Y*.40,p-Y*.12,r*1.22,"Graphite_Alloy",16)
    def bridge(a,b,width,guard=True):
        a=v(a);b=v(b);f=(b-a);fl=f.length;f.normalize();r=Y.cross(f).normalized()
        steps=max(2,math.ceil(fl/4.0))
        for k in range(steps):
            s=a+(b-a)*(k/steps);e=a+(b-a)*((k+1)/steps)
            strut(s-Y*.12,e-Y*.12,width,.25,"Tidal_Deck",.02)
            for side in (-1,1):
                sk=s+r*side*(width*.5-.09);ek=e+r*side*(width*.5-.09)
                strut(sk-Y*.31,ek-Y*.31,.16,.32,"Marine_Primer")
                if guard:rails(sk,ek,.96,"Structural_Galvanized","Safety_Amber")
            if k%2==0:
                for side in (-1,1):pile(s+r*side*(width*.5-.31)-Y*.41,.36)
                strut(s-r*width*.44-Y*.59,s+r*width*.44-Y*1.52,.11,.14,"Marine_Primer")
    def mooring(p):
        p=v(p)
        cube(p+Y*.07,(.76,.14,.58),"Graphite_Alloy",.042)
        for s in (-1,1):
            q=p+X*(s*.188)+Y*.12
            rod(q,q+Y*.341,.113,"Graphite_Alloy",16);rod(q+Y*.310,q+Y*.38,.143,"Safety_Amber",16)
    def life_ring(p,n):
        p=v(p);n=v(n);torus(p,n,.286,.049,"Marine_Vermilion",30,8)
        r,u,n=basis(n)
        for j in range(4):
            a=.48+T*j/4;d=r*math.cos(a)+u*math.sin(a);pp=p+d*.286
            tang=-r*math.sin(a)+u*math.cos(a);rod(pp-tang*.037,pp+tang*.037,.051,"Ceramic_Pearl",10)
    # Dogleg access spine links the launch caisson to the stores / transfer pier.
    bridge((-12.0,-.62,-30.2),(-22.7,-.72,-50.8),2.60)
    bridge((-22.7,-.72,-50.8),(-45.2,-.77,-84.2),2.46)
    deck(-35.1,-.68,-63.4,27.7,13.4,cement)
    for x in (-46.2,-35,-23.9):
        for z in (-68.2,-58.3):pile((x,-1.0,z),.79)
    for z in (-69.93,-56.91):
        rails((-48.5,-.68,z),(-21.7,-.68,z),1.0,"Structural_Galvanized","Safety_Amber")
        for xx in (-45,-36.4,-27.8):mooring((xx,-.67,z+.33))
    # Cylindrical hydraulic accumulator bank and folded pipe gallery.
    for j in range(3):
        c=v((-38.4,-.05+j*.64,-63.8));a=c-X*3.36;b=c+X*3.36
        rod(a,b,.737,"Marine_Primer" if j<2 else "Structural_Galvanized",26)
        for s in (-1,1):
            end=c+X*s*3.36;rod(end,end+X*s*.195,.737,"Structural_Galvanized",26,r2=.624)
            rod(end+X*s*.195,end+X*s*.366,.624,"Marine_Primer",22,r2=.291)
            rod(end+X*s*.361,end+X*s*.547,.153,"Titanium",14)
        for xoff in (-2.18,2.18):
            torus(c+X*xoff,X,.743,.032,"Graphite_Alloy",28,7)
            cube(c+X*xoff-Y*.67,(.24,.32,1.51),"Marine_Vermilion",.025)
    for k in range(4):
        z=-61.1+k*.27
        pipe([(-43.8,-.22,z),(-43.8,1.12,z),(-43.69,1.36,z),(-43.38,1.49,z),(-29.7,1.49,z),
              (-29.41,1.37,z),(-29.3,1.10,z),(-29.3,-.03,z)],.099 if k%2 else .071,
             ("Structural_Galvanized","Marine_Vermilion","Graphite_Alloy","Marine_Primer")[k])
    # Lattice-boom, luffing service crane. Its slew bearing, drum, counterweight and
    # load path are visible from the saloon and become a scale cue after the car clears the shaft.
    crane=v((9.0,-.63,-48.3))
    bridge((9.6,-.64,-28.91),(9.23,-.66,-45.30),3.02)
    deck(crane.x,-.65,crane.z,10.46,12.70,cement)
    for s in (-1,1):
        for q in (-1,1):pile(crane+v((s*4.24,-.32,q*5.02)),.75)
    rod(crane-Y*.16,crane+Y*.25,2.44,"Pier_Concrete" if "Pier_Concrete" in meta else "Tidal_Deck",36)
    rod(crane+Y*.21,crane+Y*2.19,1.43,"Marine_Primer",32,r2=1.10)
    rod(crane+Y*2.17,crane+Y*2.60,1.66,"Graphite_Alloy",40)
    for j in range(22):
        d=X*math.cos(T*j/22)+Z*math.sin(T*j/22)
        rod(crane+d*1.48+Y*2.56,crane+d*1.48+Y*2.68,.079,"Titanium",8)
    cube(crane+v((.22,2.87,.11)),(3.20,.51,3.34),"Marine_Vermilion",.112)
    # Counterweights sit behind the lifting pin, with retained slings at the corners.
    for j in range(3):
        cube(crane+v((-.56,3.37+j*.37,1.29)),(2.08,.34,1.13),cement,.079)
    for signx in (-1,1):
        strut(crane+v((signx*.95,3.09,1.13)),crane+v((signx*.58,6.73,.35)),.177,.214,"Structural_Galvanized",.018)
        strut(crane+v((signx*.58,6.73,.35)),crane+v((signx*.93,3.31,-.91)),.156,.176,"Marine_Vermilion",.016)
    cabin=crane+v((1.19,3.85,.38))
    cube(cabin-Y*.34,(1.56,.75,1.67),"Marine_Primer",.112)
    cube(cabin+Y*.85,(1.69,.156,1.81),"Structural_Galvanized",.043)
    for sx in (-1,1):
        for sz in (-1,1):
            strut(cabin+v((sx*.69,-.01,sz*.77)),cabin+v((sx*.71,.83,sz*.75)),.060,.065,"Graphite_Alloy",.007)
    plate(cabin+Y*.415+Z*.761,Z,1.30,.684,.026,"Smoked_Display",.014)
    plate(cabin+Y*.417+X*.716,X,1.36,.684,.026,"Smoked_Display",.014)
    start=crane+v((0,3.80,-.95));end=crane+v((6.93,17.75,-17.34))
    f=(end-start).normalized();lat=Y.cross(f).normalized();vert=f.cross(lat).normalized()
    for j in range(11):
        a=j/11;b=(j+1)/11;p=start+(end-start)*a;q=start+(end-start)*b
        w0=.94-.63*a;w1=.94-.63*b;h0=.78-.49*a;h1=.78-.49*b
        for side in (-1,1):
            for up in (-1,1):
                pa=p+lat*side*w0+vert*up*h0;pb=q+lat*side*w1+vert*up*h1
                rod(pa,pb,.083 if j<6 else .061,"Marine_Vermilion",9)
            pa=p+lat*side*w0-vert*h0;pb=q+lat*side*w1+vert*h1
            rod(pa,pb,.046,"Structural_Galvanized",7)
            rod(p+lat*side*w0+vert*h0,q+lat*side*w1-vert*h1,.036,"Marine_Vermilion",7)
        rod(p-lat*w0-vert*h0,p+lat*w0-vert*h0,.054,"Graphite_Alloy",7)
    for side in (-1,1):
        top=crane+v((side*.55,6.71,.36));rod(top,end+lat*side*.31+vert*.29,.026,"Graphite_Alloy",8)
        rod(top,crane+v((side*.68,3.02,1.36)),.022,"Titanium",8)
    rod(end-lat*.39,end+lat*.39,.292,"Graphite_Alloy",20)
    hook=end-Y*6.37
    for dx in (-.12,.12):rod(end+lat*dx,hook+lat*dx,.019,"Titanium",7)
    rod(hook-lat*.17,hook+lat*.17,.147,"Safety_Amber",14)
    tube([hook-Y*.10,hook-Y*.47,hook-Y*.60+lat*.13,hook-Y*.54+lat*.27,hook-Y*.42+lat*.28],.048,"Graphite_Alloy",9)
    # A moored offshore crew launch. Separate hull strakes, sloping bridge glass,
    # rub rails and the stern working deck distinguish it from the small inspection skiff.
    b=v((1.03,-6.71,-52.4));rows=[]
    cross=[(-7.12,.04,.84),(-6.38,1.07,1.11),(-5.18,1.79,1.19),(-3.27,2.10,1.12),(.19,2.26,1.03),
           (3.81,2.21,.91),(5.96,1.94,.89),(6.55,1.66,.88)]
    for z,w,h in cross:
        rows.append([b+v((x,y,z)) for x,y in ((-w,h),(-w*.97,.32),(-w*.81,-.50),(-w*.39,-.91),(0,-1.02),
             (w*.39,-.91),(w*.81,-.50),(w*.97,.32),(w,h))])
    for aa,bb in zip(rows[:-1],rows[1:]):
        for j in range(8):face([aa[j],aa[j+1],bb[j+1],bb[j]],"Marine_Vermilion" if j in (0,7) else "Graphite_Alloy")
        face([aa[0],bb[0],bb[-1],aa[-1]],"Tidal_Deck",Y)
    for idx in (0,8):tube([row[idx] for row in rows],.098,"Black_Rubber",10)
    cube(b+v((0,1.31,-.47)),(3.07,.74,4.34),"Orbital_Porcelain",.151)
    cube(b+v((0,2.59,-.46)),(3.06,.203,4.31),"Orbital_Porcelain",.071)
    for side in (-1,1):
        for zz in (-2.33,-.92,.54,1.44):
            strut(b+v((side*1.49,1.61,zz)),b+v((side*1.37,2.49,zz+.065)),.070,.071,"Structural_Galvanized",.008)
        for zz in (-1.63,-.19,.995):
            lp=b+v((side*1.435,2.063,zz));plate(lp,X*side,.99,.74,.046,"Smoked_Display",.020)
        life_ring(b+v((side*1.53,1.48,.96)),X*side)
        rails(b+v((side*1.92,.94,1.69)),b+v((side*1.77,.92,5.39)),.77,"Titanium")
    fn=v((0,.22,-1)).normalized()
    for sx in (-1,1):plate(b+v((sx*.69,2.048,-2.56)),fn,1.24,.75,.042,"Smoked_Display",.019)
    mast=b+v((0,2.69,-.09));rod(mast,mast+Y*2.46,.044,"Structural_Galvanized",12)
    rod(mast+Y*1.73-X*.86,mast+Y*1.73+X*.86,.040,"Orbital_Porcelain",10)
    cube(mast+Y*1.92,(1.39,.11,.16),"Orbital_Porcelain",.036)
    for sx,col in ((-1,"Red_Emitter"),(1,"Mint_Emitter")):rod(mast+X*sx*.77+Y*1.76,mast+X*sx*.77+Y*1.91,.068,col,12)
    crate(b+v((.61,1.37,3.39)),1.07,.78,.97,"Marine_Primer")
    drum(b+v((-.75,1.31,3.96)),X,.74,.36,"Marine_Vermilion")
    for zz in (-3.61,3.93):
        for sx in (-1,1):
            p=b+v((sx*1.86,1.00,zz));torus(p,X,.274,.122,"Black_Rubber",18,8)
    for zz in (-4.56,4.13):
        tube([b+v((1.75,1.14,zz)),(4.29,-5.35,b.z+zz*.97),(6.10,-3.11,b.z+zz*.75),(5.09,-.47,b.z+zz*.72)],.043,"Aramid_Webbing",8)
    # A chain of semi-submerged wave attenuators protects the tender basin.
    for j in range(7):
        a=v((-53.0+j*9.87,-5.92,-100.3+j*1.49));b=a+v((9.35,0,1.41));f=(b-a).normalized();r=Y.cross(f).normalized()
        strut(a,b,2.63,1.61,cement,.239);strut(a+Y*.851,b+Y*.851,2.34,.159,"Tidal_Deck",.043)
        for k in (-1,1):
            pp=a.lerp(b,.34 if k<0 else .69)-r*1.368
            rod(pp-f*.38,pp+f*.38,.42,"Black_Rubber",14)
        if j<6:
            for k in (-1,1):rod(b+r*k*.75,b+r*k*.75+f*.60,.093,"Graphite_Alloy",9)
    def buoy(c,col,id):
        c=v(c);rod(c-Y*.80,c-Y*.20,.65,"Graphite_Alloy",16,r2=1.04)
        rod(c-Y*.20,c+Y*.234,1.04,col,18,r2=.96);rod(c+Y*.234,c+Y*.53,.96,col,18,r2=.45)
        for a in (0,T/3,2*T/3):
            d=X*math.cos(a)+Z*math.sin(a);rod(c+d*.37+Y*.44,c+d*.13+Y*2.52,.040,"Structural_Galvanized",8)
        rod(c+Y*2.48,c+Y*2.81,.132,"Amber_Emitter" if id%2 else "Mint_Emitter",14)
        plate(c+Y*1.46,Z,.66,.45,.069,col,.018)
    for j in range(4):
        for s in (-1,1):
            buoy((s*(25.1+j*4.71)+19.2,-6.98,-87.7-j*23.3),"Marine_Vermilion" if s<0 else "Marine_Primer",j+(0 if s<0 else 1))
    # Beacon tower on the outer attenuator. A viewer at 100 m can still resolve this navigation light.
    c=v((-51.4,-5.05,-100.1))
    for sx,sz in ((-1,-1),(-1,1),(1,-1),(1,1)):
        rod(c+v((sx*.85,0,sz*.85)),c+v((sx*.37,7.31,sz*.37)),.102,"Marine_Vermilion",8)
    for j in range(4):
        h=j*1.69;w=.80-j*.09;w1=w-.090
        for s in (-1,1):
            rod(c+v((-w,h,s*w)),c+v((w1,h+1.55,s*w1)),.057,"Structural_Galvanized",7)
            rod(c+v((s*w,h,-w)),c+v((s*w1,h+1.55,w1)),.057,"Structural_Galvanized",7)
    rod(c+Y*7.29,c+Y*7.87,.56,"Graphite_Alloy",16,r2=.38);rod(c+Y*7.83,c+Y*8.37,.273,"Amber_Emitter",18)
    # An offshore crew-transfer / rescue helideck adjoins the stores pier. Its
    # real international-style touchdown circle also reads at true ascent range.
    hc=v((-45.90,-.40,-87.05))
    rod(hc-Y*.61,hc-Y*.082,10.81,"Graphite_Alloy",8)
    rod(hc-Y*.082,hc,10.64,cement,8)
    torus(hc+Y*.009,Y,6.71,.080,"Safety_Amber",64,6)
    for x in (-1.21,1.21):cube(hc+X*x+Y*.021,(.52,.012,4.41),"Ceramic_Pearl",.003)
    cube(hc+Y*.020,(2.48,.012,.51),"Ceramic_Pearl",.003)
    for j in range(8):
        a=T*j/8;d=X*math.cos(a)+Z*math.sin(a);t=-X*math.sin(a)+Z*math.cos(a)
        pp=hc+d*9.84
        rod(pp-Y*.54,pp-Y*6.5,.44,cement,12)
        strut(pp-Y*.65,pp-d*2.90-Y*2.56,.133,.154,"Marine_Primer")
        rod(pp+Y*.023,pp+Y*.139,.110,"Graphite_Alloy",10)
        rod(pp+Y*.132,pp+Y*.201,.081,"Mint_Emitter",10)
    # Painted loading lane and actual recessed edge fittings on the remote apron.
    for j in range(9):
        cube((-45.21+j*2.39,-.645,-59.26),(1.40,.009,.20),"Safety_Amber",.002)
    print_face((-27.90,-.644,-64.30),Y,4.12,1.16,"cargo")
    for ss in (-1,1):
        dock=crane+X*ss*4.08
        for k in range(3):
            p=dock+Z*((k-1)*2.74)+Y*.016
            cube(p,(.17,.009,1.64),"Ceramic_Pearl")
    station=hc+v((6.93,.40,5.33));crate(station,.94,.74,1.15,"Marine_Vermilion")
    mast=hc+v((-6.79,.11,6.09));rod(mast,mast+Y*3.73,.045,"Titanium",9)
    tip=mast+Y*3.73
    for j in range(5):
        p=tip+v((j*.283,-j*.035,-j*.066));q=tip+v(((j+1)*.283,-(j+1)*.035,-(j+1)*.066))
        rod(p,q,.223-j*.032,"Marine_Vermilion" if j%2==0 else "Ceramic_Pearl",12,r2=.223-(j+1)*.032)
    for z in (-.41,.41):
        bridge((hc.x+7.96,-.41,hc.z+4.88+z),(-40.32,-.74,-70.13+z),.80,guard=False)
harbor()
