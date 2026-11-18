const units = [
  ['guide_flood','Guide inspection flood','EL / 112','A guarded lever powers the white work light over the port guide wheels. The guide camera looks directly into its beam.'],
  ['cabin_lights','Cabin light rocker','EL / 211','The split rocker switches the saloon lights. For stargazing, switch them off and turn the display luminance down.'],
  ['solar_film','Solar film paddle','PV / 207','This amber paddle runs the forward solar film between the two limits of its track.'],
  ['vent_fan','Circulation fan switch','EC / 116','The crossbar switches the overhead impeller. Air from the grille moves the loose restraints and wrist cords.'],
  ['key_route','Passage page key','AV / 121','Selects passage altitude, elapsed ship time and the current climb sector on the wide display.'],
  ['key_optics','Exterior optics key','AV / 122','Selects the live camera image. The selector lever chooses the head and the lens encoder changes its field of view.'],
  ['key_seals','Pressure page key','AV / 123','Brings up the pressure taps, service access and transfer clamp on the wide display.'],
  ['key_load','Apparent load key','AV / 124','Shows which way loose objects fall. Press LOAD again to mark the vertical reading or clear its reference.'],
  ['key_traffic','Counterline traffic key','AV / 125','Shows the next or passing counterline car, its service class and crossing time.'],
  ['key_comms','Crew radio key','CO / 126','Calls the current operations bulletin from the crew channel. The wide display carries the local transcript.'],
  ['key_lamp_test','Annunciator test key','EL / 127','Energizes every switch witness light for a timed lamp check. The other controls keep their positions.'],
  ['panel_gain','Display luminance encoder','AV / 128','Five mechanical stops set the brightness of the three flight-deck screens.'],
  ['camera_focus','Camera lens encoder','OP / 129','Five stops change the focal length of the selected exterior camera. The narrowest field resolves detail on the guide and passing traffic.'],
  ['diagnostic_screen','Environmental display','EC / 131','Touch the small port screen to alternate between cabin air and the 28-volt electrical bus.'],
  ['drive_screen','Traction display','DR / 132','Touch the drive repeater to choose motor output or guide pickup readings.'],
  ['test_power','Power bus test','EW / 521','Loads the 28-volt feeder with its calibrated resistor and measures the return voltage at the far connector.'],
  ['test_fiber','Fiber loopback test','EW / 522','Sends an optical packet around the blue return loop. The receiver measures optical loss.'],
  ['test_seal','Pressure reference test','PV / 523','Applies the internal 0.20 kPa calibration reference to the seal instrument, then returns its taps to the hatch.'],
  ['test_return','Guide pickup test','EW / 524','Sends the pickup reference to the guide head and measures the phase offset on the return pair.'],
];
export const SWITCHES = Object.fromEntries(units.map(([id,name,tag,description]) => [
  id,{id,name,tag,description,room:id.startsWith('test_')?'service':'observation'},
]));
export const GAIN = [.32,.55,.8,1,1.25];
export const FOV = [72,52,36,23,14];
export const LENS_MM = FOV.map(angle => Math.round(12/Math.tan(angle*Math.PI/360)));
export const PAGES = ['Passage','Exterior optics','Pressure and seals','Apparent load','Counterline traffic','Crew radio'];
export const PAGE_KEYS = ['key_route','key_optics','key_seals','key_load','key_traffic','key_comms'];
export const CIRCUITS = ['test_power','test_fiber','test_seal','test_return'];
export const TEST_NAMES = ['DC FEED','FIBER LOOP','PRESSURE REF','GUIDE RETURN'];
export const BULLETINS = [
  'Bridge retracting. Stand clear of the guide bay.',
  'Upper gantry clear. The ocean platform is below the carriage.',
  'Entering the marine cloud field. Sunlight will be intermittent.',
  'Clearing the high cloud tops.',
  'Stratosphere sector. The atmosphere is thinning.',
  'Passing one hundred kilometres. The bright edge below is the atmosphere.',
  'Earth limb sector. The lower camera is tracking the surface.',
  'High orbit. The Earth camera is available at the window seat.',
  'Aster Reach has the carriage. Braking for the receiving vault.',
  'Receiving bay. The capture arms are standing by.',
  'Terminal collar aligned. Seat the transfer clamp with the service handwheel.',
];
export const freshSwitchState = () => ({
  guideFlood:false,ventOn:true,panelGain:2,cameraLens:1,diagElectrical:false,driveGuides:false,loadReference:null,
});
export function restoreSwitchState(state,raw) {
  for(const [id,initial] of Object.entries(freshSwitchState())){
    if(id==='loadReference')state[id]=Number.isFinite(raw[id])&&Math.abs(raw[id])<=1.2?raw[id]:null;
    else if(typeof initial==='boolean')state[id]=typeof raw[id]==='boolean'?raw[id]:initial;
    else state[id]=Number.isInteger(raw[id])?Math.max(0,Math.min(4,raw[id])):initial;
  }
  return state;
}
export const switchVisible = (id,s) => !CIRCUITS.includes(id)||s.cabinet;
export function switchLabel(id,s){
  const page=PAGE_KEYS.indexOf(id);
  if(id==='key_load'&&s.screen===3)return Number.isFinite(s.loadReference)?'Clear load reference':'Mark vertical load';
  if(page>=0)return page===5?'Receive bulletin':'Show '+PAGES[page].toLowerCase();
  if(CIRCUITS.includes(id))return 'Run test';
  return ({
    guide_flood:s.guideFlood?'Extinguish flood':'Light the guide',cabin_lights:s.lamps?'Lights off':'Lights on',
    solar_film:s.shade?'Retract film':'Deploy film',vent_fan:s.ventOn?'Stop fan':'Start fan',
    key_lamp_test:'Test witness lights',panel_gain:'Turn brighter',camera_focus:'Increase focal length',
    diagnostic_screen:s.diagElectrical?'Read cabin air':'Read power bus',drive_screen:s.driveGuides?'Read traction':'Read guide heads',
  })[id];
}
export function electrical(s){
  const amps=1.32+(s.lamps?2.46:0)+(s.berthLight ? .57:0)+(s.ventOn ? .91:0)+(s.bayLight?1.24:0)+(s.guideFlood?3.85:0)+.19*(s.panelGain??2);
  return {amps,volts:28.43-amps*.043};
}
export const crewClock = seconds => {
  const n=Math.floor(seconds+4*3600+12*60);
  return [Math.floor(n/3600)%24,Math.floor(n/60)%60,n%60].map(x=>String(x).padStart(2,'0')).join(':');
};
