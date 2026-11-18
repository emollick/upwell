"""The visible quilt and its fixed restraint rails share this measured rest surface."""
import math

QUILT_X=(-2.086,-1.282)
QUILT_Z=(-.605,1.013)
QUILT_BELTS=(-.461,.533)

def quilt_seam(x,index):
    # Real sewn baffles are continuous across the berth. Their slightly bowed
    # centre lines allow long, soft folds without a pointed diamond-grid cusp.
    across=(x-QUILT_X[0])/(QUILT_X[1]-QUILT_X[0]);a=math.pi*across
    return -.677+index*.235+.014*math.sin(index*1.45)+.041*math.sin(a+.32*index)+.014*math.sin(2*a-.41*index)

def quilt_height(x,z):
    def ease(t):
        t=max(0.,min(1.,t));return t*t*(3.-2.*t)
    # The overstitched, turned hem stays near the mattress instead of tracing
    # the baffle crests at every edge. Let independent radii meet at corners.
    dx=min(x-QUILT_X[0],QUILT_X[1]-x);dz=min(z-QUILT_Z[0],QUILT_Z[1]-z)
    interior=ease(dx/.079)*ease(dz/.083)
    i=math.floor((z+.677)/.235)
    closest=min(abs(z-quilt_seam(x,j)) for j in range(i-1,i+3))
    # A broad, rounded seam profile resolves under close grazing light. Slow
    # loft and bias wrinkles keep adjacent cotton-filled chambers asymmetric.
    tuck=.0178*math.exp(-(closest/.028)**2)
    bias=.0041*math.sin(19*x+8.8*z+1.7*math.sin(z*5))+.0028*math.sin(10.5*x-11.7*z)
    bias+=.0016*math.sin(30*x+18*z+.8*math.cos(z*7))
    crown=.9858-tuck+bias
    rim=.948+.0015*math.sin(23*z+4*x)+.0010*math.cos(12*x-9*z)
    return rim+(crown-rim)*interior
