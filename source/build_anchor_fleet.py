"""Build the original Pelagic Anchor work fleet in Blender, in actual metres.

Run python harbor_finishes.py first, then blender -b -P build_anchor_fleet.py.
Local coordinates below are glTF X starboard, Y above water, minus Z forward.
The original reference arrangements are Damen's ASD 2312 and PSV 5000 sheets.
"""
from pathlib import Path
import json
import math
import random
import runpy
import sys
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'web/assets/harbor';NATIVE=ROOT/'unity/Assets/Upwell/Resources/Harbor';ART=ROOT/'blender/harbor'
for directory in (WEB,NATIVE,ART):directory.mkdir(parents=True,exist_ok=True)
atlas=json.loads((NATIVE/'fleet-atlas.json').read_text());specs=runpy.run_path(str(ROOT/'source/harbor_finishes.py'))['MATERIALS']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
v=Vector;X=v((1,0,0));Y=v((0,1,0));Z=v((0,0,1));T=math.tau;metadata={}
exec(compile((ROOT/'source/mesh_primitives.py').read_text(),str(ROOT/'source/mesh_primitives.py'),'exec'))

def lin(a):return a/12.92 if a<=.04045 else ((a+.055)/1.055)**2.4
def color(hex):return tuple(lin(int(hex[i:i+2],16)/255.) for i in (1,3,5))
def bl(p):return (p[0],-p[2],p[1])
def trim(p):return [round(float(k),5) for k in p]
def umat(s):return 'Harbor_'+s
materials={};images={}
for d in specs:
    name=d['name'];m=bpy.data.materials.new(name);materials[name]=m;m.use_nodes=True
    bs=m.node_tree.nodes['Principled BSDF'];rgb=color(d['color']);m.diffuse_color=(*rgb,d['alpha']);bs.inputs['Base Color'].default_value=(*rgb,1)
    bs.inputs['Metallic'].default_value=d['metal'];bs.inputs['Roughness'].default_value=d['rough'];bs.inputs['Alpha'].default_value=d['alpha']
    bs.inputs['Emission Color'].default_value=(*color(d['emit']),1);bs.inputs['Emission Strength'].default_value=d['gain']
    if name.endswith('Glass'):
        bs.inputs['Coat Weight'].default_value=.56;bs.inputs['Coat Roughness'].default_value=.14;m.surface_render_method='BLENDED'
    if name.endswith(('Rubber','CoatedPlate','Deck','Enamel','Rope')):bs.inputs['Specular IOR Level'].default_value=.30
    for key,target in [('image','Base Color'),('normal','Normal')]:
        tex=d.get(key)
        if not tex:continue
        if tex not in images:
            im=bpy.data.images.load(str(NATIVE/(tex+'.jpg')));images[tex]=im
            if key=='normal':im.colorspace_settings.name='Non-Color'
        node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=images[tex]
        if key=='normal':
            norm=m.node_tree.nodes.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=d['normalStrength'];m.node_tree.links.new(node.outputs['Color'],norm.inputs['Color']);out=norm.outputs['Normal']
        else:out=node.outputs['Color']
        m.node_tree.links.new(out,bs.inputs[target])

def uvrect(rect,u,w,paint=False):
    x,y,width,height=rect;aw,ah=atlas['paintSize' if paint else 'size'];return ((x+u*width)/aw,1-(y+(1-w)*height)/ah)
def quadmap(rect,paint=False):return [uvrect(rect,x,y,paint) for x,y in ((0,0),(1,0),(1,1),(0,1))]
def painted(points,shade,normal=None,uv=None,normals=None):
    points=[v(p) for p in points];rect=atlas['paint'][shade]
    if uv is None:
        if len(points)==4:uv=quadmap(rect,True)
        else:
            xs=[p.x for p in points];zs=[p.z for p in points]
            uv=[uvrect(rect,(p.x-min(xs))/max(.01,max(xs)-min(xs)),(p.z-min(zs))/max(.01,max(zs)-min(zs)),True) for p in points]
    face(points,umat('CoatedPlate'),normal,uv,normals=normals)
def railpipe(path,r,mat='Alloy',segments=7):tube(path,r,umat(mat),segments)
def beam(a,b,w,h,mat='Graphite',chamfer=.01):
    a,b=v(a),v(b);direction=(b-a).normalized();side=Y.cross(direction)
    if side.length<.01:side=X.copy()
    side.normalize();up=direction.cross(side).normalized();cube((a+b)*.5,(w,h,(b-a).length),umat(mat),chamfer,Matrix((side,up,direction)).transposed())
def mastrod(a,b,r,mat='Alloy',n=8,end=None):rod(a,b,r,umat(mat),n,r2=end)
def prism(points,y0,y1,shade='ivory',sx=1.,sz=1.,dx=0.,dz=0.,cap='CoatedPlate'):
    zc=sum(z for x,z in points)/len(points);xc=sum(x for x,z in points)/len(points)
    bottom=[v((x,y0,z)) for x,z in points];top=[v((xc+(x-xc)*sx+dx,y1,zc+(z-zc)*sz+dz)) for x,z in points]
    center=v((xc,(y1+y0)/2,zc));num=len(bottom)
    for i,a in enumerate(bottom):
        j=(i+1)%num;pts=[a,bottom[j],top[j],top[i]];n=(a+bottom[j])*.5-center;n.y=0;painted(pts,shade,n)
    if cap=='CoatedPlate':painted(top,shade,Y)
    else:face(top,umat(cap),Y)
    painted(bottom,shade,-Y)
    return top
def footprint(w,fwd,aft,chamfer=.5):
    return [(-w+chamfer,fwd),(w-chamfer,fwd),(w,fwd+chamfer),(w,aft-chamfer),(w-chamfer,aft),(-w+chamfer,aft),(-w,aft-chamfer),(-w,fwd+chamfer)]
def nameplate(c,n,w,h,key):
    c=v(c);r,u,n=basis(n);corners=[c+r*a*w*.5+u*b*h*.5 for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))]
    face(corners,umat('Mark'),n,quadmap(atlas['marks'][key]))
def roundbox(p,dim,mat='Graphite',b=.055):cube(p,dim,umat(mat),b)
def chain(a,b,width=.062):
    a,b=v(a),v(b);dr=b-a;count=max(2,int(dr.length/(width*1.65)))
    for j in range(count):
        point=a+dr*(j+.5)/count;radial=(X if j%2==0 else v((.5,0,.86)))
        torus(point,radial,width,width*.23,umat('Graphite'),9,5)
def rail(path,h=1.03,pitch=1.42,mat='Enamel',r=.037):
    points=[v(p) for p in path]
    for level,thick in ((h,r),(h*.5,r*.67)):railpipe([p+Y*level for p in points],thick,mat,7)
    distances=[0.]
    for a,b in zip(points,points[1:]):distances.append(distances[-1]+(b-a).length)
    total=distances[-1];steps=max(1,math.ceil(total/pitch));j=0
    for k in range(steps+1):
        d=k/steps*total
        while j<len(points)-2 and d>distances[j+1]:j+=1
        f=(d-distances[j])/max(.00001,distances[j+1]-distances[j]);p=points[j].lerp(points[j+1],f)
        mastrod(p,p+Y*(h+.01),r*.87,mat);roundbox(p+Y*.019,(.115,.038,.115),'Graphite',.006)
def ladder(base,n,height,width=.45):
    p=v(base);r,u,n=basis(n)
    for side in (-1,1):
        a=p+r*width*.5*side;railpipe([a-n*.14,a,a+u*height,a+u*(height+.27)-n*.13],.027)
    for k in range(max(2,int(height/.27))+1):
        x=p+u*(height*k/max(2,int(height/.27)));mastrod(x-r*width*.5,x+r*width*.5,.021)
