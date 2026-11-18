"""Normalize the fabrication manifest for Unity's serializer without changing the Blender sources."""
import json
import shutil
import filecmp
import hashlib
from io import BytesIO
from pathlib import Path

project = Path(__file__).resolve().parents[1]
from fracture_hulls import sync_cartridge_hulls
sync_cartridge_hulls(project)
moment_source=project.parent/"web/assets/passage-moments.json"
moment_dest=project/"Assets/Upwell/Resources/PassageMoments.json"
moment_dest.parent.mkdir(parents=True,exist_ok=True)
if not moment_dest.exists() or moment_source.read_bytes()!=moment_dest.read_bytes():
    shutil.copyfile(moment_source,moment_dest)
from sync_weather import sync_weather
if (project.parent/"web/weather-density.js").is_file():sync_weather(project)
models = project / "Assets/Upwell/SourceModels"
art = json.loads((project.parent / "art/manifest.json").read_text(encoding="utf-8"))
props = {p["id"]: p for r in art["rooms"] for p in r["props"]}
layout = json.loads((models / "layout.json").read_text(encoding="utf-8"))
board_path=models/"switchboard.json"
board=json.loads(board_path.read_text(encoding="utf-8")) if board_path.is_file() else {}
control_labels={"guide_flood":("Guide work light","Switch the exterior work light"),"cabin_lights":("Saloon lighting","Switch the saloon lights"),"solar_film":("Solar glazing","Change the glazing transmission"),"vent_fan":("Circulation fan","Switch the blower"),"panel_gain":("Display gain","Change instrument luminance"),"camera_focus":("Optical focal length","Advance the lens detent"),"diagnostic_screen":("Cabin diagnostics","Cycle ECLSS and electrical readings"),"drive_screen":("Drive telemetry","Inspect the drives and guide rollers")}
parts = []
control_labels.update({
    "accelerometer":("Mechanical accelerometer","Inspect the signed scale"),
    "accel_test":("Accelerometer test plunger","Hold the calibration plunger"),
    "capillary_cell":("Sealed capillary cell","Inspect the liquid chamber"),
    "capillary_primer":("Capillary primer","Press the diaphragm"),
})
for part in layout["parts"]:
    prop = props.get(part["id"], {})
    is_camera = part["id"] == "ascent_lever"
    key=part["id"];auto=(key.replace("_"," ").title(),"Operate")
    if key.startswith("key_"):auto=(key[4:].replace("_"," ").title()+" key","Press")
    if key.startswith("test_"):auto=(key[5:].title()+" test","Run the diagnostic")
    title,action=control_labels.get(key,auto)
    parts.append(dict(
        id=part["id"], room=part["room"], file=part["file"], pivot=part["webPivot"], focus=part["webCenter"],
        low=part["webBounds"][0], high=part["webBounds"][1], animation=part.get("animation", {}),
        title="Exterior camera selector" if is_camera else prop.get("name", "Pressure shell" if key=="shell" else title),
        action="Select an exterior camera" if is_camera else prop.get("action", action),
    ))
finishes=json.loads((models/"Textures/materials.json").read_text(encoding="utf-8"))
out={"parts":parts,"materials":[dict(name=k,**v) for k,v in finishes.items()]}
out["textureAliases"]=[]
# Multiple finishes use the identical scanned textile or metal map with their own
# metallic/roughness strengths. Resolve only byte-identical files with identical
# import settings so Unity packs each measurement just once.
for directory in [models/"Textures",project/"Assets/Upwell/Guideway/Textures",project/"Assets/Upwell/Terminals/Textures"]:
    canonical={}
    for source in sorted(directory.glob("*")):
        if source.suffix.lower() not in (".jpg",".jpeg",".png"):continue
        importer=source.with_name(source.name+".meta")
        if not importer.exists():continue
        settings=importer.read_text(encoding="utf-8").partition("TextureImporter:")[2]
        role=("normal" in source.name.lower(),"roughness" in source.name.lower())
        key=(hashlib.sha256(source.read_bytes()).digest(),settings,role)
        path=source.relative_to(project).as_posix()
        if key in canonical:out["textureAliases"].append(dict(path=path,source=canonical[key]))
        else:canonical[key]=path
