"""Reproducible tileable PBR surface studies and alpha-derived reference masks."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
PROPS=[p for r in json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['rooms'] for p in r['props']]
# Base-color sRGB, roughness, material family. Primary surface only.
MATS={
'pilot_console':((223,229,229),.32,'aramid'),'nav_screen':((12,20,25),.10,'glass'),
'ascent_lever':((130,140,145),.28,'metal'),'window':((160,184,192),.05,'glass'),
'roller_shade':((35,42,47),.57,'fabric'),'lounge_seat':((42,49,55),.78,'fabric'),
'lamp':((231,237,238),.22,'glass'),'field_glasses':((30,37,43),.48,'carbon'),
'bunk':((45,52,57),.81,'fabric'),'privacy_curtain':((183,193,198),.73,'fabric'),
'locker_drawer':((221,229,229),.34,'aramid'),'access_card':((16,23,29),.28,'laminate'),
'reading_lamp':((147,157,163),.27,'metal'),'logbook':((20,28,34),.20,'glass'),
'mug':((223,230,230),.28,'aramid'),'grab_handle':((124,137,145),.30,'metal'),
'pressure_hatch':((223,230,230),.33,'aramid'),'card_reader':((17,25,31),.16,'glass'),
'service_cabinet':((219,227,229),.34,'aramid'),'breaker':((128,140,147),.28,'metal'),
'pressure_gauge':((130,141,147),.26,'metal'),'intercom':((222,230,231),.34,'aramid'),
'tool_roll':((35,43,49),.80,'fabric'),'docking_wheel':((29,37,43),.42,'carbon')}

def generate_maps():
    dest=ROOT/'textures';dest.mkdir(exist_ok=True)
    n=512;y,x=np.mgrid[:n,:n];out=[]
    for p in PROPS:
        id=p['id']; rgb,rough,family=MATS[id]
        rng=np.random.default_rng(int(hashlib.sha256(id.encode()).hexdigest()[:8],16))
        field=np.zeros((n,n));micro=rng.normal(0,1,(n,n))
        for k in range(20):
            fx,fy=rng.integers(-16,17,2);field+=np.sin((x*fx+y*fy)*2*np.pi/n+rng.uniform(0,6.28))/(1+abs(fx)+abs(fy))
        field/=max(field.std(),.001)
        h=field*.008+micro*.006
        color=np.array(rgb,dtype=float)[None,None,:]+field[:,:,None]*.45+micro[:,:,None]*.35
        roughmap=np.full((n,n),rough)+field*.006+micro*.003
        if family=='fabric':
            weave=(np.cos(x*2*np.pi/4)+np.cos(y*2*np.pi/4))*.5
            h+=weave*.14;color+=weave[:,:,None]*4;roughmap+=weave*.015
        elif family=='rubber':
            grain=(np.sin(x*2*np.pi/8)*np.sin(y*2*np.pi/8))
            h+=grain*.06;color+=grain[:,:,None]*1.5
        elif family=='carbon':
            warp=(np.floor(x/8)+np.floor(y/8))%2
            weave=np.where(warp<1,np.sin(x*2*np.pi/4),np.sin(y*2*np.pi/4))
            h+=weave*.035;color+=weave[:,:,None]*2;roughmap+=weave*.025
        elif family=='aramid':
            h*=.25
        elif family=='metal':
            brush=np.sin(y*2*np.pi/2)+np.sin(y*2*np.pi/8)*.4
            h+=brush*.022;color+=brush[:,:,None]*2.5
        elif family=='enamel':
            # Isolated small paint pits on the material study, not baked edge wear.
            pits=field < -2.6
            color[pits]=np.array([75,70,58])+micro[pits,None]*2
            h[pits]-=.08;roughmap[pits]=.78
        elif family=='glass':
            h*=.02;color=np.array(rgb)[None,None,:]+field[:,:,None]*.45;roughmap=np.full((n,n),rough)+field*.003
        dx=(np.roll(h,-1,1)-np.roll(h,1,1))*.5
        dy=(np.roll(h,-1,0)-np.roll(h,1,0))*.5
        normal=np.stack([-dx,-dy,np.ones_like(h)],2);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
        for name,a in [('basecolor',color),('roughness',np.clip(roughmap,0,1)*255),('normal',(normal*.5+.5)*255)]:
            Image.fromarray(np.uint8(np.clip(a,0,255))).save(dest/f'{id}_{name}.png')
        out.append({'id':id,'primary_surface':p['surface'],'family':family,'base_color_srgb':rgb,'roughness':rough,'dimensions':[n,n],'normal_convention':'OpenGL tangent space +Y','source':'deterministic procedural tile; not measured or photo-reconstructed','physical_tile_m':.25 if family=='fabric' else .5,'metallic':1 if family=='metal' else 0,'glass_note':'Set transmission in shader; basecolor is tinted surface study, not opacity.' if family=='glass' else None})
    (dest/'materials.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    sheet=Image.new('RGB',(1440,1200),(32,37,35));d=ImageDraw.Draw(sheet)
    for i,m in enumerate(out):
        x=(i%6)*240;y=(i//6)*300;id=m['id']
        for suffix,size,offset in [('basecolor',(200,150),(20,20)),('roughness',(90,90),(20,180)),('normal',(90,90),(130,180))]:
            a=Image.open(dest/f'{id}_{suffix}.png').resize(size)
            sheet.paste(a,(x+offset[0],y+offset[1]))
        d.text((x+20,y+278),id,fill=(230,220,200))
    sheet.save(ROOT/'surface-contact-sheet.jpg',quality=94)

def masks_and_sheet():
    dest=ROOT/'masks';dest.mkdir(exist_ok=True)
    sheet=Image.new('RGB',(1440, len(PROPS)//4*300),(32,37,35));d=ImageDraw.Draw(sheet)
    status=[]
    for i,p in enumerate(PROPS):
        id=p['id'];f=ROOT/'refs'/f'{id}.png';x=(i%4)*360;y=(i//4)*300
        d.text((x+12,y+272),id,fill=(232,225,207))
        if not f.exists():status.append({'id':id,'status':'pending'});continue
        im=Image.open(f).convert('RGBA');alpha=im.getchannel('A')
        lo,hi=alpha.getextrema()
        if lo==255:status.append({'id':id,'status':'opaque-source-mask-unavailable'});continue
        alpha.save(dest/f'{id}_alpha.png')
        alpha.point(lambda v:255 if v>=128 else 0).save(dest/f'{id}_silhouette.png')
        im.thumbnail((336,252));sheet.paste(im,(x+(360-im.width)//2,y+(260-im.height)//2),im)
        status.append({'id':id,'status':'complete','reference':f'refs/{id}.png','mask':f'masks/{id}_silhouette.png','alpha':f'masks/{id}_alpha.png','mask_source':'actual generated alpha, threshold 128; includes visible transparent glass alpha','size':Image.open(f).size})
    sheet.save(ROOT/'contact-sheet.jpg',quality=94)
    (ROOT/'reference-status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    print(f"{sum(s['status']=='complete' for s in status)}/{len(PROPS)} reference/mask pairs complete")

if __name__=='__main__':
    generate_maps();masks_and_sheet()