def bollard(p,scale=1.):
    p=v(p);roundbox(p+Y*.04*scale,(.62*scale,.09*scale,.33*scale),'Graphite',.034*scale)
    for s in (-1,1):
        a=p+X*s*.17*scale; mastrod(a,a+Y*.27*scale,.078*scale,'Graphite',10);mastrod(a+Y*.26*scale,a+Y*.32*scale,.112*scale,'Alloy',10)
def worklight(p,aim):
    n=v(aim).normalized();p=v(p);plate(p,n,.23,.17,.13,umat('Graphite'),.032);plate(p+n*.071,n,.18,.115,.018,umat('Lens'),.013)
def navlight(p,mat):
    p=v(p);mastrod(p,p+Y*.048,.105,'Graphite',14);mastrod(p+Y*.045,p+Y*.205,.076,mat,14);mastrod(p+Y*.20,p+Y*.23,.091,'Graphite',14)
def ring_buoy(p,n,diam=.80):
    p=v(p);n=v(n);r,u,n=basis(n);R=diam*.40;rr=diam*.100
    for k in range(8):
        a=k*T/8;b=(k+1)*T/8
        for start,end,mat in ((a,b-.19,'Safety'),(b-.19,b,'Enamel')):
            torus(p,n,R,rr,umat(mat),max(4,int((end-start)*10)),7,span=(start,end))
    pts=[p+(r*math.cos(T*j/16)+u*math.sin(T*j/16))*(diam*(.514 if j%2 else .469)) for j in range(16)]
    tube(pts,.014,umat('Rope'),5,closed=True)
def raft(p,sz=1.):
    p=v(p);a=p-X*.60*sz;b=p+X*.60*sz;mastrod(a,b,.31*sz,'Enamel',18)
    for s in (-1,1):
        foot=p+X*s*.43*sz;torus(foot,X,.311*sz,.027*sz,umat('Graphite'),18,7);roundbox(foot-Y*.287*sz,(.13*sz,.12*sz,.56*sz),'Graphite',.03)
def window_band(poly,y0,y1,expansion,shade='ivory',pitch=1.02,spill=None):
    center=v((sum(x for x,z in poly)/len(poly),0,sum(z for x,z in poly)/len(poly)))
    bot=[v((x,y0,z)) for x,z in poly];top=[center+(p-center)*expansion for p in bot]
    for p in top:p.y=y1
    for i,a in enumerate(bot):
        j=(i+1)%len(bot);b=bot[j];ta,tb=top[i],top[j];normal=(b-a).cross(ta-a).normalized()
        if normal.dot((a+b)/2-center)<0:normal=-normal
        count=max(1,round((a-b).length/pitch))
        for k in range(count):
            def point(uu,vv):return a.lerp(b,uu).lerp(ta.lerp(tb,uu),vv)
            lo=k/count;hi=(k+1)/count;du=.055/max(.1,(a-b).length);margin=.057
            outer=[point(lo,0),point(hi,0),point(hi,1),point(lo,1)]
            inner=[point(lo+du,margin),point(hi-du,margin),point(hi-du,1-margin),point(lo+du,1-margin)]
            for t in range(4):painted([outer[t],outer[(t+1)%4],inner[(t+1)%4],inner[t]],shade,normal)
            pane=[p+normal*.005 for p in inner];face(pane,umat('Glass'),normal)
            if (k+i)%4==0 and abs(normal.z)>.7:
                railpipe([point(lo+du,.075)+normal*.020,point(lo+(hi-lo)*.47,.67)+normal*.020],.013,'Graphite',5)
    face(bot,umat('Deck'),Y);return top
def bridge_detail(x,z,y,w):
    # Actual consoles, helm seats and chart tables behind the bridge glazing.
    roundbox((x,y+.24,z-.56),(w,.45,.52),'Graphite',.08)
    for j in range(3):
        p=v((x+(j-1)*w*.24,y+.58,z-.62));plate(p,v((0,.68,1)),.50,.31,.065,umat('Graphite'),.025);plate(p+v((0,.023,.033)),v((0,.68,1)),.40,.215,.020,umat('Glass'),.015)
    for side in (-1,1):
        p=v((x+w*.25*side,y+.48,z+.15));mastrod(p-Y*.48,p,.058,'Alloy');roundbox(p,(.46,.13,.43),'Graphite',.065);roundbox(p+v((0,.18,.20)),(.44,.37,.12),'Rubber',.056)
def porthole(p,n,size=.17):
    p=v(p);n=v(n);mastrod(p-n*.009,p+n*.013,size,'Graphite',16);mastrod(p+n*.014,p+n*.029,size*.83,'Glass',16)
def door(p,n,w=.78,h=1.76):
    p=v(p);r,u,n=basis(n);rim(p,n,w,h,.105,w-.074,h-.080,.088,.034,umat('Graphite'));flat_round(p+n*.002,n,w-.078,h-.082,.085,umat('Enamel'))
    porthole(p+u*h*.19+n*.014,n,w*.178);railpipe([p+r*w*.25+n*.018,p+r*w*.25+n*.079,p+r*w*.05+n*.081],.022)
def vents(p,n,w,h):
    p=v(p);r,u,n=basis(n);plate(p,n,w,h,.029,umat('Graphite'),.026)
    for k in range(max(3,int(h/.115))):
        y=(k+.5)/max(3,int(h/.115))-.5;beam(p-r*w*.465+u*y*h+n*.019,p+r*w*.465+u*y*h+n*.019,.032,.045,'Alloy',.003)
def mast(p,h,spread=1.):
    p=v(p);mastrod(p,p+Y*h,.096*spread,'Graphite',12,end=.048*spread)
    for s in (-1,1):
        mastrod(p+X*s*.52*spread,p+Y*h*.68,.039*spread,'Alloy');mastrod(p+Y*.65*h,p+Y*.69*h+X*s*.94*spread,.040*spread,'Graphite')
    bar=p+Y*h*.73;roundbox(bar+Y*.12,(.30,.24,.26),'Enamel',.035);roundbox(bar+Y*.30,(1.72*spread,.11,.16),'Enamel',.026)
    navlight(p+Y*(h+.03),'Lens');mastrod(p+Y*h+X*.10,p+Y*(h+.70),.010,'Graphite',5,end=.005)
def anchor(p,side,scale=1.):
    p=v(p);n=X*side;torus(p+n*.04,n,.20*scale,.075*scale,umat('Graphite'),18,7)
    railpipe([p+n*.09,p+n*.20-Y*.33*scale,p+n*.16-Y*.68*scale],.064*scale,'Alloy')
    t=p+n*.16-Y*.68*scale
    for s in (-1,1):
        end=t+Z*s*.33*scale+Y*.20*scale;beam(t,end,.13*scale,.15*scale,'Graphite');beam(end,end+Y*.17*scale-Z*s*.020,.18*scale,.095*scale,'Alloy')

def cubic(z,knots,values):
    z=max(knots[0],min(knots[-1],z));i=next((j for j in range(len(knots)-1) if knots[j+1]>=z),len(knots)-2)
    span=knots[i+1]-knots[i];a=(z-knots[i])/span
    def slope(j):
        if j==0:return (values[1]-values[0])/(knots[1]-knots[0])
        if j==len(knots)-1:return (values[-1]-values[-2])/(knots[-1]-knots[-2])
        l=(values[j]-values[j-1])/(knots[j]-knots[j-1]);r=(values[j+1]-values[j])/(knots[j+1]-knots[j]);return 2*l*r/(l+r) if l*r>0 else 0.
    return values[i]*(2*a**3-3*a*a+1)+slope(i)*span*(a**3-2*a*a+a)+values[i+1]*(-2*a**3+3*a*a)+slope(i+1)*span*(a**3-a*a)

