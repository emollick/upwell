import * as T from 'three';
import { GLTFLoader } from './assets/vendor/loaders/GLTFLoader.js';
import {MeshoptDecoder} from './assets/vendor/meshopt.js';
import { Exterior } from './exterior.js';
import { Instruments } from './instruments.js';
import { loadFinishes, fitMaterial } from './finish.js';
import { PROPS, CARRIED, clamp, roomAt, visibleProp, travel, RIDE_SECONDS } from './journey.js';
import { CabinLight,physicalSurface } from './cabin-light.js';
import { PassengerOptics } from './passenger-optics.js';
import { InHand } from './in-hand.js';
import { CarDynamics } from './car-dynamics.js';
import { Furnishings } from './fabric-dynamics.js';
import { LooseItems } from './loose-items.js';
import { Switchboard, SWITCHES } from './switchboard.js';
import { GravityFixtures } from './gravity-fixtures.js';
import { loadFractureBench } from './fracture-bench.js';
import { laminatedPane } from './laminated-pane.js';
import {readGraphics} from './graphics.js';
import {PassengerMotion,PassengerClearance,ceilingAt} from './passenger-motion.js';
import {handrailLoad} from './flight-physics.js';
import {fitClampGauge} from './docking.js';
import {fitVesselCradle} from './vessel-cradle.js';

