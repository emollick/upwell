"""The inner transfer gallery and its three inhabited land strips, in habitat survey units (80 m)."""
from math import sin, cos, pi, exp
import random

TAU=2*pi
LAND_RADIUS=7.22
GALLERY_ANGLE=-.70


def river(y):
    return .146*sin(y*.31+.26)+.055*sin(y*.72-.48)


def village_house(drum,p,Y,radial,tangent,a,y,sector,w,length,height,index):
    rt=radial(a);side=tangent(a);base=p(a,y,LAND_RADIUS-.006)
    # Every building casts onto its own curved parcel. All parts co-rotate
    # with the collector, so these recessed baked umbrae remain in register.
    theta=a-sector;run=height/(-.79*cos(theta)+.64*sin(theta))
    skew=(side*(.79*sin(theta)+.64*cos(theta))-Y*.41)*run
    level=base-rt*.001
    x=side*(w*.50);z=Y*(length*.50)
    footprint=[level-x-z,level+x-z,level+x+z,level-x+z]
    # The visible left and far sides form the convex outline in this light.
    drum.face([footprint[0],footprint[1],footprint[2],footprint[2]+skew,footprint[3]+skew,footprint[0]+skew],
              'LandShadow',-rt,uv=[(0,0)]*6)
    drum.obox(a,y,LAND_RADIUS-.006-height*.5,w,length,height,'Building')
    eave=base-rt*height
    x=side*(w*.53);z=Y*(length*.52)
    if index%4==0:
        drum.obox(a,y,LAND_RADIUS-height-.020,w+.008,length+.010,.025,'Roof')
        drum.obox(a,y+length*.08,LAND_RADIUS-height-.038,w*.59,length*.65,.017,'WindowBank')
    else:
        height_roof=w*(.26+.045*(index%3));ridge=eave-rt*height_roof;end=Y*(length*.32)
        drum.face([eave-x-z,eave-x+z,ridge+end,ridge-end],'Roof',-rt-side*.48)
        drum.face([eave+x+z,eave+x-z,ridge-end,ridge+end],'Roof',-rt+side*.48)
        drum.face([eave-x+z,eave+x+z,ridge+end],'Roof',-rt+Y*.45)
        drum.face([eave+x-z,eave-x-z,ridge-end],'Roof',-rt-Y*.45)
        if index%3==0:
            drum.obox(a+.16*w/LAND_RADIUS,y+.23*length,LAND_RADIUS-height-height_roof*.70,.019,.026,.045,'Building')
    # A recessed run of dark glazing with two or more structural divisions.
    for sign in (-1,1):
        face=eave+rt*(.34*height)+side*(sign*(w*.5+.0012))
        drum.block(face,(side,Y,rt),(.0025,length*.78,min(.031,height*.25)),'WindowBank')
        for multiplier in (-.21,.10):
            drum.block(face+Y*(multiplier*length)+side*(sign*.0012),(side,Y,rt),(.0025,.008,min(.033,height*.26)),'Building')


