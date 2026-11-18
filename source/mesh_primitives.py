"""Geometry primitives shared by Blender authoring scripts, in glTF world axes."""
groups={}; current=None
class Batch:
    """Group authoring surfaces into one mesh with a persistent interaction pivot."""
    def __init__(self,room,id,pivot=(0,0,0),center=None,animation=None,parent=None):
        self.room=room;self.id=id;self.pivot=v(pivot);self.center=v(center or pivot)
        self.animation=animation;self.parent=parent;self.verts=[];self.faces=[];self.normals=[];self.uv=[];self.ids=[]
        self.matlist=[];self.matindex={};self.object=None;self.mesh=None
        self.lo=[1e9]*3;self.hi=[-1e9]*3
        groups[(room,id)]=self
    def face(self,pts,mat,normal=None,uv=None,normals=None):
        handheld=self.id in ("field_glasses","mug","access_card","logbook","tool_roll") or self.id.startswith("mech_")
        if handheld:
            mat={"Titanium":"Precision_Titanium","Graphite_Alloy":"Anodized_Frame","Ceramic_Pearl":"Handheld_Shell"}.get(mat,mat)
        pts=[v(p) for p in pts]
        n=(pts[1]-pts[0]).cross(pts[2]-pts[0])
        if n.length_squared<1e-17:return
        n.normalize()
        if normal is not None and n.dot(v(normal))<0:
            pts.reverse();n.negate()
            if uv is not None:uv=list(reversed(uv))
            if normals is not None:normals=list(reversed(normals))
        if mat not in self.matindex:
            self.matindex[mat]=len(self.matlist);self.matlist.append(mat)
        start=len(self.verts);self.verts.extend(pts);self.faces.append(tuple(range(start,start+len(pts))))
        self.ids.append(self.matindex[mat]);self.normals.extend(normals or [n]*len(pts))
        if uv is None:
            ax=max(range(3),key=lambda i:abs(n[i]))
            ids=((2,1),(0,2),(0,1))[ax]
            rep=4 if mat.endswith(("Wool","Cloth","Canvas")) or metadata.get(mat,{}).get("family")=="fabric" else 2
            if handheld:rep=5.5 if mat in ("Wallet_Canvas","Aramid_Webbing","Restraint_Webbing") else 8.0
            uv=[(p[ids[0]]*rep,p[ids[1]]*rep) for p in pts]
        self.uv.extend(uv)
        for p in pts:
            for i in range(3):
                if p[i]<self.lo[i]:self.lo[i]=p[i]
                if p[i]>self.hi[i]:self.hi[i]=p[i]


def active(room,id,pivot=(0,0,0),center=None,animation=None,parent=None):
    global current
    current=Batch(room,id,pivot,center,animation,parent)
    return current

def shell(room):
    global current
    current=groups[(room,"shell")]

def face(pts,mat,n=None,uv=None,normals=None):
    current.face(pts,mat,n,uv,normals)
def P(id):
    return "Surface_"+id
def basis(n):
    n=v(n).normalized()
    right=(Y.cross(n) if abs(n.y)<.98 else X).normalized()
    return right,n.cross(right).normalized(),n
def rot(axis,ang):
    return Matrix.Rotation(ang,3,v(axis))
def cube(c,dim,mat,b=0,rotation=None):
    c=v(c);half=[d/2 for d in dim]
    b=min(b,min(half)*.82)
    orient=(lambda vec:rotation@v(vec)) if rotation is not None else v
    def point(core,normal):
        return c+orient(v(core)+v(normal)*b)
    def fc(core,ns,exp):
        face([point(z,n) for z,n in zip(core,ns)],mat,orient(exp),normals=[orient(n) for n in ns])
    hs=[max(.00001,k-b) for k in half]
    for axis in range(3):
        i=(axis+1)%3;j=(axis+2)%3
        for s in (-1,1):
            n=[0,0,0];n[axis]=s
            cs=[]
            for a,h in ((-1,-1),(1,-1),(1,1),(-1,1)):
                co=[0.,0.,0.];co[axis]=s*hs[axis];co[i]=a*hs[i];co[j]=h*hs[j];cs.append(co)
            fc(cs,[n]*4,n)
    if b<=1e-6:return
    for axis in range(3):
        i=(axis+1)%3;j=(axis+2)%3
        for a,h in ((-1,-1),(1,-1),(1,1),(-1,1)):
            n1=v((0,0,0));n2=n1.copy();n1[i]=a;n2[j]=h
            ca=v((0,0,0));ca[i]=a*hs[i];ca[j]=h*hs[j];cb=ca.copy();ca[axis]=-hs[axis];cb[axis]=hs[axis]
            fc([ca,cb,cb,ca],[n1,n1,n2,n2],n1+n2)
    for sx in (-1,1):
        for sy in (-1,1):
            for sz in (-1,1):
                co=(sx*hs[0],sy*hs[1],sz*hs[2]);ns=[(sx,0,0),(0,sy,0),(0,0,sz)]
                fc([co]*3,ns,(sx,sy,sz))


def rod(a,b,r,mat,seg=14,r2=None,cap=True):
    a=v(a);b=v(b);n=(b-a).normalized()
    if (b-a).length_squared<1e-12:return
    right,up,_=basis(n);r2=r if r2 is None else r2
    dr=[right*math.cos(T*i/seg)+up*math.sin(T*i/seg) for i in range(seg)]
    a1=[a+d*r for d in dr];b1=[b+d*r2 for d in dr]
    for i,j in enumerate(list(range(1,seg))+[0]):
        face([a1[i],a1[j],b1[j],b1[i]],mat,dr[i]+dr[j],normals=[dr[i],dr[j],dr[j],dr[i]])
    if cap:
        face(a1,mat,-n);face(b1,mat,n)