class Hull:
    """Station-lofted hull. Each point exists exactly on the shared waterline row."""
    def __init__(self,zs,widths,deck,keel,cl,x0=0.):
        self.zs=zs;self.widths=widths;self.decks=deck;self.keels=keel;self.cl=cl;self.x0=x0
    def deck(self,z):return cubic(z,self.zs,self.decks)
    def width(self,z):return cubic(z,self.zs,self.widths)
    def p(self,z,q,side):
        width=self.width(z);deck=self.deck(z);keel=cubic(z,self.zs,self.keels);y=deck*q if q>=0 else -keel*q
        radius=cubic(q,[-1,-.88,-.65,-.35,-.14,0,.2,.42,.70,.88,1],[.034,.376,.664,.844,.950,.977,1.004,1.013,1.006,.995,.981])
        # Inclined side shell above the waterline, progressively flared bow.
        t=(z-self.zs[0])/(self.zs[-1]-self.zs[0]);bow=max(0,1-t/.3)**2
        radius*=1-bow*.24*(1-max(0,q));return v((self.x0+side*width*radius,y,z))
    def normal(self,z,q,side):
        a=self.p(min(self.zs[-1],z+.024),q,side)-self.p(max(self.zs[0],z-.024),q,side)
        b=self.p(z,min(1,q+.005),side)-self.p(z,max(-1,q-.005),side)
        n=b.cross(a).normalized();return n if n.x*side>0 else -n
    def side(self,z,y,sign,extra=0):
        q=y/(self.deck(z) if y>=0 else -cubic(z,self.zs,self.keels));return self.p(z,q,sign)+X*sign*extra
    def top(self,z,sign):return self.p(z,1,sign)
    def build(self):
        length=self.zs[-1]-self.zs[0];n=max(26,math.ceil(length/.40));stations=[self.zs[0]+length*j/n for j in range(n+1)]
        qs=[-1,-.89,-.72,-.50,-.33,-.15,-.047,0,.036,.075,.18,.35,.54,.72,.82,.91,1.]
        for s in (-1,1):
            for i,z in enumerate(stations[:-1]):
                z1=stations[i+1]
                for k,q in enumerate(qs[:-1]):
                    q1=qs[k+1];coords=((z,q),(z1,q),(z1,q1),(z,q1));pts=[self.p(a,b,s) for a,b in coords]
                    color='antifoul' if q<-.047 else 'slime' if q<.036 else self.cl[0] if q<self.cl[2] else self.cl[1]
                    ix=i%5;uv=[uvrect(atlas['paint'][color],(ix+a)/5,b,True) for a,b in ((0,.13),(1,.13),(1,.86),(0,.86))]
                    ns=[self.normal(a,b,s) for a,b in coords];painted(pts,color,sum(ns,v((0,0,0))),uv,ns)
            # Cove line and rounded rail cap follow the changing freeboard.
            railpipe([self.p(z,.887,s)+X*s*.01 for z in stations],.027 if length>18 else .016,'Alloy',6)
        for i,z in enumerate(stations[:-1]):
            q=stations[i+1];pts=[self.top(z,-1),self.top(z,1),self.top(q,1),self.top(q,-1)]
            face(pts,umat('Deck'),Y,[(p.x*.59,p.z*.59) for p in pts]);painted([self.p(z,-1,-1),self.p(q,-1,-1),self.p(q,-1,1),self.p(z,-1,1)],'antifoul',-Y)
        for z,norm in ((stations[0],-Z),(stations[-1],Z)):
            for q,q1 in zip(qs,qs[1:]):
                color='antifoul' if q<-.047 else 'slime' if q<.036 else self.cl[0] if q<self.cl[2] else self.cl[1]
                painted([self.p(z,q,-1),self.p(z,q,1),self.p(z,q1,1),self.p(z,q1,-1)],color,norm)

def tyre(p,n,R,r):
    # Rounded, flattened-sidewall tyre with a through hub, moulding ribs and
    # selected shoulder tread. Vary the actual suspending position by vessel station.
    p=v(p);a,b,n=basis(n);segments=26
    profile=[(.44,-.50),(.65,-.71),(.90,-.72),(.97,-.51),(1,-.31),(1,.28),(.96,.52),(.89,.68),(.73,.71),(.48,.47)]
    for j,(rr,ss) in enumerate(profile):
        rr1,ss1=profile[(j+1)%len(profile)]
        for k in range(segments):
            corners=[];ns=[]
            for q,sr,ax in ((k,rr,ss),(k+1,rr,ss),(k+1,rr1,ss1),(k,rr1,ss1)):
                radial=a*math.cos(T*q/segments)+b*math.sin(T*q/segments);corners.append(p+radial*R*sr+n*r*ax)
                direction=(radial*((sr-.70)/.32)+n*(ax/.65)).normalized();ns.append(direction)
            face(corners,umat('DampRubber' if j in (2,4) else 'Rubber'),sum(ns,v((0,0,0))),normals=ns)
    for rr in (.72,.85):torus(p+n*r*.715,n,R*rr,.010 if R>.4 else .006,umat('DampRubber'),26,6)
    for k in range(segments):
        ra=a*math.cos(T*k/segments)+b*math.sin(T*k/segments);rb=a*math.cos(T*(k+.43)/segments)+b*math.sin(T*(k+.43)/segments)
        mastrod(p+ra*R*.962+n*r*.54,p+rb*R+n*r*.20,.015 if R>.43 else .011,'DampRubber',5)

def curved_mark(hull,zc,y,w,h,side,key):
    rect=atlas['marks'][key]
    for k in range(14):
        uv=((k/14,0),((k+1)/14,0),((k+1)/14,1),(k/14,1));pts=[]
        for u,vv in uv:pts.append(hull.side(zc+(u-.5)*w*(-side),y+(vv-.5)*h,side,.012))
        face(pts,umat('Mark'),X*side,[uvrect(rect,u,vv) for u,vv in uv])
def towing_drum(c,width,rad):
    c=v(c);width=float(width);rad=float(rad)
    for s in (-1,1):
        base=c+X*s*(width*.51+.12);pr=[(-.35,-.77),(.31,-.77),(.27,.18),(0,.31),(-.19,.25)]
        pts=[base+Z*z*rad+Y*y*rad for z,y in pr];other=[i+X*s*.14 for i in pts]
        painted(pts,'ochre',-X*s);painted(other,'ochre',X*s)
        for i in range(len(pts)):painted([pts[i],pts[(i+1)%len(pts)],other[(i+1)%len(pts)],other[i]],'ochre')
        wall=c+X*s*(width*.5);mastrod(wall-X*.048,wall+X*.048,rad,'Ochre',28)
        torus(wall+X*s*.049,X,rad*.87,.033,umat('Graphite'),26,6)
    mastrod(c-X*width*.5,c+X*width*.5,rad*.68,'Rope',24)
    winding=[];turns=max(9,int(width/.085));steps=turns*16
    for j in range(steps+1):
        f=j/steps;a=T*turns*f;winding.append(c+X*width*(f-.5)+(Y*math.sin(a)+Z*math.cos(a))*rad*.683)
    railpipe(winding,min(.038,width/(turns*2.3)),'Rope',5)
    for s in (-1,1):mastrod(c+X*s*(width*.54),c+X*s*(width*.56+.19),rad*.30,'Alloy',14)
