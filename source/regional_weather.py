"""Reproject NOAA GOES-19 physical retrievals to an Atlantic weather tile.

Channels are scalar optical depth, cloud-top height, and detected cloud cover.
No radiance/scene color is used to render the sky. Source ODs are dimensionless.
"""
from pathlib import Path
import io
import json
import hashlib
import sys
import urllib.request

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"source"/".weather-tools"))
import h5py

SOURCE=ROOT/"art"/"weather-source"
OUT=ROOT/"web"/"assets"/"planet"
BUCKET="https://noaa-goes19.s3.amazonaws.com/"
FILES={
    "COD":"ABI-L2-CODF/2025/182/15/OR_ABI-L2-CODF-M6_G19_s20251821500211_e20251821509520_c20251821514310.nc",
    "HT":"ABI-L2-ACHAF/2025/182/15/OR_ABI-L2-ACHAF-M6_G19_s20251821500211_e20251821509520_c20251821513110.nc",
}
EXTENT=(-57.,-15.,-15.,15.)  # west, east, south, north

def sample(file,band):
    with h5py.File(file,"r") as f:
        pr=f["goes_imager_projection"].attrs
        a=float(pr["semi_major_axis"][0]);b=float(pr["semi_minor_axis"][0])
        sat=float(pr["perspective_point_height"][0])+a;lon0=float(pr["longitude_of_projection_origin"][0])
        x=f["x"];y=f["y"]
        def ax(v):
            return np.asarray(v,dtype=np.float64)*float(v.attrs.get("scale_factor",[1])[0])+float(v.attrs.get("add_offset",[0])[0])
        xx,yy=ax(x),ax(y)
        west,east,south,north=EXTENT
        la=np.deg2rad(np.linspace(north,south,1596,endpoint=False)+((south-north)/1596)/2)[:,None]
        lo=np.deg2rad(np.linspace(west,east,2240,endpoint=False)+((east-west)/2240)/2-lon0)[None,:]
        geo=np.arctan((b/a)**2*np.tan(la));rc=b/np.sqrt(1-(1-b*b/(a*a))*np.cos(geo)**2)
        sx=sat-rc*np.cos(geo)*np.cos(lo);sy=-rc*np.cos(geo)*np.sin(lo);sz=rc*np.sin(geo)
        scanx=np.arcsin(-sy/np.sqrt(sx*sx+sy*sy+sz*sz));scany=np.arctan2(sz,sx)
        ix=(scanx-xx[0])/(xx[1]-xx[0]);iy=(scany-yy[0])/(yy[1]-yy[0])
        ds=f[band];raw=np.asarray(ds);fill=ds.attrs.get("_FillValue",[65535])[0]
        good=raw!=fill
        actual=raw.astype("float32")*float(ds.attrs.get("scale_factor",[1])[0])+float(ds.attrs.get("add_offset",[0])[0])
        actual[~good]=0
        value=map_coordinates(actual,[iy,ix],order=1,mode="constant",cval=0,prefilter=False)
        coverage=map_coordinates(good.astype("float32"),[iy,ix],order=1,mode="constant",cval=0,prefilter=False)
        print(band,raw.shape,ds.attrs.get("units"),np.percentile(value,[5,50,90,99]),flush=True)
        return value,coverage

if __name__=='__main__':
    SOURCE.mkdir(parents=True,exist_ok=True);maps={};receipts={}
    for kind,key in FILES.items():
        file=SOURCE/(kind+".nc");url=BUCKET+key
        if not file.exists():
            with urllib.request.urlopen(url,timeout=90) as r:file.write_bytes(r.read())
        receipts[kind]={"url":url,"sha256":hashlib.sha256(file.read_bytes()).hexdigest()}
        maps[kind]=sample(file,kind)
    tau,cloud=maps["COD"];height,_=maps["HT"]
    data=np.stack((np.log1p(np.clip(tau,0,80))/np.log(81),np.clip(height/18000,0,1),np.clip(cloud,0,1)),axis=-1)
    Image.fromarray(np.uint8(np.clip(data,0,1)*255)).save(OUT/"atlantic-weather.png",optimize=True)
    receipt={"source":"NOAA GOES-19 ABI, archived July 1, 2025 15:00 UTC","extentWestEastSouthNorth":EXTENT,"fields":receipts,
        "usage":"Independent scalar fields for optical extinction and cloud height; local advection and evolving 3D structure are simulated. This is not a current weather feed.",
        "catalog":"https://registry.opendata.aws/noaa-goes/","product":"https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc%3AC01508/html"}
    (OUT/"regional-sources.json").write_text(json.dumps(receipt,indent=2),encoding="utf8")
