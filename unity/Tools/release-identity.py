"""Tie the native archive and static files to their observed test receipts."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import json

project=Path(__file__).resolve().parents[1]
web=project.parent/"web/unity"
proof=project/"Verification"
archive=project/"Upwell-Windows.zip"
assembly=Path("Upwell_Data/Managed/Assembly-CSharp.dll")
with ZipFile(archive) as player:
    assert player.testzip() is None
    assert player.read(assembly.as_posix())==(project/"Build"/assembly).read_bytes()
    assert "Licenses/Geist.txt" in player.namelist()
files=[("windows",archive),*((f.relative_to(web).as_posix(),f) for f in sorted(web.rglob("*")) if f.is_file())]
ids={label:{"bytes":f.stat().st_size,"sha256":sha256(f.read_bytes()).hexdigest()} for label,f in files}
tests=json.loads((proof/"webgl-brotli.json").read_text())
data=ids["Build/unity.data.unityweb"]
assert tests["compressedBytes"]==data["bytes"] and tests["compressedSHA256"]==data["sha256"]
for name in ("native-checks.json","native-input-checks.json","graphics/native-persistence.json","graphics/native-software.json","fracture/native-fracture.json","gravity-windows.json"):
    assert json.loads((proof/name).read_text())["passed"],name
tour=json.loads((proof/"gravity-webgl.json").read_text())["tour"]
assert tour["freeBeforePush"]==0 and tour["freeHeight"]>2.27 and tour["explicitWindowAfterDock"]==1
touch=json.loads((proof/"gravity-touch.json").read_text())["beforePush"]
assert touch["seconds"]==360 and touch["view"]==0 and touch["drifting"] and touch["eye"]["y"]>2.27
browser=json.loads((proof/"webgl-checks.json").read_text())
assert not browser["consoleErrors"] and not browser["software"]["consoleErrors"]
bench=json.loads((proof/"fracture/web-fracture.json").read_text())
assert bench["coast"]["moving"]>=3 and bench["settled"]["escape"]<.0015
assert bench["delivered"].endswith(".data.unityweb") and bench["quiet"]["contacts"]==bench["resting"]["contacts"] and bench["quiet"]["moving"]==0
output=proof/"graphics/release-hashes.json"
output.write_text(json.dumps(ids,indent=2)+"\n",encoding="utf-8")
print(json.dumps(ids,indent=2));print("Total static bytes:",sum(v["bytes"] for k,v in ids.items() if k!="windows"))
