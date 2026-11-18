"""A small physically scaled unidirectional tow / twill finish for the visible tether."""
from pathlib import Path
import json
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[1]
dest=root/"unity"/"Assets"/"Upwell"/"Guideway"/"Textures";dest.mkdir(parents=True,exist_ok=True)
size=512;x,y=np.meshgrid(np.arange(size),np.arange(size));gen=np.random.default_rng(7981)
warp=np.cos((x+y)*2*np.pi/16);weft=np.cos((x-y)*2*np.pi/16)
swap=((x//16+y//16)%2)*2-1
relief=(warp*(.46+.32*swap)+weft*(.49-.33*swap))*.64+gen.normal(0,.15,(size,size))
color=np.array([49,56,58])[None,None,:]+relief[:,:,None]*10
norm=np.stack((-(np.roll(relief,-1,1)-np.roll(relief,1,1))*.31,(np.roll(relief,-1,0)-np.roll(relief,1,0))*.31,np.ones_like(relief)),axis=2)
norm/=np.linalg.norm(norm,axis=2,keepdims=True)
for nm,im in (("Tow_Carbon_Color",color),("Tow_Carbon_Normal",(norm*.5+.5)*255),("Tow_Carbon_Roughness",100+relief*17)):
    Image.fromarray(np.uint8(im.clip(0,255))).save(dest/(nm+".jpg"),quality=88)
(dest/"materials.json").write_text(json.dumps({"Tow_Carbon":{"rgb":[49,56,58],"metallic":.42,"roughness":.39,"alpha":1,
    "baseColor":"Tow_Carbon_Color.jpg","normal":"Tow_Carbon_Normal.jpg","roughnessMap":"Tow_Carbon_Roughness.jpg"}},indent=2))
