"""Design a phase-continuous cabin motor and domain-specific onboard sound cues."""
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[1] / "Assets" / "Upwell" / "Audio"
SR = 22050
rng = np.random.default_rng(76)


def write(name, samples):
    wavfile.write(ROOT / (name + ".wav"), SR, (np.clip(samples, -.95, .95) * 32767).astype(np.int16))


import sys
for file in ([] if "--mechanisms-only" in sys.argv else ROOT.glob("Dispatch*.wav")):
    sr, speech = wavfile.read(file)
    if speech.dtype.kind == "f":
        continue
    speech = speech.astype(np.float64) / 32768
    speech = sosfilt(butter(3, [330, 3500], btype="bandpass", fs=sr, output="sos"), speech)
    speech = np.tanh(speech * 2.4) * .57
    t = np.arange(round(sr * .38)) / sr
    beep = .075 * np.sin(2 * np.pi * 590 * t) * np.sin(np.pi * t / .38)**10
    speech = np.concatenate((beep, np.zeros(round(sr * .13)), speech, beep * .28))
    wavfile.write(file, sr, (speech * 32767).astype(np.int16))

t = np.arange(SR * 8) / SR
noise = sosfilt(butter(2, 660, fs=SR, output="sos"), rng.normal(0, .035, len(t)))
noise *= np.clip(np.minimum(t, 8-t) / .2, 0, 1)
hum = noise + .038*np.sin(2*np.pi*47*t + .18*np.sin(2*np.pi*.25*t)) + .019*np.sin(2*np.pi*94*t)
write("Traction", hum)
vent=sosfilt(butter(3,[270,2050],fs=SR,btype="bandpass",output="sos"),rng.normal(0,.082,len(t)))
vent*=np.clip(np.minimum(t,8-t)/.13,0,1)
vent+=.021*np.sin(2*np.pi*138*t)+.012*np.sin(2*np.pi*414*t+np.sin(2*np.pi*.25*t)*.12)
write("Circulation",vent)
for name, freq, dur in [("Relay", 270, .14), ("Runner", 162, .38), ("Latch", 105, .53), ("Keyscan", 750, .23)]:
    t = np.arange(int(SR * dur)) / SR
    spring = np.sin(2*np.pi*(freq*t + .8*(1-np.exp(-10*t)))) * .19
    noise = sosfilt(butter(2, 2600, fs=SR, output="sos"), rng.normal(0, .3, len(t)))
    write(name, (spring + noise*.55) * np.exp(-t * (6/dur)) * np.minimum(t/.002, 1))
for name, mass in [("PassengerPass",1.0),("FreightPass",1.35)]:
    t=np.arange(int(SR*2.4))/SR
    envelope=np.clip(np.sin(np.pi*t/2.4),0,1)**2.4
    frequency=86-40/(1+np.exp(-(t-1.04)*8))
    phase=np.cumsum(frequency)/SR*2*np.pi
    bearings=np.sin(phase*mass)*.079+np.sin(phase*2)*.044+np.sin(phase*.53)*.055
    transferred=sosfilt(butter(3,390,fs=SR,output="sos"),rng.normal(0,.19,len(t)))
    pulse=np.exp(-((t-.73)/.13)**2)+.68*np.exp(-((t-1.39)/.17)**2)
    write(name,(bearings+transferred)*envelope*(.75+pulse*.38)*mass)
