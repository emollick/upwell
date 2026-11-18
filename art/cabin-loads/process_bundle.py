from pathlib import Path
import json,shutil,hashlib,os
import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
TEX=PROJECT/'unity/Assets/Upwell/SourceModels/Textures'
specs=json.loads((TEX/'materials.json').read_text())
prompts=json.loads((ROOT/'prompts.json').read_text())
names={'accelerometer':'Axial accelerometer','accel_test':'+0.10 g test plunger','capillary_cell':'77% capillary sight cell','capillary_primer':'Capillary primer piston','loom_service_power':'Orange feeder service span','loom_service_fiber':'Blue fiber service span','cloth_berth_quilt':'Stitched ripstop berth quilt','cloth_berth_curtain':'Pleated acoustic berth curtain'}
assign={
 'accelerometer':['Anodized_Frame','Handheld_Shell','Precision_Titanium','Black_Rubber','Carbon_Ceramic','Ceramic_Pearl','Gravity_Print','Load_Mass','Load_Index','Cell_Optical_Glass'],
 'accel_test':['Anodized_Frame','Precision_Titanium','Load_Index'],
 'capillary_cell':['Anodized_Frame','Handheld_Shell','Precision_Titanium','Black_Rubber','Cell_Diffuser','Cell_Etch','Cell_Optical_Glass','Cell_Liquid','Cell_Gas','Cell_Meniscus','Wick_Mesh','Gravity_Print'],
 'capillary_primer':['Titanium','Anodized_Frame','Precision_Titanium','Load_Index'],
 'loom_service_power':['Cable_Orange','Anodized_Frame','Precision_Titanium','Grip_Elastomer','Technical_Twill','Load_Index'],
 'loom_service_fiber':['Cable_Cyan','Anodized_Frame','Precision_Titanium','Grip_Elastomer','Technical_Twill','Load_Index'],
 'cloth_berth_quilt':['Quilt_Ripstop','Quilt_Lining','Berth_Bias_Tape'],
 'cloth_berth_curtain':['Curtain_Acoustic','Quilt_Lining','Berth_Bias_Tape','Precision_Titanium','Anodized_Frame'],
}
evidence={'accelerometer':'qa/cabin-loads/finished/loaded-pointer.jpg','accel_test':'qa/cabin-loads/finished/test-stroke.jpg','capillary_cell':'qa/cabin-loads/finished/ground-cell.jpg','capillary_primer':'qa/cabin-loads/finished/primer-target.jpg','loom_service_power':'qa/fabric-evidence/12-cable-in-hand.jpg','loom_service_fiber':'qa/fabric-evidence/09-panel-open-anchor.jpg','cloth_berth_quilt':'qa/fabric-evidence/01-berth-anchor.jpg','cloth_berth_curtain':'qa/fabric-evidence/06-screen-drawn.jpg'}
items=[]
for g in prompts['groups']:
 target=ROOT/'sheets'/f"{g['id']}.png";shutil.copy2(g['source'],target)
 sheet=Image.open(target).convert('RGBA');arr=np.array(sheet);w,h=sheet.size
 # Locate a real transparent gutter rather than assume exact generated alignment.
 score=(arr[:,:,3]>220).sum(axis=0);lo,hi=int(w*.43),int(w*.56);cut=lo+int(np.argmin(score[lo:hi]))
 assert score[cut]<10,(g['id'],'no clean gutter')
 for j,id in enumerate(g['ids']):
  if id=='cloth_privacy_curtain':id='cloth_berth_curtain'
  bounds=(0,0,cut,h) if j==0 else (cut,0,w,h)
  a=np.array(sheet.crop(bounds));alpha=a[:,:,3]
  core=ndi.binary_opening(alpha>=220,iterations=1);labels,n=ndi.label(core);sizes=np.bincount(labels.ravel());sizes[0]=0
  # Keep all substantial islands (instrument labels are separate real assemblies).
  allowed=np.where(sizes>max(80,sizes.max()*.0008))[0]
  keep=ndi.binary_dilation(np.isin(labels,allowed),iterations=2)
  a[:,:,3]=np.where(keep,alpha,0).astype('uint8');im=Image.fromarray(a)
  b=im.getbbox();b=(max(0,b[0]-10),max(0,b[1]-10),min(im.width,b[2]+10),min(im.height,b[3]+10));im=im.crop(b)
  im.save(ROOT/'refs'/f'{id}.png');mask=im.getchannel('A');mask.save(ROOT/'masks'/f'{id}_alpha.png');mask.point(lambda v:255 if v>=128 else 0).save(ROOT/'masks'/f'{id}_silhouette.png')
  source=PROJECT/evidence[id];out=ROOT/'evidence'/f'{id}.jpg';shutil.copy2(source,out)
  items.append(dict(id=id,name=names[id],variant='generated_documentary_concept',reference=f'refs/{id}.png',alpha=f'masks/{id}_alpha.png',silhouette=f'masks/{id}_silhouette.png',source_sheet=f'sheets/{g["id"]}.png',source_dimensions=[w,h],sheet_crop=bounds,trim=b,dimensions=im.size,materials=assign[id],evidence=dict(file=f'evidence/{id}.jpg',source=evidence[id],type='actual production in-engine capture of Blender-authored geometry; not an offline Blender render'),registration='Alpha and silhouette are pixel registered to generated reference only; not to production mesh, UVs or evidence camera.',sha256=hashlib.sha256((ROOT/'refs'/f'{id}.png').read_bytes()).hexdigest()))
