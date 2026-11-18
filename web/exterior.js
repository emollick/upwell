import * as T from 'three';
import { createPlanetSky } from './planet.js';
import { loadTerminals } from './terminals.js';
import { createAnchorSea } from './anchor-sea.js';
import { loadHarbor,harborSeconds } from './harbor.js';
import { loadGuideway } from './guideway.js';
import { loadOrbitalHardware } from './orbital-hardware.js';
import { clamp, smooth, TRAFFIC } from './journey.js';

const vec = (x, y, z) => new T.Vector3(x, y, z);
export class Exterior {
  constructor(renderer,scene) {
    this.renderer=renderer;this.scene=scene;this.root=new T.Group();this.root.name="Exterior guideway and terminals";scene.add(this.root);
  }
  async init() {
    const [planet,terminals,guideway]=await Promise.all([
      createPlanetSky(),loadTerminals(this.root),loadGuideway(this.root)
    ]);
    const [orbital,harbor]=await Promise.all([loadOrbitalHardware(terminals,TRAFFIC),loadHarbor(terminals.bays.anchor.root)]);
    this.planet = planet;
    this.root.add(planet.mesh);
    this.terminals=terminals;this.guideway=guideway;
    this.harbor=harbor;this.sea=createAnchorSea(harbor.water);this.root.add(this.sea.mesh);
    this.orbital=orbital;this.other=orbital.other;this.freight=orbital.freight;this.plate=orbital.plate;
    this.hab=orbital.habitat;this.rotor=orbital.rotor;this.root.add(this.other,this.hab);
    this.cams = [
      new T.PerspectiveCamera(54, 2.1, 0.08, 1200),
      new T.PerspectiveCamera(68, 2.1, 0.035, 1200),
      new T.PerspectiveCamera(42, 2.1, 0.1, 1200),
    ];
    this.cams[0].position.set(0.2, 2.15, -5.9);
    this.cams[0].lookAt(-2.5, 1.4, -27);
    this.cams[1].position.set(-2.50,.77,4.45);
    this.cams[1].lookAt(-3.38,1.57,3.06);
    this.cams[2].position.set(-2.22, 2.82, -5.71);
    // The passenger gimbal has its own zoom drive. The flight deck's
    // three sensor heads keep the field selected on the physical encoder.
    this.counterCamera=this.cams[2].clone();this.counterCamera.layers.set(1);
    this.root.traverse(n=>{n.layers.set(1);if(!n.isMesh||n===this.planet.mesh||n===this.sea.mesh)return;
      if(n.material?.isMeshStandardMaterial&&!n.material.transparent){n.castShadow=true;n.receiveShadow=true;}});
    this.cams.forEach(c=>c.layers.set(1));
    this.nadir=new T.PerspectiveCamera(52,1,.08,8000);this.nadir.layers.set(1);
    this.nadir.position.set(3.45,-.38,1.9);this.nadir.up.set(0,1,0);
    this.viewCamera=new T.PerspectiveCamera(55,1,.06,8000);this.viewCamera.layers.set(1);
  }
  update(s, m, time, dt=0, eyeSeconds=dt) {
    this.planet.update(s, m, time,this.beam??1,eyeSeconds);
    const dip = Math.acos(6371 / (6371 + m.km));
    const cameraDip = Math.min(1.55, dip + 0.13 + 0.45 * smooth(0.52, 0.9, s.progress));
    this.cams[0].lookAt(-0.42, 2.15 - 15 * Math.sin(cameraDip), -5.9 - 15 * Math.cos(cameraDip));
    const seaTime=harborSeconds(m);this.harbor.update(m,seaTime);
    this.sea.update(m,seaTime,m.sunVisible*(this.beam??1));
    this.terminals.update(m,time,s.clamp);
    const isLaunch=1-smooth(47,85,m.seconds),nadirTilt=.37+.95*smooth(5,630,m.km)+.21*smooth(800,14500,m.km);
    this.nadir.position.set(3.45,-.38,1.9);this.nadir.up.set(0,1,0);
    const oceanRay=vec(-3.2,-Math.min(1100,7+m.km*1000),-10).normalize();
    const earthRay=vec(.80*Math.cos(nadirTilt),-Math.sin(nadirTilt),.60*Math.cos(nadirTilt));
    earthRay.lerp(oceanRay,isLaunch).normalize();this.nadir.lookAt(earthRay.add(this.nadir.position));
    const earthRadius=Math.asin(6371/(6371+m.km))*180/Math.PI;
    const harborView=1-smooth(.43,1.5,m.km);
    this.nadir.fov=Math.min(60,Math.max(24,earthRadius*2.95));
    if(harborView>0){
      // Pan from the fender line to the outer roadstead as it clears the keel.
      // The gimbal and focal program stay in the car as the real dock falls away.
      const clear=smooth(8,105,m.km*1000);
      const bearing=vec(23-14*clear,-7-m.km*1000+3*clear,-24-57*clear).sub(this.nadir.position).normalize();
      const program=vec(0,0,-1).applyQuaternion(this.nadir.quaternion);
      const emerged=smooth(5.5,18,m.km*1000),well=vec(0,-7-m.km*1000,-3.2).sub(this.nadir.position).normalize();
      bearing.copy(well.lerp(bearing,emerged).normalize());
      this.nadir.lookAt(program.lerp(bearing,harborView).normalize().add(this.nadir.position));
      this.nadir.fov=T.MathUtils.lerp(this.nadir.fov,49+4*clear,harborView);
    }
    this.nadir.updateProjectionMatrix();
    this.guideway.update(m,time);
    const contact=m.traffic;
    this.other.visible=contact.inRange;
    // Mount the four 269 mm tyres tangent to the two surveyed guide rails.
    this.other.position.set(this.guideway.counter.x+1.671,1.52+contact.separation,this.guideway.counter.z+.015);
    this.orbital.update(m,time,contact);
    const head=this.cams[2],acquisition=this.counterCamera,range=head.position.distanceTo(this.other.position);
    head.lookAt(this.other.position.x+.50,this.other.position.y+.19,this.other.position.z);
    acquisition.quaternion.copy(head.quaternion);
    const trafficFov=clamp(2*Math.atan(7.4/range)*180/Math.PI,14,44);
    if(Math.abs(trafficFov-acquisition.fov)>.03){acquisition.fov=trafficFov;acquisition.updateProjectionMatrix();}
    this.hab.visible = m.km>9000;
    // The terminal is attached to the tether. Its rotating cylinder stays at
    // a fixed scale as the passenger climbs up the last section of guideway.
    // The model uses a fixed 1:80 distant scale. At the collar the 3.3 km
    // habitat is 8.4 km away; its angular diameter follows actual range.
    this.hab.position.set(13.7,12.9+m.remainingMeters/80,-103);
    this.viewCamera.position.set(-.32,2.29,-5.92);
    let ray=vec(-.29,-.04,-1).normalize();
    const sunrise=vec(.68,.115,-.73).normalize();ray.lerp(sunrise,smooth(20,48,m.seconds));
    const limbRay=vec(.30,-Math.sin(dip*.92),-.954*Math.cos(dip*.92)).normalize();
    ray.lerp(limbRay,smooth(105,156,m.seconds));
    if(m.seconds>285){
      const watch=vec(-3.8,Math.min(450,m.remainingMeters)+3.5,-12).normalize();
      ray.lerp(watch,smooth(285,318,m.seconds));
      ray.lerp(vec(.132,.123,-.984).normalize(),smooth(344,360,m.seconds));
    }
    // The acquisition head narrows its optical field to track the receiving
    // aperture at long range, then returns to a wide field inside the leads.
    let field=55;
    if(m.seconds>291&&m.remainingMeters>24){
      const desired=clamp(2*Math.atan(30/Math.max(24,m.remainingMeters))*180/Math.PI,4.5,55);
      field=T.MathUtils.lerp(55,desired,smooth(304,319,m.seconds));
    }
    if(Math.abs(this.viewCamera.fov-field)>.03){this.viewCamera.fov=field;this.viewCamera.updateProjectionMatrix();}
    this.viewCamera.lookAt(ray.normalize().add(this.viewCamera.position));

  }
}
