"""Small, inexpensive geometry primitives for the clockwork sports arenas."""
import math
import pygame


def blend(a,b,t):
    return tuple(round(x+(y-x)*t) for x,y in zip(a,b))


def polygon_ring(surface,center,radius,thickness,color,angle=0.,squash=1.,segments=64):
    """An actual filled annulus, also usable as a perspective floor platform."""
    x,y=center
    outer=[]
    inner=[]
    for i in range(segments+1):
        a=i*math.tau/segments+angle
        outer.append((x+math.sin(a)*radius,y+math.cos(a)*radius*squash))
        inner.append((x+math.sin(a)*(radius-thickness),y+math.cos(a)*(radius-thickness)*squash))
    for i in range(segments):
        shade=.82+.18*math.cos(i*math.tau/segments-.7)
        c=tuple(round(v*shade) for v in color)
        pygame.draw.polygon(surface,c,[outer[i],outer[i+1],inner[i+1],inner[i]])


def prism(surface,rect,color,depth=15,edge=None):
    """Extruded wall panels with separate top, side, frame and inset faces."""
    r=pygame.Rect(rect)
    if r.width<2 or r.height<2:
        return
    dx=max(3,depth*.65)
    dy=-max(3,depth)
    tl,tr,br,bl=r.topleft,r.topright,r.bottomright,r.bottomleft
    back=lambda p:(p[0]+dx,p[1]+dy)
    pygame.draw.polygon(surface,blend(color,(255,241,211),.22),[tl,tr,back(tr),back(tl)])
    pygame.draw.polygon(surface,blend(color,(5,13,29),.52),[tr,br,back(br),back(tr)])
    pygame.draw.rect(surface,blend(color,(5,13,29),.48),r,border_radius=4)
    inset=r.inflate(-max(4,r.width*.035),-max(4,r.height*.08))
    pygame.draw.rect(surface,blend(color,(15,28,39),.28),inset,border_radius=3)
    pygame.draw.rect(surface,edge or color,r,max(1,min(4,round(depth/7))),border_radius=4)
    pygame.draw.line(surface,blend(color,(255,255,244),.6),tl,tr,2)
    if r.width>36 and r.height>28:
        for p in (r.topleft,r.topright,r.bottomleft,r.bottomright):
            x=p[0]+(6 if p[0]==r.left else -6)
            y=p[1]+(6 if p[1]==r.top else -6)
            pygame.draw.circle(surface,(9,23,32),(round(x),round(y)),2)


def chevron(surface,center,size,color,direction=1,width=3):
    x,y=center
    pygame.draw.lines(surface,color,False,[(x-direction*size*.4,y-size),(x+direction*size*.4,y),(x-direction*size*.4,y+size)],width)


def shield(surface,center,size,color,filled=True):
    x,y=center
    points=[(x,y-size),(x+size*.78,y-size*.6),(x+size*.58,y+size*.3),(x,y+size),(x-size*.58,y+size*.3),(x-size*.78,y-size*.6)]
    pygame.draw.polygon(surface,color,points,0 if filled else 2)
    if filled and size>6:
        pygame.draw.line(surface,blend(color,(255,255,255),.5),(x-size*.42,y-size*.45),(x,y-size*.65),1)
