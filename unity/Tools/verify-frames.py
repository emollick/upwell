"""Guard against a blank swap chain, missing camera colour input, or copied room frames."""
from pathlib import Path
from PIL import Image, ImageStat, ImageChops, ImageDraw
import json

verification = Path(__file__).resolve().parents[1] / "Verification"
report = json.loads((verification / "native-checks.json").read_text())
assert report["passed"] and report["controls"] == 50 and report["rooms"] == 3, report
for name in ("01-observation", "06-terminal", "unity-webgl"):
    image = Image.open(verification / (name + ".jpg")).convert("RGB").resize((256, 160))
    r, g, b = image.split()
    spread = ImageStat.Stat(image).stddev
    chroma = ImageStat.Stat(ImageChops.difference(r, b)).mean[0]
    assert min(spread) > 19 and chroma > 4, (name, spread, chroma)
    print(f"{name}: RGB deviation {spread[0]:.1f}, red/blue difference {chroma:.1f}")
web = json.loads((verification / "webgl-checks.json").read_text())
assert web["loaded"] and web["boarded"] and not web["consoleErrors"], web["consoleErrors"]
assert json.loads((verification/"graphics/native-persistence.json").read_text())["passed"]
assert web["graphics"]["held"]["held"] and web["graphics"]["optic"]["optical"]
assert web["graphics"]["persisted"]["edges"] == 0 and web["software"]["graphics"]["defaults"]["atmosphere"] == 0
proof = verification/"graphics"
with Image.open(proof/"web-hardware-menu.png") as on, Image.open(proof/"web-hardware-menu-aa-off.png") as off:
    w,h=on.size
    scale=max(.74,min(1.6,h/850))
    x=(w-420*scale)/2+18*scale;y=(h-402*scale)/2+11*scale
    rect=(int(x),int(y),int(x+92*scale),int(y+32*scale))
    pair=zip(on.convert("RGB").crop(rect).getdata(),off.convert("RGB").crop(rect).getdata())
    text_pixels=[max(abs(c-d) for c,d in zip(a,b)) for a,b in pair if min(a)>178 and max(a)-min(a)<23]
    assert len(text_pixels)>65 and sum(d<=2 for d in text_pixels)/len(text_pixels)>.98, ("Graphics title changed under AA",text_pixels[:30])
    print(f"HUD lettering: {sum(d<=2 for d in text_pixels)}/{len(text_pixels)} light glyph pixels agree within two color levels across scene AA.")
edge=Image.new("RGB",(960,572))
for column,level in enumerate(("low","high")):
    with Image.open(proof/f"01-cabin-aa-{level}.png") as source:
        edge.paste(source.crop((555,206,795,472)).resize((480,532),Image.Resampling.NEAREST),(column*480,40))
    ImageDraw.Draw(edge).text((column*480+12,13),("Off","FXAA")[column],fill="white")
edge.save(proof/"native-edge-crop.png")
contact=Image.new("RGB",(1000,839))
for row,room in enumerate(("observation","berth","service")):
    for column,version in enumerate(("base","registered")):
        with Image.open(verification/"finish"/f"{room}-{version}.jpg") as source:
            source.thumbnail((498,277))
            contact.paste(source,(column*500,row*280))
contact.save(verification/"finish-comparison.jpg",quality=91)
