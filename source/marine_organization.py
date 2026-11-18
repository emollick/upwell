"""Periodic scalar boundary conditions for the marine cloud volume.

R distinguishes rainy open-cell interiors and closed stratiform cells, G measures
local updraft strength, B is the wind-parallel breakup of cell walls, and A is
mesoscale moisture. Every altitude, density and optical path is evaluated live.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

root = Path(__file__).resolve().parents[1]
n = 256
rng = np.random.default_rng(4017)

def turbulence(width_u, width_v):
    a = gaussian_filter(rng.standard_normal((n,n)), (width_v,width_u), mode="wrap")
    return a / np.std(a)

def ramp(a,b,x):
    t = np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)

v,u = (np.indices((n,n))+.5)/n
wet = turbulence(53,35)*.84 + turbulence(18,12)*.22
warp_u = .034*turbulence(21,15) + .011*turbulence(8,6) + .003*turbulence(2.7,3.3)
warp_v = .041*turbulence(26,17) + .013*turbulence(12,8) + .0037*turbulence(3.3,2.1)
air = np.stack(((u+warp_u)%1,(v+warp_v)%1),axis=-1)

def cell_network(count):
    seeds = rng.random((count,2))
    dist, ids = cKDTree(seeds, boxsize=1).query(air,k=3)
    spacing = 1/np.sqrt(count)
    trench = (dist[:,:,1]-dist[:,:,0])/spacing
    junction = (dist[:,:,2]-dist[:,:,0])/spacing
    return trench,junction,rng.uniform(0,1,count)[ids[:,:,0]]

trench, junction, family = cell_network(74)
twigs, j2, storm = cell_network(309)
rolls = .54*turbulence(13,2.8)+.29*turbulence(6.4,1.5)+.17*turbulence(2.,.85)
small = .61*turbulence(4.8,3.9)+.27*turbulence(2.3,1.5)+.12*turbulence(.75,.72)
# Dry, evaporatively cooled centres are broad. Walls are thicker in a moister
# air mass; profiles branch and merge instead of stamping isolated billow shapes.
open_cell = 1-ramp(.045+.036*rolls,.48+.09*wet+.049*small,trench)
closed_cell = .73+.13*rolls+.10*small-.32*np.exp(-np.maximum(0,trench)*13)
regime = ramp(-.73,.67,wet+.21*small)
fraction = (1-regime)*(.12+.91*open_cell) + regime*closed_cell
fraction += .14*(1-ramp(.025,.35,twigs))+.10*rolls+.052*small-.095
draft = .34+.44*(1-ramp(.07,.79,junction))+.22*(1-ramp(.03,.46,twigs))
draft += .12*rolls+.11*small+.07*storm
# A large, subsiding humid sector caps the thermals. The darkest offshore
# sector supports sparse wet cell walls and broad, continuous clear-water gaps.
quiet = ramp(.19,1.04,wet)
dry = 1-ramp(-.83,-.27,wet)
slow = turbulence(15,9)
fraction += quiet*(.83+.088*slow+.03*small-fraction)-.22*dry*(1-open_cell)
draft += quiet*(.58+.115*slow+.07*rolls-draft)*.76
breakup = .50+.22*rolls+.105*small+.09*np.sin((u+warp_u*.9)*2*np.pi*3)
moisture = .51+.23*wet+.10*turbulence(12,9)+.036*rolls
data = np.uint8(np.rint(255*np.clip(np.stack((fraction,draft,breakup,moisture),axis=-1),0,1)))
for out in [root/'web/assets/planet/marine-organization.rgba',root/'unity/Assets/Upwell/Resources/MarineOrganization.bytes']:
    out.write_bytes(data.tobytes())
