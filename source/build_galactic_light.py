"""Sample the Pioneer 10/11 IPP straight coadds at one degree per texel."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://www.stsci.edu/~kgordon/pioneer_ipp/"
HASHES = {
    "B": "9e0f68b4780f38d16cedd91d6405d3e675cab0a2362680125b9a04ed89025ea4",
    "R": "f8fa52e34d2a491035cc45375590ff09cbdb9ad241e194cccae3dd084a115af2",
}


def band_samples(band):
    name = f"P_all_1_{band}.fits"
    path = ROOT / "source/.export-cache" / name
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        with urlopen(SOURCE + name, timeout=30) as response:
            path.write_bytes(response.read())
    data = path.read_bytes()
    if sha256(data).hexdigest() != HASHES[band]:
        raise ValueError(f"Check the dimensions, units and WCS of the revised {name}")
    end = next(i for i in range(0, len(data), 80) if data[i:i+8] == b"END     ")
    offset = (end + 80 + 2879) // 2880 * 2880
    flux = np.frombuffer(data, dtype=">f4", offset=offset, count=1440*720).reshape(720, 1440)
    # No observation is coded as zero. In the uncovered high-latitude wedge,
    # use the median at that Galactic latitude. Preserve nearby observed
    # structure across its boundary without adding unmeasured small features.
    valid = flux > 0
    profile = np.array([np.median(row[row > 0]) if np.any(row > 0) else np.nan for row in flux])
    observed = np.flatnonzero(np.isfinite(profile))
    profile = np.interp(np.arange(720), observed, profile[observed])[:, None]
    mode = ("nearest", "wrap")
    weight = gaussian_filter(valid.astype("f4"), 12, mode=mode)
    near = gaussian_filter(flux, 12, mode=mode)
    fill = near + (1 - weight) * profile
    flux = gaussian_filter(np.where(valid, flux, fill), 1.3, mode=mode)
    # FITS pixel (720,360) is l=180, b=0. The texture's lower left texel
    # centre is l=0.5, b=-89.5. The sampling below includes the FITS 1-origin.
    return flux[1::4, 1::4]


def build():
    pixels = np.zeros((180, 360, 4), dtype="u1")
    for channel, (band, scale) in enumerate((("B", 768), ("R", 1536))):
        flux = band_samples(band)
        assert flux.shape == (180, 360) and np.all(np.isfinite(flux))
        pixels[:, :, channel] = np.rint(255 * np.sqrt(np.clip(flux / scale, 0, 1)))
    pixels[:, :, 3] = 255
    data = pixels.tobytes()
    for path in ("web/assets/planet/galactic-light.rgba", "unity/Assets/Upwell/Resources/GalacticLight.bytes"):
        (ROOT / path).write_bytes(data)
    print(f"360 × 180 Galactic sky, two photometric bands, {len(data)} bytes, {sha256(data).hexdigest()}")


if __name__ == "__main__":
    build()
