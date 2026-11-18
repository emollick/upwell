"""Losslessly encode browser mesh views and deduplicate byte-identical images.

Every shared texture bank groups assets with the same consumers. This keeps the
number of requests small without charging the initial room for unrelated maps.
The supplied browser decoder verifies the exact original view bytes before any
GLB is replaced. Run after pack_web.py and the authoring exports. Use
--guide-journals after guide_journals.py to repack only the bearing kit.
"""
from collections import defaultdict
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/"web"/"assets"
orbital=sys.argv[1:]==["--orbital"]
journals=sys.argv[1:]==["--guide-journals"]
CACHE=ROOT/"source"/".export-cache"/("delivery-journals" if journals else "delivery-orbital" if orbital else "delivery");CACHE.mkdir(parents=True,exist_ok=True)
# Journal caps contain positions, normals and indices only. Their isolated run
# must never collect or prune another flight asset's texture banks.
BANK=CACHE/"banks" if journals else BASE/("orbital" if orbital else "pbr")
BANK.mkdir(exist_ok=True)
EXT="EXT_meshopt_compression"
libpath=os.environ.get("UPWELL_MESHOPT_DLL","C:/Program Files/Blender Foundation/Blender 5.2/blender.shared/meshoptimizer.dll")
lib=C.CDLL(libpath);ptr=C.c_void_p;sz=C.c_size_t
for name,args,rest in (("encodeVertexVersion",[C.c_int],None),("encodeIndexVersion",[C.c_int],None),
        ("encodeVertexBufferBound",[sz,sz],sz),("encodeVertexBuffer",[ptr,sz,ptr,sz,sz],sz),
        ("decodeVertexBuffer",[ptr,sz,sz,ptr,sz],C.c_int),("encodeIndexSequenceBound",[sz,sz],sz),
        ("encodeIndexSequence",[ptr,sz,ptr,sz],sz),("decodeIndexSequence",[ptr,sz,sz,ptr,sz],C.c_int)):
    fn=getattr(lib,"meshopt_"+name);fn.argtypes=args;fn.restype=rest
lib.meshopt_encodeVertexVersion(0);lib.meshopt_encodeIndexVersion(1)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def pad(buf):buf.extend(b"\0"*((-len(buf))%4))
def write_glb(doc,data):
    text=json.dumps(doc,separators=(",",":"),ensure_ascii=False).encode("utf8")
    text+=b" "*((-len(text))%4)
    return struct.pack("<4sIIII",b"glTF",2,28+len(text)+len(data),len(text),0x4E4F534A)+text+struct.pack("<II",len(data),0x004E4942)+data
def unpack(path):
    src=path.read_bytes();l=struct.unpack_from("<I",src,12)[0];j=json.loads(src[20:20+l]);bufs=[src[28+l:]]
    for b in j["buffers"][1:]:
        bufs.append((path.parent/b["uri"]).read_bytes() if "uri" in b else None)
    raw=[]
    for bv in j["bufferViews"]:
        ext=bv.get("extensions",{}).get(EXT)
        if ext:
            start=ext.get("byteOffset",0);encoded=bufs[ext["buffer"]][start:start+ext["byteLength"]]
            count,stride=ext["count"],ext["byteStride"];dst=(C.c_uint8*(count*stride))()
            decode=lib.meshopt_decodeVertexBuffer if ext["mode"]=="ATTRIBUTES" else lib.meshopt_decodeIndexSequence
            if decode(dst,count,stride,encoded,len(encoded)):raise ValueError("Unable to expand "+path.name)
            data=bytes(dst)
        else:
            o=bv.get("byteOffset",0);data=bufs[bv["buffer"]][o:o+bv["byteLength"]]
        raw.append(data)
    return j,raw