def propulsor(x,y,z,scale):
    c=v((x,y,z));n=Z;R=scale*.63
    mastrod(c+Y*.1,c+Y*1.04*scale,.18*scale,'Graphite',12,end=.34*scale)
    torus(c,n,R,.085*scale,umat('Graphite'),24,8);torus(c+Z*.22*scale,n,R*.94,.069*scale,umat('Alloy'),24,7)
    mastrod(c-Z*.28*scale,c+Z*.50*scale,.13*scale,'Alloy',12,end=.095*scale)
    for j in range(4):
        a=T*j/4;ray=X*math.cos(a)+Y*math.sin(a);across=-X*math.sin(a)+Y*math.cos(a)
        painted([c+ray*R*.10,c+ray*R*.56+across*R*.29+Z*.07,c+ray*R*.88+across*R*.16+Z*.15,c+ray*R*.81-across*R*.25+Z*.10,c+ray*R*.30-across*R*.19],'ochre',n)

def tug():
    hull=Hull([-12.3,-11.6,-10.3,-8.5,-5.6,-2,2,5.6,8.4,10.4,11.6,12.3],
        [.08,1.54,2.93,3.76,4.31,4.43,4.44,4.31,4.01,3.38,2.46,1.38],
        [2.47,2.41,2.32,2.17,1.98,1.87,1.83,1.78,1.79,1.82,1.84,1.85],
        [-.19,-1.08,-1.85,-2.56,-2.85,-3.,-2.89,-2.55,-1.98,-1.37,-.87,-.61],('navy','tug-red',.54));hull.build()
    # Continuous heavy braided bow fenders follow both contours; separate
    # compression blocks and through-chain tyres carry side work against the quay.
    for side in (-1,1):
        path=[hull.p(-12.3+i*(4.35/17),.795,side)+X*side*.096 for i in range(18)]
        railpipe(path,.23,'Rubber',12);railpipe([p+Y*.34-X*side*.04 for p in path],.157,'DampRubber',10)
        for k,z in enumerate((-7.25,-5.31,-3.22,-1.14,1.05,3.19,5.26,7.22,9.14)):
            rad=(.50,.54,.47,.52)[k%4];p=hull.side(z,.98+(k%3)*.06,side,.116);direction=(X*side+Z*(.10*math.sin(k))).normalized()
            tyre(p,direction,rad,.43)
            for s in (-1,1):
                a=p+Y*rad*.56+Z*s*rad*.43+direction*.23;upper=hull.top(z+s*rad*.49,side)+Y*.22-X*side*.10
                chain(a,upper,.066);torus(upper,Y,.073,.022,umat('Alloy'),12,5)
        # Deep scupper slots are above the fender line in the coaming, with a
        # full cap rail and reinforced webs, rather than an uninterrupted wall.
        for fwd,aft in ((-11.7,-6.1),(5.25,11.82)):
            count=math.ceil((aft-fwd)/.55);pts=[hull.top(fwd+(aft-fwd)*i/count,side) for i in range(count+1)]
            for i,(a,b) in enumerate(zip(pts,pts[1:])):
                low=.29 if i%5 in (1,2) else .014;painted([a+Y*low,b+Y*low,b+Y*.72,a+Y*.72],'tug-red',X*side)
                if i%2==0:beam(a-X*side*.11,a+Y*.66,.085,.09,'Graphite')
            railpipe([p+Y*.73 for p in pts],.055,'Rubber',8)
        rail([hull.top(z,side)-X*side*.14 for z in (-6,-4,-2,0,2,4,5.26)],.88,1.83,'Graphite')
        p=hull.side(-5.12,.77,side,.034);nameplate(p,X*side,2.13,.63,'tug')
        anchor(hull.side(-8.7,1.41,side,.025),side,.83)
        for z in (-8.4,7.7,9.73):bollard(hull.top(z,side)-X*side*.65,.94)
    # Skeletal curved main deckhouse and cantilevered 360-degree pilot house.
    lower=footprint(2.58,-5.61,1.44,.74);prism(lower,1.86,3.86,'ivory',.952,.986)
    prism(footprint(2.97,-5.84,1.63,.78),3.82,4.0,'ivory',cap='Deck')
    superstructure=footprint(2.10,-5.11,.60,.69);prism(superstructure,4.00,4.59,'ivory')
    bridge_detail(0,-2.46,4.43,3.11)
    for s in (-1,1):
        for z in (-4.39,-3.24,-2.09):porthole((s*2.51,3.09,z),X*s,.228)
        door((s*2.52,2.97,-.76),X*s,.69,1.61);ring_buoy((s*2.525,3.02,.39),X*s,.77)
        rail([(s*2.67,3.99,-4.70),(s*2.84,3.99,-3.46),(s*2.84,3.99,.78),(s*2.18,3.99,1.48)],.90,1.42)
        ladder((s*2.82,2.04,1.06),X*s,1.96,.39)
        navlight((s*2.78,6.42,-2.17),'Starboard' if s>0 else 'Port')
    # Forward-access watertight door, separately mounted name boards and
    # louvred intake make the house legible from an approaching vessel.
    door((.99,2.9,-5.63),-Z,.77,1.68);vents((-1.10,2.96,-5.64),-Z,.87,.67)
    nameplate((-.27,3.58,-5.639),-Z,1.42,.31,'tughouse')
    for s in (-1,1):
        for z in (-5.05,-3.83,-2.60,-1.39,.29):
            if z>-.3:continue
            a=v((s*2.55,2.19,z));beam(a,a+Y*.56,.036,.026,'Enamel',.004)
    # Twin warping heads with enclosed gearbox and spurling pipes.
    center=v((0,hull.deck(-8.29),-8.29));roundbox(center+Y*.17,(1.56,.34,.95),'Graphite',.09)
    gear=center+Y*.56+Z*.11;roundbox(gear,(.55,.55,.62),'Ochre',.11)
    mastrod(gear-X*.83,gear+X*.83,.083,'Alloy',14)
    for s in (-1,1):
        p=gear+X*s*.61;mastrod(p-X*.15,p+X*.15,.272,'Graphite',18)
        for side in (-1,1):torus(p+X*side*.15,X,.276,.035,umat('Alloy'),16,6)
        hawse=center+v((s*.91,.075,-1.22));torus(hawse,Y,.16,.046,umat('Graphite'),14,6)
        railpipe([p-Y*.06-Z*.22,p-Y*.31-Z*.53,hawse+Y*.027],.043,'Graphite',8)
    for s in (-1,1):
        for zz in (-7.12,-9.43):
            p=v((s*1.64,hull.deck(zz)+.024,zz));roundbox(p,(.65,.054,.72),'Alloy',.055)
            railpipe([p+X*.14+Y*.03,p+X*.14+Y*.09,p-X*.14+Y*.09,p-X*.14+Y*.03],.018,'Graphite',6)
    window_poly=footprint(2.27,-5.37,.70,.74);window_band(window_poly,4.58,6.06,1.083,'ivory',1.03)
    prism(footprint(2.50,-5.74,1.07,.82),6.055,6.22,'ivory');prism(footprint(2.55,-5.79,1.12,.845),6.205,6.305,'tug-red')
    # Two distinct exhaust uptakes with actual open pipes inside a cowling.
    for s in (-1,1):
        footprint0=[(s*x+.0,z) for x,z in ((1.41,.90),(2.11,.92),(2.22,1.31),(2.04,2.13),(1.42,1.96))]
        prism(footprint0,2.0,5.84,'tug-red',.90,.87,dz=.25);prism([(x,z+.21) for x,z in footprint0],5.76,6.20,'black',.85,.86)
        for k in range(2):
            a=v((s*(1.65+.29*k),6.12,1.82+.09*k));mastrod(a,a+v((0,.43,.13)),.147,'Graphite',16);torus(a+v((0,.43,.13)),v((0,.98,.1)),.128,.026,umat('Alloy'),18,7)
        vents((s*2.16,4.86,1.55),X*s,.61,.69);worklight((s*2.22,6.02,.80),(s*.30,-.52,1))
    crown=v((0,6.315,-1.78));mast(crown,2.75,1.18);raft((0,6.66,-4.09),1.04)
    for s in (-1,1):mastrod((s*.86,6.30,-2.36),(s*.28,8.28,-1.73),.046,'Alloy')
    nameplate((0,6.138,-5.782),-Z,1.06,.32,'tugcall')
    gear=v((0,2.55,6.00));towing_drum(gear,2.28,.77)
    for z in (3.14,8.50):
        for s in (-1,1):mastrod((s*.56,1.85,z),(s*.56,2.53,z),.136,'Graphite',14);mastrod((s*.56,2.49,z),(s*.56,2.63,z),.18,'Alloy',14)
    # Rounded stern fairlead, sheaves and a loose tail passing round the H-bitts.
    for s in (-1,1):
        beam((s*1.08,1.80,9.23),(s*.71,2.42,9.51),.21,.24,'Graphite');mastrod((s*.72,1.89,9.48),(s*.72,2.61,9.48),.16,'Alloy',14)
    mastrod((-.81,2.55,9.48),(.81,2.55,9.48),.136,'Graphite',16)
    railpipe([(0,2.22,6.52),(.12,2.07,7.23),(.22,1.95,8.18),(.25,2.11,8.80),(.1,2.14,9.55)],.065,'Rope',8)
    for s in (-1,1):propulsor(s*1.85,-2.70,7.09,1.23)
    cleats={key:trim(hull.top(z,-1)+X*.65+Y*.17) for key,z in (('port_forward',-8.40),('port_aft',9.73))}
    return dict(name='Nereid',role='Azimuth harbour tug',length=24.6,beam=9.1,draft=3.55,wakes=[[-2.10,0,11.06],[2.10,0,11.06]],receiver=[0,2.13,9.56],cleats=cleats)

