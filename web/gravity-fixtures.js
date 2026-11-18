import * as T from 'three';
import { FixturePhysics } from './fixture-physics.js';
import { CapillaryOptics } from './capillary-optics.js';
import { HelicalSpring } from './helical-spring.js';

export class GravityFixtures {
  constructor(world, survey) {
    this.world=world;
    const a=survey.accelerometer,c=survey.capillary;
    this.physics=new FixturePhysics({radius:c.radius,depth:c.depth,gasFraction:c.gasFraction,metersPerG:a.metersPerG});
    function required(name){
      const node=world.scene.getObjectByName(name);
      if(!node)throw Error('Missing surveyed cabin fitting '+name);
      return node;
    }
    const slider=(name,axis,travel)=>{
      const node=required(name);
      return {node,rest:node.position.clone(),travel:new T.Vector3(...axis).multiplyScalar(travel)};
    };
    this.mass=slider(a.massNode,a.slideAxis,a.metersPerG);this.referenceG=a.referenceG;
    this.test=slider(a.testNode,a.testAxis,a.testTravel);
    this.primer=slider(c.primerNode,c.primerAxis,c.primerTravel);
    this.springs=a.springs.map(spec=>new HelicalSpring(required(spec.node),spec));
    c.standInNodes.forEach(name=>{required(name).visible=false;});
    this.right=new T.Vector3(...c.right);this.up=new T.Vector3(...c.up);
    // A recessed light pipe rakes the printed rule. It shares the existing
    // flight-deck dimmer and has a short beam to preserve night adaptation.
    this.ruleLight=new T.SpotLight(0xffe6c3,.18,.52,.70,.70,2);
    this.ruleLight.position.set(-.718,1.444,-5.159);this.ruleLight.target.position.set(-.743,1.250,-5.218);
    this.ruleLight.name='Scale illumination';world.scene.add(this.ruleLight,this.ruleLight.target);
    this.lens=new T.Mesh(new T.CapsuleGeometry(.0015,.050,3,10),new T.MeshBasicMaterial({color:0xffdfb5}));
    this.lens.name='Recessed scale light guide';this.lens.rotation.z=Math.PI*.5;
    this.lens.position.set(-.718,1.443,-5.184);world.scene.add(this.lens);
    this.optics=new CapillaryOptics(world,required(c.node),c,this.physics);
    this.lastSeconds=-Infinity;
  }
  operate(id, held=false) {
    const p=this.physics;
    if(id==='accel_test'){p.test();p.testHeld=held;return true;}
    if(id==='capillary_primer'){const charged=p.pump();p.pumpHeld=held;return charged;}
    return false;
  }
  release() { this.physics.testHeld=this.physics.pumpHeld=false; }
  update(state, metrics, time, dt) {
    const force=this.world.dynamics.bodyForce,p=this.physics;
    const discontinuity=state!==this.state||Math.abs(metrics.seconds-this.lastSeconds)>1.5;
    this.state=state;this.lastSeconds=metrics.seconds;
    // A sealed instrument feels acceleration of the frame. Vent air acts on
    // the textiles, while the gas and liquid inside the glass are isolated.
    p.update(dt,-force.y/9.80665,-force.dot(this.right),-force.dot(this.up),discontinuity);
    const dimmer=[.30,.51,.76,1,1.20][state.panelGain??2];
    this.ruleLight.intensity=(.17+.11*(1-metrics.sunVisible))*dimmer;
    this.lens.material.color.setRGB(.87,.69,.43).multiplyScalar(.54+.42*dimmer);
    const delta=p.proof.x-this.referenceG;
    this.mass.node.position.copy(this.mass.rest).addScaledVector(this.mass.travel,delta);
    this.test.node.position.copy(this.test.rest).addScaledVector(this.test.travel,p.plunger.x);
    this.primer.node.position.copy(this.primer.rest).addScaledVector(this.primer.travel,p.primer.x);
    for(const spring of this.springs){
      const spec=spring.spec;
      const displacement=delta*this.mass.travel[spec.axis];
      spring.setLength(spec.restLength-spec.fixedEndSign*displacement);
    }
    this.optics.update(state,time);
  }
}