const V = (x, y, z) => new T.Vector3(x, y, z);
const DEGREES = Math.PI / 180;
// The millimetres of compliance belong to the retainers. The card can slip
// laterally within its tray; the magnet under the drink vessel is stiffer.
const mountProperties={
  field_glasses:{rise:.0022,side:.0010,frequency:18},mug:{rise:.0007,side:.00030,frequency:29},
  logbook:{rise:.0024,side:.0010,frequency:19},tool_roll:{rise:.0037,side:.0016,frequency:16},
  access_card:{rise:.00035,side:.0028,frequency:22},
};
const smallControls = new Set([
  'accel_test','capillary_primer','fracture_press','fracture_reload',
  ...Object.keys(SWITCHES),
  'ascent_lever',
  'nav_screen',
  'card_reader',
  'access_card',
  'field_glasses',
  'reading_lamp',
  'grab_handle',
  'pressure_gauge',
  'breaker',
  'intercom',
  'logbook',
  'mug',
  'tool_roll',
  'docking_wheel',
]);
const stations = {
  observation: [
    [1.38, 1.65, -2.18],
    [-0.47, 1.28, -4.72],
  ],
  berth: [
    [0.06, 1.53, -1.35],
    [0.72, 1.14, 0.3],
  ],
  service: [
    [0.07, 1.54, 2.33],
    [0.83, 1.34, 4.48],
  ],
};
const resting = {
  lounge_seat: [
    [-1.42, 1.31, -3.68],
    [0.15, 1.58, -5.7],
  ],
  bunk: [
    [-1.57, 1.13, 0.57],
    [1.98, 1.74, -0.08],
  ],
  window: [
    [-0.62, 1.49, -4.64],
    [-0.5, 1.6, -11],
  ],
  grab_handle: [
    [-0.69, 1.46, 0.89],
    [1.86, 1.73, 0.05],
  ],
  field_glasses: [
    [-0.58, 1.49, -4.56],
    [-0.96, 1.48, -16],
  ],
};
function ownProp(obj) {
  for (let n = obj; n; n = n.parent) if (n.userData.fitting) return n.userData.fitting;
  return null;
}
function isFlexibleSurface(obj){
  for(let n=obj;n;n=n.parent)if(/^(cloth_berth_|loom_service_)/.test(n.name))return true;
  return false;
}
export class World {
  constructor(element) {
    this.element = element;
    this.scene = new T.Scene();
    this.camera = new T.PerspectiveCamera(61, 1, 0.035, 1200);
    this.camera.userData.passengerEye=true;
    this.camera.rotation.order = 'YXZ';
    this.nodes = {};
    this.base = {};
    this.hull = [];
    this.keys = new Set();
    this.ray = new T.Raycaster();
    this.look = new T.Vector3();
    this.position = V(...stations.observation[0]);
    this.pitch = 0;
    this.yaw = 0;
    this.restId = null;
    this.walkCycle = 0;
    this.lastFoot = 0;
    this.aisleVelocity=new T.Vector2();this.deckLoad=1;
    this.flight=new PassengerMotion(this.position.y);
    this.bodyFits=(x,z,y)=>this.walkable(x,z,this.rideState,y);
    this.aimAt(...stations.observation[1]);
    this.onStep = () => {};
    this.onFittingStop=()=>{};
    this.inspection=null;this.view='window';this.lensZoom=1;
    this.reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  async init(progress) {
    this.r = new T.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
    const gl=this.r.getContext(),vendor=gl.getExtension('WEBGL_debug_renderer_info');
    const gpu=vendor?gl.getParameter(vendor.UNMASKED_RENDERER_WEBGL):'';
    this.softwareGpu=/swiftshader|llvmpipe|software rasterizer|basic render driver/i.test(gpu);
    this.graphics=readGraphics(this.softwareGpu);
    this.renderScale=this.softwareGpu?.60:1;this.frameMean=1/35;this.qualityAt=0;this.activeFrames=0;
    this.r.autoClear = false;
    this.r.outputColorSpace = T.SRGBColorSpace;
    this.r.toneMapping = T.ACESFilmicToneMapping;
    this.r.toneMappingExposure = 1.08;
    this.r.shadowMap.enabled = true;
    this.r.shadowMap.type = T.PCFSoftShadowMap;
    this.r.setClearColor(0x0a1117);
    this.element.appendChild(this.r.domElement);
    this.resize();
    this.exterior = new Exterior(this.r,this.scene);
    this.camera.layers.enable(1);
    this.optics=new PassengerOptics(this.r,this.softwareGpu);
    this.instruments = new Instruments(this.softwareGpu);
    const indexResponse = await fetch('./assets/rooms/scene.json');
    if (!indexResponse.ok) throw Error('Room index could not be loaded');
    this.layout = await indexResponse.json();
    const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
    const surfaceFilter=Math.min(8,this.r.capabilities.getMaxAnisotropy());
    let loaded = 0;
    const finishTask = loadFinishes();
    const flexData=fetch('./assets/rooms/flex.json').then(r=>{if(!r.ok)throw Error('The restraint rig could not be loaded.');return r.json();});
    const furnishings=fetch('./assets/rooms/furnishings.json').then(r=>{if(!r.ok)throw Error('The cabin fabric rig could not be loaded.');return r.json();});
    const mechanisms=fetch('./assets/rooms/mechanisms.json').then(r=>{if(!r.ok)throw Error('The instrument pivots could not be loaded.');return r.json();});
    const cartridgeTask=loadFractureBench(this,loader);
    await Promise.all([
      finishTask,
      cartridgeTask,
      this.exterior.init(),
      ...Object.entries(this.layout.rooms).map(async ([id, room]) => {
        const gltf = await loader.loadAsync('./assets/rooms/' + room.file);
        gltf.scene.updateMatrixWorld(true);
        this.scene.add(gltf.scene);
        gltf.scene.traverse((n) => {
          if (n.name.startsWith('prop_') && PROPS[n.name.slice(5)]) {
            const key = n.name.slice(5);
            n.userData.fitting = key;
            this.nodes[key] = n;
            this.base[key] = {
              pos: n.position.clone(),
              scale: n.scale.clone(),
              quat: n.quaternion.clone(),
              restInverse: n.matrixWorld.clone().invert(),
              v: 0,
            };
          }
          if (!n.isMesh) return;
          const source=n.material;
          const coverGlass=source.name==='Cell_Optical_Glass';
          const glass=coverGlass||/^(Surface_window|Clear_Glass)$/i.test(source.name);
          const m=glass&&!coverGlass?laminatedPane(n,source,this):physicalSurface(source);n.material=m;
          if(glass){
            m.transparent=true;m.depthWrite=false;
            if(coverGlass){m.opacity=.034;m.roughness=.056;m.metalness=.23;}
            if(coverGlass&&m.isMeshPhysicalMaterial)m.transmission=0;
          }
          if(m.name==='Cell_Diffuser'){
            m.emissiveMap=m.map;m.emissive.setRGB(.98,.88,.68);m.emissiveIntensity=.32;
          }
          n.castShadow = !glass;
          n.receiveShadow = !glass;
          n.userData.isGlass = glass;
          if (m.name === 'Nav_Active_Pixels') {
            n.material = this.instruments.material;
            n.castShadow = false;
          }
          // Albedo, tool marks and roughness must cover the same oblique
          // footprint, particularly on the floor panels and equipment rims.
          for(const texture of [m.map,m.normalMap,m.roughnessMap,m.metalnessMap])if(texture)texture.anisotropy=surfaceFilter;
          this.hull.push(n);
        });
        const finishes = await finishTask;
        gltf.scene.traverse((n) => {
          if (n.isMesh && !CARRIED.includes(ownProp(n))&&!isFlexibleSurface(n)) fitMaterial(n, finishes[id]);
        });
        loaded++;
        progress?.(loaded);
      }),
    ]);
    this.photometry=new CabinLight(this.scene,this.r,this.exterior);
    if(this.softwareGpu){
      this.photometry.sun.shadow.mapSize.set(1024,1024);
      for(const lamp of this.photometry.baySpots)lamp.shadow.mapSize.set(512,512);
    }
    this.dynamics=new CarDynamics(await flexData,this.nodes);
    this.furnishings=new Furnishings(await furnishings,this.scene);
    this.fabricRay=new T.Raycaster();
    this.mechanisms=Object.fromEntries((await mechanisms).parts.map(spec=>[spec.parentId,spec]));
    this.fixedDevices=[];
    for(const [id,spec] of Object.entries(this.mechanisms)){
      const n=this.nodes[id].getObjectByName(spec.node);if(!n)throw Error('Missing instrument mechanism '+spec.node);
      const ax=new T.Vector3();ax[spec.axis]=1;this.fixedDevices.push({id,spec,node:n,rest:n.quaternion.clone(),axis:ax,quat:new T.Quaternion(),factor:0});
    }
    [this.fracture,this.clampGauge,this.vesselCradle]=await Promise.all([cartridgeTask,fitClampGauge(this),fitVesselCradle(this)]);
    this.touchZones = [];
    for (const id of smallControls) {
      const n = this.nodes[id],
        meta = this.layout.props[id];
      if (!n || !meta) continue;
      const box = new T.Box3(V(...meta.webBounds[0]), V(...meta.webBounds[1]));
      box.applyMatrix4(this.base[id].restInverse);
      box.expandByScalar(id === 'access_card' ? 0.012 : 0.019);
      this.touchZones.push({ id, n, box, worldBox: new T.Box3() });
    }
    this.lighting();
    this.looseItems=new LooseItems(this);
    this.flight.clearance=new PassengerClearance(this.looseItems,this.base);
    this.switchboard=new Switchboard(this,this.layout);
    if(this.nodes.accelerometer){
      const response=await fetch('./assets/rooms/gravity-instruments.json');
      if(!response.ok)throw Error('The cabin instrument survey could not be loaded.');
      this.fixtures=new GravityFixtures(this,await response.json());
      this.instruments.mechanical=this.fixtures.physics;
    }
    this.camera.position.copy(this.position);
    this.updateCamera(0);
    this.shadowSources=[];
    this.scene.traverse(o=>{if(o.isLight&&o.castShadow&&o.shadow)this.shadowSources.push([o.shadow,o.shadow.mapSize.x]);});
    this.applyGraphics(this.graphics,true);
    this.scene.updateMatrixWorld(true);
    return this;
  }
  lighting() {
    const point = (c, p, x, y, z, reach = 6) => {
      const l = new T.PointLight(c, p, reach, 2);
      l.position.set(x, y, z);
      this.scene.add(l);
      return l;
    };
    this.practical = new T.SpotLight(0xf7efdf, 6, 5.5, 1.12, 0.86, 2);
    this.practical.position.set(-1.46, 2.23, -3.98);
    this.practical.target.position.set(-0.38, 0.7, -3.35);
    this.scene.add(this.practical, this.practical.target);
    this.instrumentLight = point(0x9ad6e3, 0.36, 1.05, 1.23, -4.74, 2);
    this.sleeper = point(0xffe9cc, 4.5, -1.56, 1.82, -0.68, 4.4);
    this.trayLamp=new T.SpotLight(0xffdeaa,0,1.5,.74,.64,2);
    this.scene.add(this.trayLamp,this.trayLamp.target);
    this.trayCenter=new T.Vector3(...this.layout.props.access_card.webCenter).applyMatrix4(this.base.access_card.restInverse);
    this.service = point(0xc5d6df, 6, 0.28, 2.31, 3.55, 5);
    this.loom = point(0xf6fbff, 0, 0.97, 1.54, 3.52, 3.3);
    this.earthBounce = point(0xb1ddff, 9, 1.12, 2.05, -5.22, 6.1);
    this.handLight=new T.SpotLight(0xfff1d9,0,1.65,.69,.65,2);
    this.handLight.castShadow=true;this.handLight.shadow.mapSize.set(512,512);
    this.handLight.shadow.camera.near=.035;this.handLight.shadow.camera.far=1.65;
    this.handLight.shadow.bias=-.00010;this.handLight.shadow.normalBias=.00045;
    this.handLight.shadow.autoUpdate=false;this.scene.add(this.handLight,this.handLight.target);
    this.lightOffset=new T.Vector3();this.lightTarget=new T.Vector3();this.presenting=false;
    this.emitterGroups = {};
    for (const key of ['lamp', 'reading_lamp', 'card_reader', 'breaker', 'pressure_gauge']) {
      this.emitterGroups[key] = [];
      this.nodes[key]?.traverse((n) => {
        if (n.isMesh && (n.material.emissive?.getHex() || n.material.name === 'Surface_lamp')) {
          n.material = n.material.clone();
          this.emitterGroups[key].push([n.material, n.material.emissiveIntensity || 1]);
        }
      });
    }
  }
  resize() {

    if (!this.r) return;
    const w = this.element.clientWidth || innerWidth,
      h = this.element.clientHeight || innerHeight;
    const maxPixels=this.softwareGpu?460000:2600000;
    const ratio=Math.min(devicePixelRatio||1,w<750?1.25:1.5,Math.sqrt(maxPixels/(w*h)));
    let pixelRatio=ratio*(this.renderScale??1);this.resolutionLimited=false;
    if(this.graphics.resolution!=='auto'){
      const budget=this.softwareGpu?1500000:8294400;
      const desired=(devicePixelRatio||1)*Number(this.graphics.resolution);
      pixelRatio=Math.min(desired,Math.sqrt(budget/(w*h)),this.r.capabilities.maxTextureSize/Math.max(w,h));
      this.resolutionLimited=pixelRatio<desired-.001;
    }
    this.r.setPixelRatio(pixelRatio);
    this.r.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }
  frameBudget(seconds,time){
    if(this.graphics.resolution!=='auto'||seconds<=0||seconds>.6)return;
    if(time<this.qualityAt)this.qualityAt=0;
    this.frameMean+=.035*(seconds-this.frameMean);this.activeFrames++;
    if(this.activeFrames<80||time-this.qualityAt<4.5)return;
    const prior=this.renderScale,low=this.softwareGpu?.52:.68,high=this.softwareGpu?.72:1;
    if(this.frameMean>.052)this.renderScale=Math.max(low,prior-.10);
    else if(this.frameMean<.027)this.renderScale=Math.min(high,prior+.06);
    if(Math.abs(prior-this.renderScale)>.001){this.resize();this.qualityAt=time;this.activeFrames=0;}
  }
  applyGraphics(settings,first=false){
    const previous=this.graphics;
    this.graphics={...settings};
    if(!this.optics.aaModes.some(([id])=>id===this.graphics.aa))this.graphics.aa='auto';
    this.optics.setAA(this.graphics.aa);
    if(first||previous.shadows!==settings.shadows){
      this.r.shadowMap.enabled=settings.shadows!=='off';
      const scale=settings.shadows==='fine'?2:settings.shadows==='auto'&&this.softwareGpu?.5:1;
      for(const [shadow,nativeSize] of this.shadowSources){
        const size=Math.min(Math.round(nativeSize*scale),this.r.capabilities.maxTextureSize);
        if(shadow.mapSize.x!==size){
          shadow.dispose();shadow.map=null;shadow.mapPass=null;shadow.mapSize.set(size,size);
        }
        shadow.needsUpdate=true;
      }
      if(!first&&(previous.shadows==='off'||settings.shadows==='off')){
        const materials=new Set();this.scene.traverse(o=>{if(o.material)for(const m of [].concat(o.material))materials.add(m);});
        for(const m of materials)m.needsUpdate=true;
      }
      this.r.shadowMap.needsUpdate=true;this.photometry.probeKey='';
    }
    if(first||previous.resolution!==settings.resolution){
      this.renderScale=this.softwareGpu?.60:1;this.activeFrames=0;this.resize();
    }
  }
  setView(view){this.view=view;this.lensZoom=1;this.gimbalX=0;this.gimbalY=0;}
  seat(room){
    this.go(room);this.view='window';
    const seats={observation:[[.21,1.52,-3.76],[-1.9,1.74,-13.4]],berth:[[-.82,1.36,.9],[2.05,1.64,-.15]],service:[[.50,1.53,2.73],[-1.65,1.55,3.7]]};
    const [eye,at]=seats[room]||seats.observation;this.position.set(...eye);this.aimAt(...at);this.updateCamera(0);
    if(room==='observation')this.windowGrip('seat');
  }
  windowGrip(mode){
    const ref=mode==='seat'?[[.21,1.52,-3.76],[-1.9,1.74,-13.4]]:resting.window;
    const base=V(...ref[0]),dir=V(...ref[1]).sub(base).normalize();
    this.harborLean={base,change:V(-1.21,1.57,-4.81).sub(base),weight:0,
      yaw:.146-Math.atan2(-dir.x,-dir.z),pitch:-.131-Math.asin(dir.y)};
    this.windowClearance((this.rideState?.progress??0)*RIDE_SECONDS,true);this.updateCamera(0);
  }
  windowClearance(seconds,entering=false){
    const lean=this.harborLean;if(!lean)return;
    const w=1-T.MathUtils.smoothstep(seconds,23,36),delta=w-lean.weight;
    if(!entering&&Math.abs(delta)<1e-7)return;
    this.position.copy(lean.base).addScaledVector(lean.change,w);
    this.yaw+=lean.yaw*delta;this.pitch+=lean.pitch*delta;lean.weight=w;
  }
  sensorCamera(m){
    if(this.view==='window')return this.camera;
    if(this.view==='shaded'){
      const cam=this.shadedEye??=new T.PerspectiveCamera(52,1,.025,2200);
      const ray=(this.shadedRay??=new T.Vector3()).fromArray(m.sunDirection).negate();
      cam.layers.enable(1);cam.userData.passengerEye=true;cam.position.set(ray.x<0?-1.28:1.28,1.82,-4.03);
      cam.aspect=this.camera.aspect;cam.fov=clamp(52/this.lensZoom,24,78);
      const halfWidth=Math.atan(Math.tan(cam.fov*DEGREES/2)*cam.aspect);
      cam.lookAt(ray.add(cam.position));cam.rotateY(-Math.min(5*DEGREES,.35*halfWidth));cam.rotateX(2.5*DEGREES);
      cam.rotateY(this.gimbalX||0);cam.rotateX(this.gimbalY||0);
      cam.updateProjectionMatrix();cam.updateMatrixWorld();return cam;
    }
    if(this.view==='floor'){
      const cam=this.floorEye??=new T.PerspectiveCamera(52,1,.023,2200);
      cam.layers.enable(1);cam.userData.passengerEye=true;cam.position.set(.016,1.32,-3.739);cam.up.set(0,0,-1);
      cam.lookAt(.005,-2.2,-3.85);cam.rotateY(this.gimbalX||0);cam.rotateX(this.gimbalY||0);
      cam.aspect=this.camera.aspect;
      const horizontalFit=2*Math.atan(Math.tan(23.5*DEGREES)/cam.aspect)/DEGREES;
      cam.fov=clamp(Math.max(52,horizontalFit)/this.lensZoom,25,94);cam.updateProjectionMatrix();cam.updateMatrixWorld();return cam;
    }
    const cam=this.exterior.sensorCamera??=new T.PerspectiveCamera(50,1,.04,2200);
    cam.layers.set(1);
    const from=this.view==='earth'?this.exterior.nadir:this.view==='guide'?this.exterior.cams[1]:this.view==='counter'?this.exterior.counterCamera:this.exterior.viewCamera;
    cam.position.copy(from.position);cam.quaternion.copy(from.quaternion);cam.aspect=this.camera.aspect;
    let field=from.fov;cam.near=.04;cam.up.set(0,1,0);
    if(this.view==='earth'&&m.km>1300){
      // The under-hull pupil sees the rails all the way to the near edge of
      // the frame. Only aim and focal length change as the planet recedes.
      const blend=T.MathUtils.smoothstep(m.km,1300,4300);
      const disc=Math.asin(6371/(6371+m.km));
      const framed=2*Math.atan(Math.tan(disc)/(.78*Math.min(1,cam.aspect)))/DEGREES;
      const direction=V(0,0,-1).applyQuaternion(from.quaternion).lerp(V(.0008,-1,.0006),blend).normalize();
      cam.lookAt(direction.add(cam.position));field=T.MathUtils.lerp(field,clamp(framed,16,133),blend);
    }else if(this.view==='stars'){
      const side=m.sunDirection[0]>=0?-1:1;
      cam.lookAt(cam.position.x+side*.72,cam.position.y+.16,cam.position.z-.70);field=61;
    }else if(this.view==='valley'&&m.remainingMeters<=.10){
      this.exterior.orbital.valleyPose(cam);
      field=54;cam.near=.002;
    }else if(this.view==='colony'||this.view==='valley'){
      const destination=this.exterior.hab.position;
      if(m.remainingMeters<=.10)this.exterior.orbital.relayEye.getWorldPosition(cam.position);
      cam.lookAt(destination);field=clamp(2*Math.atan(32/(cam.position.distanceTo(destination)*Math.min(1,cam.aspect)))/DEGREES,2.1,74);
    }
    cam.rotateY(this.gimbalX||0);cam.rotateX(this.gimbalY||0);cam.fov=field/this.lensZoom;cam.updateProjectionMatrix();cam.updateMatrixWorld();return cam;
  }
  aimAt(x, y, z) {
    this.look.set(x, y, z).sub(this.position).normalize();
    this.yaw = Math.atan2(-this.look.x, -this.look.z);
    this.pitch = Math.asin(this.look.y);
  }
  rotate(dx, dy) {
    if(this.view!=='window'){this.gimbalX=clamp((this.gimbalX||0)-dx*.0025,-.98,.98);this.gimbalY=clamp((this.gimbalY||0)-dy*.0025,-.72,.72);return;}
    this.yaw -= dx * 0.0038;
    this.pitch = clamp(this.pitch - dy * 0.0034, -1.28, 1.28);
  }
  go(room) {
    this.view='window';this.restId = null;this.harborLean=null;this.aisleVelocity.set(0,0);
    const st = stations[room] || stations.observation;
    this.position.set(...st[0]);
    this.flight.reset(this.position.y);
    this.aimAt(...st[1]);
    this.updateCamera(0);
  }
  rest(id) {
    const st = resting[id];
    if (!st) return false;
    if (!this.restId) {
      this.returnPos = this.position.clone();
      this.returnAim = [this.yaw, this.pitch];
      this.returnDeckY=this.flight.deckY;
    }
    this.view='window';this.restId = id;
    this.flight.reset(this.position.y);
    this.position.set(...st[0]);
    this.aimAt(...st[1]);
    this.harborLean=null;if(id==='window')this.windowGrip('grip');
    return true;
  }
  stand() {
    if (!this.restId) return;
    this.restId = null;this.harborLean=null;
    this.position.copy(this.returnPos);
    this.flight.reset(this.returnDeckY??this.position.y);
    this.flight.ballistic=this.position.y>this.flight.deckY+.02;
    [this.yaw, this.pitch] = this.returnAim;
  }
  aimFitting(id) {
    this.flight.reset(1.48);
    if(id.startsWith('loom_service_')){this.aimFabric(id);return;}
    if(id==='privacy_curtain'){
      if(this.restId)this.stand();if(roomAt(this.position.z)!=='berth')this.go('berth');
      const stile=this.furnishings.part('curtain').hardware.at(-1).node;
      const grip=stile.localToWorld(V(.05,.022,0));
      this.position.set(-.23,1.48,clamp(grip.z+.05,-1.55,1.43));
      this.aimAt(grip.x,grip.y,grip.z);this.updateCamera(0);return;
    }
    if(id==='nadir_port'){
      this.go('observation');this.position.set(.08,1.47,-3.12);
      this.aimAt(0,.01,-3.80);this.updateCamera(0);return;
    }
    const meta = this.layout.props[id];
    if (!meta) return;
    const loose=this.looseItems?.bodies.get(id);
    if(loose){
      const center=loose.root.position,room=roomAt(center.z);
      if(this.restId)this.stand();
      if(roomAt(this.position.z)!==room)this.go(room);
      if(this.position.distanceTo(center)>2.35){
        const x=clamp(center.x*.39,-.70,.72),z=clamp(center.z+.49,-4.15,4.8);
        if(this.walkable(x,z,this.rideState))this.position.set(x,1.48,z);
      }
      this.aimAt(center.x,center.y,center.z);this.updateCamera(0);return;
    }
    const keyRoom =
      ['pressure_hatch', 'card_reader'].includes(id) && this.position.z < 1.91
        ? 'berth'
        : meta.room;
    if (roomAt(this.position.z) !== keyRoom) this.go(keyRoom);
    if (this.restId) this.stand();
    const center = V(...meta.webCenter)
      .applyMatrix4(this.base[id].restInverse)
      .applyMatrix4(this.nodes[id].matrixWorld);
    let x = clamp(center.x * 0.47, -0.75, 0.76),
      z = clamp(center.z, -4.0, 4.76);
    if (id === 'ascent_lever' || id === 'nav_screen' || id === 'pilot_console'||SWITCHES[id]?.room==='observation') {
      x = id === 'ascent_lever' ? 1.33 : 0.58;
      z = -3.86;
    }
    if (id === 'pressure_hatch' || id === 'card_reader') {
      x = 0.1;
      z = 0.82;
    }
    if (id === 'service_cabinet'||id.startsWith('test_')) {
      x = 0.04;
      z = 3.62;
    }
    if(id==='reading_lamp'){x=-.78;z=-.18;}
    if(id==='accel_test'||id==='accelerometer'){x=-.51;z=-4.17;}
    if(id==='capillary_cell'||id==='capillary_primer'){x=.96;z=center.z+.43;}
    const atBench=id.startsWith('fracture_');
    if(atBench){x=-1.65;z=4.61;}
    this.position.set(x, atBench?1.58:1.48, z);
    this.aimAt(center.x, center.y, center.z);
    this.updateCamera(0);
    // Rounded grips, ring handles and open-frame hardware have empty space at
    // their nominal center. Find an actual visible surface for keyboard focus.
    if (this.pick() !== id) {
      const bb = new T.Box3().setFromObject(this.nodes[id]);
      const mid = bb.getCenter(new T.Vector3()),
        size = bb.getSize(new T.Vector3());
      for (const [u, v, w] of [
        [0, 0.38, 0],
        [0, 0, 0.34],
        [0.32, 0, 0],
        [-0.32, 0, 0],
        [0, -0.32, 0],
        [0.28, 0.28, 0.23],
        [-0.3, 0.28, 0.23],
        [0, 0.24, -0.28],
      ]) {
        this.aimAt(mid.x + u * size.x, mid.y + v * size.y, mid.z + w * size.z);
        this.updateCamera(0);
        if (this.pick() === id) return;
      }
      this.aimAt(center.x, center.y, center.z);
      this.updateCamera(0);
    }
  }
  clearKeys() {
    this.keys.clear();
    this.aisleVelocity.set(0,0);
  }
  passengerPose(seconds){
    return {position:this.position.toArray(),yaw:this.yaw,pitch:this.pitch,flight:this.flight.bookmark(),seconds};
  }
  resumePassenger(pose,s,seconds){
    this.rideState=s;
    this.position.fromArray(pose.position);this.yaw=pose.yaw;this.pitch=pose.pitch;
    this.flight.restore(pose.flight);
    if(seconds>pose.seconds||this.deckLoad<=handrailLoad)this.flight.clearance.prepare();
    this.flight.seek(this.position,this.bodyFits,pose.seconds,seconds);this.updateCamera(0);
  }
  rewindPassengerBookmark(pose,s,from,to,time){
    // The mounted camera can be rewound independently of the traveller who
    // was floating when they selected it. Accrue that motion before rewinding.
    if(from>pose.seconds){
      this.rideState=s;
      const p=V(...pose.position),pending=new PassengerMotion(pose.flight.deckY);
      pending.restore(pose.flight);pending.clearance=this.flight.clearance;
      if(from>240||pending.ballistic)pending.clearance.prepare();
      pending.seek(p,this.bodyFits,pose.seconds,from,time-(from-pose.seconds));
      pose.position=p.toArray();pose.flight=pending.bookmark();pose.room=roomAt(p.z);
    }
    pose.seconds=to;
  }
  seekPassage(s,from,to,time,free){
    const m=travel(to/RIDE_SECONDS);this.rideState=s;this.deckLoad=Math.min(1,m.forces.gravityG);
    const tracked=free&&s.followMomentView&&to>from&&this.view==='window'&&!this.inspection?this.looseItems.bodies.get(this.pick()):null;
    this.trackedSeek=false;
    if(free&&!this.restId){
      const old=this.position.clone();
      if(Math.max(from,to)>240||this.flight.ballistic)this.flight.clearance.prepare();
      this.flight.seek(this.position,this.bodyFits,from,to,time);
      if(old.distanceToSquared(this.position)>.0001)this.inspection?.resetReleaseSample();
    }
    this.looseItems.seek(s,from,to);
    this.fracture.seek(s,from,to,time);
    this.dynamics.seek(m,time,s.ventOn);
    if(tracked&&roomAt(tracked.root.position.z)===roomAt(this.position.z)&&tracked.root.position.distanceTo(this.position)>.12){
      const p=tracked.root.position;this.aimAt(p.x,p.y,p.z);this.trackedSeek=true;
    }
    this.updateCamera(0);
  }
  faceDock(onlyIfObstructed=false){
    if(onlyIfObstructed){
      this.ray.setFromCamera(new T.Vector2(0,0),this.camera);this.ray.far=.65;
      const blocked=this.ray.intersectObjects(this.hull,false).some(hit=>{
        if(hit.object.userData.isGlass)return false;
        for(let n=hit.object;n;n=n.parent)if(!n.visible)return false;
        return true;
      });
      if(!blocked)return;
    }
    const room=roomAt(this.position.z);
    if(room==='observation')this.aimAt(-.18,1.61,-5.62);
    else if(room==='berth')this.aimAt(this.position.x<0?1.45:-1.4,1.33,.13);
    else this.aimAt(0,1.4,this.position.z>4.8?2.2:5.42);
    this.updateCamera(0);
  }
  pushPassenger(direction='away'){
    if(this.deckLoad>handrailLoad||this.restId)return false;
    return this.flight.push(this.position,this.bodyFits,direction);
  }
  leanTo(id,on=true){
    const center=this.layout.props[id]?.webCenter;if(!center||!on){this.lean=null;return;}
    const meta=this.layout.props[id],along=V(...center).sub(this.position),distance=along.length();
    const tightBench=id==='fracture_cell'&&this.camera.aspect<.85;
    const offset=along.normalize().multiplyScalar(Math.min(tightBench?.045:.30,Math.max(0,distance-.31)));
    const eye=this.position.clone().add(offset),right=V(1,0,0).applyQuaternion(this.camera.quaternion);
    const up=V(0,1,0).applyQuaternion(this.camera.quaternion),forward=V(0,0,-1).applyQuaternion(this.camera.quaternion);
    const [lo,hi]=meta.webBounds;let width=0,height=0;
    for(const x of [lo[0],hi[0]])for(const y of [lo[1],hi[1]])for(const z of [lo[2],hi[2]]){
      const p=V(x,y,z).sub(eye),depth=Math.max(.08,p.dot(forward));
      width=Math.max(width,Math.abs(p.dot(right))/depth);height=Math.max(height,Math.abs(p.dot(up))/depth);
    }
    this.lean={offset,fov:35,width,height};
  }
  walkable(x, z, s, eyeY=this.position.y) {
    if (Math.abs(x) > 1.97 || z < -5.18 || z > 5.37) return false;
    if(eyeY>ceilingAt(z)+.001)return false;
    if (Math.abs(z + 1.9) < 0.2 && Math.abs(x) > 0.48) return false;
    if (
      Math.abs(z - 1.9) < 0.27 &&
      (Math.abs(x) > 0.48 || !s.hatch || this.base.pressure_hatch?.v < 0.8)
    )
      return false;
    if (z < -4.51 && (x > -0.18 || x < -0.7)) return false;
    if (z < -2.47 && z > -4.96 && x < -1.09) return false;
    if (z > -1.47 && z < 1.5 && (x < -1.03 || x > (s.drawer ? 0.93 : 1.17))) return false;
    if (z > 2.62 && z < 4.48){
      if(x>1.65&&z>2.69)return false;
      // The aft side of an open cover leads to the exposed backplane. Leave
      // shoulder clearance only along the physical sweep of the door leaf.
      const angle=-(this.base.service_cabinet?.v??Number(s.cabinet))*84*DEGREES;
      const sx=Math.sin(angle),cz=Math.cos(angle),dx=x-1.755,dz=z-2.877;
      const t=clamp(dx*sx+dz*cz,0,1.35);
      if((dx-t*sx)**2+(dz-t*cz)**2<.255**2)return false;
    }
    if (z > 3.1 && z < 4.27 && x < -1.48) return false;
    return true;
  }
  movement(dt, s, active, unrestrained=active) {
    if (!unrestrained || this.restId) {
      this.clearKeys();
      this.flight.velocity.set(0,0,0);this.flight.ballistic=false;
      return;
    }
    if(!active)this.clearKeys();
    const k = this.keys;
    if (k.has('q')) this.yaw += dt * 1.35;
    if (k.has('c')) this.yaw -= dt * 1.35;
    if (k.has('arrowleft')) this.yaw += dt * 1.5;
    if (k.has('arrowright')) this.yaw -= dt * 1.5;
    if (k.has('pageup')) this.pitch = clamp(this.pitch + dt, -1.28, 1.28);
    if (k.has('pagedown')) this.pitch = clamp(this.pitch - dt, -1.28, 1.28);
    const forward =
      Number(k.has('w') || k.has('arrowup')) - Number(k.has('s') || k.has('arrowdown'));
    const side = Number(k.has('d')) - Number(k.has('a'));
    const grip=this.deckLoad;
    const lowLoad=grip<=handrailLoad,wasAirborne=this.flight.ballistic;
    if(lowLoad&&!wasAirborne)this.flight.velocity.set(this.aisleVelocity.x,0,this.aisleVelocity.y);
    const wish=this.flight.pushDirection;
    if(lowLoad||wasAirborne){
      this.flight.clearance.prepare();
      const horizontal=forward*Math.cos(this.pitch);
      wish.set(-Math.sin(this.yaw)*horizontal+Math.cos(this.yaw)*side,Math.sin(this.pitch)*forward,
        -Math.cos(this.yaw)*horizontal-Math.sin(this.yaw)*side).normalize();
      if(this.flight.advance(this.position,this.bodyFits,this.dynamics.bodyForce,lowLoad,dt,wish)){
        this.aisleVelocity.set(0,0);return;
      }
      this.aisleVelocity.set(this.flight.velocity.x,this.flight.velocity.z);
    }
    if(!active)return;
    if(!forward&&!side&&this.aisleVelocity.lengthSq()<.0003){this.aisleVelocity.set(0,0);return;}
    const speed=(1.07+.48*grip)/Math.max(1,Math.hypot(side,forward));
    const wantedX=(-Math.sin(this.yaw)*forward+Math.cos(this.yaw)*side)*speed;
    const wantedZ=(-Math.cos(this.yaw)*forward-Math.sin(this.yaw)*side)*speed;
    // In the upper car movement follows a handrail pull, with a short coast
    // before the next grip. Ground walking transfers weight much faster.
    const response=1-Math.exp(-dt*((forward||side?3.4:4.3)+grip*20));
    this.aisleVelocity.x+=(wantedX-this.aisleVelocity.x)*response;
    this.aisleVelocity.y+=(wantedZ-this.aisleVelocity.y)*response;
    const dx=this.aisleVelocity.x*dt,dz=this.aisleVelocity.y*dt;
    const x = this.position.x,
      z = this.position.z;
    if (this.walkable(x + dx, z, s)) this.position.x += dx;else this.aisleVelocity.x=0;
    if (this.walkable(this.position.x, z + dz, s)) this.position.z += dz;else this.aisleVelocity.y=0;
    const d = Math.hypot(this.position.x - x, this.position.z - z);
    this.walkCycle += d * 8.25;
    this.lastFoot += d;
    if (this.lastFoot > 0.88) {
      this.lastFoot = 0;
      this.onStep(grip);
    }
  }
  updateCamera(dt) {
    const blend = dt === 0 ? 1 : 1 - Math.exp(-dt * 15);
    this.camera.position.lerp(this.position, blend);
    if(this.lean)this.camera.position.addScaledVector(this.lean.offset,blend);
    this.camera.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
    if(this.dynamics&&!this.reduced){
      this.camera.position.addScaledVector(this.dynamics.head,blend);
      this.camera.rotation.z+=this.dynamics.roll;
    }
    let base = this.lean?.fov??(this.restId === 'field_glasses' ? 27 : this.restId === 'window' ? 52 : 61);
    const rect=this.fittingPanel?.getBoundingClientRect(),w=this.element.clientWidth,h=this.element.clientHeight;
    if(rect&&w&&h){
      const phone=w<=720,top=phone?48:22,area=phone?clamp((rect.top-top-8)/h,.32,.84):.91;
      if(this.lean){
        const width=phone?.94:clamp(rect.left/w,.58,.94);
        const fitted=2*Math.atan(1.08*Math.max(this.lean.height/area,this.lean.width/(this.camera.aspect*width)))/DEGREES;
        base=Math.max(base,Math.min(82,fitted));
      }
      const offX=phone?0:Math.round(clamp(w*.5-rect.left*.53,0,w*.17));
      const offY=phone?Math.round(clamp((h-rect.top-top)*.5,0,h*.30)):0;
      const view=this.camera.view;
      if(!view?.enabled||view.offsetX!==offX||view.offsetY!==offY||view.fullWidth!==w||view.fullHeight!==h){
        this.camera.setViewOffset(w,h,offX,offY,w,h);
      }
    }else if(this.camera.view?.enabled)this.camera.clearViewOffset();
    if (Math.abs(this.camera.fov - base) > 0.05) {
      this.camera.fov = T.MathUtils.lerp(this.camera.fov, base, blend);
      this.camera.updateProjectionMatrix();
    }
    if (!this.restId && this.keys.size && !this.reduced)
      this.camera.position.y += Math.sin(this.walkCycle) * 0.003*this.deckLoad;
    this.camera.updateMatrixWorld(true);
  }
  pick(nx = 0, ny = 0) {
    this.fabricUnderAim=null;
    this.curtainHandleUnderAim=false;
    this.ray.setFromCamera(new T.Vector2(nx, ny), this.camera);
    this.ray.far = 3.45;
    const loose=this.looseItems?.meshes;
    const hits = this.ray.intersectObjects(loose?.length?this.hull.concat(loose):this.hull, false);
    let surface = null,
      limit = this.ray.far;
    const room=roomAt(this.position.z);
    for (const hit of hits) {
      let id = ownProp(hit.object);
      let visible=true;
      for(let n=hit.object;n;n=n.parent)if(!n.visible){visible=false;break;}
      if(!visible)continue;
      if(id==='privacy_curtain'&&hit.distance<=2.65&&this.isCurtainHandle(hit)){
        this.curtainHandleUnderAim=true;
        return id;
      }
      const cloth=hit.object.userData.fabricPart;
      if(cloth&&hit.distance<=2.65&&(cloth.kind!=='service'||this.furnishings.cover>=.6)&&cloth.spec.room===room){
        this.fabricUnderAim={id:cloth.id,kind:cloth.kind,point:hit.point};
        if(cloth.kind==='service')return cloth.id;
      }
      if(!id&&room==='observation'&&hit.point.y<.045&&hit.point.y>-.18&&Math.abs(hit.point.x)<.8&&Math.abs(hit.point.z+3.8)<.64)id='nadir_port';
      if(!id&&hit.object.userData.isGlass)continue;
      if(id&&(this.looseItems.room(id)||PROPS[id].room)!==room&&!['card_reader','pressure_hatch'].includes(id))id=null;
      surface = id;
      limit = hit.distance;
      break;
    }
    if (smallControls.has(surface)) return surface;
    // A switch sits nearly flush with its housing. A small access volume
    // includes its bezel without allowing a reach through a partition.
    const point = new T.Vector3();
    let candidate = null,
      best = limit + (surface ? 0.075 : 0.025);
    for(const [id,body] of this.looseItems?.bodies??[]){
      const box=body.pickBox??=new T.Box3();
      box.setFromCenterAndSize(V(0,0,0),body.size).expandByScalar(.014).applyMatrix4(body.root.matrixWorld);
      if(!this.ray.ray.intersectBox(box,point))continue;
      const d=point.distanceTo(this.ray.ray.origin);
      if(d<best&&d<=limit+.012){candidate=id;best=d;}
    }
    for (const { id, n, box, worldBox } of this.touchZones || []) {
      if (!n.visible) continue;
      if(PROPS[id].room!==room&&!['card_reader','pressure_hatch'].includes(id))continue;
      worldBox.copy(box).applyMatrix4(n.matrixWorld);
      if (!this.ray.ray.intersectBox(worldBox, point)) continue;
      const distance = point.distanceTo(this.ray.ray.origin);
      if (distance < best && distance <= this.ray.far) {
        candidate = id;
        best = distance;
      }
    }
    return candidate || surface;
  }
  pickEvent(e) {
    const b = this.element.getBoundingClientRect();
    return this.pick(
      ((e.clientX - b.left) / b.width) * 2 - 1,
      1 - ((e.clientY - b.top) / b.height) * 2,
    );
  }
  safeToShut() {
    return Math.abs(this.position.z - 1.9) > 0.43;
  }
  isCurtainHandle(hit){
    const stile=this.furnishings.part('curtain').hardware.at(-1).node;
    for(let mesh=hit.object;mesh;mesh=mesh.parent)if(mesh===stile)return true;
    // The loop has an open middle. A passenger putting a finger through
    // that opening still has hold of the handle on the leading stile.
    const point=stile.worldToLocal(hit.point.clone());
    return Math.abs(point.z)<.052&&Math.abs(point.y-.022)<.116&&point.x>-.048;
  }
  curtainDragAxis(){
    const lead=this.furnishings.part('curtain').hardware.at(-1);
    const point=lead.node.getWorldPosition(V(0,0,0));
    const axis=lead.delta.clone().applyQuaternion(lead.node.parent.getWorldQuaternion(new T.Quaternion()));
    const a=point.clone().project(this.camera),b=point.addScaledVector(axis,.05).project(this.camera);
    const width=this.element.clientWidth,height=this.element.clientHeight;
    const dx=(b.x-a.x)*width*.5,dy=(a.y-b.y)*height*.5,length=Math.hypot(dx,dy);
    if(length<.01)return null;
    const span=clamp(length/.05,Math.min(width*.4,130),width*.63);
    return {x:dx/length/span,y:dy/length/span,start:this.base.privacy_curtain.v};
  }
  firstFabricHit(){
    const loose=this.looseItems?.meshes??[];
    const hits=this.fabricRay.intersectObjects(loose.length?this.hull.concat(loose):this.hull,false);
    for(const hit of hits){
      if(hit.object.userData.isGlass)continue;
      let visible=true;for(let n=hit.object;n;n=n.parent)if(!n.visible){visible=false;break;}
      if(!visible)continue;
      const part=hit.object.userData.fabricPart;
      if(!part||part.kind==='service'&&this.furnishings.cover<.6)return null;
      return {id:part.id,kind:part.kind,point:hit.point};
    }
    return null;
  }
  fabricHit(nx=0,ny=0){
    if(this.view!=='window'||this.inspection)return null;
    this.fabricRay.setFromCamera(new T.Vector2(nx,ny),this.camera);this.fabricRay.far=2.65;
    return this.firstFabricHit();
  }
  fabricHitEvent(e){
    const b=this.element.getBoundingClientRect();return this.fabricHit((e.clientX-b.left)/b.width*2-1,1-(e.clientY-b.top)/b.height*2);
  }
  aimFabric(kind){
    this.flight.reset(1.48);
    const part=this.furnishings.part(kind);if(!part)return false;
    if(part.kind==='service'&&(!this.rideState?.unlocked||this.furnishings.cover<.6))return false;
    if(part.kind==='quilt'&&this.furnishings.rail>.92)return false;
    const room=part.kind==='service'?'service':'berth',p=this.furnishings.target(kind);
    if(this.restId)this.stand();if(roomAt(this.position.z)!==room)this.go(room);
    this.view='window';this.lean=null;
    if(part.kind==='service')this.position.set(.99,1.47,clamp(p.z+.18,3.29,4.24));
    else if(part.kind==='quilt')this.position.set(-.70,1.48,.93);
    else this.position.set(-.44,1.49,clamp(p.z+.27,-1.39,1.43));
    this.aimAt(p.x,p.y,p.z);this.updateCamera(0);this.furnishings.deform(this.camera,'window');
    this.surveyedFabricPoint=null;
    if(part.kind==='service'){
      // The two spans cross in projection. Aim at exposed insulation on the
      // requested span and check occlusion against the open cabinet.
      for(const u of [.36,.65,.23,.77,.5]){
        const point=part.sample(u);this.aimAt(point.x,point.y,point.z);this.updateCamera(0);
        const direction=point.clone().sub(this.camera.position);
        this.fabricRay.far=direction.length()+.09;this.fabricRay.set(this.camera.position,direction.normalize());
        const hit=this.firstFabricHit();
        if(hit?.id===part.id){this.surveyedFabricPoint={id:part.id,u};return true;}
      }
      return false;
    }
    return true;
  }
  touchFabric(kind,worldPoint){
    const part=this.furnishings.part(kind);if(!part||this.view!=='window')return false;
    const surveyed=this.surveyedFabricPoint;
    const p=worldPoint??(surveyed?.id===part.id?part.sample(surveyed.u):this.furnishings.target(kind));
    const direction=p.clone().sub(this.camera.position),distance=direction.length();
    if(distance>2.65||distance<.01)return false;
    this.fabricRay.set(this.camera.position,direction.normalize());this.fabricRay.far=distance+.10;
    const hit=this.firstFabricHit();if(!hit||hit.id!==part.id)return false;
    return this.furnishings.touch(hit.id,hit.point);
  }
  gripFabric(hit){
    if(!hit||this.view!=='window'||!this.furnishings.grip(hit))return false;
    const distance=hit.point.distanceTo(this.camera.position),height=this.element.clientHeight||innerHeight;
    this.handReach={scale:2*distance*Math.tan(this.camera.fov*DEGREES*.5)/height,
      right:V(1,0,0).applyQuaternion(this.camera.quaternion),up:V(0,1,0).applyQuaternion(this.camera.quaternion),
      toward:V(0,0,1).applyQuaternion(this.camera.quaternion),delta:V(0,0,0)};
    return true;
  }
  pullFabric(dx,dy){
    const h=this.handReach;if(!h)return false;
    h.delta.copy(h.right).multiplyScalar(dx*h.scale).addScaledVector(h.up,-dy*h.scale);
    h.delta.addScaledVector(h.toward,Math.min(.048,h.delta.length()*.30));return this.furnishings.pull(h.delta);
  }
  releaseFabric(){this.handReach=null;return this.furnishings.release();}
  update(s, m, time, dt, active, monitor, unrestrained=active, eyeSeconds=dt, stargazing=false) {
    this.rideState=s;
    this.windowClearance(m.seconds);
    if(this.valveReturn>0){this.valveReturn-=dt;if(this.valveReturn<=0)s.deviceStops.mug=0;}
    this.deckLoad=clamp(m.forces.gravityG,0,1);
    this.dynamics.advance(m,time,dt,s.ventOn);
    this.movement(dt, s, active,unrestrained);
    this.updateCamera(dt);
    this.exterior.update(s, m, time,dt,eyeSeconds);
    this.clampGauge.update(this.exterior.terminals.bays.aster.coupling.travel);
    const goals = {
      roller_shade: +s.shade,
      privacy_curtain: +s.curtain,
      locker_drawer: +s.drawer,
      pressure_hatch: +s.hatch,
      service_cabinet: +s.cabinet,
      ascent_lever: s.feed / 2,
      docking_wheel: s.clamp / 3,
    };
    if (this.dragPreview) {
      const { id, travel } = this.dragPreview;
      const current = goals[id] || 0;
      const goal =
        id === 'docking_wheel' && s.progress < 1
          ? 0.075
          : id === 'ascent_lever'
            ? ((s.feed + 1) % 3) / 2
            : id === 'docking_wheel'
              ? Math.min(1, (s.clamp + 1) / 3)
              : 1 - current;
      goals[id] = current + (goal - current) * travel * 0.9;
    }
    for (const [id, target] of Object.entries(goals)) {
      const n = this.nodes[id],
        b = this.base[id],
        a = this.layout.props[id]?.animation;
      if (!n || !b || (!a&&id!=='privacy_curtain')) continue;
      const drawer=id==='locker_drawer';
      const w=id==='pressure_hatch'?5.6:id==='privacy_curtain'?(this.drawingCurtain?16:4.7):id==='roller_shade'?6.7:drawer?12:id==='docking_wheel'?10:15;
      const damping=drawer?1.50+.24*clamp(Math.abs(m.forces.down)/9.80665):1.72;
      const previousSpeed=b.speed||0,fullTarget=Number(s.drawer);
      if(drawer&&b.latchGoal!==fullTarget){b.travelStarted=b.latchGoal!==undefined;b.latchGoal=fullTarget;}
      const h=dt/Math.max(1,Math.ceil(dt/.013));b.speed??=0;
      for(let d=0;d<dt-.000001;d+=h){b.speed+=((target-b.v)*w*w-damping*w*b.speed)*h;
        b.v+=b.speed*h;if(b.v<0||b.v>1){b.v=clamp(b.v);b.speed*=-.08;}}
      if(drawer){
        b.railAcceleration=dt>0?(b.speed-previousSpeed)*a.amount/dt:0;
        if(b.travelStarted&&!this.dragPreview&&Math.abs(fullTarget-b.v)<.010){
          b.travelStarted=false;this.onFittingStop(id,!s.items.includes('access_card')&&!s.loose.access_card);
        }
      }
      if(id==='privacy_curtain')continue;
      const axis = a.axis;
      if (a.kind === 'translate') n.position[axis] = b.pos[axis] + a.amount * b.v;
      if (a.kind === 'scale') n.scale[axis] = b.scale[axis] * (1 + (a.amount - 1) * b.v);
      if (a.kind === 'rotate') {
        const rot = new T.Quaternion().setFromAxisAngle(
          axis === 'x' ? V(1, 0, 0) : axis === 'y' ? V(0, 1, 0) : V(0, 0, 1),
          a.amount * DEGREES * b.v,
        );
        n.quaternion.copy(b.quat).premultiply(rot);
      }
    }
    for(const [id,n] of Object.entries(this.nodes)) n.visible=visibleProp(id,s)&&!s.loose?.[id]&&this.inspection?.id!==id;
    for(const d of this.fixedDevices){d.factor+=(s.deviceStops[d.id]/(d.spec.detents-1)-d.factor)*(1-Math.exp(-dt*12));
      d.node.quaternion.copy(d.rest).multiply(d.quat.setFromAxisAngle(d.axis,d.factor*d.spec.amount*DEGREES));}
    for(const id of CARRIED){
      const node=this.nodes[id],base=this.base[id],p=mountProperties[id],force=this.dynamics.bodyForce;
      const offset=base.mount??=V(0,0,0),velocity=base.mountVelocity??=V(0,0,0);
      const lateral=force.x-(id==='access_card'?this.base.locker_drawer.railAcceleration||0:0);
      const x=clamp(lateral*p.side,-.005,.005),y=clamp(p.rise*(1+force.y/9.764),-.0012,p.rise*1.12);
      const z=clamp(force.z*p.side,-.003,.003),steps=Math.max(1,Math.ceil(dt*90)),h=dt/steps,k=p.frequency*p.frequency;
      for(let i=0;i<steps;i++){
        const drag=Math.exp(-1.54*p.frequency*h);
        velocity.x=(velocity.x+(x-offset.x)*k*h)*drag;velocity.y=(velocity.y+(y-offset.y)*k*h)*drag;
        velocity.z=(velocity.z+(z-offset.z)*k*h)*drag;offset.addScaledVector(velocity,h);
      }
      node.position.copy(base.pos).add(offset);
    }
    this.vesselCradle.update(dt);
    const light=this.photometry;light.update(s,m,time,dt,this.position,stargazing);
    const settle=1-Math.exp(-dt*5);
    this.earthBounce.intensity=light.bounce;
    const night=1-smoothLight(m.sunDirection[1]);
    this.practical.intensity=T.MathUtils.lerp(this.practical.intensity,s.lamps?5.1+5.0*night:.025,settle);
    this.sleeper.intensity=s.berthLight?3.90:.035;this.loom.intensity=T.MathUtils.lerp(this.loom.intensity,s.bayLight?5.8:0,settle);
    this.trayLamp.target.position.copy(this.trayCenter).applyMatrix4(this.nodes.access_card.matrixWorld);
    this.trayLamp.position.copy(this.trayLamp.target.position);this.trayLamp.position.y+=.225;this.trayLamp.position.x+=.055;
    this.trayLamp.intensity=this.base.locker_drawer.v*.52;
    this.service.intensity=3.75;this.instrumentLight.intensity=.23;
    for (const [key, v] of [
      ['lamp', s.lamps],
      ['reading_lamp', s.berthLight],
    ])
      for (const [mat, base] of this.emitterGroups[key]) mat.emissiveIntensity = v ? base : 0.015;
    for (const [mat] of this.emitterGroups.card_reader)
      if (/mint|amber/i.test(mat.name)) mat.emissive.set(s.unlocked ? 0xaaefe3 : 0xffa059);
    this.inspection?.update(this.camera,dt,this.dynamics);
    if(this.inspection){
      this.handLight.position.copy(this.lightOffset.set(-.21,.08,.025).applyQuaternion(this.camera.quaternion)).add(this.camera.position);
      this.handLight.target.position.copy(this.inspection.rig.position);
      this.handLight.intensity=this.inspection.workLamp?.25:0;
      this.handLight.shadow.needsUpdate=this.inspection.workLamp&&this.r.shadowMap.enabled;
    }else this.handLight.intensity=0;
    this.switchboard.update(s,m,time,dt);
    this.furnishings.advance(dt,time,this.dynamics.bodyForce,this.switchboard.fanSpeed/17,
      this.base.privacy_curtain.v,this.base.service_cabinet.v,this.restId==='bunk');
    this.furnishings.deform(this.camera,this.view);
    this.fixtures?.update(s,m,time,dt);
    this.fracture.advance(s,this.dynamics.bodyForce,dt);
    this.scene.updateMatrixWorld(true);
    this.looseItems.update(s,m,dt,time);
    this.dynamics.deform();
    light.reflect(time,this.inspection?.rig);
    this.instruments.capture(this.r,this.exterior,s,m,time,monitor);
    const camera=this.inspection?this.camera:this.sensorCamera(m);
    this.optics.render(this.scene,camera,this.inspection);
  }
  hold(id,panel){this.hideModel();const source=this.nodes[id];if(!source||!CARRIED.includes(id))return false;
    this.view='window';this.inspection=new InHand(this.scene,source,id,panel,this.mechanisms[id],this.rideState||{deviceStops:{field_glasses:0,mug:0,logbook:0,tool_roll:0}});
    const device=this.fixedDevices.find(d=>d.id===id);
    if(device)this.inspection.initialJoint.copy(device.rest);
    this.dynamics.handling(id,this.inspection.copy);return true;}
  presentKey(onRead,onCancel){
    this.aimFitting('card_reader');
    const temporary=this.inspection?.id!=='access_card';
    if(temporary)this.hold('access_card',{getBoundingClientRect:()=>({left:innerWidth,width:0,top:innerHeight})});
    const item=this.inspection;
    item.onTapCancel=onCancel;
    item.tapReader(new T.Vector3(...this.layout.props.card_reader.webCenter).add(new T.Vector3(0,0,-.064)),onRead,()=>{
      item.onTapCancel=null;if(temporary&&this.inspection===item)this.hideModel();
    });
  }
  operateHeld(direction=1){
    const changed=this.inspection?.operate(direction);
    if(changed&&this.inspection.id==='mug')this.valveReturn=.64;
    if(changed)this.dynamics.handJolt(this.inspection.id==='tool_roll'?.10:.035);
    return changed;
  }
  hideModel(){this.lean=null;this.fittingPanel=null;if(this.camera.view?.enabled)this.camera.clearViewOffset();
    if(this.inspection){if(this.inspection.tap&&!this.inspection.tap.read)this.inspection.onTapCancel?.();this.dynamics.handling(null,null);}
    this.inspection?.release();this.inspection=null;}
}
function smoothLight(y){const f=clamp((y+.06)/.55);return f*f*(3-2*f);}
