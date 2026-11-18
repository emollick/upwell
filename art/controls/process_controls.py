"""Deterministic crop, alpha cleanup, manifest and contact sheet; no synthetic upscaling."""
from pathlib import Path
import json,re,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
GROUPS={
 'switches':['guide_flood','cabin_lights','solar_film','vent_fan'],
 'keys_a':['key_route','key_optics','key_seals','key_load'],
 'keys_b_port':['key_traffic','key_comms','key_lamp_test','floor_observation_port'],
 'encoders_displays':['panel_gain','camera_focus','diagnostic_screen','drive_screen'],
 'service':['test_power','test_fiber','test_seal','test_return'],
}
catalog={m[0]:dict(name=m[1],tag=m[2],description=m[3]) for m in re.findall(r"\['([^']+)','([^']+)','([^']+)','([^']+)'\]",(PROJECT/'web/control-catalog.js').read_text().split('export const SWITCHES')[0])}
catalog['floor_observation_port']=dict(name='Sealed floor observation port',tag='PRESSURE GLAZING',description='Closed laminated observation glazing, titanium pressure frame and double elastomer seals; no open hatch.')
scans={x['asset']:x for x in json.loads((ROOT.parent/'surface-scans/sources.json').read_text())}
def finish(name,scan,tint,roughness,metallic,normal_strength):
 return dict(material=name,source_asset=scan,source_page=scans[scan]['page'],license='CC0',maps={k:f'../surface-scans/{scan}/{k}.jpg' for k in ['albedo','normal','roughness']},tint_srgb=tint,roughness_target=roughness,metallic=metallic,normal_strength=normal_strength,usage='Retint/remap measured source microstructure; material is a finish approximation, not a measured aerospace alloy.')