out["switches"]=board.get("controls",[])
out["materials"].extend(m for m in board.get("materials",[]) if m["name"] not in finishes)
if (models/"flex.json").is_file():
    out["flex"]=[]
    for f in json.loads((models/"flex.json").read_text(encoding="utf-8"))["parts"]:
        out["flex"].append(dict(id=f["id"],parentId=f["parentId"],file=f["file"],points=[n for xyz in f["restPoints"] for n in xyz],pinned=f["pinIndices"],limit=f["maxOffset"],support=f.get("supportY") or 0,hasSupport=f.get("supportY") is not None,width=f["width"],thickness=f["thickness"],kind=f["kind"],widthGuide=f["widthGuide"],material=f["material"]))
if (models/"mechanisms.json").is_file():
    out["mechanisms"]=json.loads((models/"mechanisms.json").read_text(encoding="utf-8"))["parts"]
survey_file=models/"gravity-instruments.json"
if survey_file.exists():
    apparatus=json.loads(survey_file.read_text(encoding="utf-8"))
    out["apparatus"]=apparatus
soft_file=models/"furnishings.json"
if soft_file.exists():
    out["furnishings"]=[]
    for part in json.loads(soft_file.read_text(encoding="utf-8"))["parts"]:
        grid=part.get("grid",{})
        clearance=part.get("clearance",{}).get("localBounds",[])
        data={k:part[k] for k in ("id","room","file","parentId","webPivot","kind")}
        data.update(u=grid.get("u",[]),v=grid.get("v",[]),pinned=part.get("pinIndices",[]),
            rest=[n for p in grid.get("restPoints",part.get("restPoints",[])) for n in p],
            open=[n for p in grid.get("openPoints",[]) for n in p],belts=part.get("beltRows",[]),
            radius=part.get("radius",0),maxOffset=part.get("maxOffset",.17),hardware=[{"id":h["node"],"u":h["u"]} for h in part.get("hardware",[])],
            uvInverted=part.get("fbxVIsOneMinusV",False),
            lower=clearance[0] if clearance else [],upper=clearance[1] if clearance else [])
        out["furnishings"].append(data)
guide=project/"Assets/Upwell/Guideway"
if (guide/"layout.json").is_file():
    out["guide"]=json.loads((guide/"layout.json").read_text(encoding="utf-8"))
    out["guideMaterials"]=[dict(name=k,**v) for k,v in json.loads((guide/"Textures/materials.json").read_text(encoding="utf-8")).items()]
stations=project/"Assets/Upwell/Terminals"
if (stations/"layout.json").is_file():
    data=json.loads((stations/"layout.json").read_text(encoding="utf-8"))
    terminal_finishes=json.loads((stations/"Textures/materials.json").read_text(encoding="utf-8"))
    out["terminalMaterials"]=[dict(name=k,**v) for k,v in terminal_finishes.items()]
    out["stations"]=[]
    for key in ("anchor","aster"):
        info=data["stations"][key]
        kit=[]
        for p in data["parts"]:
            if p["station"]==key:
                kit.append(dict(id=p["id"],room=key,file=p["file"],pivot=p["webPivot"],focus=p["webCenter"],
                                low=p["webBounds"][0],high=p["webBounds"][1],reference=p["localReferenceVertex"],animation=p.get("animation",{})))
        out["stations"].append(dict(station=key,parts=kit,lights=info["lights"]))
world=project.parent/"web/assets/world"
if (world/"habitat-hull.webp").is_file():
    from PIL import Image
    for source,target in (("habitat-hull.webp","HabitatHull_Color.png"),("habitat-rough.webp","HabitatHull_Roughness.png")):
        # PNG retains the colour and data values of the shared source atlas for native importers.
        stream=BytesIO()
        with Image.open(world/source) as image: image.convert("RGB").save(stream,format="PNG")
        raw=stream.getvalue();native=project/"Assets/Upwell/Environment"/target
        if not native.exists() or native.read_bytes()!=raw: native.write_bytes(raw)
