const wheelSounds = ['CenterJaws', 'DrawCollar', 'LockCollar'];
const impactSounds = {mug:'VesselImpact',field_glasses:'OpticsImpact',logbook:'FolioImpact',access_card:'KeycardImpact',tool_roll:'WalletImpact'};
const wheelPosition = {x:0,y:1.27,z:5.43};

export class CabinAudio {
  constructor() {
    this.enabled = true;
    this.ctx = null;
    this.gain = null;
    this.osc = [];
    this.lastStep = -1;
    this.clips = new Map();
    try {
      this.enabled = localStorage.getItem('upwell.sound') !== 'off';
    } catch {}
  }
  async start() {
    if (!this.ctx) {
      const AudioEngine = window.AudioContext || window.webkitAudioContext;
      if (!AudioEngine) return;
      this.ctx = new AudioEngine();
      this.gain = this.ctx.createGain();
      this.gain.gain.value = this.enabled ? 0.24 : 0;
      this.gain.connect(this.ctx.destination);
      for(const name of ['GuideJoint','SleeveContact',...wheelSounds,...Object.values(impactSounds)]) {
        fetch('./assets/audio/'+name+'.wav').then(r=>r.ok?r.arrayBuffer():Promise.reject())
          .then(bytes=>this.ctx.decodeAudioData(bytes)).then(clip=>this.clips.set(name,clip)).catch(()=>{});
      }
      for (const [hz, volume, wave] of [
        [49, 0.085, 'sine'],
        [98.2, 0.019, 'sine'],
        [122, 0.008, 'triangle'],
      ]) {
        const o = this.ctx.createOscillator(),
          g = this.ctx.createGain();
        o.type = wave;
        o.frequency.value = hz;
        g.gain.value = volume;
        o.connect(g);
        g.connect(this.gain);
        o.start();
        this.osc.push(o);
      }
      const buffer = this.ctx.createBuffer(1, this.ctx.sampleRate * 2, this.ctx.sampleRate);
      const channel = buffer.getChannelData(0);
      let previous = 0;
      for (let i = 0; i < channel.length; i++) {
        previous = 0.91 * previous + 0.09 * (Math.random() * 2 - 1);
        channel[i] = previous;
      }
      this.noise = buffer;
      const fan = this.ctx.createBufferSource(),
        filter = this.ctx.createBiquadFilter(),
        g = this.ctx.createGain();
      fan.buffer = buffer;
      fan.loop = true;
      filter.type = 'lowpass';
      filter.frequency.value = 925;
      g.gain.value = 0.11;
      fan.connect(filter);
      filter.connect(g);
      g.connect(this.gain);
      fan.start();
      this.fan = filter;
      this.fanGain = g;
    }
    if (this.ctx.state === 'suspended') await this.ctx.resume().catch(() => {});
  }
  toggle() {
    this.enabled = !this.enabled;
    this.start().catch(() => {});
    if (this.gain)
      this.gain.gain.setTargetAtTime(this.enabled ? 0.24 : 0, this.ctx.currentTime, 0.04);
    if (!this.enabled && 'speechSynthesis' in window) speechSynthesis.cancel();
    try {
      localStorage.setItem('upwell.sound', this.enabled ? 'on' : 'off');
    } catch {}
  }
  tone(from, to, dur, vol = 0.23, delay = 0, type = 'sine') {
    if (!this.ctx || !this.enabled) return;
    const now = this.ctx.currentTime + delay,
      o = this.ctx.createOscillator(),
      g = this.ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(from, now);
    o.frequency.exponentialRampToValueAtTime(Math.max(16, to), now + dur);
    g.gain.setValueAtTime(0.001, now);
    g.gain.exponentialRampToValueAtTime(vol, now + 0.008);
    g.gain.exponentialRampToValueAtTime(0.001, now + dur);
    o.connect(g);
    g.connect(this.gain);
    o.start(now);
    o.stop(now + dur + 0.02);
  }
  hiss(duration, freq, vol = 0.22, delay = 0) {
    if (!this.ctx || !this.enabled || !this.noise) return;
    const now = this.ctx.currentTime + delay,
      n = this.ctx.createBufferSource(),
      f = this.ctx.createBiquadFilter(),
      g = this.ctx.createGain();
    n.buffer = this.noise;
    n.loop = true;
    f.type = 'bandpass';
    f.frequency.value = freq;
    f.Q.value = 0.7;
    g.gain.setValueAtTime(0.001, now);
    g.gain.exponentialRampToValueAtTime(vol, now + Math.min(0.05, duration * 0.25));
    g.gain.exponentialRampToValueAtTime(0.001, now + duration);
    n.connect(f);
    f.connect(g);
    g.connect(this.gain);
    n.start(now, Math.random() * 0.6);
    n.stop(now + duration + 0.01);
  }
  contactSound(name, position, volume) {
    if(!this.ctx || !this.enabled || !this.clips.has(name)) return false;
    const source=this.ctx.createBufferSource(),gain=this.ctx.createGain();
    source.buffer=this.clips.get(name);
    const listener=this.listener;
    let distance=0,pan=0;
    if(listener && position) {
      const dx=position.x-listener.x,dz=position.z-listener.z;
      distance=Math.hypot(dx,position.y-listener.y,dz);
      pan=.85*(dx*Math.cos(this.heading)-dz*Math.sin(this.heading))/(distance+.45);
    }
    gain.gain.value=volume*(.37+.63/(1+.18*distance));
    source.connect(gain);
    if(this.ctx.createStereoPanner) {
      const stereo=this.ctx.createStereoPanner();stereo.pan.value=pan;gain.connect(stereo);stereo.connect(this.gain);
    } else gain.connect(this.gain);
    source.start();
    return true;
  }
  dockTurn(turns) {
    if(!this.contactSound(wheelSounds[turns-1],wheelPosition,1.12))this.play('clamp');
    else if('vibrate' in navigator)navigator.vibrate(turns===3?[16,30,24]:12);
  }
  structure(world, metrics, dt) {
    this.listener=world.position;this.heading=world.yaw;
    const guide=world.exterior.guideway;
    const metres=guide.distanceTravelled;
    const index=Math.floor(metres/guide.layout.splicePeriod);
    const complete=world.exterior.terminals.bays.aster.coupling.sleeve>=1;
    const sec=metrics.seconds;
    const continuous=this.previousRoute!==undefined && sec>=this.previousRoute-.002 && sec-this.previousRoute<.6;
    if(continuous) {
      if(complete&&!this.wasSeated)this.contactSound('SleeveContact',wheelPosition,.90);
      const speed=dt>0?Math.abs(metres-this.lastMetres)/dt:0;
      if(index===this.lastJoint+1 && speed>.12 && speed<46) {
        const strength=.62*Math.min(1,speed/4)*Math.min(1,(46-speed)/16);
        const lane=guide.layout.placements[0].position;
        this.contactSound('GuideJoint',{x:lane[0],y:lane[1],z:lane[2]},strength);
      }
    }
    this.previousRoute=sec;this.lastMetres=metres;this.lastJoint=index;this.wasSeated=complete;
  }
  impact(id,force,point){
    if(this.contactSound(impactSounds[id],point,Math.min(1.1,.15+force)))return;
    const hit={
      mug:[1080,470,.24,.14],field_glasses:[245,98,.13,.25],
      logbook:[145,68,.09,.26],tool_roll:[182,106,.12,.38],access_card:[890,280,.055,.078],
    }[id];
    if(!hit)return;
    const [from,to,time,gain]=hit;
    this.tone(from,to,time,Math.max(.002,gain*force),0,'triangle');
    this.hiss(time*.74,id==='tool_roll'?780:1670,Math.max(.002,force*gain));
  }
  chip(force){
    const gain=Math.max(.002,.12*force);
    this.tone(2310,1740,.043,gain,0,'sine');this.hiss(.025,3300,gain*.5,.001);
  }
  play(kind) {
    if (!this.ctx || !this.enabled) return;
    switch (kind) {
      case 'fractureCam':
        this.tone(270,129,.055,.11,0,'triangle');this.hiss(.09,640,.11);break;
      case 'fractureSnap':
        this.hiss(.015,4700,.82);this.tone(3120,2220,.07,.35,.003,'triangle');
        this.tone(1130,910,.13,.16,.014);this.tone(238,130,.084,.21,.006,'triangle');break;
      case 'fractureIndex':
        this.hiss(.27,1270,.31);this.tone(179,104,.15,.18,.014,'triangle');break;
      case 'fractureSeat':
        this.tone(520,258,.067,.17,0,'triangle');this.hiss(.16,960,.13,.09);break;
      case 'runner':
        this.hiss(.28,920,.36);this.tone(152,100,.19,.13,0,'triangle');break;
      case 'drawerStop':
        this.tone(132,64,.087,.29,0,'triangle');this.hiss(.042,1320,.23);break;
      case 'cardTap':
        this.tone(1050,498,.042,.09,.016,'triangle');break;
      case 'proof':
        this.tone(570,270,.050,.15,0,'triangle');this.tone(218,208,.21,.07,.035);break;
      case 'prime':
        this.hiss(.16,540,.44);this.tone(152,83,.12,.20,0,'triangle');this.tone(483,260,.06,.12,.18,'triangle');break;
      case 'brush':
        this.hiss(.22,1750,.48);this.hiss(.12,830,.19,.07);break;
      case 'pluck':
        this.tone(118,88,.24,.22,0,'triangle');this.hiss(.08,850,.23);break;
      case 'focus':
        this.hiss(.055,2700,.26);this.tone(740,390,.035,.18,0,'triangle');this.tone(290,145,.06,.1,.035,'triangle');break;
      case 'valve':
        this.tone(425,160,.09,.26,0,'triangle');this.hiss(.18,1760,.33,.035);this.tone(300,125,.063,.17,.21);break;
      case 'folio':
        this.hiss(.28,2200,.72);this.tone(137,72,.09,.14,.24,'triangle');break;
      case 'keeper':
        this.hiss(.14,1150,.55);this.tone(1180,270,.065,.22,.08,'triangle');break;
      case 'detent':
        this.tone(690, 180, 0.045, 0.36, 0, 'triangle');
        this.hiss(0.06, 2200, 0.42);
        this.tone(123, 72, 0.085, 0.29, 0.04);
        break;
      case 'slide':
        this.tone(118, 64, 0.32, 0.23, 0, 'triangle');
        this.hiss(0.38, 750, 0.55);
        this.tone(151, 75, 0.075, 0.32, 0.31);
        break;
      case 'shade':
        this.hiss(0.68, 1400, 0.32);
        this.tone(195, 138, 0.65, 0.12, 0, 'triangle');
        this.tone(220, 117, 0.07, 0.18, 0.64);
        break;
      case 'equalize':
        this.tone(735, 735, 0.11, 0.16);
        this.hiss(1.25, 2100, 1.18, 0.12);
        this.tone(1030, 1030, 0.12, 0.17, 1.24);
        break;
      case 'hatch':
        this.tone(95, 62, 0.85, 0.3, 0, 'triangle');
        this.hiss(0.78, 600, 0.5);
        this.tone(95, 38, 0.24, 0.66, 0.74);
        break;
      case 'clamp':
        this.hiss(0.12, 1100, 0.5);
        this.tone(165, 72, 0.19, 0.37, 0, 'triangle');
        this.tone(90, 41, 0.23, 0.5, 0.12);
        break;
      case 'alert':
        this.tone(535, 535, 0.14, 0.16);
        this.tone(795, 795, 0.19, 0.15, 0.19);
        break;
      case 'traffic':
        this.tone(45, 88, 0.48, 0.62);
        this.tone(86, 35, 1.2, 0.67, 0.4);
        this.hiss(1.25, 320, 1.1);
        break;
      case 'no':
        this.tone(196, 165, 0.12, 0.19);
        break;
      case 'step':
        this.tone(86, 40, 0.11, 0.2);
        this.hiss(0.105, 420, 0.26);
        break;
      case 'handhold':
        this.hiss(.075,690,.10);this.tone(187,121,.053,.025,0,'triangle');
        break;
      default:
        this.tone(610, 215, 0.055, 0.19, 0, 'triangle');
        this.hiss(0.05, 1700, 0.22);
    }
    if ('vibrate' in navigator && ['detent', 'clamp', 'hatch'].includes(kind))
      navigator.vibrate(kind === 'clamp' ? [16, 24, 25] : 12);
  }
  update(speed, room, ventilation = true) {
    if (!this.ctx) return;
    this.osc[0].frequency.setTargetAtTime(39 + (10 * speed) / 612, this.ctx.currentTime, 0.7);
    this.fan.frequency.setTargetAtTime(
      room === 'service' ? 1550 : room === 'berth' ? 620 : 980,
      this.ctx.currentTime,
      0.4,
    );
    this.fanGain.gain.setTargetAtTime(ventilation ? .11 : 0, this.ctx.currentTime, ventilation ? .29 : .49);
  }
}
