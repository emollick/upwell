"""Keep glTF self-contained while compressing exporter-generated opaque PBR channels."""
from pathlib import Path
from io import BytesIO
import json
import struct
import sys
from PIL import Image


folder=Path(__file__).resolve().parents[1]/"web"/"assets"/"rooms"
paths=[folder/(name+".glb") for name in sys.argv[1:]] if sys.argv[1:] else folder.glob("*.glb")
for path in paths:
    data=path.read_bytes()
    json_len=struct.unpack_from("<I",data,12)[0]
    doc=json.loads(data[20:20+json_len]);body=data[28+json_len:]
    images={image["bufferView"]:image for image in doc.get("images",[]) if "bufferView" in image}
    binary=bytearray()
    for i,view in enumerate(doc["bufferViews"]):
        part=body[view.get("byteOffset",0):view.get("byteOffset",0)+view["byteLength"]]
        imdef=images.get(i)
        if imdef and imdef["mimeType"]=="image/png" and imdef["name"].endswith(("_Roughness","_roughness")):
            im=Image.open(BytesIO(part)).convert("RGB")
            out=BytesIO();im.save(out,format="JPEG",quality=88,subsampling=0,optimize=True)
            if len(out.getvalue())<len(part):
                part=out.getvalue();imdef["mimeType"]="image/jpeg"
        view["byteOffset"]=len(binary);view["byteLength"]=len(part)
        binary+=part;binary+=b"\0"*((-len(binary))%4)
    for mat in doc["materials"]:
        if mat["name"]=="Hull_Stencils":
            mat["alphaMode"]="MASK";mat["alphaCutoff"]=.33
    doc["buffers"][0]["byteLength"]=len(binary)
    text=json.dumps(doc,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    text+=b" "*((-len(text))%4)
    size=28+len(text)+len(binary)
    head=struct.pack("<4sIIII",b"glTF",2,size,len(text),0x4E4F534A)
    blob=head+text+struct.pack("<II",len(binary),0x004E4942)+binary
    tmp=path.with_suffix(".building");tmp.write_bytes(blob);tmp.replace(path)
    print(f"{path.name}: {len(data)/1024**2:.2f} -> {len(blob)/1024**2:.2f} MiB")