FINISHES={
 'Graphite_Alloy':finish('Graphite_Alloy','metal_plate',[.12,.15,.17],.34,.8,.12),
 'Titanium':finish('Titanium','metal_plate',[.63,.66,.68],.27,.92,.1),
 'Carbon_Ceramic':finish('Carbon_Ceramic','blue_metal_plate',[.025,.035,.04],.29,.05,.06),
 'Black_Rubber':finish('Black_Rubber','rubber_tiles',[.012,.015,.017],.62,0,.08),
 'Grip_Elastomer':finish('Grip_Elastomer','scuba_suede',[.028,.035,.037],.54,0,.1),
 'Sapphire_Glass':dict(material='Sapphire_Glass',source_asset=None,maps={},ior=1.52,roughness=.075,transmission=1,thickness_m=.024,usage='Analytic dielectric; no opaque scan painted onto glass. Existing nav_screen procedural roughness is optional, not a factual scan.'),
 'Witness_Amber':dict(material='Witness_Amber',source_asset=None,maps={},color_srgb=[1,.54,.17],roughness=.23,emission=1.1,usage='Analytic tinted lens/emission; not a measured material.'),
 'Witness_Teal':dict(material='Witness_Teal',source_asset=None,maps={},color_srgb=[.28,.83,.78],roughness=.23,emission=1.1,usage='Analytic tinted lens/emission; not a measured material.'),
}
entries=[]
for group,ids in GROUPS.items():
 sheet=Image.open(ROOT/'sheets'/f'{group}.png').convert('RGBA');w,h=sheet.size
 for i,id in enumerate(ids):
  x0=(i%2)*(w//2);y0=(i//2)*(h//2);rect=(x0,y0,x0+w//2,y0+h//2)
  im=sheet.crop(rect);arr=np.array(im);alpha=arr[:,:,3]
  # Remove low-alpha disconnected generation spill, preserve original antialiasing
  # close to the largest opaque object; do not infer background from RGB color.
  core=ndi.binary_opening(alpha>=220,iterations=2)
  labels,count=ndi.label(core);sizes=np.bincount(labels.ravel());sizes[0]=0
  keep=ndi.binary_dilation(labels==sizes.argmax(),iterations=3)
  cleaned=np.where(keep,alpha,0).astype('uint8');arr[:,:,3]=cleaned
  im=Image.fromarray(arr);box=im.getbbox();pad=12
  box=(max(0,box[0]-pad),max(0,box[1]-pad),min(im.width,box[2]+pad),min(im.height,box[3]+pad))
  im=im.crop(box);a=im.getchannel('A');sil=a.point(lambda v:255 if v>=128 else 0)
  im.save(ROOT/'refs'/f'{id}.png');a.save(ROOT/'masks'/f'{id}_alpha.png');sil.save(ROOT/'masks'/f'{id}_silhouette.png')
  mats=['Graphite_Alloy','Titanium','Black_Rubber']
  if id.startswith('key_') or id in ['cabin_lights','panel_gain','test_fiber','test_return']:mats+=['Carbon_Ceramic']
  if id in ['vent_fan','camera_focus']:mats+=['Grip_Elastomer']
  if id in ['floor_observation_port','diagnostic_screen','drive_screen']:mats+=['Sapphire_Glass']
  if id!='floor_observation_port':mats+=['Witness_Amber' if id in ['guide_flood','solar_film','key_comms','key_lamp_test','test_power','test_seal'] else 'Witness_Teal']
  aa=np.array(a)
  entries.append(dict(id=id,**catalog[id],variant='generated_documentary_concept',reference=f'refs/{id}.png',alpha=f'masks/{id}_alpha.png',silhouette=f'masks/{id}_silhouette.png',source_sheet=f'sheets/{group}.png',sheet_dimensions=[w,h],sheet_quadrant_xyxy=rect,crop_within_quadrant_xyxy=box,dimensions=im.size,material_assignments=mats,registration='Reference/alpha/silhouette exactly pixel registered. Generated view is not UV-, camera-, or geometry-registered to the production mesh.',alpha_cleanup='Largest alpha>=220 component after 2px opening, expanded3px; original alpha retained inside. No RGB threshold or hand-drawn silhouette.',removed_alpha_pixels=int(((alpha>0)&(cleaned==0)).sum()),transparent_fraction=float((aa==0).mean()),silhouette_area=int((aa>=128).sum()),sha256=hashlib.sha256((ROOT/'refs'/f'{id}.png').read_bytes()).hexdigest()))
manifest=dict(version=1,count=len(entries),generation='Built-in image_gen; five explicitly authorized four-piece family sheets; no API/CLI fallback',rendered_variants=0,generated_variants=len(entries),limitations=['Returned source sheets are1254x1254 despite a2048 request. Native crops are not upscaled.','These are generated documentary-style concept references, not photographs of manufactured hardware or exact Blender renders.','Knurl counts, fasteners, dimensions and legend placement may differ from source geometry.','No per-pixel material segmentation or UV registration is claimed. Glass rendered alpha is coverage, not physical transmission.'],finishes=FINISHES,items=entries)
regions={'Graphite_Alloy':'housing and mounting bezel','Titanium':'guards, stem, cap, retaining rim and exposed fasteners','Black_Rubber':'gasket and seal','Carbon_Ceramic':'button or rocker face','Grip_Elastomer':'crossbar or lens knob grip','Sapphire_Glass':'closed glazing surface','Witness_Amber':'amber witness slit or lens','Witness_Teal':'teal witness slit or lens'}
for entry in entries:
 entry['finish_regions']={name:regions[name] for name in entry['material_assignments']}
 if entry['id']=='key_optics':entry['visible_variation']='Generated CAM key lacks requested witness slit; production geometry remains authoritative.'
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
canvas=Image.new('RGB',(1400,1660),(20,27,31));d=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
d.text((24,16),'UPWELL / FITTINGS REFERENCE INDEX',font=font,fill=(235,237,231));d.text((24,46),'20 GENERATED CONCEPT REFERENCES / ALPHA-DERIVED MASKS / SOURCE PBR ASSIGNMENTS',font=small,fill=(140,174,174))
for j,e in enumerate(entries):
 x=20+(j%4)*345;y=84+(j//4)*310
 im=Image.open(ROOT/e['reference']);im.thumbnail((320,257),Image.Resampling.LANCZOS);canvas.paste(im,(x+(320-im.width)//2,y+(257-im.height)//2),im)
 d.text((x,y+266),e['name'],font=small,fill=(235,237,231));d.text((x,y+286),e['id'],font=small,fill=(127,165,167))
canvas.save(ROOT/'contact-sheet.jpg',quality=94)
assert set(catalog)=={e['id'] for e in entries}
assert all(e['transparent_fraction']>.02 and e['silhouette_area']>10000 for e in entries)
for f in FINISHES.values():
 for path in f['maps'].values():assert (ROOT/path).exists(),path
for e in entries:
 im=Image.open(ROOT/e['reference']);a=Image.open(ROOT/e['alpha']);s=Image.open(ROOT/e['silhouette'])
 assert np.array_equal(np.array(im.getchannel('A')),np.array(a))
 assert np.array_equal(np.array(a)>=128,np.array(s)>0)
report=dict(status='passed',catalog_fittings=19,floor_ports=1,references=20,alpha_masks=20,silhouettes=20,sheets=5,exact_alpha_registration=True,all_material_map_paths_exist=True,empty_or_opaque_masks=0,output_dimensions={e['id']:e['dimensions'] for e in entries})
(ROOT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
