"""Package the released Unity player for itch.io's static HTML hosting."""
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PLAYER = WEB / "unity"


def package():
    destination = ROOT / "Upwell-itch-WebGL.zip"
    index = (PLAYER / "index.html").read_text(encoding="utf-8")
    files = {"Build/unity.loader.js": (PLAYER / "Build/unity.loader.js").read_bytes(),
             "assets/passage-moments.json": (WEB / "assets/passage-moments.json").read_bytes()}
    for name in ("unity.framework.js", "unity.wasm", "unity.data"):
        asset = "Build/" + name
        compressed = asset + ".unityweb"
        if compressed not in index:
            raise ValueError(f"The Unity loader no longer references {compressed}")
        # The Netlify build uses HTTP Brotli headers. A ZIP upload cannot set them.
        decoder = "process.stdout.write(require('node:zlib').brotliDecompressSync(require('node:fs').readFileSync(process.argv[1])))"
        files[asset] = run(["node", "-e", decoder, str(PLAYER / compressed)],
                           check=True, capture_output=True).stdout
        index = index.replace(compressed, asset)
    index = index.replace("../assets/passage-moments.json", "assets/passage-moments.json")
    index = index.replace('href="../"', 'href="https://upwell-tetherline.netlify.app/" target="_blank" rel="noopener"')
    files["index.html"] = index.encode("utf-8")
    for source in (PLAYER / "StreamingAssets").rglob("*"):
        if source.is_file():
            files[source.relative_to(PLAYER).as_posix()] = source.read_bytes()
    if not files["Build/unity.wasm"].startswith(b"\x00asm") or not files["Build/unity.data"].startswith(b"UnityWebData1.0\0"):
        raise ValueError("Unexpected Unity payload format")
    if max(map(len, files.values())) > 200_000_000 or sum(map(len, files.values())) > 500_000_000:
        raise ValueError("The uncompressed release exceeds the HTML upload size limit")
    with TemporaryDirectory(dir=ROOT) as workspace:
        staged = Path(workspace) / destination.name
        with ZipFile(staged, "w", compression=ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        with ZipFile(staged) as archive:
            if set(archive.namelist()) != set(files) or any(archive.read(k) != v for k, v in files.items()):
                raise ValueError("The archived files differ from the prepared Unity player")
        staged.replace(destination)
    print(f"{destination.name}: {destination.stat().st_size:,} bytes, {len(files)} files")


if __name__ == "__main__":
    package()
