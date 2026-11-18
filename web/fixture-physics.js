// Distances in metres, time in passenger seconds. The accelerometer measures
// signed force along the carriage axis. The liquid chamber is vertical; its
// two in-plane axes are supplied by the Blender survey.
const G = 9.80665;
const limit = (x, a, b) => Math.max(a, Math.min(b, x));
const WATER_DENSITY = 997;
const SURFACE_TENSION = .072;
const SLICES = 9;

// Area shared by a unit disk and a disk of radius r a distance d away.
// An intersection near the rim represents a high-g gas cap; a disk entirely
// inside the vessel represents the contained low-g bubble.
export function sharedArea(d, r) {
  if (d >= 1 + r) return 0;
  if (d <= Math.abs(1 - r)) return Math.PI * Math.min(1, r * r);
  const a = limit((d * d + 1 - r * r) / (2 * d), -1, 1);
  const b = limit((d * d + r * r - 1) / (2 * d * r), -1, 1);
  const triangle = (-d + 1 + r) * (d + 1 - r) * (d - 1 + r) * (d + 1 + r);
  return Math.acos(a) + r * r * Math.acos(b) - .5 * Math.sqrt(Math.max(0, triangle));
}

function radiusForArea(d, fraction) {
  if (d + Math.sqrt(fraction) <= 1) return Math.sqrt(fraction);
  let low = Math.max(0, d - 1), high = d + 1;
  for (let i = 0; i < 25; i++) {
    const r = (low + high) * .5;
    if (sharedArea(d, r) < Math.PI * fraction) low = r;
    else high = r;
  }
  return (low + high) * .5;
}

// Exact underdamped response to a constant force during a time step. It
// behaves identically under ordinary frame rates and occasional slow frames.
export class Oscillator {
  constructor() { this.x = 0; this.v = 0; }
  reset(x = 0) { this.x = x; this.v = 0; }
  advance(target, frequency, damping, dt) {
    const decay = damping * frequency;
    const w = frequency * Math.sqrt(1 - damping * damping);
    const e = Math.exp(-decay * dt), cosine = Math.cos(w * dt), sine = Math.sin(w * dt);
    const offset = this.x - target, v = this.v;
    this.x = target + e * (offset * cosine + (v + decay * offset) * sine / w);
    this.v = e * (v * cosine - (frequency * frequency * offset + decay * v) * sine / w);
  }
  stops(low, high) {
    if (this.x < low || this.x > high) {
      this.x = limit(this.x, low, high);
      this.v *= -.08;
    }
  }
}

export class FixturePhysics {
  constructor({radius = .102, depth = .022, gasFraction = .23, metersPerG = .162} = {}) {
    this.radius = radius;
    this.depth = depth;
    this.gasFraction = gasFraction;
    this.coreRadius = 1 - .00025 / radius;
    this.coreDepth = 1 - 2 * .00016 / depth;
    this.proofFrequency = Math.sqrt(G / metersPerG);
    this.proof = new Oscillator();
    this.plunger = new Oscillator();
    this.primer = new Oscillator();
    this.right = new Oscillator();
    this.up = new Oscillator();
    this.wave = new Oscillator();
    this.radii = new Float32Array(SLICES);
    const profile = Array.from({length:SLICES}, (_, i) => {
      const z = 2 * i / (SLICES - 1) - 1;
      const shoulder=Math.min(.30,.82*depth/(2*radius*Math.sqrt(gasFraction)));
      const radiusRatio=1-shoulder*(1-Math.sqrt(Math.max(0,1-z*z)));
      return radiusRatio*radiusRatio;
    });
    const mean = profile.reduce((a, p, i) => a + p * (i === 0 || i === SLICES - 1 ? .5 : 1), 0) / (SLICES - 1);
    const fraction = gasFraction / (this.coreRadius ** 2 * this.coreDepth);
    this.sliceFractions = profile.map(p => fraction * p / mean);
    this.testHeld = false; this.pumpHeld = false;
    this.testTime = 0;
    this.pumpTime = 0;
    this.distance = -1;
    this.ready = false;
  }
  test() { this.testTime = .38; }
  pump() {
    // One mechanical stroke gives the closed circuit a tangential impulse.
    // The spring must return before it can deliver another full stroke.
    if (this.pumpTime > 0 || this.primer.x > .56) return false;
    this.pumpTime = .19;
    this.wave.v = limit(this.wave.v + 1.40, -1.8, 1.8);
    return true;
  }
  update(dt, signedVerticalG, buoyantRight, buoyantUp, cut = false) {
    dt = limit(dt, 0, .25);
    if (!this.ready || cut) {
      this.proof.reset(signedVerticalG); this.right.reset(buoyantRight); this.up.reset(buoyantUp);
      this.wave.reset(); this.plunger.reset(); this.primer.reset();
      this.testHeld = this.pumpHeld = false; this.testTime = this.pumpTime = 0; this.ready = true;
    }
    const waveNumber = 1.84 / this.radius;
    const accel = Math.hypot(buoyantRight, buoyantUp);
    const omega = Math.sqrt(waveNumber * accel + SURFACE_TENSION / WATER_DENSITY * waveNumber ** 3 + 1.5 ** 2);
    const damping = .33 + .27 * Math.exp(-accel / .19);
    this.right.advance(buoyantRight, omega, damping, dt);
    this.up.advance(buoyantUp, omega, damping, dt);
    this.wave.advance(0, omega, damping, dt);
    this.wave.stops(-.29, .29);
    this.plunger.advance(this.testHeld || this.testTime > 0 ? 1 : 0, 32, .76, dt);
    this.primer.advance(this.pumpHeld || this.pumpTime > 0 ? 1 : 0, 30, .75, dt);
    this.plunger.stops(0, 1); this.primer.stops(0, 1);
    this.proof.advance(signedVerticalG + .10 * this.plunger.x, this.proofFrequency, .38, dt);
    this.proof.stops(-.18, 1.18);
    this.testTime = Math.max(0, this.testTime - dt); this.pumpTime = Math.max(0, this.pumpTime - dt);

    const length = Math.hypot(this.right.x, this.up.x);
    this.bond = WATER_DENSITY * this.radius ** 2 * length / SURFACE_TENSION;
    const reach = 28 * -Math.expm1(-this.bond / 85);
    const ca = Math.cos(this.wave.x), sa = Math.sin(this.wave.x), scale = length > 1e-9 ? reach / length : 0;
    this.cx = .08 + (ca * this.right.x - sa * this.up.x) * scale + .75 * this.wave.x;
    this.cy = .035 + (sa * this.right.x + ca * this.up.x) * scale + .16 * this.wave.x;
    const distance = Math.hypot(this.cx, this.cy);
    if (Math.abs(distance - this.distance) > 1e-6) {
      this.distance = distance;
      for (let i = 0; i < SLICES; i++) this.radii[i] = radiusForArea(distance, this.sliceFractions[i]);
    }
  }
  measuredGasFraction() {
    // Integrate the reconstructed sections, including both pane films and
    // the liquid on the rim, independently of the requested fill fraction.
    let total = 0;
    for (let i = 0; i < SLICES; i++) {
      const weight = i === 0 || i === SLICES - 1 ? .5 : 1;
      total += weight * sharedArea(this.distance, this.radii[i]);
    }
    return total * this.coreRadius ** 2 * this.coreDepth / (Math.PI * (SLICES - 1));
  }
}