def cargo_case(p,w,h,l,shade):
    p=v(p);x,y,z=p;corners=[(x-w/2,z-l/2),(x+w/2,z-l/2),(x+w/2,z+l/2),(x-w/2,z+l/2)]
    prism(corners,y,y+h,shade)
    # Rolled corrugations, tubular corner posts and the full-height door dogs
    # distinguish a lashed ISO cargo unit from an unmodified rectangular box.
    for s in (-1,1):
        for j in range(max(4,round(l/.34))):
            zz=z-l*.48+(j+.5)*(l*.96)/max(4,round(l/.34));top=y+h-.09;bottom=y+.09;xx=x+s*w/2
            a=v((xx,bottom,zz-.099));b=v((xx+s*.052,bottom,zz-.058));c=v((xx+s*.052,bottom,zz+.061));d=v((xx,bottom,zz+.099));dy=Y*(top-bottom)
            for p0,p1 in ((a,b),(b,c),(c,d)):painted([p0,p1,p1+dy,p0+dy],shade,X*s)
        for side in (-1,1):
            zz=z+side*(l*.5-.055);beam((x+s*(w*.5-.054),y+.04,zz),(x+s*(w*.5-.054),y+h-.04,zz),.126,.135,'Graphite')
        for yy in (y+.05,y+h-.05):beam((x+s*w*.5,yy,z-l*.5),(x+s*w*.5,yy,z+l*.5),.086,.095,'Graphite')
    for k in (-.36,-.12,.12,.36):
        a=v((x+w*k,y+.12,z+l*.5+.045));mastrod(a,a+Y*(h-.24),.033,'Alloy');railpipe([a+Y*h*.32,a+Y*h*.32+X*.14],.025,'Graphite')
    nameplate((x+w*.5+.062,y+h*.73,z+l*.25),X,1.09,.45,'cargo')

def crane(p):
    p=v(p);mastrod(p,p+Y*.39,.66,'Graphite',24);mastrod(p+Y*.29,p+Y*1.49,.48,'Ochre',24);torus(p+Y*1.34,Y,.49,.08,umat('Alloy'),24,7)
    foot=p+Y*1.48;elbow=p+v((-.22,4.40,2.81));tip=p+v((-.65,2.94,6.65));end=p+v((-.69,2.83,6.99));end2=end-Y*1.28
    def link(a,b,rootw,endw):
        delta=b-a;vec=delta.normalized();side=X;up=side.cross(vec).normalized()
        def section(q,w,depth):return [q+side*w*.5*s+up*depth*.5*t for s,t in ((-1,1),(1,1),(1,-1),(-1,-1))]
        one=section(a,rootw,rootw*1.23);two=section(b,endw,endw*1.17)
        for i in range(4):painted([one[i],one[(i+1)%4],two[(i+1)%4],two[i]],'ochre',(one[i]+one[(i+1)%4])*.5-a)
        for joint in (a,b):mastrod(joint-X*rootw*.57,joint+X*rootw*.57,rootw*.34,'Alloy',16)
    link(foot,elbow,.67,.45);link(elbow,tip,.49,.28);link(tip,end,.29,.19)
    a=foot+Y*.10+Z*.35;b=foot.lerp(elbow,.68)+Z*.29
    mastrod(a,a.lerp(b,.62),.123,'Graphite',12);mastrod(a.lerp(b,.59),b,.068,'Alloy',12)
    a=elbow-Z*.47-Y*.15;b=elbow.lerp(tip,.73)-Y*.44
    mastrod(a,a.lerp(b,.55),.102,'Graphite',12);mastrod(a.lerp(b,.55),b,.066,'Alloy',12)
    for side in (-1,1):
        railpipe([foot+X*side*.39,elbow+X*side*.28+Y*.24,tip+X*side*.17+Y*.13,end+X*side*.12],.034,'Rubber',6)
        mastrod(end+X*side*.065,end2+X*side*.065,.014,'Graphite',6)
    roundbox(end2,(.27,.26,.22),'Ochre',.055);torus(end2-Y*.18,X,.13,.034,umat('Alloy'),20,6,span=(-.55,4.40))

