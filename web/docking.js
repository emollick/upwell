import * as T from 'three';
import { GLTFLoader } from './assets/vendor/loaders/GLTFLoader.js';

// Travel of the screw followers at the handwheel's four indexed positions.
// The last part of the stroke compresses the seal and starts the sleeve drive.
const followerStops = [0, 6 / 18, 13.5 / 18, 1];
const move = (value, target, step) => value + Math.sign(target - value) * Math.min(Math.abs(target - value), step);

export class CaptureCollar {
  constructor() {
    this.travel = 0;
    this.sleeve = 0;
  }
  update(turns, docked, dt, discontinuity) {
    const target = docked ? followerStops[turns] || 0 : 0;
    if (!docked || discontinuity) {
      this.travel = target;
      this.sleeve = target === 1 ? 1 : 0;
      return;
    }
    // A quick series of wheel inputs still has to wind the draw screw before
    // the passenger bridge can move. Integrate the crossing within this frame.
    const timeToSeat = Math.max(0, 1 - this.travel) / 1.55;
    this.travel = move(this.travel, target, dt * 1.55);
    if (this.travel === 1) this.sleeve = Math.min(1, this.sleeve + Math.max(0, dt - timeToSeat) / 1.68);
  }
  get bridgeClearance() {
    const t = this.sleeve;
    return 1 - t * t * (3 - 2 * t);
  }
  get status() {
    if (this.sleeve >= 1) return 'Transfer ready';
    if (this.travel === 1) return 'Sleeve extending';
    if (this.travel >= .73) return 'Collar drawn in';
    if (this.travel >= .32) return 'Jaws centered';
    return 'Soft capture';
  }
}

export async function fitClampGauge(world) {
  const {scene} = await new GLTFLoader().loadAsync('./assets/docking/ClampIndicator.glb');
  const pointer = scene.getObjectByName('clamp_gauge_needle');
  if (!pointer) throw Error('The clamp travel indicator is missing its pointer.');
  scene.name = 'Collar travel indicator';
  scene.position.set(0, 1.27, 5.346);
  scene.traverse(part => {
    if (!part.isMesh) return;
    part.castShadow = true;
    part.receiveShadow = true;
    part.userData.fitting = 'docking_wheel';
    world.hull.push(part);
  });
  world.scene.add(scene);
  const rest = pointer.quaternion.clone();
  const axis = new T.Vector3(0, 0, 1);
  const span = 236 * Math.PI / 180;
  return {
    angle: 0,
    update(travel) {
      this.angle = travel * span;
      pointer.quaternion.setFromAxisAngle(axis, this.angle - span / 2).multiply(rest);
    }
  };
}
