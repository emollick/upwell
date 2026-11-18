"""Create the portable Netlify upload and verify every published byte."""
from hashlib import sha256
import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def fingerprint(path):
    return {"bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest()}


def package(root):
    web = root / "web"
    files = {p.relative_to(web).as_posix(): p for p in sorted(web.rglob("*")) if p.is_file()}
    required = {"index.html", "_headers", "unity/index.html", "unity/Build/unity.data.unityweb",
                "unity/Build/unity.loader.js", "unity/Build/unity.framework.js.unityweb", "unity/Build/unity.wasm.unityweb",
                "assets/rooms/furnishings.json", "assets/rooms/gravity-instruments.json",
                "docking.js", "assets/docking/ClampIndicator.glb", "vessel-cradle.js", "assets/docking/VesselCradle.glb", "audio.js", "cabin-light.js", "photo-journal.js", "photo-journal.css",
                "assets/finish/aperture-transfer.png", "assets/finish/berth-cover.png", "weather-density.js", "planet.js", "assets/planet/marine-organization.rgba", "assets/planet/car-sun-mask.png",
                "media/cabin-dynamics.mp4", "media/upwell-one-minute.mp4", "media/upwell-second-passage.mp4", "media/upwell-cloud-passage.mp4",
                "fracture-bench.js", "assets/fracture/cartridge.json", "assets/fracture/FractureCartridge.glb",
                "passenger-motion.js", "flight-physics.js", "loose-items.js", "in-hand.js", "car-dynamics.js",
                "habitat-members.js", "assets/orbital/members.bin", "fabric-dynamics.js", "capillary-optics.js",
                "passage-moments.js", "assets/passage-moments.json", "laminated-pane.js", "cabin-hardware.js",
                "graphics.js", "passenger-optics.js", "guideway.js", "guide-finish.js", "assets/guideway/journal-caps.glb", "instruments.js",
                "assets/orbital/AsterReach.glb", "assets/orbital/Receiver.glb", "assets/orbital/CounterCar.glb"}
    required.update(("harbor.js", "harbor-water.js", "assets/orbital/CounterFleet.glb", "stellar-sky.js", "assets/planet/bright-stars.bin", "assets/planet/galactic-light.rgba"))
    required.add("assets/orbital/finishes.json")
    required.update("assets/harbor/"+name+".glb" for name in ("tug", "supply", "pilot", "buoy", "line_berth", "offshore_depot"))
    required.update("assets/audio/"+name+".wav" for name in (
        "CenterJaws", "DrawCollar", "LockCollar", "SleeveContact", "GuideJoint",
        "VesselImpact", "FolioImpact", "KeycardImpact", "OpticsImpact", "WalletImpact"))
    if not required.issubset(files) or any(files[name].stat().st_size == 0 for name in required):
        raise ValueError("The browser or Unity WebGL build is incomplete")
    headers = files["_headers"].read_text(encoding="utf-8").split("\n\n")
    for name, path in files.items():
        if name.endswith(".unityweb"):
            with path.open("rb") as packet:
                magic = packet.read(2)
            encoding = "gzip" if magic == b"\x1f\x8b" else "br"
            rule = next((part for part in headers if part.strip().startswith("/" + name + "\n")), "")
            if len(magic) != 2 or ("Content-Encoding: " + encoding) not in rule:
                raise ValueError("Unity payload and hosting headers disagree for " + name)

    staged = root / "source/.export-cache/netlify-release.zip"
    staged.parent.mkdir(exist_ok=True)
    with ZipFile(staged, "w", compression=ZIP_DEFLATED, compresslevel=6) as target:
        for name, source in files.items():
            target.write(source, name)
    with ZipFile(staged) as archive:
        if set(archive.namelist()) != set(files):
            raise ValueError("Archive contents differ from the publish directory")
        for name, source in files.items():
            if sha256(archive.read(name)).digest() != sha256(source.read_bytes()).digest():
                raise ValueError("Archive verification failed for " + name)
    destination = root / "Upwell-Netlify.zip"
    os.replace(staged, destination)
    report = {
        "netlifyTreeFiles": len(files),
        "netlifyArchive": fingerprint(destination),
        "nativeArchive": fingerprint(root / "unity/Upwell-Windows.zip"),
        "blender": fingerprint(root / "blender/Upwell.blend"),
        "orbitalBlender": fingerprint(root / "blender/orbital/OrbitalHardware.blend"),
        "counterFleetBlender": fingerprint(root / "blender/orbital/CounterFleet.blend"),
        "fractureBlender": fingerprint(root / "blender/equipment/fracture/FractureCartridge.blend"),
        "clampBlender": fingerprint(root / "blender/equipment/docking/ClampIndicator.blend"),
        "cradleBlender": fingerprint(root / "blender/equipment/docking/VesselCradle.blend"),
        "harborBlender": {p.name: fingerprint(p) for p in sorted((root / "blender/harbor").glob("*.blend"))},
        "passageMoments": {"count": len(json.loads(files["assets/passage-moments.json"].read_text(encoding="utf-8"))["moments"]),
                           "sha256": fingerprint(files["assets/passage-moments.json"])["sha256"]},
    }
    receipt = root / "qa/release.json"
    if receipt.is_file():
        previous = json.loads(receipt.read_text(encoding="utf-8-sig"))
        if all(previous.get(key) == value for key, value in report.items()):
            report = {**previous, **report}
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Verified all {len(files)} files in {destination.name}")


if __name__ == "__main__":
    package(Path(__file__).resolve().parents[1])
