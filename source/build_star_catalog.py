"""Pack measured J2000 stars into cubeface bins for the two full-resolution sky shaders."""
from collections import defaultdict
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://heasarc.gsfc.nasa.gov/FTP/heasarc/dbase/tdat_files/heasarc_bsc5p.tdat.gz"
ORIGINAL = "122628cde2d8bedf7e16ddf5f888167ac58c04b5592d6155408ce297f3073931"
SIZE, MARGIN, SLOTS = 64, 0.30, 16


def encode():
    cached = ROOT / "source/.export-cache/heasarc_bsc5p.tdat.gz"
    if not cached.exists():
        cached.parent.mkdir(exist_ok=True)
        with urlopen(SOURCE, timeout=45) as response:
            cached.write_bytes(response.read())
    packet = cached.read_bytes()
    if sha256(packet).hexdigest() != ORIGINAL:
        raise ValueError("The source catalogue has changed. Verify the schema and epoch before repacking.")
    table = gzip.decompress(packet).decode("ascii")
    names = next(s.split("=")[1].split() for s in table.splitlines() if s.startswith("line[1]"))
    bins = defaultdict(list)
    stars = 0
    for line in table.split("<DATA>\n")[1].split("<END>")[0].splitlines():
        row = dict(zip(names, line.split("|")))
        if not all(row[k] for k in ("ra", "dec", "vmag")):
            continue
        magnitude = float(row["vmag"])
        if magnitude > 6.5:
            continue
        stars += 1
        bv = float(row["bv_color"]) if row["bv_color"] else .65
        ra, dec = (math.radians(float(row[k])) for k in ("ra", "dec"))
        x, y, z = math.cos(dec)*math.cos(ra), math.cos(dec)*math.sin(ra), math.sin(dec)
        flux = 1 + round((magnitude+1.5)/8*254)
        colour = round(max(0, min(1, (bv+.4)/2.6))*255)
        # Halos overlap bin and cubeface edges. Replicate the source centre in each
        # touched tile so looking across a seam still yields the same integrated light.
        for face, (major, u, v) in enumerate(((x,y,z),(-x,y,z),(y,z,x),(-y,z,x),(z,x,y),(-z,x,y))):
            if major <= 0 or max(abs(u), abs(v)) > major*(1+2*MARGIN/SIZE):
                continue
            gx, gy = (u/major+1)*SIZE/2, (v/major+1)*SIZE/2
            for iy in range(max(0, math.floor(gy-MARGIN)), min(SIZE, math.floor(gy+MARGIN)+1)):
                for ix in range(max(0, math.floor(gx-MARGIN)), min(SIZE, math.floor(gx+MARGIN)+1)):
                    offset = lambda value, tile: round((value-tile+MARGIN)/(1+2*MARGIN)*255)
                    bins[face, ix, iy].append(bytes((offset(gx, ix),offset(gy, iy),flux,colour)))
    assert stars == 8404 and max(map(len, bins.values())) <= SLOTS
    records = bytearray()
    for (face, ix, iy), group in sorted(bins.items()):
        group.sort(key=lambda item: item[2])
        records.extend(struct.pack("<HB", (face*SIZE+iy)*SIZE+ix, len(group)))
        records.extend(b"".join(group))
    output = struct.pack("<4sBBHHH", b"YST1", SIZE, SLOTS, stars, len(bins), 0) + records
    for destination in (ROOT/"web/assets/planet/bright-stars.bin", ROOT/"unity/Assets/Upwell/Resources/BrightStars.bytes"):
        destination.write_bytes(output)
    print(json.dumps(dict(stars=stars, bins=len(bins), maxPerTile=max(map(len,bins.values())),
                          bytes=len(output), sha256=sha256(output).hexdigest())))


if __name__ == "__main__":
    encode()
