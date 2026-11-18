import * as T from 'three';
import {GLTFLoader} from './assets/vendor/loaders/GLTFLoader.js';

export async function fitVesselCradle(world) {
  const {scene} = await new GLTFLoader().loadAsync('./assets/docking/VesselCradle.glb');
  const vessel = world.nodes.mug, rest = world.base.mug;
  const point = new T.Vector3(...world.layout.props.mug.webPivot);
  point.y = world.layout.props.mug.webBounds[0][1]-.0028;
  scene.position.copy(point);
  scene.traverse(mesh => { if(mesh.isMesh){mesh.castShadow=true;mesh.receiveShadow=true;world.hull.push(mesh);} });
  world.scene.add(scene);
  const from = new T.Vector3(), rotation = new T.Quaternion(), parentRotation = new T.Quaternion();
  let t = 1, contact;
  return {
    get moving(){return t<1;},
    fits(){return world.camera.position.distanceTo(point)<=1.24;},
    park(hand,onSeat){
      if(t<1 || !this.fits())return false;
      hand.copy.updateWorldMatrix(true,false);
      vessel.parent.worldToLocal(hand.copy.getWorldPosition(from));
      vessel.parent.getWorldQuaternion(parentRotation).invert();
      hand.copy.getWorldQuaternion(rotation).premultiply(parentRotation);
      contact=onSeat;t=0;return true;
    },
    update(dt){
      if(t>=1)return;
      t=Math.min(1,t+dt/.72);
      const approach=Math.min(1,t/.83), eased=approach*approach*(3-2*approach);
      vessel.position.lerpVectors(from,rest.pos,eased);
      const seat=t>.83?(1-Math.pow((t-.83)/.17,2)):Math.sin(eased*Math.PI/2);
      vessel.position.y+=.045*seat;
      vessel.quaternion.slerpQuaternions(rotation,rest.quat,eased);
      if(t===1){contact?.(point);contact=null;}
    }
  };
}
