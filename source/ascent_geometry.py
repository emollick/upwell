"""Native sampling of the six-minute ride used by the browser and Unity."""
import math

FLIGHT=((0,0),(9,0),(12,.0025),(16,.012),(22,.040),(32,.150),(44,.55),(58,1.48),
 (75,3.35),(92,6.4),(108,12),(135,35),(154,100),(184,660),(213,3900),(244,12600),
 (267,22500),(290,32000),(305,35500),(315,35780),(323,35785.820),(330,35785.905),
 (339,35785.954),(345,35785.979),(351,35785.994),(360,35786))
def height(t):
    if t<=0:return 0.
    if t>=360:return 35786.
    def slope(k):
        if k==0 or k==len(FLIGHT)-1:return 0.
        ta,ha=FLIGHT[k-1];tb,hb=FLIGHT[k];tc,hc=FLIGHT[k+1]
        p=(hb-ha)/(tb-ta);q=(hc-hb)/(tc-tb)
        if p*q<=0:return 0.
        a=2*(tc-tb)+(tb-ta);b=(tc-tb)+2*(tb-ta)
        return (a+b)/(a/p+b/q)
    i=next(i for i in range(len(FLIGHT)-1) if FLIGHT[i+1][0]>t)
    a,p=FLIGHT[i];b,q=FLIGHT[i+1];d=b-a;u=(t-a)/d;u2=u*u;u3=u2*u
    return (2*u3-3*u2+1)*p+(u3-2*u2+u)*d*slope(i)+(-2*u3+3*u2)*q+(u3-u2)*d*slope(i+1)
def sun_at(h):
    angle=((6.58+h/612)/24-.5)*2*math.pi;dec=math.radians(-12)
    return (-math.cos(dec)*math.sin(angle),math.cos(dec)*math.cos(angle),math.sin(dec))
def frame_at(t):return 1+269*t/360