materials={}
for name in sorted(set(sum(assign.values(),[]))):
 s=specs[name];record=dict(production_parameters=s,maps={})
 for kind in ['baseColor','roughnessMap','normal']:
  if kind not in s:continue
  source=TEX/s[kind];assert source.exists(),source
  out=ROOT/'samples'/source.name;shutil.copy2(source,out)
  record['maps'][kind]=dict(file=f'samples/{source.name}',production_source=os.path.relpath(source,PROJECT).replace('\\','/'),dimensions=Image.open(out).size,sha256=hashlib.sha256(out.read_bytes()).hexdigest())
 if name in ['Quilt_Ripstop','Quilt_Lining','Curtain_Acoustic','Berth_Bias_Tape']:
  asset='terlenka' if name in ['Quilt_Ripstop','Quilt_Lining'] else 'denim_fabric_06'
  record['provenance']=dict(source=f'https://polyhaven.com/a/{asset}',license='CC0',recipe='source/gravity_finishes.py: measured_cloth; retinted captured yarn, source roughness/normal; Quilt_Ripstop adds authored paired-yarn reinforcement at 5.4 mm pitch.')
 else:record['provenance']=dict(recipe='Existing production material definition and image maps, copied byte-for-byte. No claim that these finishes are measured aerospace samples. Analytic materials intentionally have no image maps.')
 materials[name]=record
manifest=dict(count=8,generation='Built-in ImageGen; four two-object sheets plus two targeted mechanical corrections',generated_variants=8,offline_blender_render_variants=0,production_capture_evidence=8,items=items,materials=materials,limitations=['Generated assembly details are conceptual; production geometry and simulation remain authoritative.','Native returned sheets measure 1254 by 1254 pixels. Crops retain their native resolution.','The 77% cell fill comes from the production simulation.','Glass alpha records image coverage.'])
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
canvas=Image.new('RGB',(1600,1480),(21,28,30));d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
d.text((24,17),'UPWELL / CABIN LOADS AND SOFT FITTINGS',font=font,fill=(232,235,227));d.text((24,49),'GENERATED DOCUMENTARY CONCEPTS — PRODUCTION EVIDENCE AND ACTUAL MAPS PACKAGED SEPARATELY',font=small,fill=(136,177,173))
for j,item in enumerate(items):
 x=20+(j%4)*395;y=90+(j//4)*690;im=Image.open(ROOT/item['reference']);im.thumbnail((370,615),Image.Resampling.LANCZOS);canvas.paste(im,(x+(370-im.width)//2,y+(615-im.height)//2),im)
 d.text((x,y+628),item['name'],font=small,fill=(235,237,229));d.text((x,y+653),item['id'],font=small,fill=(130,170,165))
canvas.save(ROOT/'contact-sheet.jpg',quality=94)
for item in items:
 im=Image.open(ROOT/item['reference']);a=np.array(Image.open(ROOT/item['alpha']));b=np.array(Image.open(ROOT/item['silhouette']))
 assert np.array_equal(np.array(im.getchannel('A')),a) and np.array_equal(a>=128,b>0)
 assert (a==0).sum()>100 and (a>=128).sum()>10000
report=dict(status='passed',reference_count=8,alpha_masks=8,silhouette_masks=8,source_sheets=4,evidence_captures=8,production_maps=len(list((ROOT/'samples').glob('*'))),alpha_registration=True,all_map_paths_verified=True,dimensions={x['id']:x['dimensions'] for x in items})
(ROOT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