planet=project.parent/"web/assets/planet"
if (planet/"earth-day.webp").is_file():
    from PIL import Image
    environment=project/"Assets/Upwell/Environment"
    for filename,target,mode in (("earth-day.webp","EarthAlbedo.jpg","RGB"),("earth-night.webp","EarthNight.jpg","RGB"),("earth-cloud-density.webp","EarthWeatherClimatology.jpg","L")):
        stream=BytesIO()
        with Image.open(planet/filename) as image:image.convert(mode).save(stream,format="JPEG",quality=96,subsampling=0)
        content=stream.getvalue();d=environment/target
        if not d.exists() or d.read_bytes()!=content:d.write_bytes(content)
    for source,target in (("cloud-noise-64.rgba","CloudNoise.bytes"),("regional-sources.json","Atlantic-weather-sources.json")):
        a=planet/source;b=environment/target
        if a.exists() and (not b.exists() or not filecmp.cmp(a,b,shallow=False)):shutil.copy2(a,b)
    credit=["Earth geography and weather observations",""]
    for item in json.loads((planet/"sources.json").read_text(encoding="utf-8")):
        credit.extend([item["file"],item["url"],""])
    if (planet/"regional-sources.json").exists():
        observed=json.loads((planet/"regional-sources.json").read_text(encoding="utf-8"))
        credit.extend([observed["source"],"Atlantic cloud optical depth and cloud-top height",""])
        for key,field in observed["fields"].items():credit.extend([key,field["url"],field["sha256"],""])
    credit.append("NASA Earth Observatory and NOAA supply the geographical albedo, night lights and meteorological inputs. Cloud motion, light transport and weather structure are simulated during the ride.")
    credit.extend(["", "Stars", "Yale Bright Star Catalogue, 5th Revised Edition, D. Hoffleit and W. H. Warren Jr. (1991). J2000 coordinates, V magnitudes and B-V colours supplied by NASA HEASARC BSC5P.", "https://heasarc.gsfc.nasa.gov/W3Browse/all/bsc5p.html"])
    credit.extend(["", "Integrated Galactic light", "Blue and red Pioneer 10/11 Imaging Photopolarimeter sky coadds from Karl D. Gordon, Adolf N. Witt and Richard C. Friedmann (1998).", "https://karllark.github.io/data_pioneer10_11_ipp.html"])
    b=environment/"Earth-data-credits.txt";content=("\n".join(credit)+"\n").encode("utf-8")
    if not b.exists() or b.read_bytes()!=content:b.write_bytes(content)
    regional=planet/"atlantic-weather.png"
    if regional.is_file():
        destination=environment/"AtlanticWeather.png"
        if not destination.exists() or not filecmp.cmp(regional,destination,shallow=False):shutil.copy2(regional,destination)
shared_finish=project.parent/"web/assets/finish"
if (shared_finish/"cameras.json").is_file():
    data=json.loads((shared_finish/"cameras.json").read_text(encoding="utf-8"))
    lookup=data.get("rooms",data.get("cameras",data))
    if isinstance(lookup,list): lookup={r.get("room",r.get("id")):r for r in lookup}
    destination=project/"Assets/Upwell/Finish";destination.mkdir(exist_ok=True)
    out["cameras"]=[]
    for room in ("observation","berth","service"):
        m=lookup[room]["viewProjection"]
        if len(m)==4 and isinstance(m[0],list):m=sum(m,[])
        assert len(m)==16
        out["cameras"].append({"room":room,"viewProjection":m})
        for kind in ("detail","depth"):
            f=shared_finish/f"{room}-{kind}.png";d=destination/f.name
            if not d.exists() or not filecmp.cmp(f,d,shallow=False):shutil.copy2(f,d)
assert len(parts)>=27 and len({(p["room"],p["id"]) for p in parts})==len(parts)
assert set(props).issubset({p["id"] for p in parts})
for p in parts: assert (models/p["file"]).stat().st_size>1000, p["file"]
(models/"UnityLayout.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
