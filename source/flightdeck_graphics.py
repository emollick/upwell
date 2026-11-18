"""Baked legends and powered-up standby artwork for the packed Blender carriage."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'unity/Assets/Upwell/SourceModels/Textures'


def font(size):
    for name in ('bahnschrift.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


legends = ['GUIDE', 'CABIN', 'FILM', 'VENT', 'RTE', 'CAM', 'SEAL', 'LOAD', 'TRAF', 'CREW',
           'TEST', 'GAIN', 'LENS', '28 V', 'FIBER', 'SEALS', 'RETURN', 'BERTH', 'BAY LIGHT', 'COMMS',
           'ILLUMINATION', 'FLIGHT COMPUTER', 'OPTICS', 'IN', 'OUT']
cell_w, cell_h = 256, 64
sheet = Image.new('RGB', (cell_w * 4, cell_h * 7), (23, 32, 37))
d = ImageDraw.Draw(sheet)
rects = {}
for i, word in enumerate(legends):
    x, y = i % 4 * cell_w, i // 4 * cell_h
    size = min(51, int(365 / max(len(word), 1)))
    face = font(size)
    d.text((x + cell_w / 2, y + cell_h / 2), word, font=face, fill=(220, 223, 210), anchor='mm', stroke_width=0)
    box = d.textbbox((x + cell_w / 2, y + cell_h / 2), word, font=face, anchor='mm')
    rects[word] = [box[0] - 6, box[1] - 5, box[2] - box[0] + 12, box[3] - box[1] + 10]
sheet.save(OUT / 'Deck_Legends.png', optimize=True)
(OUT / 'deck_legends.json').write_text(json.dumps({'size': sheet.size, 'rects': rects}, indent=2))

# The drawings are also visible in offline Cycles renders, before a runtime is attached.
previews = {
    'Diagnostic': ('ENVIRONMENT', '101.3', 'kPa  |  CABIN'), 'Drive': ('TRACTION', '0.0', 'm/s  |  HOLD'),
    'Access': ('CREW ACCESS', 'PRESENT CARD', 'LOCAL CONTACT'), 'Pressure': ('SEAL DELTA', '0.02', 'kPa  |  SEALED'),
    'Berth': ('BERTH 02', '1.00 g', 'AIRFLOW  /  ON'), 'Seal': ('PRESSURE LOCK', 'SEALED', 'TAPS A + B'),
    'Intercom': ('CREW RADIO', 'RX READY', 'CHANNEL 07'), 'Service': ('INSPECTION BUS', 'STANDBY', 'SELECT A CIRCUIT'),
    'Folio': ('WATCH LOG   /   07', '04:12', 'ANCHOR  |  GROUND'), 'Vessel': ('VALVE', 'SEALED', 'CAR 07'),
    'Optic': ('OPTICS', '1.0 x', 'STABILIZED'),
}
for name, (heading, value, foot) in previews.items():
    board = Image.new('RGB', (384, 232), (6, 20, 24))
    p = ImageDraw.Draw(board)
    p.text((18, 14), heading, font=font(24), fill=(151, 197, 194))
    p.line((17, 54, 366, 54), fill=(66, 107, 106), width=2)
    p.text((16, 81), value, font=font(min(68, 540 // len(value))), fill=(235, 240, 221))
    p.text((18, 174), foot, font=font(23), fill=(224, 176, 111))
    board.save(OUT / ('Standby_' + name + '.png'), optimize=True)

# Preserve the instrument maker's original instrument artwork, including the six
# signed flight-log entries. The runtime adds live measurements over that paper trail.
hand_tiles = json.loads((OUT / 'handheld_atlas.json').read_text())['rects']
with Image.open(OUT / 'Handheld_Atlas.jpg') as atlas:
    for name, key in [('Folio', 'log_display'), ('Vessel', 'cup_lcd'), ('Optic', 'optic_lcd')]:
        x, y, w, h = hand_tiles[key]
        atlas.crop((x, y, x + w, y + h)).save(OUT / ('Standby_' + name + '.png'), optimize=True)