def attr_config(doc):
    result={}
    sizes={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}
    dims={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT2":4,"MAT3":9,"MAT4":16}
    for a in doc["accessors"]:
        bv=a.get("bufferView")
        if bv is None:continue
        view=doc["bufferViews"][bv];stride=view.get("byteStride",sizes[a["componentType"]]*dims[a["type"]])
        if view.get("target")==34963 and a["componentType"] in (5123,5125):
            result[bv]=("INDICES",stride,a["count"])
        elif stride%4==0 and stride<=256 and view["byteLength"]%stride==0:
            result[bv]=("ATTRIBUTES",stride,view["byteLength"]//stride)
    return result
def encode(raw,mode,stride,count):
    if mode=="INDICES":
        original=np.frombuffer(raw,dtype="<u2" if stride==2 else "<u4").astype(np.uint32)
        bound=lib.meshopt_encodeIndexSequenceBound(count,int(original.max())+1);dst=(C.c_uint8*bound)()
        length=lib.meshopt_encodeIndexSequence(dst,bound,original.ctypes.data,count)
    else:
        bound=lib.meshopt_encodeVertexBufferBound(count,stride);dst=(C.c_uint8*bound)()
        length=lib.meshopt_encodeVertexBuffer(dst,bound,raw,count,stride)
    return bytes(dst[:length])

files=[*sorted((BASE/"rooms").glob("*.glb")),*sorted((BASE/"terminals").glob("*.glb")),BASE/"guideway"/"guideway.glb"]
if orbital:files=[BANK/(name+".glb") for name in ("AsterReach","CounterCar","Receiver")]
if journals:files=[BASE/"guideway"/"journal-caps.glb"]
source={};images={};usage=defaultdict(set);frequency=defaultdict(int);bank_map={}
for path in files:
    doc,data=unpack(path);source[path]=(doc,data)
    for im in doc.get("images",[]):
        raw=data[im["bufferView"]];h=digest(raw);images[h]=raw;usage[h].add(path.name);frequency[h]+=1
grouped=defaultdict(list)
for h,count in frequency.items():
    if count>1:grouped[tuple(sorted(usage[h]))].append(h)
bankfiles={}
for names,hashes in grouped.items():
    data=bytearray();entries=[]
    for h in sorted(hashes):
        entries.append((h,len(data),len(images[h])));data+=images[h];pad(data)
    name="shared-"+digest(data)[:20]+".bin";path=BANK/name
    if not path.exists():path.write_bytes(data)
    bankfiles[name]=len(data)
    for h,pos,n in entries:bank_map[h]=(name,pos,n)
receipts=[]
for path,(doc,views) in source.items():
    # Blender exports the white sheen tint instead of multiplying it by the
    # Principled weight. Encode the measured grazing tint of the woven fibres.
    for mat in doc.get("materials",[]):
        if mat["name"] in {"Quilt_Ripstop","Quilt_Lining","Curtain_Acoustic","Berth_Bias_Tape"}:
            sheen=mat.get("extensions",{}).get("KHR_materials_sheen")
            if sheen is not None:sheen["sheenColorFactor"]=[.12,.135,.12]
    ids={im["bufferView"] for im in doc.get("images",[])};cfg=attr_config(doc);binary=bytearray();virtual=0
    banks=[];pending_fallback=[];out_views=[];expect=[]
    for i,(old,raw) in enumerate(zip(doc["bufferViews"],views)):
        bv={k:v for k,v in old.items() if k not in ("buffer","byteOffset","byteLength","extensions")}
        hh=digest(raw);expect.append(hh)
        if i in ids and hh in bank_map:
            bank,position,size=bank_map[hh]
            if bank not in banks:banks.append(bank)
            bv.update(buffer=banks.index(bank)+1,byteOffset=position,byteLength=size)
        else:
            encoding=None
            if i not in ids and i in cfg:
                mode,stride,count=cfg[i]
                if len(raw)==stride*count:
                    encoded=encode(raw,mode,stride,count)
                    if len(encoded)+64<len(raw):
                        encoding=dict(buffer=0,byteOffset=len(binary),byteLength=len(encoded),byteStride=stride,count=count,mode=mode,filter="NONE")
            if encoding:
                bv.update(buffer=-1,byteOffset=virtual,byteLength=len(raw),extensions={EXT:encoding})
                pending_fallback.append(bv);virtual+=len(raw);virtual=(virtual+3)&~3
                binary+=encoded
            else:
                bv.update(buffer=0,byteOffset=len(binary),byteLength=len(raw));binary+=raw
            pad(binary)
        out_views.append(bv)
    doc["bufferViews"]=out_views
    doc["buffers"]=[{"byteLength":len(binary)}]+[{"byteLength":bankfiles[n],"uri":("./" if orbital else "../pbr/")+n} for n in banks]
    if pending_fallback:
        for bv in pending_fallback:bv["buffer"]=len(doc["buffers"])
        doc["buffers"].append({"byteLength":virtual,"extensions":{EXT:{"fallback":True}}})
        for key in ("extensionsUsed","extensionsRequired"):
            if EXT not in doc.setdefault(key,[]):doc[key].append(EXT)
    staged=CACHE/(path.name+".stage")
    staged.write_bytes(write_glb(doc,binary))
    receipts.append({"path":str(path),"stage":str(staged),"hashes":expect})
report=CACHE/"expected.json";report.write_text(json.dumps(receipts,separators=(",",":")))
subprocess.run(["node",str(ROOT/"source"/"verify_delivery.mjs"),str(report)],check=True)
for r in receipts:os.replace(r["stage"],r["path"])
for old in BANK.glob("shared-*.bin"):
    if old.name not in bankfiles:old.unlink()
print("Packed",len(files),"models with",len(bankfiles),"shared banks. Total",round((sum(p.stat().st_size for p in files)+sum(bankfiles.values()))/1024**2,2),"MiB.")