def supply():
    hull=Hull([-21.75,-20.8,-19.3,-16.7,-12.4,-7.1,-1.4,6.9,14.5,19.3,21,21.75],
        [.055,1.06,2.45,3.78,4.76,5.14,5.21,5.17,5.08,4.89,4.58,4.01],
        [5.36,5.28,5.06,4.67,4.18,3.55,2.61,2.27,2.25,2.28,2.29,2.29],
        [-.44,-1.46,-2.07,-2.71,-3.22,-3.36,-3.29,-3.05,-2.48,-1.53,-1.05,-.83],('psv-blue','navy',.82));hull.build()
    # Raised forecastle and accommodation stepped with the hull's sheer.
    for side in (-1,1):
        zs=(-21.29,-20.3,-18.8,-16.8,-14.5,-12.05,-10.25);pts=[hull.top(z,side) for z in zs]
        for i,(a,b) in enumerate(zip(pts,pts[1:])):
            painted([a,b,b+Y*.59,a+Y*.59],'psv-blue',X*side)
            if i>1:beam(b-X*side*.28,b+Y*.53,.085,.09,'Graphite')
        railpipe([p+Y*.59 for p in pts],.068,'Alloy');anchor(hull.side(-16.5,2.72,side,.036),side,1.06)
        curved_mark(hull,-10.70,2.37,2.75,.88,side,'supply')
        for h in (.25,.51,.75,1.01,1.25):
            loc=hull.side(-14.1,h,side,.025);mastrod(loc-Z*.092,loc+Z*.092,.013,'Enamel',5)
        for z in (-16.2,-13.7,-1.5,10.4,18.1):bollard(hull.top(z,side)-X*side*.58,1.02)
    body=footprint(3.89,-15.08,-2.8,1.0);prism(body,3.02,5.52,'ivory',.976,.98)
    prism(footprint(4.16,-15.46,-2.53,1.09),5.50,5.73,'ivory',cap='Deck')
    accom=footprint(3.54,-14.3,-3.53,.83);prism(accom,5.71,7.33,'ivory',.978,.98)
    prism(footprint(4.04,-14.68,-3.10,.94),7.30,7.53,'ivory',cap='Deck')
    bridge=footprint(3.67,-14.05,-5.30,1.22);prism(bridge,7.50,7.76,'ivory')
    bridge_detail(0,-11.30,7.55,5.29);window_band(bridge,7.75,9.17,1.07,'ivory',1.14)
    prism(footprint(4.10,-14.57,-4.91,1.25),9.15,9.36,'ivory');prism(footprint(4.15,-14.63,-4.86,1.27),9.355,9.45,'navy')
    for s in (-1,1):
        for z in (-12.7,-11.0,-9.3,-7.6,-5.9):
            plate((s*3.52,6.50,z),X*s,.79,.64,.036,umat('Graphite'),.075);plate((s*3.548,6.50,z),X*s,.69,.53,.026,umat('Glass'),.056)
            porthole((s*3.86,4.51,z),X*s,.217)
        rail([(s*3.78,5.74,-14.81),(s*4.02,5.74,-13.73),(s*4.02,5.74,-3.48),(s*3.27,5.74,-2.72)],.91,1.64)
        rail([(s*3.69,7.52,-13.98),(s*3.93,7.52,-13.44),(s*3.93,7.52,-4.14),(s*3.54,7.52,-3.30)],.91,1.60)
        door((s*3.80,4.39,-4.08),X*s,.73,1.68);ladder((s*3.98,3.12,-3.78),X*s,2.49)
        ring_buoy((s*3.57,6.36,-4.49),X*s,.76);navlight((s*3.91,9.44,-10.14),'Starboard' if s>0 else 'Port')
        raft((s*2.72,5.99,-3.37),1.10);worklight((s*3.74,7.30,-3.20),(s*.16,-.45,1))
        # Dense external water/air/transfer stations along the edge of the open well deck.
        pts=[hull.top(z,s)-X*s*.10 for z in (-2.48,.4,3.9,8.4,12.9,17.5,20.54)]
        rail(pts,1.06,1.88,'Alloy')
        for k,z in enumerate((1.5,4.25,6.85,9.61,12.33,15.05,17.76)):
            p=hull.top(z,s)-X*s*.27;roundbox(p+Y*.28,(.23,.56,.50),'Graphite',.035)
            railpipe([p-X*s*.075+Y*.49,p-X*s*.27+Y*.49,p-X*s*.36+Y*.39],.051,'Ochre' if k%3==0 else 'Alloy')
    # Enclosed funnel louvres, exhaust liners, satcom and radio aerials.
    for s in (-1,1):
        pod=[(s*x,z) for x,z in ((1.97,-3.86),(2.95,-3.83),(3.21,-3.35),(2.95,-2.12),(1.97,-2.33))]
        prism(pod,5.38,8.54,'cyan',.86,.91,dz=.25);prism([(x,z+.19) for x,z in pod],8.45,8.86,'black',.84,.89)
        vents((s*2.99,7.32,-3.11),X*s,1.04,.88)
        for k in (-1,1):mastrod((s*(2.49+.22*k),8.72,-2.99),(s*(2.49+.22*k),9.36,-2.83),.224,'Graphite',20)
    mast((0,9.44,-7.83),3.88,1.26);p=v((-2.03,9.45,-11.34));mastrod(p,p+Y*.43,.25,'Alloy',14)
    sphere(p+Y*.73,.43,'Enamel');nameplate((0,7.66,-14.08),-Z,1.7,.40,'supply')
    # The stern is a cargo deck with a timber impact bed, transverse sea
    # fastenings, separately lashed ISO case and a manifold skid.
    for j in range(24):
        x=-3.84+j*.334;z0=.13;z1=19.56
        for k in range(5):
            za=z0+(z1-z0)*k/5+(.013 if k>0 else 0);zb=z0+(z1-z0)*(k+1)/5-.013
            shade='timber'+str((j*7+k*3)%4)
            pts=[v((xx,hull.deck(zz)+.029,zz)) for xx,zz in ((x-.154,za),(x+.154,za),(x+.154,zb),(x-.154,zb))]
            # Long deck planks are pressure-treated timber stained by service;
            # their neutral muted surface contrasts with the protective side walkway.
            painted(pts,shade,Y)
    for j in (-1,1):
        for z in (.82,4.12,6.86,10.36,13.54,16.42,19.02):
            p=v((j*3.28,hull.deck(z)+.063,z));roundbox(p,(.20,.042,.28),'Graphite',.012);torus(p+Y*.036,Z,.064,.018,umat('Alloy'),11,5,span=(0,math.pi))
    cargo_case((1.92,hull.deck(6.96)+.05,6.96),2.18,2.28,5.51,'cyan')
    for x in (-2.95,-1.92):
        for z in (11.88,13.92,15.83):
            y=hull.deck(z)+.40;roundbox((x,y-.19,z),(.87,.29,.21),'Graphite',.04)
        p=v((x,2.93,13.79));mastrod(p-Z*2.46,p+Z*2.46,.365,'Alloy',17)
        for z in (-2.28,-.92,.95,2.28):torus(p+Z*z,Z,.377,.042,umat('Ochre'),16,6)
    crane((-2.58,hull.deck(.34)+.08,.34));towing_drum((.25,3.14,-1.39),1.75,.59)
    nameplate((.00,1.49,21.764),Z,2.25,.58,'transom');door((1.42,4.17,-2.75),Z,.78,1.71);vents((-1.49,4.65,-2.75),Z,1.33,.75)
    for s in (-1,1):porthole((s*2.62,5.04,-2.79),Z,.16)
    for s in (-1,1):
        for z in (12.52,14.99):
            outboard=-3.72 if s<0 else -.55
            a=v((outboard,2.34,z));b=v((-2.43+s*.39,3.17,z));mastrod(a,b,.024,'Rope',6)
    for side in (-1,1):propulsor(side*2.88,-2.66,15.74,.98)
    return dict(name='Ceiba',role='Offshore supply vessel',length=43.5,beam=10.6,draft=3.45,wakes=[[-2.88,0,20.15],[2.88,0,20.15]],receiver=[0,2.38,20.9])

def sphere(c,rad,mat):
    c=v(c);nr=8;ns=16
    for j in range(nr):
        for k in range(ns):
            values=[]
            for jj,kk in ((j,k),(j,k+1),(j+1,k+1),(j+1,k)):
                a=-math.pi/2+math.pi*jj/nr;b=T*kk/ns;dir=v((math.cos(a)*math.cos(b),math.sin(a),math.cos(a)*math.sin(b)))
                if not values or (dir-values[-1]).length>.000001:values.append(dir)
            if len(values)>2:
                if (values[0]-values[-1]).length<.000001:values.pop()
                if len(values)>2:face([c+p*rad for p in values],umat(mat),sum(values,v((0,0,0))),normals=values)