def fixtures(drum,axle,tram,p,Y,radial,tangent):
    # The camera is on the nonrotating transfer spindle, 320 m inside its end.
    # A broad inspection pane faces the land; its sill and lamp stay stationary.
    rad=radial(GALLERY_ANGLE);tan=tangent(GALLERY_ANGLE)
    eye=Y*(-16.1)+rad*1.58
    forward=(rad*.46+Y*.888).normalized();up=(Y*.46-rad*.888).normalized()
    right=tan
    pane=eye+forward*.083
    for side in (-1,1):
        a=pane+right*(side*.072)
        axle.block(a,(right,up,forward),(.007,.109,.008),'Frame')
        axle.block(a+right*(side*.003)+forward*.001,(right,up,forward),(.003,.111,.004),'Structure')
        for yy in (-.037,-.017,.021,.043):
            ctr=a+up*yy-forward*.0048
            axle.rod(ctr,ctr-forward*.0018,.0016,'Structure',8)
    for sign in (-1,1):
        ctr=pane+up*(.0445*sign)
        axle.block(ctr,(right,up,forward),(.148,.006,.012),'Frame')
        axle.block(ctr+up*sign*.003-forward*.001,(right,up,forward),(.149,.003,.013),'BlueGrey')
        axle.block(ctr-up*sign*.0029-forward*.006,(right,up,forward),(.146,.00065,.0015),'PaleStone')
    sill=pane-up*.049
    axle.block(sill-forward*.006,(right,up,forward),(.151,.004,.041),'Gasket')
    for x in (0,.019,.038):
        axle.block(sill+right*(x-.056)+up*.0057-forward*.0057,(right,up,forward),(.009,.0012,.0011),'LitWindow')
    # Spine terminates just abaft the optical pupil; its wall faces the rotating landscape.
    axle.rod(Y*(-20.45),Y*(-16.7),.48,'Frame',32)
    axle.rod(Y*(-16.91),Y*(-16.59),.53,'Foil',32)
    axle.rod(Y*(-16.67),eye-forward*.063,.17,'Structure',20)
    axle.rod(eye-forward*.068,eye-forward*.030,.084,'Frame',24)
    for j in range(3):
        sector=j*TAU/3
        rng=random.Random(3113+j)
        # Each canopied group is one merged surface of overlapping ellipsoids.
        # Survey units are 80 m: mature crowns are 7–14 m, roofs below give scale.
        def crown(a,y,h,radius):
            centre=p(a,y,LAND_RADIUS-h)
            rt=radial(a);tn=tangent(a)
            for lobe in range(3):
                lc=centre+tn*rng.uniform(-.035,.035)+Y*rng.uniform(-.042,.042)-rt*rng.uniform(-.014,.018)
                radi=radius*(1 if lobe==0 else .72)
                spin=rng.random()*TAU
                rim=[lc+(tn*cos(spin+k*TAU/7)+Y*sin(spin+k*TAU/7))*radi*(.86+.14*rng.random()) for k in range(7)]
                upper=[lc+(v-lc)*.66-rt*radi*.52 for v in rim]
                lower=[lc+(v-lc)*.64+rt*radi*.44 for v in rim]
                top=lc-rt*radi*.71
                for k in range(7):
                    n=(k+1)%7
                    for poly in ((top,upper[k],upper[n]),(upper[k],rim[k],rim[n],upper[n]),(rim[k],lower[k],lower[n],rim[n])):
                        direction=sum(poly,lc*0)/len(poly)-lc
                        normals=[(q-lc).normalized() for q in poly]
                        drum.face(poly,'Timber',direction,normals=normals)
        for i in range(88):
            yy=rng.uniform(-18.9,18.8);side=-1 if i%2 else 1
            a=sector+river(yy)+side*rng.uniform(.064,.106)
            crown(a,yy,rng.uniform(.077,.13),rng.uniform(.059,.101))
        urban=-6.1+j*3.6
        # Occupied terraces and canopies share a riverbank, with a larger station
        # and market on the outer bank opposite the floodplain.
        a=sector+river(urban)+.161
        for k in range(3):
            yy=urban+(k-1)*.83
            drum.obox(a,yy,LAND_RADIUS-.089,.53,.72,.16,'Building')
            drum.obox(a,yy,LAND_RADIUS-.18,.47,.66,.035,'Roof')
            drum.obox(a+.009,yy+.031,LAND_RADIUS-.24,.29,.43,.11,'Greenhouse')
            for q in range(5):
                drum.obox(a-.032,yy+(q-2)*.116,LAND_RADIUS-.118,.013,.078,.045,'WindowBank')
        # Several related concrete arches form a transverse viaduct. Their piers
        # and walkways are real relief above water; all gravity points outward.
        for n in range(2):
            yy=urban+.95-n*2.47;aa=sector+river(yy);rad0=LAND_RADIUS-.16
            for i in range(9):
                lo=aa-.215+i*.047;hi=lo+.047
                drum.arc(lo,hi,yy-.035,yy+.035,rad0,'PaleStone',2,inside=True)
                for g in (-1,1):
                    drum.rod(p(lo,yy+g*.039,rad0-.021),p(hi,yy+g*.039,rad0-.021),.0043,'Structure',5)
                drum.rod(p(lo,yy,LAND_RADIUS-.007),p(lo,yy,rad0),.016,'PaleStone',7)
                for k in range(7):
                    v=k/7;w=(k+1)/7
                    r0=LAND_RADIUS-.025-.096*sin(v*pi)
                    r1=LAND_RADIUS-.025-.096*sin(w*pi)
                    drum.rod(p(lo+(hi-lo)*v,yy-.029,r0),p(lo+(hi-lo)*w,yy-.029,r1),.012,'PaleStone',6)
        # The river town's ferry-sized ribbed glass market ends at a stepped quay.
        marketA=sector+river(urban)-.136;start=urban-.73;end=urban+.27
        drum.obox(marketA,(start+end)/2,LAND_RADIUS-.035,.56,end-start+.09,.07,'PaleStone')
        for span in range(3):
            delta=(span-1)*.154
            for b in range(8):
                s=b*pi/8;t=(b+1)*pi/8
                a0=marketA+(delta+.078*cos(s))/LAND_RADIUS;a1=marketA+(delta+.078*cos(t))/LAND_RADIUS
                r0=LAND_RADIUS-.08-.084*sin(s);r1=LAND_RADIUS-.08-.084*sin(t)
                drum.face([p(a0,start,r0),p(a0,end,r0),p(a1,end,r1),p(a1,start,r1)],'Greenhouse',-radial(marketA))
                for yy in (start,start+.24,start+.49,start+.74,end):
                    drum.rod(p(a0,yy,r0-.003),p(a1,yy,r1-.003),.0037,'PaleStone',5)
        # Underlit shore on approach to the axial end wall.
        for i in range(39):
            yy=-19.6+i*1.02
            for side in (-1,1):
                a=sector+river(yy)+side*(.043+.004*sin(yy*.44))
                if i%3==0:
                    drum.rod(p(a,yy,LAND_RADIUS-.007),p(a,yy,LAND_RADIUS-.053),.004,'Frame',5)
                    drum.obox(a,yy,LAND_RADIUS-.054,.012,.023,.009,'LitWindow')
        # A lock gate and stair-stepped quays articulate the station's waterfront.
        for b in range(7):
            yy=urban-1.04+b*.27;a=sector+river(yy)+.062
            for level in range(3):
                drum.obox(a+.009*level,yy,LAND_RADIUS-.016-level*.011,.076,.259,.030,'PaleStone')
        # Double-ended land bands meet a single pressure bulkhead. Real service
        # tiers, lift shafts and windows let its scale read from the gallery.
        far=20.35
        for k in range(7):
            a=sector+(k-3)*.125;radius=6.99
            block=lambda rr,ww,hh,dd,mat:drum.obox(a,far-.03,rr,ww,dd,hh,mat)
            h=.41+.57*exp(-((k-3)/1.82)**2)
            block(radius-h*.5,.72,h,.42,'Building')
            for n in range(1,6):
                r=radius-h*n/6
                drum.obox(a,far-.246,r,.68,.014,.023,'WindowBank')
        for row,radius in enumerate((3.0,4.2,5.4,6.45)):
            for i in range(15):
                lo=sector-.964+i*.132;hi=lo+.118;rr=radius+.018*sin(i+j)
                # Far pressure face is only slightly recessed. Its ring concourses
                # face toward the axis; glazing and pale reveals face the gallery.
                for k0,k1,mat in ((rr,rr+.079,'PaleStone'),(rr+.081,rr+.194,'WindowBank'),(rr+.195,rr+.213,'Building')):
                    for end in (-1,1):
                        drum.face([p(lo,end*20.36,k0),p(hi,end*20.36,k0),p(hi,end*20.36,k1),p(lo,end*20.36,k1)],mat,-Y*end)
                if row%2==0 and i%3:
                    drum.rod(p(lo,20.32,rr+.061),p(hi,20.32,rr+.061),.009,'LitWindow',6)
        # The incoming local train serves the existing railway on land strip zero.
        if j==0:
            a=.18
            for y in (-11.4,7.3):
                drum.obox(a+.033,y,6.964,.33,1.64,.055,'PaleStone')
                for z in (-.65,0,.65):
                    drum.rod(p(a+.049,y+z,6.95),p(a+.049,y+z,6.73),.018,'Structure',8)
                drum.obox(a+.034,y,6.715,.35,1.51,.056,'Greenhouse')
                for g in (-.62,-.31,0,.31,.62):
                    drum.obox(a+.017,y+g,6.735,.04,.14,.012,'LitWindow')
    for k in range(4):
        yy=(k-1.5)*.37
        for s in (-1,1):
            for l in range(4):
                tram.obox(s*.011,yy+(l-1.5)*.066,7.091,.012,.050,.047,'WindowBank')
        for end in (-1,1):
            if (k==0 and end==-1) or (k==3 and end==1):
                for side in (-1,1):
                    tram.obox(side*.007,yy+end*.169,7.072,.026,.007,.024,'Navigation')


