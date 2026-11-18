"""Prepare detail-bearing finishes from photographic CC0 material captures.

Run --fetch once to retrieve the original Poly Haven maps. Rebuilding then
works offline from art/surface-scans. Recoloring retains the measured spatial
variation in the material's albedo, roughness and tangent-space normal.
"""
import argparse
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SCANS = ROOT / "art" / "surface-scans"
MATERIALS = ROOT / "unity" / "Assets" / "Upwell" / "SourceModels" / "Textures"
ASSETS = ["terlenka", "denim_fabric_06", "scuba_suede", "blue_metal_plate",
          "metal_plate", "rubber_tiles", "hangar_concrete_floor"]
HEADERS = {"User-Agent": "Upwell material authoring/1.0 (local project)"}
CHANNELS = {"albedo": ["Diffuse", "diffuse", "color", "col1"], "normal": ["nor_gl"], "roughness": ["Rough", "rough"]}

def read_url(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=75) as response:
        return response.read()

def fetch(asset):
    files = json.loads(read_url("https://api.polyhaven.com/files/" + asset))
    target = SCANS / asset
    target.mkdir(parents=True, exist_ok=True)
    receipt = {"asset": asset, "page": "https://polyhaven.com/a/" + asset,
               "license": "CC0", "licenseUrl": "https://polyhaven.com/license", "maps": {}}
    for role, options in CHANNELS.items():
        channel = next((name for name in options if name in files), None)
        if not channel:
            raise ValueError(f"{asset}: missing {role}. Found {list(files)}")
        source = files[channel]["2k"]["jpg"]
        data = read_url(source["url"])
        assert source.get("md5") is None or hashlib.md5(data).hexdigest() == source["md5"]
        (target / (role + ".jpg")).write_bytes(data)
        receipt["maps"][role] = {"url": source["url"], "sha256": hashlib.sha256(data).hexdigest()}
    print(asset, "downloaded", flush=True)
    return receipt

def make_finish(slot, spec, asset, size=1024):
    directory = SCANS / asset
    machined=slot in {"Titanium","Aluminum","Graphite_Alloy","Surface_grab_handle"}
    crop=None
    if machined:
        # The unbroken sheet between diamond treads supplies mill finishes.
        # Using the entire survey on a flange embosses floor tread onto optics.
        capture=np.asarray(Image.open(directory/"albedo.jpg").convert("L"),dtype=np.float32)
        tile=148
        candidates=[]
        for y in range(32,capture.shape[0]-tile,63):
            for x in range(32,capture.shape[1]-tile,63):
                patch=capture[y:y+tile,x:x+tile]
                candidates.append((patch.std()+np.std(np.diff(patch,axis=1)),x,y))
        _,x,y=min(candidates)
        crop=(x,y,x+tile,y+tile)
    def image(role):
        im=Image.open(directory/(role+".jpg")).convert("RGB")
        if crop is not None:
            a=np.asarray(im.crop(crop))
            top=np.concatenate((a,a[:,::-1]),axis=1)
            im=Image.fromarray(np.concatenate((top,top[::-1]),axis=0))
        return im.resize((size,size),Image.Resampling.LANCZOS)
    # Preserve hue chosen for the space-rated coating. Removing a capture's
    # broad luminance gradient avoids stamping permanent light on its surface.
    grey = image("albedo").convert("L")
    luma = np.asarray(grey, dtype=np.float32)/255
    broad = np.asarray(grey.filter(ImageFilter.GaussianBlur(size/20)), dtype=np.float32)/255
    fabric = asset in {"terlenka","denim_fabric_06","scuba_suede"}
    variation = (luma-broad)*(1.05 if fabric else .39) + (broad-np.median(broad))*(.42 if fabric else .20)
    relative = np.clip(1 + variation/max(.13,float(np.median(luma))), .47, 1.68)
    rgb = np.array(spec["rgb"], dtype=np.float32)[None,None,:]*relative[:,:,None]
    rough = np.asarray(image("roughness").convert("L"),dtype=np.float32)/255
    rough = np.clip(spec["roughness"] + (rough-np.median(rough))*(.82 if fabric else .64),.07,.98)
    n = np.asarray(image("normal").convert("RGB"),dtype=np.float32)/127.5-1
    if machined:n[:,:,:2]-=np.mean(n[:,:,:2],axis=(0,1))
    n[:,:,:2] *= .95 if fabric else (.54 if asset=="rubber_tiles" else .16 if machined else .27)
    n /= np.maximum(.001,np.linalg.norm(n,axis=2,keepdims=True))
    for key,data in [("baseColor",rgb),("roughnessMap",rough*255),("normal",(n*.5+.5)*255)]:
        target=MATERIALS/spec[key]
        Image.fromarray(np.uint8(np.clip(data,0,255))).save(target,quality=92,subsampling=0)

def apply_finishes():
    specs=json.loads((MATERIALS/"materials.json").read_text(encoding="utf8"))
    groups={
        "terlenka":["Pressure_Fabric","Technical_Twill","Surface_lounge_seat","Surface_bunk","Surface_privacy_curtain"],
        "denim_fabric_06":["Aramid_Webbing","Restraint_Webbing","Wallet_Canvas","Surface_tool_roll","Data_Jacket","Surface_logbook"],
        "scuba_suede":["Harness_Grip","Grip_Elastomer","Surface_field_glasses"],
        "rubber_tiles":["Floor_Rubber","Black_Rubber"],
        "blue_metal_plate":["Ceramic_Pearl","Composite_Slate","Carbon_Ceramic","Surface_locker_drawer","Surface_service_cabinet","Surface_pressure_hatch"],
        "metal_plate":["Titanium","Aluminum","Graphite_Alloy","Surface_mug","Surface_grab_handle"],
    }
    used={}
    for source,slots in groups.items():
        for name in slots:
            spec=specs.get(name)
            if spec and all(spec.get(k) for k in ("baseColor","normal","roughnessMap")):
                make_finish(name,spec,source,1024 if not name.startswith("Surface_") else 768)
                used[name]=source
    (SCANS/"assignments.json").write_text(json.dumps(used,indent=2),encoding="utf8")
    print("Photographic surface assignments",len(used))

if __name__ == "__main__":
    options=argparse.ArgumentParser()
    options.add_argument("--fetch",action="store_true")
    options.add_argument("--fetch-only",action="store_true")
    args=options.parse_args()
    if args.fetch or args.fetch_only:
        SCANS.mkdir(parents=True,exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            sources=list(executor.map(fetch, ASSETS))
        (SCANS/"sources.json").write_text(json.dumps(sources,indent=2),encoding="utf8")
    if not args.fetch_only:
        apply_finishes()
