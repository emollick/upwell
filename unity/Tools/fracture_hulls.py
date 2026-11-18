"""Decompose the five surveyed, concave cross-sections into exact convex collision prisms."""
import json

def sync_cartridge_hulls(project):
    folder=project/"Assets/Upwell/Resources/Fracture"
    source=folder/"cartridge.json"
    if not source.is_file():
        return
    shapes=[]
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for shard in json.loads(source.read_text(encoding="utf-8"))["shards"]:
        vertices=shard["vertices"]
        ring=vertices[:len(vertices)//2]
        order=list(range(len(ring)))
        area=sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(ring,ring[1:]+ring[:1]))
        if area<0:order.reverse()
        triangles=[]
        while len(order)>3:
            for j,index in enumerate(order):
                a,b,c=order[j-1],index,order[(j+1)%len(order)]
                if cross(ring[a],ring[b],ring[c])<1e-10:continue
                if any(k not in (a,b,c) and min(cross(ring[a],ring[b],ring[k]),cross(ring[b],ring[c],ring[k]),cross(ring[c],ring[a],ring[k]))>=-1e-10 for k in order):continue
                triangles.extend([a,b,c]);order.pop(j);break
            else:raise ValueError("Degenerate cartridge shard polygon: "+shard["name"])
        triangles.extend(order)
        shapes.append({"name":shard["name"],"xyz":[n for p in vertices for n in p],"triangles":triangles})
    output=folder/"collision-hulls.json"
    data=json.dumps({"shapes":shapes},separators=(",",":"))
    if not output.is_file() or output.read_text()!=data:output.write_text(data,encoding="utf-8")
