"""Synthesize the local structure-borne sounds of the guide and collar."""
from array import array
from pathlib import Path
import math
import random
import shutil
import wave

ROOT = Path(__file__).resolve().parents[1]
UNITY = ROOT / "unity/Assets/Upwell/Resources/Docking"
WEB = ROOT / "web/assets/audio"
RATE = 32000
TAU = 2 * math.pi


def strike(samples, at, gain, modes, noise, decay, rng):
    """One contact initiates several body modes and a short broadband edge."""
    start = round(at * RATE)
    previous = 0
    for n in range(min(len(samples) - start, round(max(m[2] for m in modes) * 5 * RATE))):
        t = n / RATE
        previous += min(1, TAU * 1950 / RATE) * (rng.uniform(-1, 1) - previous)
        signal = previous * noise * math.exp(-t / decay)
        for hz, strength, life in modes:
            signal += strength * math.sin(TAU * hz * t) * math.exp(-t / life)
        samples[start + n] += gain * signal * min(t / .001, 1)


def make(name, length, hits, scrape=None):
    rng = random.Random(name)
    values = [0.] * round(length * RATE)
    for time, gain, modes, edge, decay in hits:
        strike(values, time, gain, modes, edge, decay, rng)
    if scrape:
        start, end, gain, band = scrape
        low = slow = 0.
        for i in range(round(start * RATE), round(end * RATE)):
            u = (i / RATE - start) / (end - start)
            low += .15 * (rng.uniform(-1, 1) - low)
            slow += .028 * (low - slow)
            texture = .68 + .32 * math.sin(TAU * (6.2 * u + .9 * u * u))
            values[i] += gain * math.sin(math.pi * u) ** 1.3 * texture * (low - slow + .085 * math.sin(TAU * band * i / RATE))
    peak = max(max(abs(q) for q in values), 1.)
    data = array("h", (round(.80 * 32767 * v / peak) for v in values))
    UNITY.mkdir(parents=True, exist_ok=True)
    destination = UNITY / (name + ".wav")
    with wave.open(str(destination), "wb") as sound:
        sound.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        sound.writeframes(data.tobytes())
    shutil.copyfile(destination, WEB / destination.name)


seat = [(81,.55,.13), (193,.28,.064), (356,.13,.047)]
pawl = [(214,.29,.051), (894,.25,.035), (1810,.14,.014)]
bearing = [(75,.39,.085), (161,.33,.052), (306,.15,.037), (696,.12,.019)]
make("GuideJoint", .30, [(0,.68,bearing,.26,.016),(.027,.27,bearing,.16,.011)])
make("CenterJaws", .57, [(0,.44,pawl,.45,.013),(.115,.35,pawl,.32,.010),(.274,.72,bearing,.33,.025)], (.045,.26,.33,114))
make("DrawCollar", .70, [(0,.33,pawl,.40,.01),(.38,.69,seat,.28,.021),(.416,.28,pawl,.22,.009)], (.04,.40,.54,89))
make("LockCollar", .69, [(0,.36,pawl,.4,.014),(.157,.41,pawl,.33,.013),(.201,.84,seat,.42,.018)], (.048,.175,.37,135))
make("SleeveContact", .79, [(0,.70,seat,.26,.032),(.053,.32,bearing,.21,.014)], (.012,.27,.46,59))
make("VesselImpact", .49, [(0,.76,[(418,.32,.092),(1081,.36,.062),(1422,.17,.036)],.44,.013)])
make("OpticsImpact", .32, [(0,.66,[(136,.40,.043),(327,.27,.050),(671,.11,.023)],.49,.019),
                            (.024,.26,pawl,.20,.009)])
make("FolioImpact", .26, [(0,.86,[(109,.35,.035),(236,.19,.025)],.64,.037)], (.008,.13,.22,164))
make("KeycardImpact", .23, [(0,.62,[(618,.32,.026),(1191,.26,.020)],.35,.010),(.043,.21,pawl,.18,.008)])
make("WalletImpact", .39, [(0,.86,[(91,.38,.042),(150,.18,.036)],.54,.023),(.031,.22,pawl,.18,.012)])