def pilot():
    zs=[-5.95,-5.56,-4.85,-3.64,-1.6,.76,3.09,4.72,5.48,5.95]
    hulls=[]
    for s in (-1,1):
        hull=Hull(zs,[.037,.20,.39,.55,.64,.66,.65,.62,.55,.44],
            [1.55,1.49,1.35,1.22,1.13,1.09,1.09,1.085,1.10,1.10],[-.24,-.42,-.64,-.86,-.96,-.99,-.89,-.74,-.58,-.38],('navy','grey',.72),s*1.493);hull.build();hulls.append(hull)
        for outer in (-1,1):
            path=[hull.p(-5.91+11.72*i/35,.78,outer)+X*outer*.041 for i in range(36)];railpipe(path,.102,'Rubber',10)
        for z in (-3.68,-.83,3.21):
            p=hull.top(z,s)+X*s*.043-Y*.152;tyre(p,X*s,.213,.16)
        for z in (-3.7,4.19):bollard(hull.top(z,s)-X*s*.095,.60)
        nameplate(hull.side(.77,.55,s,.018),X*s,1.07,.36,'pilothull')
    # Arched wave-piercing tunnel and a real foredeck above two slender hulls.
    for k in range(16):
        za=-4.34+10.06*k/16;zb=-4.34+10.06*(k+1)/16
        for j in range(12):
            a=-.98+j*1.96/12;b=-.98+(j+1)*1.96/12
            roof=lambda x,z:.65+.20*(1-(x/.98)**2)+.045*max(0,(-z-2)/2)
            coords=[(a,za),(b,za),(b,zb),(a,zb)];painted([(x,roof(x,z),z) for x,z in coords],'ivory',-Y)
        for z in ([za] if k in (0,4,9) else []):beam((-1.71,.79,z),(1.71,.79,z),.14,.17,'Alloy')
    prism(footprint(1.84,-4.61,5.61,.46),.956,1.125,'navy',cap='Deck')
    lower=footprint(1.514,-3.45,2.20,.48);prism(lower,1.114,1.73,'orange',.91,.94)
    wind=footprint(1.38,-3.31,2.12,.44);bridge_detail(0,-1.65,1.39,1.83);window_band(wind,1.73,2.81,.90,'orange',.87)
    prism(footprint(1.40,-3.19,2.04,.47),2.81,2.93,'ivory');prism(footprint(1.44,-3.22,2.11,.48),2.928,3.015,'orange')
    for s in (-1,1):
        nameplate((s*1.489,1.438,-.36),X*s,1.06,.37,'pilot');ring_buoy((s*1.46,1.69,1.44),X*s,.55)
        rail([(s*1.80,1.12,-.32),(s*1.78,1.12,-2.28),(s*1.68,1.20,-3.91),(s*1.48,1.26,-4.66)],.65,1.06,'Alloy',.024)
        rail([(s*1.82,1.12,2.53),(s*1.84,1.12,4.47),(s*1.64,1.12,5.37)],.68,1.00,'Alloy',.024)
        mastrod((s*1.44,3.01,-.52),(s*1.44,3.08,-.52),.08,'Graphite');navlight((s*1.34,3.04,-.23),'Starboard' if s>0 else 'Port')
        worklight((s*1.19,2.89,-2.79),(s*.23,-.20,-1))
        c=v((s*1.48,.11,5.68));mastrod(c-Z*.42,c+Z*.34,.17,'Graphite',14);torus(c+Z*.35,Z,.143,.038,umat('Alloy'),13,6)
    rail([(-1.62,1.12,5.40),(-.67,1.12,5.54)],.66,1.04,'Alloy',.023)
    raft((0,3.26,.73),.63);mast((0,3.016,-.93),1.10,.51);door((0,1.81,2.19),Z,.62,1.24)
    roundbox((0,1.30,3.56),(1.22,.35,1.13),'Enamel',.13);roundbox((0,1.51,3.56),(1.27,.085,1.17),'Graphite',.063)
    return dict(name='Pilot 12',role='Twin-hull pilot launch',length=11.9,beam=4.4,draft=1.0,wakes=[[-1.49,0,5.68],[1.49,0,5.68]],receiver=[0,1.12,5.35])

def buoy():
    # Starboard-hand green conical mark. Ballast skirt and mooring shackle
    # make the same source usable at the water surface or in an overhead pass.
    profile=[(-2.04,.16,'black'),(-1.85,.30,'black'),(-1.57,.23,'black'),(-.87,.25,'antifoul'),(-.64,.56,'antifoul'),(-.38,.91,'antifoul'),
             (-.08,1.00,'slime'),(.07,1.036,'green'),(.37,1.006,'green'),(.51,.94,'green'),(.63,.81,'green'),(.70,.45,'green')]
    count=36
    for i,((y,rr,cl),(y1,rr1,_)) in enumerate(zip(profile,profile[1:])):
        for j in range(count):
            data=[(y,rr,j),(y,rr,j+1),(y1,rr1,j+1),(y1,rr1,j)];ns=[v((math.cos(T*k/count),(rr-rr1)/max(.001,y1-y),math.sin(T*k/count))).normalized() for _,_,k in data]
            painted([v((radius*math.cos(T*k/count),h,radius*math.sin(T*k/count))) for h,radius,k in data],cl,ns[0],normals=ns)
    mastrod((0,.62,0),(0,.72,0),.818,'Graphite',32);torus((0,.23,0),Y,1.028,.048,umat('Rubber'),36,7)
    mastrod((0,.71,0),(0,2.46,0),.22,'Graphite',16,end=.16)
    feet=[];tops=[]
    for i in range(3):
        a=T*i/3+.28;feet.append(v((.65*math.cos(a),.71,.65*math.sin(a))));tops.append(v((.23*math.cos(a),2.57,.23*math.sin(a))))
    for i,p in enumerate(feet):
        mastrod(p,tops[i],.052,'Alloy',8);mastrod(p.lerp(tops[i],.37),feet[(i+1)%3].lerp(tops[(i+1)%3],.72),.023,'Alloy',7)
    for z in (-1,1):nameplate((0,1.88,.218*z),Z*z,.38,.29,'buoy')
    ladder((.40,.67,-.14),X,1.36,.23)
    mastrod((0,2.5,0),(0,2.60,0),.32,'Graphite',16);mastrod((0,2.6,0),(0,2.96,0),.136,'Starboard',15);mastrod((0,2.96,0),(0,3.02,0),.182,'Graphite',15)
    mastrod((0,3.0,0),(0,3.71,0),.031,'Alloy');cone=[v((.35*math.cos(T*i/24),3.22,.35*math.sin(T*i/24))) for i in range(24)]
    for i,a in enumerate(cone):painted([a,cone[(i+1)%24],v((0,3.89,0))],'green',v((a.x,.3,a.z)))
    torus((0,-2.01,0),Z,.11,.034,umat('Alloy'),14,6)
    return dict(name='P4 fairway mark',role='Green conical navigation buoy',length=2.1,beam=2.1,draft=2.05,wakes=[],receiver=[0,-2.04,0])

def object_mesh(batch):
    # Weld identical geometric corners while keeping distinct normals/UVs on
    # each loop. All opaque finishes are batched by slot per moving vessel.
    coords=[];index={};remap=[]
    for p in batch.verts:
        key=tuple(round(e,6) for e in p)
        if key not in index:index[key]=len(coords);coords.append(bl(p))
        remap.append(index[key])
    mesh=bpy.data.meshes.new(batch.id+'_assembly');mesh.from_pydata(coords,[],[tuple(remap[j] for j in face0) for face0 in batch.faces],shade_flat=False)
    for slot in batch.matlist:mesh.materials.append(materials[slot])
    mesh.polygons.foreach_set('material_index',batch.ids)
    tex=mesh.uv_layers.new(name='Physical UV');tex.uv.foreach_set('vector',[x for uv in batch.uv for x in uv]);mesh.normals_split_custom_set([bl(n) for n in batch.normals]);mesh.update()
    ob=bpy.data.objects.new(batch.id+'_assembly',mesh);return ob

