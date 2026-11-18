"""Equatorial carriage load at altitude, including finite-jerk drive and brake.

Matches the SI force calculation in the web and Unity players. Native frame
time uses the surveyed six-minute trip schedule in ascent_geometry.py.
"""
import math

G=9.80665;R=6378137.;MU=3.986004418e14;OMEGA=7.292115e-5
DISTANCE=35786000.;CRUISE=170.

def drive_at(distance,acceleration,transition):
    total=CRUISE/acceleration+transition
    if distance<=0:return 0.
    if distance>=CRUISE*total/2:return 0.
    jerk=acceleration/transition
    def sample(t):
        if t<transition:return jerk*t**3/6,jerk*t
        remain=total-t
        if remain<transition:return CRUISE*total/2-CRUISE*remain+jerk*remain**3/6,jerk*remain
        steady=t-transition
        return jerk*transition**3/6+(.5*acceleration*transition)*steady+.5*acceleration*steady**2,acceleration
    a,b=0.,total
    for _ in range(32):
        m=(a+b)*.5
        if sample(m)[0]<distance:a=m
        else:b=m
    return sample((a+b)*.5)[1]

def signed_load(km):
    h=min(DISTANCE,max(0.,km*1000));r=R+h
    drive=drive_at(h,.30,4)-drive_at(DISTANCE-h,.14,7)
    return (MU/r**2-OMEGA**2*r+drive)/G