def tube(path,r,mat,seg=8,closed=False):
    path=[v(p) for p in path]; last=len(path)-1;rd=[];rings=[]
    for i,p in enumerate(path):
        prev=path[i-1] if i or closed else path[0]
        nxt=path[(i+1)%len(path)] if i<last or closed else path[-1]
        t=(nxt-prev).normalized()
        if i==0: ref,_,_=basis(t)
        ref=(ref-t*ref.dot(t)).normalized();ort=t.cross(ref).normalized()
        ds=[ref*math.cos(T*j/seg)+ort*math.sin(T*j/seg) for j in range(seg)]
        rd.append(ds);rings.append([p+q*r for q in ds])
    for i in range(len(path) if closed else last):
        k=(i+1)%len(path)
        for j in range(seg):
            l=(j+1)%seg
            ns=[rd[i][j],rd[i][l],rd[k][l],rd[k][j]]
            face([rings[i][j],rings[i][l],rings[k][l],rings[k][j]],mat,ns[0],normals=ns)
    if not closed:
        face(rings[0],mat,path[0]-path[1]);face(rings[-1],mat,path[-1]-path[-2])


def torus(c,n,R,r,mat,steps=32,seg=8,span=(0,T)):
    c=v(c);a,b,n=basis(n);closed=abs(span[1]-span[0]-T)<.0001
    pts=[c+(a*math.cos(t)+b*math.sin(t))*R for t in [span[0]+(span[1]-span[0])*i/steps for i in range(steps+(not closed))]]
    tube(pts,r,mat,seg,closed)
def screw(c,n,size=.012,slot=True):
    c=v(c);r,u,n=basis(n)
    rod(c-n*.0015,c+n*.0026,size,"Graphite_Alloy",8)
    if slot:
        a=(r*.75+u*.34)*size; w=(-r*.12+u*.24)*size
        pp=c+n*.0029;face([pp-a-w,pp+a-w,pp+a+w,pp-a+w],"Black_Rubber",n)
def label(c,n,w,h,key,display=False,right=None):
    c=v(c);r,u,n=basis(n)
    if right is not None:r=v(right).normalized();u=n.cross(r)
    u0,v0,wi,he=atlas["rects"][key];aw,ah=atlas["size"]
    uv=[(u0/aw,1-(v0+he)/ah),((u0+wi)/aw,1-(v0+he)/ah),((u0+wi)/aw,1-v0/ah),(u0/aw,1-v0/ah)]
    pts=[c+r*(w*a/2)+u*(h*b/2) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    face(pts,"Display_Phosphor" if display else "Carriage_Print",n,uv)
def mark(c,n,w,h,key,right=None):
    c=v(c);r,u,n=basis(n)
    if right is not None:r=v(right).normalized();u=n.cross(r)
    u0,v0,wi,he=stencils["rects"][key];aw,ah=stencils["size"]
    uv=[(u0/aw,1-(v0+he)/ah),((u0+wi)/aw,1-(v0+he)/ah),((u0+wi)/aw,1-v0/ah),(u0/aw,1-v0/ah)]
    face([c+r*(w*a/2)+u*(h*b/2) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]],"Hull_Stencils",n,uv)
def arc_rect(w,h,rad,steps=4):
    rad=max(.001,min(rad,w*.48,h*.48)); pts=[]
    for cx,cy,start in [(w/2-rad,-h/2+rad,-math.pi/2),(w/2-rad,h/2-rad,0),(-w/2+rad,h/2-rad,math.pi/2),(-w/2+rad,-h/2+rad,math.pi)]:
        for j in range(steps+1):
            a=start+math.pi/2*j/steps;pts.append((cx+math.cos(a)*rad,cy+math.sin(a)*rad))
    return pts
def rim(c,n,wo,ho,ro,wi,hi,ri,depth,mat,inner_mat=None,offset=0,center_offset=(0,0)):
    c=v(c);r,u,n=basis(n);c+=n*offset
    outer=[c+r*x+u*y for x,y in arc_rect(wo,ho,ro)]
    inner=[c+r*(x+center_offset[0])+u*(y+center_offset[1]) for x,y in arc_rect(wi,hi,ri)]
    for i in range(len(outer)):
        j=(i+1)%len(outer)
        face([outer[i],outer[j],inner[j],inner[i]],mat,n)
        if depth:
            face([outer[i]-n*depth,outer[j]-n*depth,outer[j],outer[i]],mat,(outer[i]+outer[j])*.5-c)
            face([inner[i],inner[j],inner[j]-n*depth,inner[i]-n*depth],inner_mat or mat,c-(inner[i]+inner[j])*.5)
            face([outer[i]-n*depth,inner[i]-n*depth,inner[j]-n*depth,outer[j]-n*depth],mat,-n)
def flat_round(c,n,w,h,rr,mat):
    c=v(c);r,u,n=basis(n)
    face([c+r*x+u*y for x,y in arc_rect(w,h,rr,7)],mat,n)
def plate(c,n,w,h,th,mat,b=.008):
    r,u,n=basis(n);basis_mat=Matrix((r,u,n)).transposed()
    cube(c,(w,h,th),mat,b,basis_mat)
def add_anim(kind,axis,amount):
    return {"kind":kind,"axis":axis,"amount":amount}
def current_bounds(g):
    return [[round(a,5) for a in g.lo],[round(a,5) for a in g.hi]]