def select(items):
    bpy.ops.object.select_all(action='DESELECT')
    for item in items:item.select_set(True)
    bpy.context.view_layer.objects.active=items[0]

def model(name,builder):
    group=active('harbor',name);contract=builder();col=bpy.data.collections.new('Vessel | '+name);bpy.context.scene.collection.children.link(col)
    base=bpy.data.objects.new(name,None);col.objects.link(base);base.empty_display_size=.35;base['design_waterline_metres']=0.;base['vessel_name']=contract['name']
    geo=object_mesh(group);col.objects.link(geo);geo.parent=base
    objects=[base,geo];z=contract['length']/2
    anchors={'bow':[0,0,-z],'stern':[0,0,z],'receiver':contract['receiver']}
    anchors.update(contract.get('cleats',{}));anchors.update({'wake_'+str(i):p for i,p in enumerate(contract['wakes'])})
    symbols={}
    for key,pos in anchors.items():
        ob=bpy.data.objects.new(name+'_'+key,None);col.objects.link(ob);ob.parent=base;ob.location=bl(pos);ob.empty_display_size=.10;objects.append(ob);symbols[key]={'node':ob.name,'web':pos,'unity':[pos[0],pos[1],-pos[2]]}
    select(objects)
    bpy.ops.export_scene.gltf(filepath=str(WEB/(name+'.glb')),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,
        export_animations=False,export_cameras=False,export_lights=False,export_normals=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO')
    bpy.ops.export_scene.fbx(filepath=str(NATIVE/(name+'.fbx')),use_selection=True,axis_forward='-Z',axis_up='Y',object_types={'MESH','EMPTY'},
        bake_space_transform=True,bake_anim=False,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_triangles=True,path_mode='STRIP',colors_type='LINEAR')
    stats=dict(contract,id=name,node=name,glb=name+'.glb',fbx=name+'.fbx',bounds=[trim(group.lo),trim(group.hi)],anchors=symbols,materials=group.matlist,
        vertices=len(geo.data.vertices),triangles=sum(len(f)-2 for f in group.faces),drawCalls=len(group.matlist))
    print('FLEET',name,stats['bounds'],stats['vertices'],stats['triangles'],stats['drawCalls'],flush=True)
    return stats,base

def photo_scene(roots):
    scene=bpy.context.scene;scene.world=bpy.data.worlds.new('Clear marine daylight');scene.world.use_nodes=True
    tree=scene.world.node_tree;background=tree.nodes.get('Background');tex=tree.nodes.new('ShaderNodeTexSky')
    try:tex.sky_type='NISHITA';tex.sun_elevation=math.radians(26);tex.sun_rotation=math.radians(129)
    except (TypeError,AttributeError):pass
    background.inputs['Strength'].default_value=.17;tree.links.new(tex.outputs['Color'],background.inputs['Color']);scene.view_settings.exposure=-.77
    sun=bpy.data.lights.new('Morning key','SUN');sun.energy=2.3;sun.angle=.026;sun.color=(1,.89,.73);so=bpy.data.objects.new('Harbor sun',sun);scene.collection.objects.link(so);so.rotation_euler=(.55,-.67,-.82)
    # The independent source library uses an actual Fresnel sea with fine
    # surface roughness. No water geometry is included in the exported boats.
    water=bpy.data.materials.new('Preview | tidal water');water.use_nodes=True;nd=water.node_tree.nodes;lk=water.node_tree.links
    w=nd['Principled BSDF'];w.inputs['Base Color'].default_value=(.012,.065,.073,1);w.inputs['Roughness'].default_value=.22;w.inputs['Metallic'].default_value=.13;w.inputs['IOR'].default_value=1.333
    coord=nd.new('ShaderNodeTexCoord');mapping=nd.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(.54,1.2,1.)
    lk.new(coord.outputs['Object'],mapping.inputs[0]);noise=nd.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=2.9;noise.inputs['Detail'].default_value=3.5;noise.inputs['Roughness'].default_value=.67
    lk.new(mapping.outputs[0],noise.inputs['Vector']);bump=nd.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.36;bump.inputs['Distance'].default_value=.093
    lk.new(noise.outputs['Fac'],bump.inputs['Height']);lk.new(bump.outputs['Normal'],w.inputs['Normal'])
    sea=bpy.data.meshes.new('Preview water');sea.from_pydata([(-1800,-1800,-.017),(1800,-1800,-.017),(1800,1800,-.017),(-1800,1800,-.017)],[],[(0,1,2,3)])
    sea.materials.append(water);waterob=bpy.data.objects.new('Preview water',sea);scene.collection.objects.link(waterob)
    sites={'tug':(0,0,0),'supply':(-64,0,-80),'pilot':(35,0,13),'buoy':(-16,0,-16)}
    for nm,ob in roots.items():ob.location=bl(sites[nm])
    def camera(id,eye,look,lens):
        d=bpy.data.cameras.new('Bridge optics '+id);d.lens=lens;d.clip_start=.1;d.clip_end=3000
        o=bpy.data.objects.new('Inspection | '+id,d);scene.collection.objects.link(o);o.location=bl(eye);o.rotation_euler=(v(bl(look))-o.location).to_track_quat('-Z','Y').to_euler();return o
    cam={}
    for id,eye,target,lens in (('tug',(23.7,12.3,-28.4),(0,2.48,-.13),45),('supply',(39.0,20.6,43.5),(0,4.0,.30),45),
                ('pilot',(10.65,5.7,-12.91),(0,1.10,.02),42),('buoy',(4.85,3.12,-5.55),(0,1.73,0),32)):
        spot=v(sites[id]);cam[id]=camera(id,spot+v(eye),spot+v(target),lens)
    scene.camera=cam['tug'];scene.render.engine='CYCLES';scene.cycles.samples=26;scene.cycles.use_denoising=True
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX';prefs.refresh_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
    except (TypeError,RuntimeError):pass
    scene.render.resolution_x=1100;scene.render.resolution_y=680;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='JPEG';scene.render.image_settings.quality=92
    for im in images.values():
        if not im.packed_file:im.pack()
    for ar in bpy.context.screen.areas:
        if ar.type=='VIEW_3D':ar.spaces.active.region_3d.view_perspective='CAMERA'
    select([roots['tug']]);bpy.ops.wm.save_as_mainfile(filepath=str(ART/'Pelagic-Harbor.blend'),compress=True)
    if '--preview' in sys.argv:
        for id,ob in cam.items():
            scene.camera=ob;scene.render.filepath=str(ART/(id+'.jpg'));bpy.ops.render.render(write_still=True)

if __name__=='__main__':
    entries={};models={}
    for label,builder in (('tug',tug),('supply',supply),('pilot',pilot),('buoy',buoy)):
        entries[label],models[label]=model(label,builder)
    manifest=dict(basis='glTF metres; +X starboard, +Y up, -Z bow',unityBasis='Unity metres; +X starboard, +Y up, +Z bow',
        waterline=0,units='m',models=entries)
    for loc in (WEB,NATIVE,ART):(loc/'layout.json').write_text(json.dumps(manifest,indent=2))
    photo_scene(models)