def terrain_texture(source_dir,filepath):
    import numpy as np
    from PIL import Image, ImageFilter
    # A meter-scale aerial ground texture kept in the UV coordinates of the
    # actual river mesh (latitudinal x, axial y). Each sample has recorded provenance.
    w,h=1024,3072
    def rgb(file):
        return Image.open(source_dir/(file+'.jpg')).convert('RGB')
    land=np.asarray(rgb('agriculture').resize((w,h),Image.Resampling.LANCZOS),dtype=np.float32)
    wood=np.asarray(rgb('riparian').crop((209,223,491,536)).resize((w//2,h//5),Image.Resampling.BICUBIC),dtype=np.float32)
    town=np.asarray(rgb('village').resize((w//2,h//5),Image.Resampling.LANCZOS),dtype=np.float32)
    yy,xx=np.mgrid[:h,:w]
    y=(.5-yy/(h-1))*40.80;a0=(xx/(w-1)-.5)*1.118
    a=.146*np.sin(y*.31+.26)+.055*np.sin(y*.72-.48)
    distance=a0-a
    def place(under,over,weight):
        weight=np.clip(weight,0,1)[...,None];return under*(1-weight)+over*weight
    shade=np.clip((land[:,:,1]-land[:,:,0]+9)/36,0,1)
    land*=np.stack([.88+.056*shade,.94+.065*shade,.82+.026*shade],axis=2)
    baseLuma=.24*wood[:,:,0]+.64*wood[:,:,1]+.12*wood[:,:,2]
    trees=np.stack([baseLuma*.70,baseLuma*.90,baseLuma*.70],axis=2)[yy%wood.shape[0],xx%wood.shape[1]]
    fringe=.04+.031*np.sin(y*.9)**2+.009*np.sin(y*1.6+xx*.008)
    land=place(land,trees,(fringe+.015-abs(distance))/.018)
    village=town[yy%town.shape[0],xx%town.shape[1]]*np.array([.96,.940,.859])
    for center,side in ((-6.1,1),(-2.5,-1),(1.1,1),(12.8,-1)):
        mask=1-((distance-.23*side)/.125)**4-((y-center)/1.56)**4
        land=place(land,village,mask*4)
    water=.021+.004*np.sin(y*.55)
    shallow=(np.clip((abs(distance)-water*.68)/(water*.32),0,1)*.40+.20*np.sin(y*.35)**2)[...,None]
    liquid=np.array([56.,109.,107.])*(1-shallow)+np.array([100.,139.,123.])*shallow
    land=place(land,liquid,(water+.005-abs(distance))/.006)
    # Gravel levee on the dry margin, eight metres wide, interrupted at the landing.
    levee=np.exp(-((distance-fringe-.009)/.008)**4)*.81
    gravel=np.stack((land[:,:,0]*.24+142,land[:,:,1]*.24+133,land[:,:,2]*.24+113),axis=2)
    land=place(land,gravel,levee)
    Image.fromarray(np.uint8(np.clip(land,0,255))).filter(ImageFilter.UnsharpMask(radius=.68,percent=65,threshold=3)).save(filepath,quality=91,subsampling=0,optimize=True)
