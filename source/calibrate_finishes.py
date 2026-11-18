"""Register the three image-directed material studies to the original Cycles cameras.

The outputs are bounded, neutral-centered differences in the surface finish.
They do not contain a baked window view or replace the lighting calculation.
Requires OpenCV, NumPy and Pillow.
"""
from pathlib import Path
import json

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / "art" / "matched"
OUTPUT = ROOT / "web" / "assets" / "finish"
OUTPUT.mkdir(parents=True, exist_ok=True)


def linear_rgb(image):
    srgb = np.asarray(image, dtype=np.float32) / 255
    return np.where(srgb < .04045, srgb / 12.92, ((srgb + .055) / 1.055) ** 2.4)


def gray_features(image):
    lum = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    return cv2.createCLAHE(clipLimit=2.5, tileGridSize=(12, 12)).apply(lum)


def blur(image, radius):
    return cv2.GaussianBlur(image, (0, 0), radius)


def calibrate(room):
    source = Image.open(ROOT / "blender" / f"{room}.jpg").convert("RGB")
    study = Image.open(MATCH / f"{room}.jpg").convert("RGB").resize(source.size, Image.Resampling.LANCZOS)
    a, b = gray_features(source), gray_features(study)
    solver = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    solver.setFinestScale(0)
    flow = solver.calc(a, b, None)
    h, w = a.shape
    x, y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    registered = cv2.remap(np.asarray(study), x + flow[:, :, 0], y + flow[:, :, 1],
                           cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    base, enriched = linear_rgb(source), linear_rgb(registered)
    raw = np.log2((enriched + .026) / (base + .026))
    medium, broad, field = blur(raw, 3.5), blur(raw, 38), blur(raw, 140)
    # The short/fine bands retain seams, material fibers and fabrication traces.
    # Remove most of the image-wide illumination difference for relighting.
    signal = .94*(raw-medium) + .79*(medium-broad) + .42*(broad-field) + .19*field
    # Downweight high-contrast source silhouettes where subpixel registration is ambiguous.
    edge = np.hypot(cv2.Sobel(a, cv2.CV_32F, 1, 0), cv2.Sobel(a, cv2.CV_32F, 0, 1))
    confidence = 1-.36*np.clip((edge-105)/240, 0, 1)
    signal *= confidence[:, :, None]
    encoded = np.round(128 + 82*np.clip(signal, -1.12, 1.12)).astype(np.uint8)
    Image.fromarray(encoded).save(OUTPUT / f"{room}-detail.png", optimize=True)
    print(room, source.size, "median registration (pixels)", np.round(np.median(flow, axis=(0, 1)), 2))


if __name__ == "__main__":
    for room_name in ("observation", "berth", "service"):
        calibrate(room_name)
    with (MATCH / "cameras.json").open(encoding="utf8") as source:
        survey = json.load(source)["rooms"]
    cameras = {}
    for room_name, values in survey.items():
        z = np.asarray(Image.open(MATCH / values["depthFile"]), dtype=np.uint16)
        channels = np.stack((z // 256, z % 256, np.zeros_like(z)), axis=-1).astype(np.uint8)
        Image.fromarray(channels).save(OUTPUT / f"{room_name}-depth.png", optimize=True)
        rows = np.asarray(values["viewProjectionRows"], dtype=float).reshape(-1).tolist()
        cameras[room_name] = {"viewProjection": rows, "eyeWeb": values["eyeWeb"]}
    with (OUTPUT / "cameras.json").open("w", encoding="utf8") as out:
        json.dump(cameras, out, indent=2)
