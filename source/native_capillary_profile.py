"""Nine-section free-surface model of the sealed inspection cell, in metres.

The gas boundary is the area of intersection of two disks at each depth.
The second disk moves along the load vector. Its radius is solved for the
fixed gas charge. This is the equilibrium construction used by both players.
"""
from functools import lru_cache
import math

import numpy as np

N=128
LEVELS=(-28.,-6.,-2.,-1.,-.5,-.25,0.,.25,.5,1.,2.,6.,28.)
R=.102;DEPTH=.022;WALL=.00025;PANE=.00016;GAS=.23
CORE=R-WALL;HALF=DEPTH/2-PANE

def signed_reach(accel_g):
    bond=997*9.80665*R*R*abs(accel_g)/.072
    return math.copysign(-28*math.expm1(-bond/85),accel_g)

def shared_area(d,r):
    if d>=1+r:return 0.
    if d<=abs(1-r):return math.pi*min(1,r*r)
    a=np.clip((d*d+1-r*r)/(2*d),-1,1);b=np.clip((d*d+r*r-1)/(2*d*r),-1,1)
    return math.acos(a)+r*r*math.acos(b)-.5*math.sqrt(max(0,(-d+1+r)*(d+1-r)*(d-1+r)*(d+1+r)))

def area_radius(d,fraction):
    if d+math.sqrt(fraction)<=1:return math.sqrt(fraction)
    low=max(0,d-1);high=d+1
    for _ in range(34):
        r=(low+high)*.5
        if shared_area(d,r)<math.pi*fraction:low=r
        else:high=r
    return (low+high)*.5

@lru_cache(maxsize=24)
def boundary(reach):
    direction=np.arange(N)*math.tau/N;dirs=np.stack((np.cos(direction),np.sin(direction)),axis=-1)
    center=np.array((.008/R,.0036/R+reach));d=np.linalg.norm(center);axis=center/max(1e-12,d)
    axial=np.linspace(-1,1,9);profile=.85+.15*np.sqrt(np.maximum(0,1-axial**2))
    weights=np.array([.5,1,1,1,1,1,1,1,.5])/8
    fraction=GAS/((CORE/R)**2*(HALF*2/DEPTH));fractions=profile*fraction/(weights@profile)
    section=[];outer=[];centroids=[]
    for f in fractions:
        r=area_radius(d,f)
        # Use an interior ray origin on the line of centres. Every radial
        # interval is then single-valued, even for a gas cap near the wall.
        start=((max(-1,d-r)+min(1,d+r))*.5)*axis
        def far(c,rad):
            v=start-c;dot=dirs@v
            return -dot+np.sqrt(np.maximum(0,dot**2+rad*rad-v@v))
        distance=np.minimum(far(np.zeros(2),1.),far(center,r))
        section.append((start+dirs*distance[:,None])*CORE)
        outer.append((start+dirs*far(np.zeros(2),R/CORE)[:,None])*CORE)
        centroids.append(start*CORE)
    return np.array(section),np.array(outer),np.array(centroids)

def points(reach,mapping):
    """Evaluate a material-bound vertex table. Columns are category, depth
    plane, spoke, radial interpolation, and axial clearance in metres."""
    tags=np.asarray(mapping);kind,level,ray=tags[:,:3].astype(int).T;ray%=N
    f=tags[:,3:4];gas,outer,center=boundary(reach);boundary_pts=gas[level,ray]
    xy=np.where((kind==0)[:,None],boundary_pts+(outer[level,ray]-boundary_pts)*f,
                center[level]+(boundary_pts-center[level])*f)
    h=(level/4-1)*HALF+tags[:,4]
    return np.column_stack((xy,h))

def gas_fraction(reach):
    rings,_,_=boundary(reach);d=np.roll(rings,-1,axis=1)
    areas=.5*np.abs((rings[:,:,0]*d[:,:,1]-d[:,:,0]*rings[:,:,1]).sum(axis=1))
    integral=(.5*areas[0]+areas[1:-1].sum()+.5*areas[-1])*HALF/4
    return integral/(math.pi*R*R*DEPTH)
